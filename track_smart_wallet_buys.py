import os
import csv
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

CSV_SMART_WALLETS = "smart_wallets.csv"
JSON_PROCESSED_TXS = "processed_txs.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_SMART_MONEY_WEBHOOK") or os.environ.get("DISCORD_WEBHOOK_URL")

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
WSOL_MINT = "So11111111111111111111111111111111111111112"

def load_processed_txs():
    if os.path.exists(JSON_PROCESSED_TXS):
        try:
            with open(JSON_PROCESSED_TXS, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_processed_txs(processed_set):
    recent_list = list(processed_set)[-500:]
    with open(JSON_PROCESSED_TXS, "w", encoding="utf-8") as f:
        json.dump(recent_list, f)

def git_push_state():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", JSON_PROCESSED_TXS], check=False)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Update smart wallet tracking state [skip ci]"], check=False)
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
            subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception as err:
        print(f"[GIT ERROR] {err}")

def get_tracked_wallets():
    wallets = []
    if not os.path.exists(CSV_SMART_WALLETS):
        return wallets
    with open(CSV_SMART_WALLETS, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            addr = row.get("wallet_address")
            if addr:
                wallets.append({
                    "address": addr,
                    "found_on": row.get("token_found_on", "UNKNOWN"),
                    "type": row.get("classification", "Trader")
                })
    return wallets

def get_latest_signatures(wallet_address, limit=5):
    payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": limit}]
    }
    try:
        r = requests.post(SOLANA_RPC_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=6)
        if r.status_code == 200:
            return [tx["signature"] for tx in r.json().get("result", []) if not tx.get("err")]
    except Exception:
        pass
    return []

def analyze_transaction_for_buy(signature, target_wallet):
    payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }
    try:
        r = requests.post(SOLANA_RPC_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
        if r.status_code != 200:
            return None
        data = r.json().get("result")
        if not data:
            return None

        meta = data.get("meta", {})
        pre_balances = meta.get("preTokenBalances", [])
        post_balances = meta.get("postTokenBalances", [])

        pre_map = {b["mint"]: float(b["uiTokenAmount"]["uiAmount"] or 0) for b in pre_balances if b.get("owner") == target_wallet}
        
        for post in post_balances:
            if post.get("owner") == target_wallet:
                mint = post.get("mint")
                if not mint or mint == WSOL_MINT:
                    continue
                post_amt = float(post["uiTokenAmount"]["uiAmount"] or 0)
                pre_amt = pre_map.get(mint, 0.0)

                if post_amt > pre_amt:
                    return mint
    except Exception:
        pass
    return None

def get_token_metadata(mint):
    try:
        r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{mint}", timeout=5)
        if r.status_code == 200:
            pairs = r.json().get("pairs") or []
            if pairs:
                p = pairs[0]
                return {
                    "symbol": p.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "mcap": float(p.get("fdv") or p.get("marketCap") or 0.0),
                    "liq": float(p.get("liquidity", {}).get("usd") or 0.0),
                    "pair_url": f"https://dexscreener.com/solana/{p.get('pairAddress')}"
                }
    except Exception:
        pass
    return {
        "symbol": "UNKNOWN",
        "mcap": 0.0,
        "liq": 0.0,
        "pair_url": f"https://solscan.io/token/{mint}"
    }

def main():
    wallets = get_tracked_wallets()
    if not wallets:
        print("Keine Smart Wallets zum Tracken gefunden.")
        return

    processed_txs = load_processed_txs()
    first_run = (len(processed_txs) == 0)
    new_alerts = []

    print(f"[TRACKING] Überprüfe Aktivität für {len(wallets)} Smart Wallets...")

    for w in wallets:
        addr = w["address"]
        sigs = get_latest_signatures(addr, limit=4)
        time.sleep(0.3)

        for sig in sigs:
            if sig in processed_txs:
                continue

            processed_txs.add(sig)

            if first_run:
                continue

            bought_mint = analyze_transaction_for_buy(sig, addr)
            time.sleep(0.3)

            if bought_mint:
                meta = get_token_metadata(bought_mint)
                new_alerts.append({
                    "wallet": addr,
                    "found_on": w["found_on"],
                    "mint": bought_mint,
                    "symbol": meta["symbol"],
                    "mcap": meta["mcap"],
                    "liq": meta["liq"],
                    "url": meta["pair_url"],
                    "sig": sig
                })

    save_processed_txs(processed_txs)

    if DISCORD_WEBHOOK_URL and new_alerts:
        fields_text = ""
        for a in new_alerts:
            w_short = f"{a['wallet'][:5]}...{a['wallet'][-4:]}"
            solscan_w = f"https://solscan.io/account/{a['wallet']}"
            tx_url = f"https://solscan.io/tx/{a['sig']}"
            rugcheck_url = f"https://rugcheck.xyz/tokens/{a['mint']}"

            fields_text += (
                f"🚨 **Smart Wallet Kauf erkannt!**\n"
                f"• **Trader:** [{w_short}]({solscan_w}) (Entdeckt bei ${a['found_on']})\n"
                f"• **Token:** [${a['symbol']}]({a['url']})\n"
                f"• **Pool:** MCap: ${a['mcap']:,.0f} | LP: ${a['liq']:,.0f}\n"
                f"• **Checks:** [RugCheck]({rugcheck_url}) | [Tx Details]({tx_url})\n"
                f"───────────────────\n"
            )

        embed = {
            "title": "🎯 Smart Money Early-Signal",
            "description": fields_text,
            "color": 0x10B981,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)

    git_push_state()
    print("Tracking-Durchlauf abgeschlossen.")

if __name__ == "__main__":
    main()
