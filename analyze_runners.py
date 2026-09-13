import os
import requests
from datetime import datetime, timezone

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def get_top_solana_runners():
    """Findet Solana-Pools mit extremen Zuwächsen und berechnet deren On-Chain-Metriken."""
    headers = {"User-Agent": "Mozilla/5.0"}
    discovered_pairs = []
    
    # 1. Abfrage über DexScreener Boosts & Profiles
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

    # 2. Token-Batches abfragen
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
                
                # Nur Raydium & Meteora SOL-Paare
                dex_id = p.get("dexId", "").lower()
                quote = p.get("quoteToken", {}).get("symbol", "").upper()
                if dex_id not in ["raydium", "meteora"] or quote not in ["SOL", "WSOL"]:
                    continue

                created_at = p.get("pairCreatedAt")
                if not created_at:
                    continue
                age_hours = (now_ts - (created_at / 1000.0)) / 3600.0
                
                # Filter für Runner: Mind. 1.5h alt, max. 48h alt
                if age_hours < 1.5 or age_hours > 48.0:
                    continue

                gain_24h = float(p.get("priceChange", {}).get("h24") or 0.0)
                # Mindestens +200% Anstieg als Runner-Kriterium
                if gain_24h < 200.0:
                    continue

                mcap = float(p.get("fdv") or p.get("marketCap") or 0.0)
                liq = float(p.get("liquidity", {}).get("usd") or 0.0)
                vol_24h = float(p.get("volume", {}).get("h24") or 0.0)
                tx_buys = p.get("txns", {}).get("h24", {}).get("buys", 0)
                tx_sells = p.get("txns", {}).get("h24", {}).get("sells", 0)

                # Wichtige Pattern-Kennzahlen:
                vol_to_liq = (vol_24h / liq) if liq > 0 else 0.0
                buy_ratio = (tx_buys / (tx_buys + tx_sells) * 100.0) if (tx_buys + tx_sells) > 0 else 0.0

                discovered_pairs.append({
                    "symbol": p.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "token_addr": p.get("baseToken", {}).get("address"),
                    "pair_addr": p.get("pairAddress"),
                    "dex": dex_id.upper(),
                    "age_h": round(age_hours, 1),
                    "gain_24h": gain_24h,
                    "mcap": mcap,
                    "liq": liq,
                    "vol_24h": vol_24h,
                    "vol_to_liq": round(vol_to_liq, 1),
                    "buy_ratio": round(buy_ratio, 1),
                    "buys_24h": tx_buys
                })
        except Exception:
            continue

    # Sortiere nach bestem 24h-Gewinn
    discovered_pairs.sort(key=lambda x: x["gain_24h"], reverse=True)
    return discovered_pairs[:5]

def audit_runner(token_addr):
    """Holt den RugCheck-Score."""
    try:
        r = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{token_addr}/report/summary", timeout=5)
        if r.status_code == 200:
            return r.json().get("score", 0)
    except Exception:
        pass
    return "N/A"

def send_discord_report(runners):
    if not DISCORD_WEBHOOK_URL or not runners:
        return

    fields_text = ""
    for r in runners:
        rc_score = audit_runner(r["token_addr"])
        chart_url = f"https://dexscreener.com/solana/{r['pair_addr']}"
        fields_text += (
            f"🚀 **[{r['symbol']}]({chart_url})** ({r['dex']}) | **+{r['gain_24h']:,.0f}%**\n"
            f"• **Alter:** {r['age_h']}h | **MCap:** ${r['mcap']:,.0f} | **LP:** ${r['liq']:,.0f}\n"
            f"• **Vol/LP-Ratio:** {r['vol_to_liq']}x | **Buys:** {r['buy_ratio']}% ({r['buys_24h']:,} Tx)\n"
            f"• **RugCheck:** {rc_score}\n"
            f"───────────────────\n"
        )

    embed = {
        "title": "🔍 Pattern-Analyse: Top Solana Runner",
        "description": fields_text,
        "color": 0xF59E0B,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)

if __name__ == "__main__":
    print("Starte Runner-Pattern-Analyse...")
    top_runners = get_top_solana_runners()
    print(f"{len(top_runners)} Runner identifiziert.")
    send_discord_report(top_runners)
