import os
import csv
import time
import subprocess
import requests
from datetime import datetime, timezone

CSV_RUNNERS = "runner_patterns.csv"
CSV_SMART_WALLETS = "smart_wallets.csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_SMART_MONEY_WEBHOOK") or os.environ.get("DISCORD_WEBHOOK_URL")

HEADERS_WALLETS = [
    "first_spotted", "wallet_address", "token_found_on", "buy_delay_min",
    "est_holding_min", "trade_pnl_usd", "wallet_tx_count", "classification"
]

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

def init_csv():
    if not os.path.exists(CSV_SMART_WALLETS):
        with open(CSV_SMART_WALLETS, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS_WALLETS)

def git_push_csv():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", CSV_SMART_WALLETS], check=False)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Expand smart wallets pool [skip ci]"], check=False)
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
            subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception as err:
        print(f"[GIT ERROR] {err}")

def get_known_wallets():
    known = set()
    if os.path.exists(CSV_SMART_WALLETS):
        with open(CSV_SMART_WALLETS, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                addr = row.get("wallet_address")
                if addr:
                    known.add(addr)
    return known

def get_all_runners_from_csv():
    if not os.path.exists(CSV_RUNNERS):
        return []
    pools = []
    with open(CSV_RUNNERS, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        # Priorisiere Runner mit den höchsten Kursgewinnen
        for row in reader:
            try:
                gain = float(row.get("gain_24h_pct", 0.0) or 0.0)
            except ValueError:
                gain = 0.0
            pools.append({
                "symbol": row.get("symbol"),
                "token_addr": row.get("token_address"),
                "pair_addr": row.get("pair_address"),
                "gain": gain,
                "age_h": float(row.get("age_hours") or 0.0)
            })
    # Sortiere nach Performance
    pools.sort(key=lambda x: x["gain"], reverse=True)
    return pools

def get_wallet_activity_metrics(wallet_address):
    try:
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet_address, {"limit": 30}]
        }
        res = requests.post(SOLANA_RPC_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=6)
        if res.status_code == 200:
            sigs = res.json().get("result", [])
            return len(sigs)
    except Exception:
        pass
    return 0

def scan_smart_traders():
    init_csv()
    known_wallets = get_known_wallets()
    runners = get_all_runners_from_csv()

    if not runners:
        print("Keine Runner-Daten in runner_patterns.csv vorhanden.")
        return

    print(f"[SMART MONEY] Durchsuche {len(runners)} Top-Runner nach profitablen Wallets...")
    new_traders = []

    for r in runners:
        token_addr = r["token_addr"]
        symbol = r["symbol"]
        
        try:
            rc_res = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{token_addr}/report", timeout=6)
            if rc_res.status_code != 200:
                continue
            data = rc_res.json()
            top_holders = data.get("topHolders", [])
            creator = data.get("creator")
        except Exception:
            continue

        # Top 30 Holder pro Runner scannen
        for holder in top_holders[:30]:
            wallet = holder.get("address")
            if not wallet or wallet in known_wallets or wallet == creator:
                continue

            pct = float(holder.get("pct", 0.0) or holder.get("percentage", 0.0) or 0.0)
            
            # Filter 1: Keine Cabal-Whales / Devs mit riesigen Supply-Blöcken (> 10%)
            if pct > 10.0 or pct < 0.2:
                continue

            # Filter 2: Mindest-Aktivität (echte Trading-Wallet, kein Einmal-Bot)
            tx_count = get_wallet_activity_metrics(wallet)
            time.sleep(0.2)

            if tx_count < 8:
                continue

            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            entry = {
                "first_spotted": now_iso,
                "wallet_address": wallet,
                "token_found_on": symbol,
                "buy_delay_min": ">15m",
                "est_holding_min": "Swing (>30m)",
                "trade_pnl_usd": f"Runner +{r['gain']:,.0f}%",
                "wallet_tx_count": tx_count,
                "classification": "Organic Accumulator"
            }
            new_traders.append(entry)
            known_wallets.add(wallet)

            with open(CSV_SMART_WALLETS, mode="a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    entry["first_spotted"], entry["wallet_address"], entry["token_found_on"],
                    entry["buy_delay_min"], entry["est_holding_min"], entry["trade_pnl_usd"],
                    entry["wallet_tx_count"], entry["classification"]
                ])

            print(f" -> Neuer Trader entdeckt: {wallet[:6]}...{wallet[-4:]} auf ${symbol} (+{r['gain']:,.0f}%) | {tx_count} Tx")

    print(f"[STATUS] {len(new_traders)} neue Trader zur Datenbank hinzugefügt. Gesamtbestand: {len(known_wallets)} Wallets.")

    # Discord Reporting (Batch-Zusammenfassung)
    if DISCORD_WEBHOOK_URL and new_traders:
        fields_text = ""
        for t in new_traders[:10]:  # Zeige die ersten 10 im Discord, um Nachrichten-Limits einzuhalten
            solscan_url = f"https://solscan.io/account/{t['wallet_address']}"
            fields_text += (
                f"👤 **[{t['wallet_address'][:6]}...{t['wallet_address'][-4:]}]({solscan_url})**\n"
                f"• **Runner:** ${t['token_found_on']} ({t['trade_pnl_usd']})\n"
                f"• **Aktivität:** {t['wallet_tx_count']}+ Tx | Typ: {t['classification']}\n"
                f"───────────────────\n"
            )

        embed = {
            "title": f"🧠 Smart Money Trichter erweitert (+{len(new_traders)} neue Wallets)",
            "description": fields_text,
            "color": 0x3B82F6,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)

    git_push_csv()

if __name__ == "__main__":
    scan_smart_traders()
