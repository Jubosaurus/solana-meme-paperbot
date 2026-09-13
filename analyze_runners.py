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
    "first_hour_max_gain_pct", "deepest_dip_pct", "rugcheck_score"
]

def init_csv():
    if not os.path.exists(CSV_RUNNERS):
        with open(CSV_RUNNERS, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS_RUNNERS)

def get_gecko_ohlcv_pattern(pool_address):
    """Holt historische 1m-Kerzen über GeckoTerminal und analysiert den Launch."""
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

        # GeckoTerminal sortiert neueste zuerst -> umkehren für chronologischen Ablauf
        ohlcv_list.reverse()
        
        open_price = float(ohlcv_list[0][1])  # Open der ersten Kerze
        if open_price <= 0:
            return 0.0, 0.0

        peak_in_hour = max(float(candle[2]) for candle in ohlcv_list) # High
        lowest_in_hour = min(float(candle[3]) for candle in ohlcv_list) # Low

        max_gain = ((peak_in_hour - open_price) / open_price) * 100.0
        max_drawdown = ((lowest_in_hour - peak_in_hour) / peak_in_hour) * 100.0

        return round(max_gain, 1), round(max_drawdown, 1)
    except Exception:
        return 0.0, 0.0

def audit_runner(token_addr):
    try:
        r = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{token_addr}/report/summary", timeout=5)
        if r.status_code == 200:
            return r.json().get("score", 0)
    except Exception:
        pass
    return "N/A"

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
        print("Keine Runner gefunden.")
        return

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    fields_text = ""

    with open(CSV_RUNNERS, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for r in runners:
            # 1. GeckoTerminal OHLCV-Analyse
            max_gain, deepest_dip = get_gecko_ohlcv_pattern(r["pair_addr"])
            time.sleep(1) # Schonung des GeckoTerminal Rate-Limits
            
            # 2. RugCheck Audit
            rc_score = audit_runner(r["token_addr"])

            writer.writerow([
                now_iso, r["symbol"], r["token_addr"], r["pair_addr"], r["dex"],
                r["age_h"], r["gain_24h"], r["mcap"], r["liq"], r["vol_24h"],
                max_gain, deepest_dip, rc_score
            ])

            chart_url = f"https://dexscreener.com/solana/{r['pair_addr']}"
            fields_text += (
                f"🚀 **[{r['symbol']}]({chart_url})** ({r['dex']}) | **+{r['gain_24h']:,.0f}%**\n"
                f"• **Alter:** {r['age_h']}h | **MCap:** ${r['mcap']:,.0f} | **LP:** ${r['liq']:,.0f}\n"
                f"• **1h-Launch-Spike:** +{max_gain}% | **Max-Dip:** {deepest_dip}%\n"
                f"• **RugCheck-Score:** {rc_score}\n"
                f"───────────────────\n"
            )

    if DISCORD_WEBHOOK_URL:
        embed = {
            "title": "🔍 Pattern-Analyse (inkl. GeckoTerminal OHLCV)",
            "description": fields_text,
            "color": 0x10B981,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)

if __name__ == "__main__":
    save_and_report()
