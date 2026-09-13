import os
import csv
import time
import subprocess
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

WSOL_MINT = "So11111111111111111111111111111111111111112"

def git_push_csv():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", CSV_RUNNERS], check=False)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Update runner patterns data [skip ci]"], check=False)
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
            subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception as err:
        print(f"[GIT ERROR] {err}")

def init_csv():
    if not os.path.exists(CSV_RUNNERS):
        with open(CSV_RUNNERS, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS_RUNNERS)

def get_gecko_ohlcv_pattern(pool_address):
    url = f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool_address}/ohlcv/minute?limit=60"
    headers = {"Accept": "application/json;version=20230302", "User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code != 200:
            return 0.0, 0.0
        data = res.json()
        ohlcv_list = data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
        if not ohlcv_list:
            return 0.0, 0.0

        ohlcv_list.reverse()
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

def audit_runner_and_holders(token_addr):
    """Zieht RugCheck-Score UND kumulierten Top-10-Holder-Anteil."""
    score = "N/A"
    top10_pct = 0.0
    try:
        r = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{token_addr}/report/summary", timeout=6)
        if r.status_code == 200:
            data = r.json()
            score = data.get("score", 0)
            holders = data.get("topHolders", [])
            if holders:
                top10_pct = sum(float(h.get("pct", 0.0) or 0.0) for h in holders[:10])
    except Exception:
        pass
    return score, round(top10_pct, 1)

def get_jupiter_price_impact(token_mint):
    try:
        url = f"https://quote-api.jup.ag/v6/quote?inputMint={WSOL_MINT}&outputMint={token_mint}&amount=250000000&slippageBps=100"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            impact = float(data.get("priceImpactPct") or 0.0)
            return round(impact, 2)
    except Exception:
        pass
    return -1.0

def get_top_solana_runners():
    headers = {"User-Agent": "Mozilla/5.0"}
    tokens = set()
    now_ts = datetime.now(timezone.utc).timestamp()
    discovered = []

    try:
        gt_url = "https://api.geckoterminal.com/api/v2/networks/solana/trending_pools"
        gt_res = requests.get(gt_url, headers={"Accept": "application/json;version=20230302", "User-Agent": "Mozilla/5.0"}, timeout=6)
        if gt_res.status_code == 200:
            gt_data = gt_res.json().get("data", [])
            for item in gt_data:
                rel = item.get("relationships", {})
                base_token_id = rel.get("base_token", {}).get("data", {}).get("id", "")
                if base_token_id.startswith("solana_"):
                    tokens.add(base_token_id.replace("solana_", ""))
    except Exception:
        pass

    endpoints = [
        "https://api.dexscreener.com/token-boosts/top/v1",
        "https://api.dexscreener.com/token-boosts/latest/v1",
        "https://api.dexscreener.com/token-profiles/latest/v1",
    ]
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

    token_list = list(tokens)[:120]
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

                quote = p.get("quoteToken", {}).get("symbol", "").upper()
                if quote not in ["SOL", "WSOL", "USDC", "USDT"]:
                    continue

                created_at = p.get("pairCreatedAt")
                if not created_at:
                    continue
                age_hours = (now_ts - (created_at / 1000.0)) / 3600.0
                if age_hours < 0.5 or age_hours > 72.0:
                    continue

                gain_24h = float(p.get("priceChange", {}).get("h24") or 0.0)
                if gain_24h < 100.0:
                    continue

                discovered.append({
                    "symbol": p.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "token_addr": p.get("baseToken", {}).get("address"),
                    "pair_addr": p.get("pairAddress"),
                    "dex": p.get("dexId", "DEX").upper(),
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
            max_gain, deepest_dip = get_gecko_ohlcv_pattern(r["pair_addr"])
            time.sleep(0.5)

            rc_score, top10_holders = audit_runner_and_holders(r["token_addr"])
            price_impact = get_jupiter_price_impact(r["token_addr"])

            writer.writerow([
                now_iso, r["symbol"], r["token_addr"], r["pair_addr"], r["dex"],
                r["age_h"], r["gain_24h"], r["mcap"], r["liq"], r["vol_24h"],
                max_gain, deepest_dip, top10_holders, price_impact, rc_score
            ])

            impact_str = f"{price_impact}%" if price_impact >= 0 else "Nicht geroutet (Bonding-Curve/Inaktiv)"
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

    if DISCORD_WEBHOOK_URL and fields_text:
        embed = {
            "title": "🔍 Deep On-Chain Pattern-Analyse (Top Runner)",
            "description": fields_text,
            "color": 0x6366F1,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)

    git_push_csv()

if __name__ == "__main__":
    print("Starte Deep On-Chain Analyse...")
    save_and_report()
    print("Fertig. Daten archiviert & Discord benachrichtigt.")
