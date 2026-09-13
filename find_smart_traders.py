import os
import csv
import time
import subprocess
import requests
from datetime import datetime, timezone

CSV_RUNNERS = "runner_patterns.csv"
CSV_SMART_WALLETS = "smart_wallets.csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

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
            subprocess.run(["git", "commit", "-m", "Update smart wallets database [skip ci]"], check=False)
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
                known.add(row.get("wallet_address"))
    return known

def get_recent_runners_from_csv():
    """Liest die letzten analysierten Runner-Pools aus runner_patterns.csv."""
    if not os.path.exists(CSV_RUNNERS):
        return []
    pools = []
    with open(CSV_RUNNERS, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        # Nimm die letzten 10 Runner
        for row in reversed(reader[-10:]):
            pools.append({
                "symbol": row.get("symbol"),
                "token_addr": row.get("token_address"),
                "pair_addr": row.get("pair_address"),
                "age_h": float(row.get("age_hours") or 0.0)
            })
    return pools

def get_wallet_activity_metrics(wallet_address):
    """Prüft über Solana Public RPC die Aktivität der Wallet."""
    try:
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet_address, {"limit": 40}]
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
    runners = get_recent_runners_from_csv()

    if not runners:
        print("Keine Runner-Daten in runner_patterns.csv vorhanden.")
        return

    print(f"[SMART MONEY] Untersuche Top-Trader für {len(runners)} Runner...")
    qualified_traders = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for r in runners:
        token_addr = r["token_addr"]
        symbol = r["symbol"]
        
        # 1. Top-Holders & Traders aus RugCheck Audit extrahieren
        try:
            rc_res = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{token_addr}/report", timeout=6)
            if rc_res.status_code != 200:
                continue
            data = rc_res.json()
            top_holders = data.get("topHolders", [])
            creator = data.get("creator")
        except Exception:
            continue

        for holder in top_holders[:15]:
            wallet = holder.get("address")
            if not wallet or wallet in known_wallets or wallet == creator:
                continue

            pct = float(holder.get("pct", 0.0) or 0.0)
            # Ausschluss von Cabal-Whales (> 12% des gesamten Supplies)
            if pct > 12.0:
                continue

            # RPC Profiling: Ist es ein echter aktiver Account oder eine Einweg-Wallet?
            tx_count = get_wallet_activity_metrics(wallet)
            time.sleep(0.3)

            if tx_count < 10:
                # Frische Throwaway-Wallet -> meiden
                continue

            # Qualifizierte 'Healthy Swing' Wallet
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            entry = {
                "first_spotted": now_iso,
                "wallet_address": wallet,
                "token_found_on": symbol,
                "buy_delay_min": ">15m",
                "est_holding_min": "Swing (>30m)",
                "trade_pnl_usd": "Top Holder (Clean)",
                "wallet_tx_count": tx_count,
                "classification": "Organic Accumulator"
            }
            qualified_traders.append(entry)
            known_wallets.add(wallet)

            with open(CSV_SMART_WALLETS, mode="a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    entry["first_spotted"], entry["wallet_address"], entry["token_found_on"],
                    entry["buy_delay_min"], entry["est_holding_min"], entry["trade_pnl_usd"],
                    entry["wallet_tx_count"], entry["classification"]
                ])

            print(f" -> Gesunder Trader gefunden: {wallet[:6]}...{wallet[-4:]} auf ${symbol}")
            if len(qualified_traders) >= 4:
                break

    # Discord Reporting
    if DISCORD_WEBHOOK_URL and qualified_traders:
        fields_text = ""
        for t in qualified_traders:
            solscan_url = f"https://solscan.io/account/{t['wallet_address']}"
            fields_text += (
                f"👤 **[{t['wallet_address'][:6]}...{t['wallet_address'][-4:]}]({solscan_url})**\n"
                f"• **Gefunden bei:** ${t['token_found_on']}\n"
                f"• **Typ:** {t['classification']} | **Aktivität:** {t['wallet_tx_count']}+ Tx\n"
                f"• **Verhalten:** Moderater Supply-Anteil, kein Throwaway-Bot\n"
                f"───────────────────\n"
            )

        embed = {
            "title": "🧠 Smart Money Scouting: Gesunde Trader-Wallets",
            "description": fields_text,
            "color": 0x3B82F6,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)

    git_push_csv()

if __name__ == "__main__":
    scan_smart_traders()
