import os
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

PORTFOLIO_FILE = "portfolio.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Public RPC funktioniert, ist aber stark limitiert und blockt viele
# Rechenzentrums-IPs (u.a. GitHub Actions). Mit Helius/QuickNode-Key als
# Secret SOLANA_RPC_URL laeuft Strategie B deutlich zuverlaessiger.
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

SCOUT_SIZE_SOL = 0.20
SIMULATED_FEE_SOL = 0.002
MAX_POSITIONS_PER_STRATEGY = 3
TOKEN_COOLDOWN_MINUTES = 120
MAX_HOLD_HOURS = 4.0
LOOP_SLEEP_SECONDS = 35
SHIFT_DURATION_SECONDS = 5 * 3600 - 300
START_BANKROLL_PER_STRATEGY = 5.0
MAX_PNL_PCT = 400.0

STRATEGY_NAMES = ("CTO", "SMART_MONEY", "SCALP_CURVE")

# A: CTO Settings
CTO_MIN_AGE_HOURS = 2.0
CTO_MAX_AGE_HOURS = 48.0
CTO_MIN_DRAWDOWN = -85.0
CTO_MAX_DRAWDOWN = -55.0
CTO_SL_PCT = -15.0
CTO_TRAILING_ACT = 35.0
CTO_TRAILING_DIST = 15.0

# B: Smart Money
SMART_WALLETS = [
    "CGy6Z4evgJpCtTr3DC3gCBfg9DoeY4fkUCMrEQT1n14n",
    "7izn9Mu6ByyCuEp9iKrAwKdTxVbaAi2eZYb46Lzg3mSX",
    "FM6gN6jiak7SGGcvFgcTWAwtFDs36J2ifsxdyRayt8yL",
    "4fNfqPTH94RibhKKsn5WyM3q8ojwWsv9W2AyJWnfVWK8",
    "4JswK49JB9YqVpJNTWsVYDStWScy9EpSzpZj7fXdsM7n",
    "64UKSJodQoMaNTcrxERMHUWkiLC91ketTYU3CGWj4jo8",
    "75p4RCsojEidqKahaGzqzogxfoQHZ2M83WDaKgXaRtzE",
    "E4mSDt9wL8faNQxXthVLn4ECToQAci5M9fgn7qPeehWX",
    "DPWaEfayi7CbqCkgre6wGdTumscDxLpt8LuSTL2GkDnV",
    "AAVQVaEuESYjtiFaE2eEpansBkHLktqf9RgbU9SQMA33",
    "Hpm5Kvf1opeJ9WLAf9HebHgU5quamVwmQx8tmVTrW7TY",
    "fKCj7ujBZaAoJjdx873pVYQwZEZmyz3qqCYCSHi4TcN",
    "6tZ1hYnnHm3dPP5UJs3B9cFJ45VNMuESYhowv4LNP2gt",
    "G2ojGGZ8LZLBchuSvVJvygaRJkwTPbMYwUnPr9V3ioAp",
    "B1fpnXtcF4AM7fy3dYbgVhb6N3x2XGPdh3FdQFZCk472"
]
SM_SL_PCT = -20.0
SM_TRAILING_ACT = 40.0
SM_TRAILING_DIST = 15.0
SM_MIN_CLUSTER_SIZE = 2
CLUSTER_WINDOW_SECONDS = 900          # 15 Minuten Cluster-Fenster

SMART_WALLET_BATCH_SIZE = 5           # Wallets pro Loop (Round-Robin)
SIG_FETCH_LIMIT = 10                  # Signaturen pro Wallet und Abfrage
MAX_NEW_TX_PER_WALLET = 5             # Backfill-Bremse pro Wallet und Loop
MIN_SOL_SPENT = 0.002                 # Wallet muss echtes SOL ausgeben -> kein Airdrop
MIN_SOL_SPENT_LAMPORTS = int(MIN_SOL_SPENT * 1_000_000_000)

# C: Scalp Curve
SCALP_MIN_CURVE = 84.0
SCALP_MAX_CURVE = 93.0
SCALP_TARGET_TP = 25.0
SCALP_FORCE_EXIT_CURVE = 97.0
SCALP_SL_PCT = -18.0
CURVE_GRADUATION_MCAP = 69000.0

WSOL_MINT = "So11111111111111111111111111111111111111112"

# Stablecoins & Wrapped SOL zaehlen nicht als "Kauf eines Memecoins"
IGNORED_MINTS = {
    WSOL_MINT,
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
}

# In-Memory Cache fuer On-Chain Activity
wallet_buy_tracker = {}        # {token_addr: [(wallet, timestamp), ...]}
last_seen_tx_per_wallet = {}   # {wallet: signature}
bootstrapped_wallets = set()   # Wallets, deren Startpunkt gesetzt wurde
_wallet_cursor = 0

RPC_STATS = {"ok": 0, "error": 0, "rate_limited": 0}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "multi-strategy-paper-bot/1.0"})


# ------------------------------------------------------------- HTTP & RPC Helpers

def api_get(url, timeout=5):
    try:
        res = SESSION.get(url, timeout=timeout)
        if res.status_code != 200:
            return None
        return res.json()
    except Exception as err:
        print(f"[API ERROR] {url} -> {err}")
        return None


def rpc_call(method, params, context=""):
    """Solana-RPC-Aufruf. Fehler werden laut geloggt, nie stumm verschluckt."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        res = SESSION.post(SOLANA_RPC_URL, json=payload, timeout=8)
    except Exception as err:
        RPC_STATS["error"] += 1
        print(f"[RPC FAIL] {method} {context} -> {err}")
        return None

    if res.status_code == 429:
        RPC_STATS["rate_limited"] += 1
        print(f"[RPC RATE-LIMIT] 429 bei {method} {context} -> RPC drosselt uns")
        return None

    if res.status_code != 200:
        RPC_STATS["error"] += 1
        print(f"[RPC HTTP {res.status_code}] {method} {context} -> {res.text[:120]}")
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


def pair_liquidity_usd(pair):
    return float((pair.get("liquidity") or {}).get("usd") or 0.0)


def pair_mcap(pair):
    return float(pair.get("fdv") or pair.get("marketCap") or 0.0)


def pair_txns_m5(pair):
    m5 = (pair.get("txns") or {}).get("m5") or {}
    return int(m5.get("buys") or 0), int(m5.get("sells") or 0)


def pair_price_change(pair, key):
    return float((pair.get("priceChange") or {}).get(key) or 0.0)


def fetch_best_pair(token_addr):
    data = api_get(f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}")
    if not isinstance(data, dict):
        return None
    pairs = data.get("pairs") or []
    if not pairs:
        return None
    return max(pairs, key=pair_liquidity_usd)


def get_sol_usd_price():
    pair = fetch_best_pair(WSOL_MINT)
    if pair:
        price = float(pair.get("priceUsd") or 0.0)
        if price > 0:
            return price
    return 100.0


# --------------------------------------------------------- On-Chain Wallet Stream

def token_deltas_for_owner(meta, wallet):
    """Bestandsveraenderung je Mint fuer genau diese Wallet."""
    pre, post = {}, {}
    for entry in meta.get("preTokenBalances") or []:
        if entry.get("owner") == wallet and entry.get("mint"):
            amount = float((entry.get("uiTokenAmount") or {}).get("uiAmount") or 0.0)
            pre[entry["mint"]] = pre.get(entry["mint"], 0.0) + amount
    for entry in meta.get("postTokenBalances") or []:
        if entry.get("owner") == wallet and entry.get("mint"):
            amount = float((entry.get("uiTokenAmount") or {}).get("uiAmount") or 0.0)
            post[entry["mint"]] = post.get(entry["mint"], 0.0) + amount
    return {mint: post.get(mint, 0.0) - pre.get(mint, 0.0) for mint in set(pre) | set(post)}


def lamports_spent_by_wallet(tx_info, wallet):
    """Netto-SOL-Abfluss der Wallet in dieser Transaktion (in Lamports)."""
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


def extract_purchased_mints(tx_info, wallet):
    """
    Liefert die Mints, die die Wallet in dieser TX GEKAUFT hat.

    Entscheidend: die Wallet muss dafuer bezahlt haben (SOL- oder WSOL-Abfluss).
    Sonst waere jeder Spam-Airdrop an eine bekannte Whale-Wallet ein Kaufsignal.
    """
    meta = tx_info.get("meta") or {}
    if meta.get("err") is not None:
        return []

    deltas = token_deltas_for_owner(meta, wallet)

    sol_out = lamports_spent_by_wallet(tx_info, wallet)
    wsol_out = -deltas.get(WSOL_MINT, 0.0)  # negativer Delta = ausgegeben

    paid = sol_out >= MIN_SOL_SPENT_LAMPORTS or wsol_out >= MIN_SOL_SPENT
    if not paid:
        return []

    return [
        mint for mint, delta in deltas.items()
        if delta > 0 and mint not in IGNORED_MINTS
    ]


def next_wallet_batch():
    """Round-Robin ueber die Wallet-Liste, ein Schritt pro Loop."""
    global _wallet_cursor
    if not SMART_WALLETS:
        return []
    size = min(SMART_WALLET_BATCH_SIZE, len(SMART_WALLETS))
    batch = [SMART_WALLETS[(_wallet_cursor + i) % len(SMART_WALLETS)] for i in range(size)]
    _wallet_cursor = (_wallet_cursor + size) % len(SMART_WALLETS)
    return batch


def collect_new_signatures(wallet):
    """Neue, erfolgreiche Signaturen seit dem letzten Durchlauf - aelteste zuerst."""
    sigs = rpc_call("getSignaturesForAddress",
                    [wallet, {"limit": SIG_FETCH_LIMIT}],
                    context=wallet[:4])
    if not isinstance(sigs, list) or not sigs:
        return [], None

    newest = sigs[0].get("signature")
    known = last_seen_tx_per_wallet.get(wallet)

    fresh = []
    for entry in sigs:
        signature = entry.get("signature")
        if not signature or signature == known:
            break
        if entry.get("err") is not None:
            continue
        fresh.append(entry)

    fresh = list(reversed(fresh[:MAX_NEW_TX_PER_WALLET]))
    return fresh, newest


def register_buy(mint, wallet, timestamp):
    cluster = wallet_buy_tracker.setdefault(mint, [])
    if any(w == wallet for w, _ in cluster):
        return
    cluster.append((wallet, timestamp))
    print(f"⚡ [ON-CHAIN] {wallet[:4]}.. kaufte {mint[:6]}.. "
          f"({len(cluster)}/{SM_MIN_CLUSTER_SIZE} im Cluster)")


def poll_smart_wallets():
    """Liest On-Chain-Swaps der Smart Wallets und aktualisiert das Cluster-Dict."""
    now = time.time()

    # Veraltete Cluster-Eintraege aufraeumen
    for mint in list(wallet_buy_tracker.keys()):
        active = [(w, ts) for w, ts in wallet_buy_tracker[mint]
                  if (now - ts) < CLUSTER_WINDOW_SECONDS]
        if active:
            wallet_buy_tracker[mint] = active
        else:
            del wallet_buy_tracker[mint]

    for wallet in next_wallet_batch():
        fresh, newest = collect_new_signatures(wallet)
        if newest is None:
            continue

        # Erster Kontakt: nur Startpunkt merken, keine Altlasten handeln
        if wallet not in bootstrapped_wallets:
            bootstrapped_wallets.add(wallet)
            last_seen_tx_per_wallet[wallet] = newest
            print(f"[BOOTSTRAP] {wallet[:4]}.. synchronisiert (ab jetzt nur neue TX)")
            continue

        last_seen_tx_per_wallet[wallet] = newest

        for entry in fresh:
            block_time = entry.get("blockTime")
            if block_time and (now - float(block_time)) > CLUSTER_WINDOW_SECONDS:
                continue

            tx_info = rpc_call(
                "getTransaction",
                [entry["signature"],
                 {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
                context=f"{wallet[:4]}../tx"
            )
            if not isinstance(tx_info, dict):
                continue

            timestamp = float(tx_info.get("blockTime") or block_time or now)
            for mint in extract_purchased_mints(tx_info, wallet):
                register_buy(mint, wallet, timestamp)


def print_rpc_health():
    total = RPC_STATS["ok"] + RPC_STATS["error"] + RPC_STATS["rate_limited"]
    if total == 0:
        print("[RPC HEALTH] keine Calls abgesetzt")
        return
    print(f"[RPC HEALTH] ok={RPC_STATS['ok']} "
          f"fehler={RPC_STATS['error']} "
          f"ratelimit={RPC_STATS['rate_limited']} | "
          f"beobachtete Token im Cluster-Fenster: {len(wallet_buy_tracker)}")
    if RPC_STATS["ok"] == 0:
        print("[RPC HEALTH] ⚠️ KEIN einziger erfolgreicher Call - "
              "Strategie B ist blind. Eigenen RPC-Key als SOLANA_RPC_URL setzen.")


# ------------------------------------------------------------------- Persistence

def default_strat():
    return {
        "bankroll_sol": START_BANKROLL_PER_STRATEGY,
        "wins": 0,
        "losses": 0,
        "total_fees_sol": 0.0,
        "open_positions": {},
        "closed_positions": []
    }


def normalize_portfolio(data):
    if not isinstance(data, dict):
        data = {}
    strategies = data.get("strategies")
    if not isinstance(strategies, dict):
        strategies = {}
    for name in STRATEGY_NAMES:
        strat = strategies.get(name)
        if not isinstance(strat, dict):
            strat = default_strat()
        else:
            base = default_strat()
            for key, value in base.items():
                strat.setdefault(key, value)
        strategies[name] = strat
    data["strategies"] = strategies
    data.setdefault("trade_history_cooldown", {})
    data.setdefault(
        "bankroll_total_sol",
        round(sum(s["bankroll_sol"] for s in strategies.values()), 4)
    )
    return data


def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return normalize_portfolio(json.load(f))
        except Exception as err:
            print(f"[LOAD ERROR] {err} -> starte mit frischem Portfolio")
    return normalize_portfolio({})


def save_portfolio(data):
    total = sum(s["bankroll_sol"] for s in data["strategies"].values())
    data["bankroll_total_sol"] = round(total, 4)
    try:
        tmp_file = PORTFOLIO_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_file, PORTFOLIO_FILE)
    except Exception as err:
        print(f"[SAVE ERROR] {err}")


def prune_cooldowns(portfolio):
    cooldowns = portfolio.setdefault("trade_history_cooldown", {})
    cutoff = time.time() - (TOKEN_COOLDOWN_MINUTES * 60)
    for addr in [a for a, ts in cooldowns.items() if float(ts or 0) < cutoff]:
        del cooldowns[addr]


def git_push_portfolio():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email",
                        "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", PORTFOLIO_FILE], check=False)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Update 3-strategy portfolio state [skip ci]"], check=False)
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
            subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception as err:
        print(f"[GIT ERROR] {err}")


# ----------------------------------------------------------------------- Discord

def send_discord_raw(title, desc, color):
    if not DISCORD_WEBHOOK_URL:
        print(f"[DISCORD OFF] {title}")
        return
    embed = {
        "title": title,
        "description": desc,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        SESSION.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=6)
    except Exception as err:
        print(f"[DISCORD ERROR] {err}")


def get_strat_stats(strat_data):
    wins = strat_data.get("wins", 0)
    losses = strat_data.get("losses", 0)
    total = wins + losses
    win_rate = (wins / total * 100.0) if total > 0 else 0.0
    return f"{wins}W / {losses}L ({win_rate:.1f}%)"


# ------------------------------------------------------------------- Scan Common

def strategy_can_trade(portfolio, strat_name):
    strat = portfolio["strategies"][strat_name]
    if len(strat["open_positions"]) >= MAX_POSITIONS_PER_STRATEGY:
        return False
    if strat["bankroll_sol"] < SCOUT_SIZE_SOL:
        return False
    return True


def is_blocked(portfolio, strat_name, token_addr, now_ts):
    if not token_addr:
        return True
    if token_addr in portfolio["strategies"][strat_name]["open_positions"]:
        return True
    cooldowns = portfolio.setdefault("trade_history_cooldown", {})
    last_trade = float(cooldowns.get(token_addr, 0) or 0)
    return (now_ts - last_trade) < (TOKEN_COOLDOWN_MINUTES * 60)


# ------------------------------------------------------------------- Strategie A

def scan_cto(portfolio, sol_price):
    if not strategy_can_trade(portfolio, "CTO"):
        return

    now_ts = time.time()
    data = api_get("https://api.dexscreener.com/token-boosts/latest/v1")
    if not isinstance(data, list):
        return
    boosts = [i.get("tokenAddress") for i in data
              if isinstance(i, dict) and i.get("chainId") == "solana"][:30]

    for token_addr in boosts:
        if is_blocked(portfolio, "CTO", token_addr, now_ts):
            continue

        pair = fetch_best_pair(token_addr)
        if not pair:
            continue

        pair_created = pair.get("pairCreatedAt") or 0
        if not pair_created:
            continue
        age_hours = (now_ts * 1000.0 - float(pair_created)) / (1000.0 * 3600.0)
        if not (CTO_MIN_AGE_HOURS <= age_hours <= CTO_MAX_AGE_HOURS):
            continue

        lowest_drawdown = min(pair_price_change(pair, "h24"), pair_price_change(pair, "h6"))
        if not (CTO_MIN_DRAWDOWN <= lowest_drawdown <= CTO_MAX_DRAWDOWN):
            continue

        m5_change = pair_price_change(pair, "m5")
        m5_buys, m5_sells = pair_txns_m5(pair)

        if m5_change >= 4.0 and m5_buys >= 6 and m5_buys > m5_sells:
            reason = f"Re-Accumulation ({lowest_drawdown:.1f}% Dip, +{m5_change:.1f}% 5m)"
            execute_entry(portfolio, "CTO", token_addr, pair, reason)
            break


# ------------------------------------------------------------------- Strategie B

def scan_smart_money(portfolio, sol_price):
    if not wallet_buy_tracker:
        return
    if not strategy_can_trade(portfolio, "SMART_MONEY"):
        return

    now_ts = time.time()

    # Groesstes Cluster zuerst
    candidates = sorted(wallet_buy_tracker.items(), key=lambda kv: len(kv[1]), reverse=True)

    for token_addr, cluster in candidates:
        if len(cluster) < SM_MIN_CLUSTER_SIZE:
            continue
        if is_blocked(portfolio, "SMART_MONEY", token_addr, now_ts):
            continue

        pair = fetch_best_pair(token_addr)
        if not pair:
            continue

        wallets = " und ".join(f"{w[:4]}.." for w, _ in cluster[:SM_MIN_CLUSTER_SIZE])
        reason = f"Cluster ({len(cluster)} Wallets: {wallets})"
        execute_entry(portfolio, "SMART_MONEY", token_addr, pair, reason)
        break


# ------------------------------------------------------------------- Strategie C

def scan_curve_scalp(portfolio, sol_price):
    if not strategy_can_trade(portfolio, "SCALP_CURVE"):
        return

    now_ts = time.time()
    data = api_get("https://api.dexscreener.com/latest/dex/search?q=pumpswap")
    if not isinstance(data, dict):
        return
    pairs = data.get("pairs") or []

    for pair in pairs[:25]:
        token_addr = (pair.get("baseToken") or {}).get("address")
        if is_blocked(portfolio, "SCALP_CURVE", token_addr, now_ts):
            continue

        curve_pct = min((pair_mcap(pair) / CURVE_GRADUATION_MCAP) * 100.0, 100.0)
        if not (SCALP_MIN_CURVE <= curve_pct <= SCALP_MAX_CURVE):
            continue

        m5_buys, m5_sells = pair_txns_m5(pair)
        if m5_buys >= 5 and m5_buys > m5_sells:
            reason = f"Pre-Graduation Curve @ {curve_pct:.1f}%"
            execute_entry(portfolio, "SCALP_CURVE", token_addr, pair, reason)
            break


# ------------------------------------------------------------------------- Entry

def execute_entry(portfolio, strat_name, token_addr, pair, reason_desc):
    strat = portfolio["strategies"][strat_name]
    symbol = str((pair.get("baseToken") or {}).get("symbol") or "TOKEN").upper()
    price_usd = float(pair.get("priceUsd") or 0.0)
    dex_name = str(pair.get("dexId") or "DEX").upper()
    mcap = pair_mcap(pair)
    liq = pair_liquidity_usd(pair)
    pair_url = f"https://dexscreener.com/solana/{pair.get('pairAddress')}"

    if price_usd <= 0 or price_usd > 1000.0:
        return

    strat["bankroll_sol"] = round(strat["bankroll_sol"] - SCOUT_SIZE_SOL, 4)
    portfolio.setdefault("trade_history_cooldown", {})[token_addr] = time.time()

    strat["open_positions"][token_addr] = {
        "symbol": symbol,
        "dex": dex_name,
        "entry_price": price_usd,
        "highest_price": price_usd,
        "entry_time": time.time(),
        "invested_sol": SCOUT_SIZE_SOL,
        "url": pair_url,
        "mcap_at_entry": mcap
    }

    desc = (
        f"**Strategie:** `{strat_name}` | **Trigger:** {reason_desc}\n"
        f"**Symbol:** {symbol} ({dex_name})\n"
        f"**MCap:** ${mcap:,.0f} | **LP:** ${liq:,.0f}\n"
        f"**Einsatz:** {SCOUT_SIZE_SOL:.4f} SOL @ ${price_usd:.8f}\n"
        f"-------------------\n"
        f"[DexScreener Live-Chart]({pair_url})\n"
        f"**Sub-Bankroll:** {strat['bankroll_sol']:.4f} SOL\n"
        f"**Strategie-Stats:** {get_strat_stats(strat)}"
    )

    send_discord_raw(f"🎯 [{strat_name}] Entry: {symbol}", desc, 0x3B82F6)
    save_portfolio(portfolio)


# --------------------------------------------------------------------- Exit Logic

def decide_exit(strat_name, pnl_pct, peak_pct, hold_hours, pair):
    if strat_name == "CTO":
        if peak_pct >= CTO_TRAILING_ACT and (peak_pct - pnl_pct) >= CTO_TRAILING_DIST:
            return f"CTO_TRAILING_TP (+{pnl_pct:.1f}%)"
        if pnl_pct <= CTO_SL_PCT:
            return f"CTO_HARD_STOP ({pnl_pct:.1f}%)"

    elif strat_name == "SMART_MONEY":
        if peak_pct >= SM_TRAILING_ACT and (peak_pct - pnl_pct) >= SM_TRAILING_DIST:
            return f"SM_TRAILING_TP (+{pnl_pct:.1f}%)"
        if pnl_pct <= SM_SL_PCT:
            return f"SM_HARD_STOP ({pnl_pct:.1f}%)"

    elif strat_name == "SCALP_CURVE":
        curve_pct = (pair_mcap(pair) / CURVE_GRADUATION_MCAP) * 100.0
        if pnl_pct >= SCALP_TARGET_TP:
            return f"SCALP_TP (+{pnl_pct:.1f}%)"
        if curve_pct >= SCALP_FORCE_EXIT_CURVE:
            return f"CURVE_PRE_GRADUATION_EXIT ({pnl_pct:+.1f}%)"
        if pnl_pct <= SCALP_SL_PCT:
            return f"SCALP_HARD_STOP ({pnl_pct:.1f}%)"

    if hold_hours >= MAX_HOLD_HOURS:
        return f"TIMEOUT ({pnl_pct:.1f}%)"

    return None


def close_position(portfolio, strat_name, pos, pnl_pct, peak_pct, exit_reason, sol_price):
    strat = portfolio["strategies"][strat_name]
    invested_sol = float(pos.get("invested_sol", SCOUT_SIZE_SOL))

    pnl_sol = invested_sol * (pnl_pct / 100.0) - SIMULATED_FEE_SOL
    pnl_usd = pnl_sol * sol_price

    strat["bankroll_sol"] = round(strat["bankroll_sol"] + invested_sol + pnl_sol, 4)
    strat["total_fees_sol"] = round(strat["total_fees_sol"] + SIMULATED_FEE_SOL, 4)

    if pnl_sol > 0:
        strat["wins"] += 1
        color = 0x10B981
    else:
        strat["losses"] += 1
        color = 0xEF4444

    desc = (
        f"**Strategie:** `{strat_name}` | {exit_reason}\n"
        f"**Net PnL:** {pnl_sol:+.4f} SOL ({pnl_usd:+.2f} USD)\n"
        f"**Peak Gain:** {peak_pct:+.1f}%\n"
        f"-------------------\n"
        f"[DexScreener Live-Chart]({pos.get('url')})\n"
        f"**Sub-Bankroll:** {strat['bankroll_sol']:.4f} SOL\n"
        f"**Strategie-Stats:** {get_strat_stats(strat)}"
    )

    send_discord_raw(f"Trade Closed: [{strat_name}] {pos['symbol']}", desc, color)

    strat["closed_positions"].append({
        "symbol": pos["symbol"],
        "strategy": strat_name,
        "pnl_pct": round(pnl_pct, 2),
        "pnl_sol": round(pnl_sol, 4),
        "exit_reason": exit_reason,
        "closed_at": datetime.now(timezone.utc).isoformat()
    })


def manage_strategy_positions(portfolio, sol_price):
    for strat_name in STRATEGY_NAMES:
        strat = portfolio["strategies"][strat_name]
        open_pos = strat["open_positions"]
        to_remove = []

        for addr, pos in list(open_pos.items()):
            entry_price = float(pos.get("entry_price") or 0.0)
            if entry_price <= 0:
                to_remove.append(addr)
                continue

            hold_hours = (time.time() - float(pos.get("entry_time", time.time()))) / 3600.0
            highest_price = float(pos.get("highest_price", entry_price))
            pair = fetch_best_pair(addr)
            curr_price = float(pair.get("priceUsd") or 0.0) if pair else 0.0

            if curr_price <= 0:
                if hold_hours < MAX_HOLD_HOURS:
                    continue
                pnl_pct = -100.0
                peak_pct = min(((highest_price - entry_price) / entry_price) * 100.0, MAX_PNL_PCT)
                exit_reason = "DEAD_TOKEN_TIMEOUT (-100.0%)"
            else:
                if curr_price > highest_price:
                    highest_price = curr_price
                    pos["highest_price"] = curr_price

                pnl_pct = min(((curr_price - entry_price) / entry_price) * 100.0, MAX_PNL_PCT)
                peak_pct = min(((highest_price - entry_price) / entry_price) * 100.0, MAX_PNL_PCT)
                exit_reason = decide_exit(strat_name, pnl_pct, peak_pct, hold_hours, pair)

            if exit_reason:
                close_position(portfolio, strat_name, pos, pnl_pct, peak_pct, exit_reason, sol_price)
                to_remove.append(addr)

        for addr in to_remove:
            open_pos.pop(addr, None)

    save_portfolio(portfolio)


# -------------------------------------------------------------------------- Loop

def run_loop():
    start_time = time.time()
    print("🚀 [START] Multi-Strategy Bot aktiv (CTO, Smart-Money On-Chain, Scalp)")
    print(f"[CONFIG] RPC: {SOLANA_RPC_URL} | Wallets: {len(SMART_WALLETS)} | "
          f"Batch: {SMART_WALLET_BATCH_SIZE}/Loop")

    loop_count = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed >= SHIFT_DURATION_SECONDS:
            print(f"⏱️ [ENDE] Schicht beendet ({elapsed/3600:.2f}h).")
            break

        loop_count += 1

        try:
            sol_price = get_sol_usd_price()
            portfolio = load_portfolio()

            manage_strategy_positions(portfolio, sol_price)
            poll_smart_wallets()
            scan_cto(portfolio, sol_price)
            scan_smart_money(portfolio, sol_price)
            scan_curve_scalp(portfolio, sol_price)

            prune_cooldowns(portfolio)
            save_portfolio(portfolio)
            git_push_portfolio()

            if loop_count % 10 == 0:
                print_rpc_health()
        except Exception as err:
            print(f"[LOOP ERROR] {err}")

        time.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    run_loop()
