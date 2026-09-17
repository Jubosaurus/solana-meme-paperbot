import os
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

PORTFOLIO_FILE = "portfolio.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- Allokation & Standard-Settings ---
SCOUT_SIZE_SOL = 0.20
SIMULATED_FEE_SOL = 0.002
MAX_POSITIONS_PER_STRATEGY = 3
TOKEN_COOLDOWN_MINUTES = 120

# --- Strategie-Parameter ---
# A: CTO (Re-Accumulation)
CTO_MIN_AGE_HOURS = 2.0
CTO_MAX_AGE_HOURS = 48.0
CTO_MIN_DRAWDOWN = -85.0
CTO_MAX_DRAWDOWN = -55.0
CTO_SL_PCT = -15.0
CTO_TRAILING_ACT = 35.0
CTO_TRAILING_DIST = 15.0

# B: Smart Money Cluster (Wallets aus CSV)
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

# C: Pre-Graduation Scalp
SCALP_MIN_CURVE = 84.0
SCALP_MAX_CURVE = 93.0
SCALP_TARGET_TP = 25.0
SCALP_FORCE_EXIT_CURVE = 97.0
SCALP_SL_PCT = -18.0

# In-Memory Cache für Smart-Wallet Signal-Cluster: {token_addr: [wallet_list]}
wallet_buy_tracker = {}

def get_sol_usd_price():
    try:
        r = requests.get("https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112", timeout=4)
        if r.status_code == 200:
            pairs = r.json().get("pairs") or []
            if pairs:
                return float(pairs[0].get("priceUsd") or 100.0)
    except Exception:
        pass
    return 100.0

def load_portfolio():
    default_strat = lambda: {
        "bankroll_sol": 5.0,
        "wins": 0,
        "losses": 0,
        "total_fees_sol": 0.0,
        "open_positions": {},
        "closed_positions": []
    }
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "strategies" not in data:
                    data = {
                        "bankroll_total_sol": 15.0,
                        "strategies": {
                            "CTO": default_strat(),
                            "SMART_MONEY": default_strat(),
                            "SCALP_CURVE": default_strat()
                        },
                        "trade_history_cooldown": {}
                    }
                return data
        except Exception:
            pass
    return {
        "bankroll_total_sol": 15.0,
        "strategies": {
            "CTO": default_strat(),
            "SMART_MONEY": default_strat(),
            "SCALP_CURVE": default_strat()
        },
        "trade_history_cooldown": {}
    }

def save_portfolio(data):
    total = sum(s["bankroll_sol"] for s in data["strategies"].values())
    data["bankroll_total_sol"] = round(total, 4)
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def git_push_portfolio():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", PORTFOLIO_FILE], check=False)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Update 3-strategy portfolio state [skip ci]"], check=False)
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
            subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception as err:
        print(f"[GIT ERROR] {err}")

def send_discord_raw(title, desc, color):
    if not DISCORD_WEBHOOK_URL:
        return
    embed = {
        "title": title,
        "description": desc,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=6)
    except Exception as e:
        print(f"[DISCORD ERROR] {e}")

def get_strat_stats(strat_data):
    w = strat_data.get("wins", 0)
    l = strat_data.get("losses", 0)
    tot = w + l
    wr = (w / tot * 100.0) if tot > 0 else 0.0
    return f"{w}W / {l}L ({wr:.1f}%)"

# --- STRATEGIE A: CTO / Re-Accumulation ---
def scan_cto(portfolio, sol_price):
    strat = portfolio["strategies"]["CTO"]
    if len(strat["open_positions"]) >= MAX_POSITIONS_PER_STRATEGY or strat["bankroll_sol"] < SCOUT_SIZE_SOL:
        return

    cooldowns = portfolio.get("trade_history_cooldown", {})
    now_ts = time.time()

    try:
        r = requests.get("https://api.dexscreener.com/token-boosts/latest/v1", timeout=5)
        if r.status_code != 200:
            return
        boosts = [i.get("tokenAddress") for i in r.json() if i.get("chainId") == "solana"][:30]
    except Exception:
        return

    for token_addr in boosts:
        if token_addr in strat["open_positions"]:
            continue
        if (now_ts - cooldowns.get(token_addr, 0)) < (TOKEN_COOLDOWN_MINUTES * 60):
            continue

        try:
            res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}", timeout=5)
            if res.status_code != 200:
                continue
            pairs = res.json().get("pairs") or []
            if not pairs:
                continue
            pair = pairs[0]
        except Exception:
            continue

        pair_created = pair.get("pairCreatedAt", 0)
        age_hours = (now_ts * 1000 - pair_created) / (1000 * 3600) if pair_created else 0.0

        if not (CTO_MIN_AGE_HOURS <= age_hours <= CTO_MAX_AGE_HOURS):
            continue

        h24_change = float(pair.get("priceChange", {}).get("h24", 0.0) or 0.0)
        h6_change = float(pair.get("priceChange", {}).get("h6", 0.0) or 0.0)
        lowest_drawdown = min(h24_change, h6_change)

        if not (CTO_MIN_DRAWDOWN <= lowest_drawdown <= CTO_MAX_DRAWDOWN):
            continue

        m5_change = float(pair.get("priceChange", {}).get("m5", 0.0) or 0.0)
        m5_buys = int(pair.get("txns", {}).get("m5", {}).get("buys", 0) or 0)
        m5_sells = int(pair.get("txns", {}).get("m5", {}).get("sells", 0) or 0)

        if m5_change >= 4.0 and m5_buys >= 6 and m5_buys > m5_sells:
            execute_entry(portfolio, "CTO", token_addr, pair, sol_price, f"Re-Accumulation ({lowest_drawdown:.1f}% Dip, +{m5_change:.1f}% 5m)")
            break

# --- STRATEGIE B: Smart-Money-Cluster ---
def scan_smart_money(portfolio, sol_price):
    strat = portfolio["strategies"]["SMART_MONEY"]
    if len(strat["open_positions"]) >= MAX_POSITIONS_PER_STRATEGY or strat["bankroll_sol"] < SCOUT_SIZE_SOL:
        return

    cooldowns = portfolio.get("trade_history_cooldown", {})
    now_ts = time.time()

    try:
        r = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=5)
        if r.status_code != 200:
            return
        tokens = [i.get("tokenAddress") for i in r.json() if i.get("chainId") == "solana"][:20]
    except Exception:
        return

    for token_addr in tokens:
        if token_addr in strat["open_positions"]:
            continue
        if (now_ts - cooldowns.get(token_addr, 0)) < (TOKEN_COOLDOWN_MINUTES * 60):
            continue

        cluster = wallet_buy_tracker.get(token_addr, [])
        if len(cluster) >= 2:
            try:
                res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}", timeout=5)
                if res.status_code == 200 and res.json().get("pairs"):
                    pair = res.json()["pairs"][0]
                    w1 = str(cluster[0])[:4]
                    w2 = str(cluster[1])[:4]
                    reason_msg = f"Cluster ({len(cluster)} Wallets: {w1}.. & {w2}..)"
                    execute_entry(portfolio, "SMART_MONEY", token_addr, pair, sol_price, reason_msg)
                    break
            except Exception:
                continue

# --- STRATEGIE C: Pre-Graduation Scalp ---
def scan_curve_scalp(portfolio, sol_price):
    strat = portfolio["strategies"]["SCALP_CURVE"]
    if len(strat["open_positions"]) >= MAX_POSITIONS_PER_STRATEGY or strat["bankroll_sol"] < SCOUT_SIZE_SOL:
        return

    cooldowns = portfolio.get("trade_history_cooldown", {})
    now_ts = time.time()

    try:
        r = requests.get("https://api.dexscreener.com/latest/dex/search?q=pumpswap", timeout=5)
        if r.status_code != 200:
            return
        pairs = r.json().get("pairs") or []
    except Exception:
        return

    for pair in pairs[:25]:
        token_addr = pair.get("baseToken", {}).get("address")
        if not token_addr or token_addr in strat["open_positions"]:
            continue
        if (now_ts - cooldowns.get(token_addr, 0)) < (TOKEN_COOLDOWN_MINUTES * 60):
            continue

        mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
        curve_pct = min((mcap / 69000.0) * 100.0, 100.0)

        if SCALP_MIN_CURVE <= curve_pct <= SCALP_MAX_CURVE:
            m5_buys = int(pair.get("txns", {}).get("m5", {}).get("buys", 0) or 0)
            m5_sells = int(pair.get("txns", {}).get("m5", {}).get("sells", 0) or 0)
            if m5_buys >= 5 and m5_buys > m5_sells:
                execute_entry(portfolio, "SCALP_CURVE", token_addr, pair, sol_price, f"Pre-Graduation Curve @ {curve_pct:.1f}%")
                break

# --- Orderausführung & Discord ---
def execute_entry(portfolio, strat_name, token_addr, pair, sol_price, reason_desc):
    strat = portfolio["strategies"][strat_name]
    symbol = pair.get("baseToken", {}).get("symbol", "TOKEN").upper()
    price_usd = float(pair.get("priceUsd") or 0.0)
    dex_name = pair.get("dexId", "DEX").upper()
    mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
    liq = float(pair.get("liquidity", {}).get("usd") or 0.0)
    pair_url = f"https://dexscreener.com/solana/{pair.get('pairAddress')}"

    if price_usd <= 0 or price_usd > 1000.0:
        return

    strat["bankroll_sol"] = round(strat["bankroll_sol"] - SCOUT_SIZE_SOL, 4)
    portfolio["trade_history_cooldown"][token_addr] = time.time()

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
        f"**MCap:** ${mcap:,.0f} \vert{} **LP:**${liq:,.0f}\n"
        f"**Einsatz:** {SCOUT_SIZE_SOL:.4f} SOL @ ${price_usd:.8f}\n"
        f"-------------------\n"
        f"[📈 DexScreener Live-Chart]({pair_url})\n"
        f"💰 **Sub-Bankroll ({strat_name}):** {strat['bankroll_sol']:.4f} SOL\n"
        f"📊 **Strategie-Stats:** {get_strat_stats(strat)}"
    )

    send_discord_raw(f"🎯 [{strat_name}] Entry: {symbol}", desc, 0x3B82F6)
    save_portfolio(portfolio)

def manage_strategy_positions(portfolio, sol_price):
    for strat_name, strat in portfolio["strategies"].items():
        open_pos = strat["open_positions"]
        closed = strat["closed_positions"]
        to_remove = []

        for addr, pos in open_pos.items():
            try:
                res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}", timeout=5)
                if res.status_code != 200:
                    continue
                pairs = res.json().get("pairs") or []
                if not pairs:
                    continue
                curr_price = float(pairs[0].get("priceUsd") or 0.0)
            except Exception:
                continue

            entry_price = pos["entry_price"]
            raw_pnl_pct = ((curr_price - entry_price) / entry_price) * 100.0
            pnl_pct = min(raw_pnl_pct, 400.0)

            if curr_price > pos.get("highest_price", entry_price):
                pos["highest_price"] = curr_price
            peak_pct = min(((pos["highest_price"] - entry_price) / entry_price) * 100.0, 400.0)

            hold_hours = (time.time() - pos["entry_time"]) / 3600.0
            invested_sol = pos.get("invested_sol", SCOUT_SIZE_SOL)
            exit_reason = None

            if strat_name == "CTO":
                if peak_pct >= CTO_TRAILING_ACT and (peak_pct - pnl_pct) >= CTO_TRAILING_DIST:
                    exit_reason = f"CTO_TRAILING_TP (+{pnl_pct:.1f}%)"
                elif pnl_pct <= CTO_SL_PCT:
                    exit_reason = f"CTO_HARD_STOP ({pnl_pct:.1f}%)"

            elif strat_name == "SMART_MONEY":
                if peak_pct >= SM_TRAILING_ACT and (peak_pct - pnl_pct) >= SM_TRAILING_DIST:
                    exit_reason = f"SM_TRAILING_TP (+{pnl_pct:.1f}%)"
                elif pnl_pct <= SM_SL_PCT:
                    exit_reason = f"SM_HARD_STOP ({pnl_pct:.1f}%)"

            elif strat_name == "SCALP_CURVE":
                mcap = float(pairs[0].get("fdv") or pairs[0].get("marketCap") or 0.0)
                curve_pct = (mcap / 69000.0) * 100.0
                if pnl_pct >= SCALP_TARGET_TP:
                    exit_reason = f"SCALP_TP (+{pnl_pct:.1f}%)"
                elif curve_pct >= SCALP_FORCE_EXIT_CURVE:
                    exit_reason = f"CURVE_PRE_GRADUATION_EXIT ({pnl_pct:+.1f}%)"
                elif pnl_pct <= SCALP_SL_PCT:
                    exit_reason = f"SCALP_HARD_STOP ({pnl_pct:.1f}%)"

            if hold_hours >= 4.0 and not exit_reason:
                exit_reason = f"TIMEOUT ({pnl_pct:.1f}%)"

            if exit_reason:
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
                    f"**Peak Gain:** +{peak_pct:.1f}%\n"
                    f"-------------------\n"
                    f"[📈 DexScreener Live-Chart]({pos.get('url')})\n"
                    f"💰 **Sub-Bankroll ({strat_name}):** {strat['bankroll_sol']:.4f} SOL\n"
                    f"📊 **Strategie-Stats:** {get_strat_stats(strat)}"
                )

                send_discord_raw(f"Trade Closed: [{strat_name}] {pos['symbol']}", desc, color)
                closed.append({
                    "symbol": pos["symbol"],
                    "strategy": strat_name,
                    "pnl_pct": round(pnl_pct, 2),
                    "pnl_sol": round(pnl_sol, 4),
                    "exit_reason": exit_reason,
                    "closed_at": datetime.now(timezone.utc).isoformat()
                })
                to_remove.append(addr)

        for addr in to_remove:
            del open_pos[addr]

    save_portfolio(portfolio)

def run_loop():
    start_time = time.time()
    max_duration_seconds = 5 * 3600 - 300

    print("🚀 [START] Multi-Strategy Bot aktiv (3x 5.0 SOL: CTO, Smart-Money, Scalp)...")

    while True:
        elapsed = time.time() - start_time
        if elapsed >= max_duration_seconds:
            print(f"⏱️ [ENDE] Schicht beendet ({elapsed/3600:.2f}h).")
            break

        try:
            sol_price = get_sol_usd_price()
            portfolio = load_portfolio()

            manage_strategy_positions(portfolio, sol_price)
            scan_cto(portfolio, sol_price)
            scan_smart_money(portfolio, sol_price)
            scan_curve_scalp(portfolio, sol_price)

            save_portfolio(portfolio)
            git_push_portfolio()
        except Exception as e:
            print(f"[LOOP ERROR] {e}")

        time.sleep(35)

if __name__ == "__main__":
    run_loop()
