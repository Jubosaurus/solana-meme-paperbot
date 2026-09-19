import os
import csv
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

CSV_SMART_WALLETS = "smart_wallets.csv"
JSON_PROCESSED_TXS = "processed_txs.json"
DISCORD_WEBHOOK_URL = (os.environ.get("DISCORD_SMART_MONEY_WEBHOOK")
                       or os.environ.get("DISCORD_WEBHOOK_URL"))

SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL") or "https://api.mainnet-beta.solana.com"
WSOL_MINT = "So11111111111111111111111111111111111111112"

IGNORED_MINTS = {
    WSOL_MINT,
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
}

# Die CSV enthaelt ~190 Adressen. Alle zu pollen erzeugt mehrere hundert
# RPC-Calls pro Lauf und drosselt den Trading-Bot. Nur die neuesten Eintraege.
MAX_TRACKED_WALLETS = 20
SIG_LIMIT_PER_WALLET = 4
MAX_PROCESSED_TXS = 800
MIN_SOL_SPENT = 0.002
MIN_SOL_SPENT_LAMPORTS = int(MIN_SOL_SPENT * 1_000_000_000)
RPC_PAUSE_SECONDS = 0.3
DISCORD_DESC_LIMIT = 3900

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "smart-wallet-tracker/2.0",
                        "Content-Type": "application/json"})

RPC_STATS = {"ok": 0, "error": 0, "rate_limited": 0}


# ------------------------------------------------------------------ State (Liste)

def load_processed_txs():
    """Als Liste laden, damit die Reihenfolge erhalten bleibt."""
    if not os.path.exists(JSON_PROCESSED_TXS):
        return []
    try:
        with open(JSON_PROCESSED_TXS, "r", encoding="utf-8") as f:
            data = json.load(f)
        return list(data) if isinstance(data, list) else []
    except Exception as err:
        print(f"[STATE ERROR] {err}")
        return []


def save_processed_txs(processed_list):
    """Aelteste zuerst verwerfen - ein Set haette keine Reihenfolge."""
    trimmed = processed_list[-MAX_PROCESSED_TXS:]
    try:
        tmp = JSON_PROCESSED_TXS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(trimmed, f)
        os.replace(tmp, JSON_PROCESSED_TXS)
    except Exception as err:
        print(f"[STATE ERROR] {err}")


def git_push_state():
    try:
        subprocess.run(["git", "config", "--global", "user.name",
                        "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email",
                        "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", JSON_PROCESSED_TXS], check=False)
        status = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m",
                            "Update smart wallet tracking state [skip ci]"], check=False)
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
            subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception as err:
        print(f"[GIT ERROR] {err}")


# ------------------------------------------------------------------- RPC Helpers

def rpc_call(method, params, context=""):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        res = SESSION.post(SOLANA_RPC_URL, json=payload, timeout=8)
    except Exception as err:
        RPC_STATS["error"] += 1
        print(f"[RPC FAIL] {method} {context} -> {err}")
        return None

    if res.status_code == 429:
        RPC_STATS["rate_limited"] += 1
        print(f"[RPC RATE-LIMIT] 429 bei {method} {context}")
        return None
    if res.status_code != 200:
        RPC_STATS["error"] += 1
        print(f"[RPC HTTP {res.status_code}] {method} {context}")
        return None

    try:
        body = res.json()
    except Exception as err:
        RPC_STATS["error"] += 1
        print(f"[RPC PARSE ERROR] {method} {context} -> {err}")
        return None

    if isinstance(body, dict) and body.get("error"):
        RPC_STATS["error"] += 1
        print(f"[RPC ERROR] {method} {context} -> {body['error']}")
        return None

    RPC_STATS["ok"] += 1
    return body.get("result") if isinstance(body, dict) else None


# ----------------------------------------------------------------- Wallet-Quelle

def get_tracked_wallets():
    wallets = []
    if not os.path.exists(CSV_SMART_WALLETS):
        print(f"[WARN] {CSV_SMART_WALLETS} nicht gefunden.")
        return wallets

    try:
        with open(CSV_SMART_WALLETS, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                addr = row.get("wallet_address")
                if addr:
                    wallets.append({
                        "address": addr,
                        "found_on": row.get("token_found_on", "UNKNOWN"),
                        "type": row.get("classification", "Trader"),
                        "first_spotted": row.get("first_spotted", "")
                    })
    except Exception as err:
        print(f"[CSV ERROR] {err}")
        return []

    # Neueste zuerst, dann begrenzen
    wallets.sort(key=lambda w: w["first_spotted"], reverse=True)
    return wallets[:MAX_TRACKED_WALLETS]


# ------------------------------------------------------------- Kauf-Erkennung

def token_deltas_for_owner(meta, wallet):
    pre, post = {}, {}
    for entry in meta.get("preTokenBalances") or []:
        if entry.get("owner") == wallet and entry.get("mint"):
            amount = float((entry.get("uiTokenAmount") or {}).get("uiAmount") or 0.0)
            pre[entry["mint"]] = pre.get(entry["mint"], 0.0) + amount
    for entry in meta.get("postTokenBalances") or []:
        if entry.get("owner") == wallet and entry.get("mint"):
            amount = float((entry.get("uiTokenAmount") or {}).get("uiAmount") or 0.0)
            post[entry["mint"]] = post.get(entry["mint"], 0.0) + amount
    return {mint: post.get(mint, 0.0) - pre.get(mint, 0.0)
            for mint in set(pre) | set(post)}


def lamports_spent_by_wallet(tx_info, wallet):
    meta = tx_info.get("meta") or {}
    message = (tx_info.get("transaction") or {}).get("message") or {}
    keys = message.get("accountKeys") or []

    index = None
    for i, key in enumerate(keys):
        pubkey = key.get("pubkey") if isinstance(key, dict) else key
        if pubkey == wallet:
            index = i
            break

    pre = meta.get("preBalances") or []
    post = meta.get("postBalances") or []
    if index is None or index >= len(pre) or index >= len(post):
        return 0
    return int(pre[index]) - int(post[index])


def analyze_transaction_for_buy(signature, wallet):
    """
    Gibt den gekauften Mint zurueck oder None.

    Entscheidend: die Wallet muss bezahlt haben (SOL- oder WSOL-Abfluss).
    Ohne diese Pruefung waere jeder Spam-Airdrop an eine bekannte
    Whale-Wallet ein 'Kauf'.
    """
    tx_info = rpc_call(
        "getTransaction",
        [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        context=f"{wallet[:4]}../tx"
    )
    if not isinstance(tx_info, dict):
        return None

    meta = tx_info.get("meta") or {}
    if meta.get("err") is not None:
        return None

    deltas = token_deltas_for_owner(meta, wallet)
    sol_out = lamports_spent_by_wallet(tx_info, wallet)
    wsol_out = -deltas.get(WSOL_MINT, 0.0)

    if not (sol_out >= MIN_SOL_SPENT_LAMPORTS or wsol_out >= MIN_SOL_SPENT):
        return None

    bought = [mint for mint, delta in deltas.items()
              if delta > 0 and mint not in IGNORED_MINTS]
    return bought[0] if bought else None


def get_latest_signatures(wallet_address):
    sigs = rpc_call("getSignaturesForAddress",
                    [wallet_address, {"limit": SIG_LIMIT_PER_WALLET}],
                    context=wallet_address[:4])
    if not isinstance(sigs, list):
        return []
    return [s["signature"] for s in sigs
            if s.get("signature") and s.get("err") is None]


def get_token_metadata(mint):
    try:
        res = SESSION.get(f"https://api.dexscreener.com/latest/dex/tokens/{mint}",
                          timeout=5)
        if res.status_code == 200:
            pairs = res.json().get("pairs") or []
            if pairs:
                best = max(pairs,
                           key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0.0))
                return {
                    "symbol": str((best.get("baseToken") or {}).get("symbol") or "UNKNOWN"),
                    "mcap": float(best.get("fdv") or best.get("marketCap") or 0.0),
                    "liq": float((best.get("liquidity") or {}).get("usd") or 0.0),
                    "pair_url": f"https://dexscreener.com/solana/{best.get('pairAddress')}"
                }
    except Exception as err:
        print(f"[DEXSCREENER ERROR] {err}")
    return {
        "symbol": "UNKNOWN",
        "mcap": 0.0,
        "liq": 0.0,
        "pair_url": f"https://solscan.io/token/{mint}"
    }


# ---------------------------------------------------------------------- Discord

def send_alerts(alerts):
    if not DISCORD_WEBHOOK_URL or not alerts:
        return

    blocks = []
    for a in alerts:
        w_short = f"{a['wallet'][:5]}...{a['wallet'][-4:]}"
        blocks.append(
            f"🚨 **Smart Wallet Kauf erkannt!**\n"
            f"• **Trader:** [{w_short}](https://solscan.io/account/{a['wallet']}) "
            f"(Entdeckt bei ${a['found_on']})\n"
            f"• **Token:** [${a['symbol']}]({a['url']})\n"
            f"• **Pool:** MCap: ${a['mcap']:,.0f} | LP: ${a['liq']:,.0f}\n"
            f"• **Checks:** [RugCheck](https://rugcheck.xyz/tokens/{a['mint']}) | "
            f"[Tx](https://solscan.io/tx/{a['sig']})\n"
            f"───────────────────\n"
        )

    # In mehrere Embeds aufteilen: Discord begrenzt description auf 4096 Zeichen
    chunks, current = [], ""
    for block in blocks:
        if len(current) + len(block) > DISCORD_DESC_LIMIT:
            chunks.append(current)
            current = ""
        current += block
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks, start=1):
        title = "🎯 Smart Money Early-Signal"
        if len(chunks) > 1:
            title += f" ({i}/{len(chunks)})"
        embed = {
            "title": title,
            "description": chunk,
            "color": 0x10B981,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            SESSION.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=6)
        except Exception as err:
            print(f"[DISCORD ERROR] {err}")


# -------------------------------------------------------------------------- Main

def main():
    wallets = get_tracked_wallets()
    if not wallets:
        print("Keine Smart Wallets zum Tracken gefunden.")
        return

    processed_list = load_processed_txs()
    processed_set = set(processed_list)
    first_run = not processed_list
    new_alerts = []

    if first_run:
        print("[BOOTSTRAP] Kein State vorhanden - dieser Lauf synchronisiert nur.")

    print(f"[TRACKING] Pruefe {len(wallets)} Wallets "
          f"(von max. {MAX_TRACKED_WALLETS}) auf frische Kaeufe...")

    for wallet in wallets:
        addr = wallet["address"]
        sigs = get_latest_signatures(addr)
        time.sleep(RPC_PAUSE_SECONDS)

        for sig in sigs:
            if sig in processed_set:
                continue

            processed_set.add(sig)
            processed_list.append(sig)

            if first_run:
                continue

            bought_mint = analyze_transaction_for_buy(sig, addr)
            time.sleep(RPC_PAUSE_SECONDS)
            if not bought_mint:
                continue

            meta = get_token_metadata(bought_mint)
            new_alerts.append({
                "wallet": addr,
                "found_on": wallet["found_on"],
                "mint": bought_mint,
                "symbol": meta["symbol"],
                "mcap": meta["mcap"],
                "liq": meta["liq"],
                "url": meta["pair_url"],
                "sig": sig
            })
            print(f"⚡ {addr[:4]}.. kaufte ${meta['symbol']}")

    # State zuerst sichern, damit ein Discord-Fehler ihn nicht verhindert
    save_processed_txs(processed_list)
    git_push_state()

    send_alerts(new_alerts)

    print(f"[STATUS] {len(new_alerts)} neue Kaeufe | "
          f"RPC ok={RPC_STATS['ok']} fehler={RPC_STATS['error']} "
          f"ratelimit={RPC_STATS['rate_limited']}")
    if RPC_STATS["ok"] == 0:
        print("[WARN] Kein erfolgreicher RPC-Call - eigenen Key als "
              "SOLANA_RPC_URL setzen.")


if __name__ == "__main__":
    main()
