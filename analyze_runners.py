import os
import csv
import time
import requests
from datetime import datetime, timezone

CSV_RUNNERS = "runner_patterns.csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

HEADERS_RUNNERS = [
    "timestamp", "symbol", "token_address", "pair_address", "dex",
    "age_hours", "gain_24h_pct", "mcap_usd", "liquidity_usd", "vol_24h_usd",
    "first_hour_max_gain_pct", "deepest_dip_pct", "top10_holder_pct",
    "jup_price_impact_pct", "rugcheck_score"
]

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
WSOL_MINT = "So11111111111111111111111111111111111111112"

def init_csv():
    if not os.path.exists(CSV_RUNNERS):
        with open(CSV_RUNNERS, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS_RUNNERS)

# --- 1. GECKOTERMINAL: HISTORISCHE 1M-KERZEN (SPIKE & DIP) ---
def get_gecko_ohlcv_pattern(pool_address):
    url = f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool_address}/ohlcv/minute?limit=60"
    headers = {"Accept": "application/json;version=20230302"}
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code != 200:
            return 0.0, 0.0
        data = res.json()
        ohlcv_list = data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
        if not ohlcv_list:
            return 0.0, 0.0

        ohlcv_list.reverse() # chronologisch
        open_price = float(ohlcv_list[0][1])
        if open_price <= 0:
            return 0.0, 0.0

        peak = max(float(c[2]) for c in ohlcv_list)
        lowest = min(float(c[3]) for c in ohlcv_list)

        max_gain = ((peak - open_price) / open_price) * 100.0
        max_drawdown = ((lowest - peak) / peak) * 100.0
        return round(max_gain, 1), round(max_drawdown, 1)
    except Exception:
        return 0.0, 0.0

# --- 2. SOLANA ON-CHAIN RPC: TOP 10 HOLDER ANTEIL ---
def get_onchain_holder_concentration(token_mint):
    try:
        headers = {"Content-Type": "application/json"}
        # Supply abfragen
        supply_payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getTokenSupply",
            "params": [token_mint]
        }
        r_sup = requests.post(SOLANA_RPC_URL, json=supply_payload, headers=headers, timeout=5).json()
        total_supply = float(r_sup.get("result", {}).get("value", {}).get("uiAmount") or 0.0)

        if total_supply <= 0:
            return 0.0

        # Top 20 Accounts abfragen
        accounts_payload = {
            "jsonrpc": "2.0", "id": 2,
            "method": "getTokenLargestAccounts",
            "params": [token_mint]
        }
        r_acc = requests.post(SOLANA_RPC_URL, json=accounts_payload, headers=headers, timeout=5).json()
        accounts = r_acc.get("result", {}).get("value", [])

        # Top 10 addieren
        top10_sum = sum(float(a.get("uiAmount") or 0.0) for a in accounts[:10])
        pct = (top10_sum / total_supply) * 100.0
        return round(pct, 1)
    except Exception:
        return 0.0

# --- 3. JUPITER AGGREGATOR: ECHTER PRICE IMPACT TEST (0.25 SOL BUY) ---
def get_jupiter_price_impact(token_mint):
    try:
        # 0.25 SOL in Lamports = 250,000,000
        url = f"https://quote-api.jup.ag/v6/quote?inputMint={WSOL_MINT}&outputMint={token_mint}&amount=250000000&slippageBps=100"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            impact = float(data.get("priceImpactPct") or 0.0)
            return round(impact, 2)
    except Exception:
        pass
    return -1.0 # Wenn nicht über Jupiter routing-fähig

# --- 4. RUGCHECK: SECURITY AUDIT ---
def audit_runner(token_addr):
    try:
        r = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{token_addr}/report/summary", timeout=5)
        if r.status_code == 200:
            return r.json().get("score", 0)
    except Exception:
        pass
    return "N/A"

# --- 5. DEXSCREENER: SCOUTING & BATCHING ---
def get_top_solana_runners():
    headers = {"User-Agent": "Mozilla/5.0"}
    discovered = []
    
    endpoints = [
        "https://api.dexscreener.com/token-boosts/top/v1",
        "https://api.dexscreener.com/token-boosts/latest/v1",
    ]
    tokens = set()
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                for item in r.json():
                    if item.get("chainId") == "solana":
                        addr = item.get("tokenAddress")
                        if addr:
                            tokens.add(addr)
        except Exception:
            pass

    token_list = list(tokens)[:60]
    now_ts = datetime.now(timezone.utc).timestamp()
    
    for i in range(0, len(token_list), 30):
        batch = token_list[i:i+30]
        try:
            b_res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{','.join(batch)}", timeout=6)
            if b_res.status_code != 200:
                continue
            pairs = b_res.json().get("pairs") or []
            for p in pairs:
                if p.get("chainId") != "solana":
                    continue
                
                dex_id = p.get("dexId", "").lower()
                quote = p.get("quoteToken", {}).get("symbol", "").upper()
                if dex_id not in ["raydium", "meteora"] or quote not in ["SOL", "WSOL"]:
                    continue

                created_at = p.get("pairCreatedAt")
                if not created_at:
                    continue
                age_hours = (now_ts - (created_at / 1000.0)) / 3600.0
                if age_hours < 1.5 or age_hours > 48.0:
                    continue

                gain_24h = float(p.get("priceChange", {}).get("h24") or 0.0)
                if gain_24h < 200.0:
                    continue

                discovered.append({
                    "symbol": p.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "token_addr": p.get("baseToken", {}).get("address"),
                    "pair_addr": p.get("pairAddress"),
                    "dex": dex_id.upper(),
                    "age_h": round(age_hours, 1),
                    "gain_24h": gain_24h,
                    "mcap": float(p.get("fdv") or p.get("marketCap") or 0.0),
                    "liq": float(p.get("liquidity", {}).get("usd") or 0.0),
                    "vol_24h": float(p.get("volume", {}).get("h24") or 0.0),
                })
        except Exception:
            continue

    discovered.sort(key=lambda x: x["gain_24h"], reverse=True)
    return discovered[:5]

def save_and_report():
    init_csv()
    runners = get_top_solana_runners()
    if not runners:
        print("Keine Runner gefunden, die die Kriterien erfüllen.")
        return

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    fields_text = ""

    with open(CSV_RUNNERS, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for r in runners:
            # 1. GeckoTerminal OHLCV
            max_gain, deepest_dip = get_gecko_ohlcv_pattern(r["pair_addr"])
            time.sleep(0.5)

            # 2. Solana RPC Holder Concentration
            top10_holders = get_onchain_holder_concentration(r["token_addr"])

            # 3. Jupiter Price Impact
            price_impact = get_jupiter_price_impact(r["token_addr"])

            # 4. RugCheck Audit
            rc_score = audit_runner(r["token_addr"])

            writer.writerow([
                now_iso, r["symbol"], r["token_addr"], r["pair_addr"], r["dex"],
                r["age_h"], r["gain_24h"], r["mcap"], r["liq"], r["vol_24h"],
                max_gain, deepest_dip, top10_holders, price_impact, rc_score
            ])

            impact_str = f"{price_impact}%" if price_impact >= 0 else "Nicht geroutet"
            chart_url = f"https://dexscreener.com/solana/{r['pair_addr']}"
            fields_text += (
                f"🚀 **[{r['symbol']}]({chart_url})** ({r['dex']}) | **+{r['gain_24h']:,.0f}%**\n"
                f"• **Alter:** {r['age_h']}h | **MCap:** ${r['mcap']:,.0f} | **LP:** ${r['liq']:,.0f}\n"
                f"• **1h Launch-Spike:** +{max_gain}% | **Max-Dip:** {deepest_dip}%\n"
                f"• **Top 10 Holder:** {top10_holders}% Supply\n"
                f"• **Jup Price Impact (0.25 SOL):** {impact_str}\n"
                f"• **RugCheck-Score:** {rc_score}\n"
                f"───────────────────\n"
            )

    if DISCORD_WEBHOOK_URL:
        embed = {
            "title": "🔍 Deep On-Chain Pattern-Analyse (5-API Synthese)",
            "description": fields_text,
            "color": 0x6366F1,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)

if __name__ == "__main__":
    print("Starte Deep On-Chain Analyse...")
    save_and_report()
    print("Fertig. Daten in CSV gespeichert & Discord benachrichtigt.")
