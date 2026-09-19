import os
import csv
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

PORTFOLIO_FILE = "portfolio.json"
REJECT_LOG_FILE = "rejected_candidates.csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Public RPC funktioniert, ist aber stark limitiert und blockt viele
# Rechenzentrums-IPs. Mit Helius/QuickNode-Key als Secret SOLANA_RPC_URL
# laeuft Strategie B (sobald aktiv) deutlich zuverlaessiger.
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL") or "https://api.mainnet-beta.solana.com"

# --------------------------------------------------------------- Grundparameter

SCOUT_SIZE_SOL = 0.20
MAX_POSITIONS_PER_STRATEGY = 3
TOKEN_COOLDOWN_MINUTES = 120
MAX_HOLD_HOURS = 4.0
LOOP_SLEEP_SECONDS = 35
SHIFT_DURATION_SECONDS = 20700        # 5h45, passend zum 6h-Cron
START_BANKROLL_PER_STRATEGY = 5.0
MAX_PNL_PCT = 400.0

STRATEGY_NAMES = ("CTO", "SMART_MONEY", "SCALP_CURVE")

# Strategie B ist deaktiviert: die Wallet-Auswahl in smart_wallets.csv beruht
# auf aktuellen Top-Holdern eines Runners, sortiert nach Aktivitaets-Zaehler.
# Das misst weder Kaufzeitpunkt noch realisierten Gewinn. Erst wieder
# aktivieren, wenn die Wallets ueber indizierte Daten validiert sind.
STRATEGY_ENABLED = {
    "CTO": True,
    "SMART_MONEY": False,
    "SCALP_CURVE": True,
}

# Budget einer deaktivierten Strategie einmalig auf die aktiven verteilen.
REBALANCE_DISABLED_BANKROLL = True

# ------------------------------------------------------- Kosten & Realitaetsnaehe

# Gebuehren pro abgeschlossenem Trade (Kauf + Verkauf, Netzwerk + Priority + DEX).
# Die Vorgaengerversion lag real bei 0.0073-0.0094 SOL; 0.002 war zu optimistisch.
SIMULATED_FEE_SOL = 0.008

# Slippage in Prozent. Beim Kauf moderat, beim Verkauf deutlich hoeher:
# CTO-Kandidaten (-55% bis -85% Drawdown) haben duenne Pools und wenig Nachfrage.
ENTRY_SLIPPAGE_PCT = {
    "CTO": 2.5,
    "SMART_MONEY": 2.5,
    "SCALP_CURVE": 3.0,
}
EXIT_SLIPPAGE_PCT = {
    "CTO": 12.0,
    "SMART_MONEY": 10.0,
    "SCALP_CURVE": 8.0,
}

# --------------------------------------------------- Einstiegsfilter (Pool-Guete)

# Gilt fuer alle Strategien: zu duenne oder tote Pools gar nicht erst anfassen.
MIN_LIQUIDITY_USD = 12000.0
MIN_VOL_H24_USD = 20000.0
# Liquiditaet im Verhaeltnis zur Bewertung. Unter 0.8% ist der Pool im
# Verhaeltnis zur Marktkapitalisierung so duenn, dass ein Exit kaum moeglich ist.
MIN_LIQ_TO_FDV_RATIO = 0.008

# A: CTO Settings
CTO_MIN_AGE_HOURS = 2.0
CTO_MAX_AGE_HOURS = 48.0
CTO_MIN_DRAWDOWN = -85.0
CTO_MAX_DRAWDOWN = -55.0
CTO_SL_PCT = -15.0
CTO_TRAILING_ACT = 35.0
CTO_TRAILING_DIST = 15.0

# B: Smart Money (inaktiv, Parameter bleiben fuer spaeter erhalten)
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
CLUSTER_WINDOW_SECONDS = 900

SMART_WALLET_BATCH_SIZE = 5
SIG_FETCH_LIMIT = 10
MAX_NEW_TX_PER_WALLET = 5
MIN_SOL_SPENT = 0.002
MIN_SOL_SPENT_LAMPORTS = int(MIN_SOL_SPENT * 1_000_000_000)

# C: Scalp Curve
SCALP_MIN_CURVE = 84.0
SCALP_MAX_CURVE = 93.0
SCALP_TARGET_TP = 25.0
SCALP_FORCE_EXIT_CURVE = 97.0
SCALP_SL_PCT = -18.0
CURVE_GRADUATION_MCAP = 69000.0

WSOL_MINT = "So11111111111111111111111111111111111111112"

IGNORED_MINTS = {
    WSOL_MINT,
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
}

REJECT_LOG_HEADERS = [
    "timestamp", "strategy", "symbol", "token_address", "reject_reason",
    "curve_pct", "drawdown_pct", "liquidity_usd", "fdv_usd", "m5_buys", "m5_sells"
]

# In-Memory State
wallet_buy_tracker = {}
last_seen_tx_per_wallet = {}
bootstrapped_wallets = set()
_wallet_cursor = 0

RPC_STATS = {"ok": 0, "error": 0, "rate_limited": 0}
SCAN_STATS = {}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "multi-strategy-paper-bot/2.0"})


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
        print(f"[RPC RATE-LIMIT] 429 bei {method} {context}")
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


def pair_vol_h24(pair):
    return float((pair.get("volume") or {}).get("h24") or 0.0)


def pair_txns_m5(pair):
    m5 = (pair.get("txns") or {}).get("m5") or {}
    return int(m5.get("buys") or 0), int(m5.get("sells") or 0)


def pair_price_change(pair, key):
    return float((pair.get("priceChange") or {}).get(key) or 0.0)


def pair_symbol(pair):
    return str((pair.get("baseToken") or {}).get("symbol") or "TOKEN").upper()


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


# ---------------------------------------------------------- Diagnose & Reject-Log

def note(reason):
    """Zaehlt Ablehnungsgruende fuer die Loop-Diagnose."""
    SCAN_STATS[reason] = SCAN_STATS.get(reason, 0) + 1


def track_range(key, value):
    """Merkt sich min/max eines beobachteten Wertes (z.B. curve_pct)."""
    lo_key, hi_key = f"{key}_min", f"{key}_max"
    if lo_key not in SCAN_STATS or value < SCAN_STATS[lo_key]:
        SCAN_STATS[lo_key] = value
    if hi_key not in SCAN_STATS or value > SCAN_STATS[hi_key]:
        SCAN_STATS[hi_key] = value


def init_reject_log():
    if not os.path.exists(REJECT_LOG_FILE):
        try:
            with open(REJECT_LOG_FILE, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(REJECT_LOG_HEADERS)
        except Exception as err:
            print(f"[REJECT LOG ERROR] {err}")


def log_rejection(strategy, pair, token_addr, reason,
                  curve_pct=None, drawdown_pct=None):
    """
    Protokolliert Kandidaten, die die Hauptbedingung erfuellt haben, aber an
    einer Nebenbedingung scheiterten. Beantwortet die Frage:
    'Filter zu eng' oder 'keine Gelegenheiten'?
    """
    try:
        m5_buys, m5_sells = pair_txns_m5(pair)
        with open(REJECT_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                strategy,
                pair_symbol(pair),
                token_addr,
                reason,
                f"{curve_pct:.1f}" if curve_pct is not None else "",
                f"{drawdown_pct:.1f}" if drawdown_pct is not None else "",
                f"{pair_liquidity_usd(pair):.0f}",
                f"{pair_mcap(pair):.0f}",
                m5_buys,
                m5_sells,
            ])
    except Exception as err:
        print(f"[REJECT LOG ERROR] {err}")


def print_scan_diagnostics():
    if not SCAN_STATS:
        print("[SCAN] keine Kandidaten gesehen")
        return
    counts = {k: v for k, v in SCAN_STATS.items() if not k.endswith(("_min", "_max"))}
    parts = [f"{k}={v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
    print("[SCAN] " + " | ".join(parts))

    if "curve_pct_min" in SCAN_STATS:
        print(f"[SCAN] beobachtete curve_pct: "
              f"{SCAN_STATS['curve_pct_min']:.1f} bis {SCAN_STATS['curve_pct_max']:.1f} "
              f"(Zielfenster {SCALP_MIN_CURVE}-{SCALP_MAX_CURVE})")
    if "drawdown_min" in SCAN_STATS:
        print(f"[SCAN] beobachtete Drawdowns: "
              f"{SCAN_STATS['drawdown_min']:.1f}% bis {SCAN_STATS['drawdown_max']:.1f}% "
              f"(Zielfenster {CTO_MIN_DRAWDOWN} bis {CTO_MAX_DRAWDOWN})")
    SCAN_STATS.clear()


def print_rpc_health():
    total = sum(RPC_STATS.values())
    if total == 0:
        return
    print(f"[RPC HEALTH] ok={RPC_STATS['ok']} fehler={RPC_STATS['error']} "
          f"ratelimit={RPC_STATS['rate_limited']}")


# ----------------------------------------------------------------- Pool-Pruefung

def pool_quality_ok(strategy, pair, token_addr):
    """Mindestanforderungen an den Pool. Schuetzt vor Rugs und toten Paaren."""
    liq = pair_liquidity_usd(pair)
    fdv = pair_mcap(pair)
    vol = pair_vol_h24(pair)

    if liq < MIN_LIQUIDITY_USD:
        note("pool_liq_zu_niedrig")
        log_rejection(strategy, pair, token_addr, f"LIQ_ZU_NIEDRIG ({liq:.0f} USD)")
        return False

    if vol < MIN_VOL_H24_USD:
        note("pool_vol_zu_niedrig")
        log_rejection(strategy, pair, token_addr, f"VOL24H_ZU_NIEDRIG ({vol:.0f} USD)")
        return False

    if fdv > 0 and (liq / fdv) < MIN_LIQ_TO_FDV_RATIO:
        ratio = (liq / fdv) * 100.0
        note("pool_liq_fdv_ratio")
        log_rejection(strategy, pair, token_addr, f"LIQ_FDV_RATIO ({ratio:.2f}%)")
        return False

    return True


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
            for key, value in default_strat().items():
                strat.setdefault(key, value)
        strategies[name] = strat
    data["strategies"] = strategies
    data.setdefault("trade_history_cooldown", {})
    data.setdefault("rebalanced_strategies", [])
    data.setdefault(
        "bankroll_total_sol",
        round(sum(s["bankroll_sol"] for s in strategies.values()), 4)
    )
    return data


def rebalance_disabled_strategies(portfolio):
    """
    Verteilt das Budget einer deaktivierten Strategie einmalig auf die aktiven.
    Laeuft nur, wenn die Strategie keine offenen Positionen hat, und merkt sich
    den Vorgang in portfolio['rebalanced_strategies'].
    """
    if not REBALANCE_DISABLED_BANKROLL:
        return

    done = portfolio.setdefault("rebalanced_strategies", [])
    active = [n for n in STRATEGY_NAMES if STRATEGY_ENABLED.get(n)]
    if not active:
        return

    for name in STRATEGY_NAMES:
        if STRATEGY_ENABLED.get(name) or name in done:
            continue
        strat = portfolio["strategies"][name]
        if strat["open_positions"]:
            continue
        amount = float(strat["bankroll_sol"])
        if amount <= 0:
            done.append(name)
            continue

        share = round(amount / len(active), 4)
        for target in active:
            portfolio["strategies"][target]["bankroll_sol"] = round(
                portfolio["strategies"][target]["bankroll_sol"] + share, 4
            )
        strat["bankroll_sol"] = 0.0
        done.append(name)
        print(f"[REBALANCE] {name} deaktiviert -> {amount:.4f} SOL auf "
              f"{', '.join(active)} verteilt ({share:.4f} SOL je Strategie)")


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


def git_push_state():
    try:
        subprocess.run(["git", "config", "--global", "user.name",
                        "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email",
                        "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", PORTFOLIO_FILE, REJECT_LOG_FILE], check=False)
        status = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m",
                            "Update portfolio + reject log [skip ci]"], check=False)
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
        "description": desc[:4000],
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
    if not STRATEGY_ENABLED.get(strat_name):
        return False
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
            note("cto_kein_pair")
            continue

        pair_created = pair.get("pairCreatedAt") or 0
        if not pair_created:
            note("cto_kein_erstellungsdatum")
            continue
        age_hours = (now_ts * 1000.0 - float(pair_created)) / (1000.0 * 3600.0)
        if not (CTO_MIN_AGE_HOURS <= age_hours <= CTO_MAX_AGE_HOURS):
            note("cto_alter_ausserhalb")
            continue

        drawdown = min(pair_price_change(pair, "h24"), pair_price_change(pair, "h6"))
        track_range("drawdown", drawdown)
        if not (CTO_MIN_DRAWDOWN <= drawdown <= CTO_MAX_DRAWDOWN):
            note("cto_drawdown_ausserhalb")
            continue

        # Ab hier: Hauptbedingung erfuellt -> Ablehnungen protokollieren
        if not pool_quality_ok("CTO", pair, token_addr):
            continue

        m5_change = pair_price_change(pair, "m5")
        m5_buys, m5_sells = pair_txns_m5(pair)

        if not (m5_change >= 4.0 and m5_buys >= 6 and m5_buys > m5_sells):
            note("cto_kein_surge")
            log_rejection("CTO", pair, token_addr,
                          f"KEIN_SURGE (m5 {m5_change:+.1f}%, {m5_buys}B/{m5_sells}S)",
                          drawdown_pct=drawdown)
            continue

        reason = f"Re-Accumulation ({drawdown:.1f}% Dip, +{m5_change:.1f}% 5m)"
        execute_entry(portfolio, "CTO", token_addr, pair, reason)
        break


# ------------------------------------------------------------------- Strategie B

def scan_smart_money(portfolio, sol_price):
    """Inaktiv - siehe STRATEGY_ENABLED. Logik bleibt fuer spaeter erhalten."""
    if not STRATEGY_ENABLED.get("SMART_MONEY"):
        return
    if not wallet_buy_tracker:
        return
    if not strategy_can_trade(portfolio, "SMART_MONEY"):
        return

    now_ts = time.time()
    candidates = sorted(wallet_buy_tracker.items(),
                        key=lambda kv: len(kv[1]), reverse=True)

    for token_addr, cluster in candidates:
        if len(cluster) < SM_MIN_CLUSTER_SIZE:
            continue
        if is_blocked(portfolio, "SMART_MONEY", token_addr, now_ts):
            continue

        pair = fetch_best_pair(token_addr)
        if not pair:
            continue
        if not pool_quality_ok("SMART_MONEY", pair, token_addr):
            continue

        wallets = " und ".join(f"{w[:4]}.." for w, _ in cluster[:SM_MIN_CLUSTER_SIZE])
        reason = f"Cluster ({len(cluster)} Wallets: {wallets})"
        execute_entry(portfolio, "SMART_MONEY", token_addr, pair, reason)
        break


# --------------------------------------------------- On-Chain Stream (fuer B)

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


def extract_purchased_mints(tx_info, wallet):
    """Nur echte Kaeufe: die Wallet muss SOL oder WSOL ausgegeben haben."""
    meta = tx_info.get("meta") or {}
    if meta.get("err") is not None:
        return []

    deltas = token_deltas_for_owner(meta, wallet)
    sol_out = lamports_spent_by_wallet(tx_info, wallet)
    wsol_out = -deltas.get(WSOL_MINT, 0.0)

    if not (sol_out >= MIN_SOL_SPENT_LAMPORTS or wsol_out >= MIN_SOL_SPENT):
        return []

    return [mint for mint, delta in deltas.items()
            if delta > 0 and mint not in IGNORED_MINTS]


def next_wallet_batch():
    global _wallet_cursor
    if not SMART_WALLETS:
        return []
    size = min(SMART_WALLET_BATCH_SIZE, len(SMART_WALLETS))
    batch = [SMART_WALLETS[(_wallet_cursor + i) % len(SMART_WALLETS)]
             for i in range(size)]
    _wallet_cursor = (_wallet_cursor + size) % len(SMART_WALLETS)
    return batch


def collect_new_signatures(wallet):
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

    return list(reversed(fresh[:MAX_NEW_TX_PER_WALLET])), newest


def register_buy(mint, wallet, timestamp):
    cluster = wallet_buy_tracker.setdefault(mint, [])
    if any(w == wallet for w, _ in cluster):
        return
    cluster.append((wallet, timestamp))
    print(f"⚡ [ON-CHAIN] {wallet[:4]}.. kaufte {mint[:6]}.. "
          f"({len(cluster)}/{SM_MIN_CLUSTER_SIZE} im Cluster)")


def poll_smart_wallets():
    if not STRATEGY_ENABLED.get("SMART_MONEY"):
        return

    now = time.time()
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

        if wallet not in bootstrapped_wallets:
            bootstrapped_wallets.add(wallet)
            last_seen_tx_per_wallet[wallet] = newest
            print(f"[BOOTSTRAP] {wallet[:4]}.. synchronisiert")
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


# ------------------------------------------------------------------- Strategie C

def scan_curve_scalp(portfolio, sol_price):
    if not strategy_can_trade(portfolio, "SCALP_CURVE"):
        return

    now_ts = time.time()
    data = api_get("https://api.dexscreener.com/latest/dex/search?q=pumpswap")
    if not isinstance(data, dict):
        return
    pairs = data.get("pairs") or []
    if not pairs:
        note("scalp_keine_pairs")
        return

    for pair in pairs[:25]:
        token_addr = (pair.get("baseToken") or {}).get("address")
        if is_blocked(portfolio, "SCALP_CURVE", token_addr, now_ts):
            continue

        fdv = pair_mcap(pair)
        curve_pct = min((fdv / CURVE_GRADUATION_MCAP) * 100.0, 100.0)
        track_range("curve_pct", curve_pct)

        if curve_pct >= 99.9:
            note("scalp_bereits_migriert")
            continue
        if not (SCALP_MIN_CURVE <= curve_pct <= SCALP_MAX_CURVE):
            note("scalp_curve_ausserhalb")
            continue

        if not pool_quality_ok("SCALP_CURVE", pair, token_addr):
            continue

        m5_buys, m5_sells = pair_txns_m5(pair)
        if not (m5_buys >= 5 and m5_buys > m5_sells):
            note("scalp_kein_momentum")
            log_rejection("SCALP_CURVE", pair, token_addr,
                          f"KEIN_MOMENTUM ({m5_buys}B/{m5_sells}S)",
                          curve_pct=curve_pct)
            continue

        reason = f"Pre-Graduation Curve @ {curve_pct:.1f}%"
        execute_entry(portfolio, "SCALP_CURVE", token_addr, pair, reason)
        break


# ------------------------------------------------------------------------- Entry

def execute_entry(portfolio, strat_name, token_addr, pair, reason_desc):
    strat = portfolio["strategies"][strat_name]
    symbol = pair_symbol(pair)
    signal_price = float(pair.get("priceUsd") or 0.0)
    dex_name = str(pair.get("dexId") or "DEX").upper()
    mcap = pair_mcap(pair)
    liq = pair_liquidity_usd(pair)
    pair_url = f"https://dexscreener.com/solana/{pair.get('pairAddress')}"

    if signal_price <= 0 or signal_price > 1000.0:
        return

    # Realistischer Fill: wir zahlen mehr als der angezeigte Kurs
    slippage = ENTRY_SLIPPAGE_PCT.get(strat_name, 2.5)
    fill_price = signal_price * (1.0 + slippage / 100.0)

    strat["bankroll_sol"] = round(strat["bankroll_sol"] - SCOUT_SIZE_SOL, 4)
    portfolio.setdefault("trade_history_cooldown", {})[token_addr] = time.time()

    strat["open_positions"][token_addr] = {
        "symbol": symbol,
        "dex": dex_name,
        "entry_signal_price": signal_price,
        "entry_fill_price": fill_price,
        "entry_slippage_pct": slippage,
        "highest_price": signal_price,
        "entry_time": time.time(),
        "invested_sol": SCOUT_SIZE_SOL,
        "url": pair_url,
        "mcap_at_entry": mcap,
        "liq_at_entry": liq
    }

    desc = (
        f"**Strategie:** `{strat_name}` | **Trigger:** {reason_desc}\n"
        f"**Symbol:** {symbol} ({dex_name})\n"
        f"**MCap:** ${mcap:,.0f} | **LP:** ${liq:,.0f}\n"
        f"**Signal-Kurs:** ${signal_price:.8f}\n"
        f"**Sim. Fill:** ${fill_price:.8f} (+{slippage:.1f}% Slippage)\n"
        f"**Einsatz:** {SCOUT_SIZE_SOL:.4f} SOL\n"
        f"-------------------\n"
        f"[DexScreener Live-Chart]({pair_url})\n"
        f"**Sub-Bankroll:** {strat['bankroll_sol']:.4f} SOL\n"
        f"**Strategie-Stats:** {get_strat_stats(strat)}"
    )

    send_discord_raw(f"🎯 [{strat_name}] Entry: {symbol}", desc, 0x3B82F6)
    save_portfolio(portfolio)


# --------------------------------------------------------------------- Exit Logic

def decide_exit(strat_name, pnl_pct, peak_pct, hold_hours, pair):
    """Entscheidet auf Basis des SIGNAL-Kurses - das ist, was der Bot sieht."""
    if strat_name == "CTO":
        if peak_pct >= CTO_TRAILING_ACT and (peak_pct - pnl_pct) >= CTO_TRAILING_DIST:
            return f"CTO_TRAILING_TP (Signal {pnl_pct:+.1f}%)"
        if pnl_pct <= CTO_SL_PCT:
            return f"CTO_HARD_STOP (Signal {pnl_pct:+.1f}%)"

    elif strat_name == "SMART_MONEY":
        if peak_pct >= SM_TRAILING_ACT and (peak_pct - pnl_pct) >= SM_TRAILING_DIST:
            return f"SM_TRAILING_TP (Signal {pnl_pct:+.1f}%)"
        if pnl_pct <= SM_SL_PCT:
            return f"SM_HARD_STOP (Signal {pnl_pct:+.1f}%)"

    elif strat_name == "SCALP_CURVE":
        curve_pct = (pair_mcap(pair) / CURVE_GRADUATION_MCAP) * 100.0
        if pnl_pct >= SCALP_TARGET_TP:
            return f"SCALP_TP (Signal {pnl_pct:+.1f}%)"
        if curve_pct >= SCALP_FORCE_EXIT_CURVE:
            return f"CURVE_PRE_GRADUATION_EXIT (Signal {pnl_pct:+.1f}%)"
        if pnl_pct <= SCALP_SL_PCT:
            return f"SCALP_HARD_STOP (Signal {pnl_pct:+.1f}%)"

    if hold_hours >= MAX_HOLD_HOURS:
        return f"TIMEOUT (Signal {pnl_pct:+.1f}%)"

    return None


def close_position(portfolio, strat_name, pos, signal_pnl_pct, peak_pct,
                   exit_signal_price, exit_reason, sol_price, dead_token=False):
    strat = portfolio["strategies"][strat_name]
    invested_sol = float(pos.get("invested_sol", SCOUT_SIZE_SOL))
    entry_fill = float(pos.get("entry_fill_price") or pos.get("entry_signal_price") or 0.0)

    exit_slippage = EXIT_SLIPPAGE_PCT.get(strat_name, 10.0)

    if dead_token or exit_signal_price <= 0 or entry_fill <= 0:
        exit_fill_price = 0.0
        real_pnl_pct = -100.0
    else:
        exit_fill_price = exit_signal_price * (1.0 - exit_slippage / 100.0)
        real_pnl_pct = min(((exit_fill_price - entry_fill) / entry_fill) * 100.0,
                           MAX_PNL_PCT)

    pnl_sol = invested_sol * (real_pnl_pct / 100.0) - SIMULATED_FEE_SOL
    pnl_usd = pnl_sol * sol_price

    # Trade, der waehrend einer Schichtpause durch den Stop gerutscht ist
    sl_thresholds = {"CTO": CTO_SL_PCT, "SMART_MONEY": SM_SL_PCT,
                     "SCALP_CURVE": SCALP_SL_PCT}
    gap_exit = bool(
        exit_reason.startswith(("TIMEOUT", "DEAD_TOKEN"))
        and signal_pnl_pct <= sl_thresholds.get(strat_name, -100.0)
    )

    strat["bankroll_sol"] = round(strat["bankroll_sol"] + invested_sol + pnl_sol, 4)
    strat["total_fees_sol"] = round(strat["total_fees_sol"] + SIMULATED_FEE_SOL, 4)

    if pnl_sol > 0:
        strat["wins"] += 1
        color = 0x10B981
    else:
        strat["losses"] += 1
        color = 0xEF4444

    slip_cost_pct = signal_pnl_pct - real_pnl_pct

    desc = (
        f"**Strategie:** `{strat_name}` | {exit_reason}\n"
        f"**Signal-PnL:** {signal_pnl_pct:+.1f}% | "
        f"**Real (nach Slippage):** {real_pnl_pct:+.1f}%\n"
        f"**Slippage-Kosten:** {slip_cost_pct:.1f} Prozentpunkte\n"
        f"**Net PnL:** {pnl_sol:+.4f} SOL ({pnl_usd:+.2f} USD, inkl. "
        f"{SIMULATED_FEE_SOL:.4f} SOL Fees)\n"
        f"**Peak (Signal):** {peak_pct:+.1f}%\n"
        + ("⚠️ **Gap-Exit:** Stop wurde in einer Pause ueberschritten\n" if gap_exit else "")
        + f"-------------------\n"
        f"[DexScreener Live-Chart]({pos.get('url')})\n"
        f"**Sub-Bankroll:** {strat['bankroll_sol']:.4f} SOL\n"
        f"**Strategie-Stats:** {get_strat_stats(strat)}"
    )

    send_discord_raw(f"Trade Closed: [{strat_name}] {pos['symbol']}", desc, color)

    strat["closed_positions"].append({
        "symbol": pos["symbol"],
        "strategy": strat_name,
        "signal_pnl_pct": round(signal_pnl_pct, 2),
        "real_pnl_pct": round(real_pnl_pct, 2),
        "entry_signal_price": pos.get("entry_signal_price"),
        "entry_fill_price": round(entry_fill, 10),
        "exit_signal_price": round(exit_signal_price, 10),
        "exit_fill_price": round(exit_fill_price, 10),
        "exit_slippage_pct": exit_slippage,
        "fees_sol": SIMULATED_FEE_SOL,
        "pnl_sol": round(pnl_sol, 4),
        "peak_pct": round(peak_pct, 2),
        "gap_exit": gap_exit,
        "exit_reason": exit_reason,
        "closed_at": datetime.now(timezone.utc).isoformat()
    })


def manage_strategy_positions(portfolio, sol_price):
    for strat_name in STRATEGY_NAMES:
        strat = portfolio["strategies"][strat_name]
        open_pos = strat["open_positions"]
        to_remove = []

        for addr, pos in list(open_pos.items()):
            # Alte Positionen ohne neue Felder migrieren
            if "entry_signal_price" not in pos and "entry_price" in pos:
                pos["entry_signal_price"] = pos["entry_price"]
                slip = ENTRY_SLIPPAGE_PCT.get(strat_name, 2.5)
                pos["entry_fill_price"] = pos["entry_price"] * (1.0 + slip / 100.0)

            entry_signal = float(pos.get("entry_signal_price") or 0.0)
            if entry_signal <= 0:
                to_remove.append(addr)
                continue

            hold_hours = (time.time() - float(pos.get("entry_time", time.time()))) / 3600.0
            highest_price = float(pos.get("highest_price", entry_signal))
            pair = fetch_best_pair(addr)
            curr_price = float(pair.get("priceUsd") or 0.0) if pair else 0.0

            if curr_price <= 0:
                if hold_hours < MAX_HOLD_HOURS:
                    continue
                signal_pnl = -100.0
                peak_pct = min(((highest_price - entry_signal) / entry_signal) * 100.0,
                               MAX_PNL_PCT)
                close_position(portfolio, strat_name, pos, signal_pnl, peak_pct,
                               0.0, "DEAD_TOKEN_TIMEOUT", sol_price, dead_token=True)
                to_remove.append(addr)
                continue

            if curr_price > highest_price:
                highest_price = curr_price
                pos["highest_price"] = curr_price

            signal_pnl = min(((curr_price - entry_signal) / entry_signal) * 100.0,
                             MAX_PNL_PCT)
            peak_pct = min(((highest_price - entry_signal) / entry_signal) * 100.0,
                           MAX_PNL_PCT)

            exit_reason = decide_exit(strat_name, signal_pnl, peak_pct,
                                      hold_hours, pair)
            if exit_reason:
                close_position(portfolio, strat_name, pos, signal_pnl, peak_pct,
                               curr_price, exit_reason, sol_price)
                to_remove.append(addr)

        for addr in to_remove:
            open_pos.pop(addr, None)

    save_portfolio(portfolio)


# -------------------------------------------------------------------------- Loop

def run_loop():
    start_time = time.time()
    loop_count = 0

    init_reject_log()

    active = [n for n in STRATEGY_NAMES if STRATEGY_ENABLED.get(n)]
    inactive = [n for n in STRATEGY_NAMES if not STRATEGY_ENABLED.get(n)]

    print("🚀 [START] Multi-Strategy Paper-Bot v2")
    print(f"[CONFIG] Aktiv: {', '.join(active) or 'keine'}")
    if inactive:
        print(f"[CONFIG] Inaktiv: {', '.join(inactive)}")
    print(f"[CONFIG] Fees {SIMULATED_FEE_SOL:.4f} SOL/Trade | "
          f"Exit-Slippage {EXIT_SLIPPAGE_PCT} | RPC {SOLANA_RPC_URL}")

    while True:
        elapsed = time.time() - start_time
        if elapsed >= SHIFT_DURATION_SECONDS:
            print(f"⏱️ [ENDE] Schicht beendet ({elapsed/3600:.2f}h).")
            break

        loop_count += 1

        try:
            sol_price = get_sol_usd_price()
            portfolio = load_portfolio()
            rebalance_disabled_strategies(portfolio)

            manage_strategy_positions(portfolio, sol_price)
            poll_smart_wallets()
            scan_cto(portfolio, sol_price)
            scan_smart_money(portfolio, sol_price)
            scan_curve_scalp(portfolio, sol_price)

            prune_cooldowns(portfolio)
            save_portfolio(portfolio)
            git_push_state()

            if loop_count % 10 == 0:
                print_scan_diagnostics()
                print_rpc_health()
        except Exception as err:
            print(f"[LOOP ERROR] {err}")

        time.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    run_loop()
