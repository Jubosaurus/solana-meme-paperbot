import os
import time
import csv
import random
import subprocess
import requests
from datetime import datetime, timezone

# --- DATEIEN & GRUNDKONFIGURATION ---
CSV_TRADES = "solana_paper_trades_v2.csv"
CSV_REJECTS = "rejected_rugs_tracking.csv"

STARTING_SOL = 5.0000
MAX_ALLOCATION_PER_COIN_SOL = 0.25  # 5% Portfolio-Regel (Phase 3)[span_0](start_span)[span_0](end_span)
MAX_OPEN_TRADES = int(STARTING_SOL / MAX_ALLOCATION_PER_COIN_SOL)
MAX_TRACKED_REJECTS = 15
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- FILTER- & STRATEGIE-PARAMETER (Washed & FXM Synthese) ---
ALLOWED_DEXES = {"raydium", "meteora"}  # Kein PumpSwap (Bonding-Curves blockiert)[span_1](start_span)[span_1](end_span)
ALLOWED_QUOTE_SYMBOLS = {"SOL", "WSOL"} # Zwingend SOL-Pairs (keine Sub-Tokens wie STONK)
MIN_PAIR_AGE_HOURS = 1.5                # Mind. 1.5h alt (Sniper & Dev-Dumps vorbei)[span_2](start_span)[span_2](end_span)
MIN_MCAP_USD = 150000.0                 # Washed Sweet Spot: $150k bis $3.5M[span_3](start_span)[span_3](end_span)
MAX_MCAP_USD = 3500000.0
MIN_LIQ_TO_MCAP_RATIO = 0.10            # Mind. 10% Liquiditätsquote[span_4](start_span)[span_4](end_span)
MIN_VOL24H_TO_MCAP_RATIO = 0.05         # Mind. 5% 24h-Volumen[span_5](start_span)[span_5](end_span)
MIN_BUYS_5M = 35                        # Transaktions-Dichte[span_6](start_span)[span_6](end_span)
MIN_VOLUME_SURGE_MULTIPLIER = 2.0       # 5m-Volumen mind. 2x 1h-Avg[span_7](start_span)[span_7](end_span)

# Tiered DCA (25% Scout / 35% Dip / 40% Momentum)[span_8](start_span)[span_8](end_span)
DCA_SCOUT_PCT = 0.25                    # 0.0625 SOL
DCA_DIP_PCT = 0.35                      # 0.0875 SOL
DCA_MOMENTUM_PCT = 0.40                 # 0.1000 SOL

# Exits & Stops[span_9](start_span)[span_9](end_span)[span_10](start_span)[span_10](end_span)
STOP_LOSS_HARD_PCT = -0.22              # Straffer Hard Stop bei -22%[span_11](start_span)[span_11](end_span)
TRAILING_TRIGGER_PCT = 0.35             # Trailing-Stop aktiviert erst ab +35% Peak[span_12](start_span)[span_12](end_span)
TRAILING_OFFSET_PCT = 0.15              # 15% Abstand vom Peak
BREAKEVEN_PROTECT_PCT = 0.03            # Exit niemals unter +3%
TIME_STOP_SECONDS = 7200                # 2 Stunden Zeitlimit

# Slippage & Gebühren
SLIPPAGE_BUY_MIN_PCT = -0.005
SLIPPAGE_BUY_MAX_PCT = 0.030
SLIPPAGE_SELL_MIN_PCT = 0.005
SLIPPAGE_SELL_MAX_PCT = 0.030
FIXED_PRIORITY_FEES_SOL = 0.006
DEX_FEE_PCT = 0.010
SESSION_DURATION_SECONDS = 12600        # 3.5 Stunden saubere Session-Dauer

COLOR_BUY = 0x00B4D8
COLOR_EXIT_WIN = 0x10B981
COLOR_EXIT_LOSS = 0xEF4444

HEADERS_TRADES = [
    "token_address", "pair_address", "symbol", "dex_id", "entry_time",
    "entry_fdv_usd", "entry_liquidity_usd", "entry_vol24h_usd", "rugcheck_score",
    "avg_entry_price_usd", "total_sol_invested", "tokens_total_bought",
    "tokens_remaining", "sol_realized", "dca_stage", "stage_profit_level",
    "peak_price_usd", "peak_gain_pct", "max_drawdown_pct", "hold_duration_seconds",
    "status", "exit_time", "signal_exit_usd", "simulated_exit_usd", "exit_reason",
    "raw_pnl_sol", "fees_sol", "net_pnl_sol", "net_pnl_usd"
]

HEADERS_REJECTS = [
    "token_address", "pair_address", "symbol", "reject_time", "rejection_reason",
    "rugcheck_score", "initial_price_usd", "initial_liq_usd", "initial_fdv_usd", "status"
]

def git_push_updates(commit_msg="Update CSV data [skip ci]"):
    try:
        subprocess.run(["git", "add", CSV_TRADES, CSV_REJECTS], check=False)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", commit_msg], check=False)
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
            subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception as err:
        print(f"[GIT-ERROR] {err}")

def get_sol_price():
    try:
        url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"
        res = requests.get(url, timeout=5).json()
        pairs = res.get("pairs", [])
        for p in pairs:
            if p.get("quoteToken", {}).get("symbol") in ["USDC", "USDT"]:
                return float(p.get("priceUsd", 150.0))
        return float(pairs[0].get("priceUsd", 150.0)) if pairs else 150.0
    except Exception:
        return 150.0

def send_discord_alert(title, description, color=0x3498db, chart_url=None):
    if not DISCORD_WEBHOOK_URL:
        return
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if chart_url:
        embed["url"] = chart_url
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
    except Exception:
        pass

def init_csvs():
    if not os.path.exists(CSV_TRADES):
        with open(CSV_TRADES, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS_TRADES)
    if not os.path.exists(CSV_REJECTS):
        with open(CSV_REJECTS, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS_REJECTS)

def read_csv(filename, headers):
    init_csvs()
    data = []
    with open(filename, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for h in headers:
                row.setdefault(h, "")
            data.append(row)
    return data

def write_csv(filename, data, headers):
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def get_current_stats(trades, sol_price):
    closed = [t for t in trades if t.get("status") == "CLOSED"]
    net_pnl_sol = sum(float(t.get("net_pnl_sol", 0.0) or 0.0) for t in closed)
    total_fees_sol = sum(float(t.get("fees_sol", 0.0) or 0.0) for t in closed)
    wins = len([t for t in closed if float(t.get("net_pnl_sol", 0.0) or 0.0) > 0])
    losses = len([t for t in closed if float(t.get("net_pnl_sol", 0.0) or 0.0) <= 0])
    current_sol = STARTING_SOL + net_pnl_sol
    current_usd = current_sol * sol_price
    winrate = (wins / len(closed) * 100) if closed else 0.0
    return {
        "current_sol": current_sol,
        "current_usd": current_usd,
        "net_pnl_sol": net_pnl_sol,
        "total_fees_sol": total_fees_sol,
        "wins": wins,
        "losses": losses,
        "total_trades": len(closed),
        "winrate": winrate
    }

def audit_token_security(token_address):
    try:
        rc_url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report/summary"
        rc_res = requests.get(rc_url, timeout=5)
        if rc_res.status_code == 200:
            data = rc_res.json()
            score = data.get("score", 0)
            risks = data.get("risks", [])

            for r in risks:
                name = r.get("name", "").lower()
                level = r.get("level", "").lower()
                if "mint authority" in name:
                    return False, score, "Mint Authority aktiv"
                if "freeze authority" in name:
                    return False, score, "Freeze Authority aktiv"
                if "top 10 holders" in name and "danger" in level:
                    return False, score, "Top 10 Wallets >40%"
                if "tax" in name or "fee" in name:
                    return False, score, "Transfer Tax gefunden"

            return True, score, "Audit Passed"
    except Exception:
        return False, 0, "Audit API Timeout"
    return False, 0, "Audit fehlgeschlagen"

def fetch_discovery_tokens():
    token_addresses = set()
    headers = {"User-Agent": "Mozilla/5.0"}
    endpoints = [
        ("https://api.dexscreener.com/token-profiles/latest/v1", True),
        ("https://api.dexscreener.com/token-boosts/latest/v1", True),
        ("https://api.dexscreener.com/token-boosts/top/v1", True),
        ("https://api.dexscreener.com/latest/dex/search?q=solana", False),
    ]

    for url, is_profile_list in endpoints:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code != 200:
                continue
            data = res.json()

            if is_profile_list and isinstance(data, list):
                for item in data:
                    if item.get("chainId") == "solana":
                        addr = item.get("tokenAddress")
                        if addr:
                            token_addresses.add(addr)
            elif not is_profile_list and isinstance(data, dict):
                pairs = data.get("pairs", [])
                for p in pairs:
                    if p.get("chainId") == "solana":
                        addr = p.get("baseToken", {}).get("address")
                        if addr:
                            token_addresses.add(addr)
        except Exception:
            continue

    return list(token_addresses)

def scan_and_enter(trades, rejects, sol_price):
    open_trades = [t for t in trades if t.get("status") == "OPEN"]
    if len(open_trades) >= MAX_OPEN_TRADES:
        return trades, rejects

    active_tokens = {t["token_address"] for t in open_trades}
    known_tokens = {t.get("token_address") for t in trades}
    now_dt = datetime.now(timezone.utc)

    try:
        candidate_tokens = fetch_discovery_tokens()
        if not candidate_tokens:
            return trades, rejects

        # Filtere bekannte Tokens vorab heraus
        tokens_to_check = [addr for addr in candidate_tokens if addr not in active_tokens and addr not in known_tokens]

        # In 30er-Batches abfragen (verhindert HTTP 429 Rate Limits)
        batch_size = 30
        for i in range(0, min(len(tokens_to_check), 90), batch_size):
            if len([t for t in trades if t.get("status") == "OPEN"]) >= MAX_OPEN_TRADES:
                break

            batch = tokens_to_check[i:i + batch_size]
            batch_url = f"https://api.dexscreener.com/latest/dex/tokens/{','.join(batch)}"
            batch_res = requests.get(batch_url, timeout=6)
            if batch_res.status_code != 200:
                continue

            pairs = batch_res.json().get("pairs") or []
            # Gruppiere Paare nach Token
            pairs_by_token = {}
            for p in pairs:
                base_addr = p.get("baseToken", {}).get("address")
                if base_addr:
                    pairs_by_token.setdefault(base_addr, []).append(p)

            for token_addr, token_pairs in pairs_by_token.items():
                if len([t for t in trades if t.get("status") == "OPEN"]) >= MAX_OPEN_TRADES:
                    break
                if token_addr in active_tokens or token_addr in known_tokens:
                    continue

                # Bevorzuge Raydium/Meteora SOL-Paare
                selected_pair = None
                for p in token_pairs:
                    dex_id = p.get("dexId", "").lower()
                    quote_sym = p.get("quoteToken", {}).get("symbol", "").upper()
                    if dex_id in ALLOWED_DEXES and quote_sym in ALLOWED_QUOTE_SYMBOLS:
                        selected_pair = p
                        break

                if not selected_pair:
                    continue

                pair = selected_pair
                dex_id = pair.get("dexId", "").lower()

                created_at_ms = pair.get("pairCreatedAt")
                if not created_at_ms:
                    continue
                pair_age_hours = (now_dt.timestamp() - (created_at_ms / 1000.0)) / 3600.0
                if pair_age_hours < MIN_PAIR_AGE_HOURS:
                    continue

                mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
                liquidity = float(pair.get("liquidity", {}).get("usd") or 0.0)
                vol_24h = float(pair.get("volume", {}).get("h24") or 0.0)
                vol_1h = float(pair.get("volume", {}).get("h1") or 0.0)
                vol_5m = float(pair.get("volume", {}).get("m5") or 0.0)
                buys_5m = pair.get("txns", {}).get("m5", {}).get("buys", 0)
                price_usd = float(pair.get("priceUsd") or 0.0)

                if mcap < MIN_MCAP_USD or mcap > MAX_MCAP_USD or price_usd <= 0.0:
                    continue
                if (liquidity / mcap) < MIN_LIQ_TO_MCAP_RATIO or (vol_24h / mcap) < MIN_VOL24H_TO_MCAP_RATIO:
                    continue

                expected_avg_5m_vol = (vol_1h / 12.0) if vol_1h > 0 else 0.0
                if expected_avg_5m_vol > 0 and vol_5m < (expected_avg_5m_vol * MIN_VOLUME_SURGE_MULTIPLIER):
                    continue
                if buys_5m < MIN_BUYS_5M:
                    continue

                is_safe, rc_score, reason = audit_token_security(token_addr)
                if not is_safe:
                    continue

                scout_sol = MAX_ALLOCATION_PER_COIN_SOL * DCA_SCOUT_PCT
                actual_buy_slip = random.uniform(SLIPPAGE_BUY_MIN_PCT, SLIPPAGE_BUY_MAX_PCT)
                sim_entry = price_usd * (1.0 + actual_buy_slip)
                tokens_scout = (scout_sol * sol_price) / sim_entry

                new_trade = {
                    "token_address": token_addr,
                    "pair_address": pair.get("pairAddress"),
                    "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "dex_id": dex_id,
                    "entry_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "entry_fdv_usd": round(mcap, 2),
                    "entry_liquidity_usd": round(liquidity, 2),
                    "entry_vol24h_usd": round(vol_24h, 2),
                    "rugcheck_score": rc_score,
                    "avg_entry_price_usd": f"{sim_entry:.8f}",
                    "total_sol_invested": f"{scout_sol:.4f}",
                    "tokens_total_bought": tokens_scout,
                    "tokens_remaining": tokens_scout,
                    "sol_realized": 0.0,
                    "dca_stage": 1,
                    "stage_profit_level": 0,
                    "peak_price_usd": f"{sim_entry:.8f}",
                    "peak_gain_pct": "0.0%",
                    "max_drawdown_pct": "0.0%",
                    "hold_duration_seconds": 0,
                    "status": "OPEN",
                    "exit_time": "",
                    "signal_exit_usd": "",
                    "simulated_exit_usd": "",
                    "exit_reason": "",
                    "raw_pnl_sol": "0.0",
                    "fees_sol": "0.0",
                    "net_pnl_sol": "0.0",
                    "net_pnl_usd": "0.0"
                }

                trades.append(new_trade)
                active_tokens.add(token_addr)
                known_tokens.add(token_addr)
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                git_push_updates(f"Scout Entry: {new_trade['symbol']}")

                stats = get_current_stats(trades, sol_price)
                chart_url = f"https://dexscreener.com/solana/{new_trade['pair_address']}"
                desc = (
                    f"**Symbol:** [{new_trade['symbol']}]({chart_url}) ({dex_id.upper()})\n"
                    f"**MCap:** ${mcap:,.0f} | **LP:** ${liquidity:,.0f} | **Alter:** {pair_age_hours:.1f}h\n"
                    f"**Vol Surge:** 5m ${vol_5m:,.0f} (Buys: {buys_5m})\n"
                    f"**Scout:** {scout_sol:.4f} SOL @ ${sim_entry:.8f}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📈 **[DexScreener Live-Chart]({chart_url})**\n"
                    f"💰 **Bankroll:** **{stats['current_sol']:.4f} SOL** (${stats['current_usd']:.2f})\n"
                    f"📊 **Stats:** {stats['wins']}W / {stats['losses']}L ({stats['winrate']:.1f}%)"
                )
                send_discord_alert(f"🎯 Scout Entry: {new_trade['symbol']}", desc, COLOR_BUY, chart_url)

    except Exception as e:
        print(f"[SCAN ERROR] {e}")

    return trades, rejects

def manage_open_trades(trades, sol_price):
    open_trades = [t for t in trades if t.get("status") == "OPEN"]
    if not open_trades:
        return trades

    now = datetime.now(timezone.utc)

    for trade in open_trades:
        try:
            token_addr = trade.get("token_address")
            pair_addr = trade.get("pair_address")
            current_price = 0.0

            # 1. Kurs primär über Token-Adresse holen (robusteste Methode)
            if token_addr:
                t_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}"
                t_res = requests.get(t_url, timeout=5).json()
                pairs = t_res.get("pairs") or []
                for p in pairs:
                    if p.get("pairAddress") == pair_addr or p.get("quoteToken", {}).get("symbol") in ALLOWED_QUOTE_SYMBOLS:
                        current_price = float(p.get("priceUsd") or 0.0)
                        break
                if current_price == 0.0 and pairs:
                    current_price = float(pairs[0].get("priceUsd") or 0.0)

            # 2. Fallback über Pair-Adresse
            if current_price <= 0.0 and pair_addr:
                p_url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
                p_res = requests.get(p_url, timeout=5).json()
                pairs = p_res.get("pairs") or []
                if pairs:
                    current_price = float(pairs[0].get("priceUsd") or 0.0)

            if current_price <= 0.0:
                continue

            avg_entry = float(trade["avg_entry_price_usd"])
            total_invested_sol = float(trade["total_sol_invested"])
            tokens_tot = float(trade["tokens_total_bought"])
            tokens_rem = float(trade["tokens_remaining"])
            dca_stage = int(trade.get("dca_stage", 1))
            profit_level = int(trade.get("stage_profit_level", 0))

            peak = max(float(trade.get("peak_price_usd", avg_entry)), current_price)
            trade["peak_price_usd"] = f"{peak:.8f}"
            peak_gain = (peak - avg_entry) / avg_entry
            trade["peak_gain_pct"] = f"{peak_gain*100:+.1f}%"

            current_pnl_pct = (current_price - avg_entry) / avg_entry
            entry_dt = datetime.strptime(trade["entry_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            held_seconds = int((now - entry_dt).total_seconds())
            trade["hold_duration_seconds"] = held_seconds

            actual_slip = random.uniform(SLIPPAGE_SELL_MIN_PCT, SLIPPAGE_SELL_MAX_PCT)
            sim_price = current_price * (1.0 - actual_slip)

            # --- DCA TRADING-LOGIK (Nur wenn noch kein Profit realisiert wurde)[span_13](start_span)[span_13](end_span) ---
            if profit_level == 0 and dca_stage == 1 and -0.22 <= current_pnl_pct <= -0.15:
                dip_sol = MAX_ALLOCATION_PER_COIN_SOL * DCA_DIP_PCT
                buy_slip = random.uniform(SLIPPAGE_BUY_MIN_PCT, SLIPPAGE_BUY_MAX_PCT)
                dip_fill = current_price * (1.0 + buy_slip)
                dip_tokens = (dip_sol * sol_price) / dip_fill

                new_tokens = tokens_tot + dip_tokens
                new_sol = total_invested_sol + dip_sol
                new_avg = (new_sol * sol_price) / new_tokens

                trade["total_sol_invested"] = f"{new_sol:.4f}"
                trade["tokens_total_bought"] = new_tokens
                trade["tokens_remaining"] = tokens_rem + dip_tokens
                trade["avg_entry_price_usd"] = f"{new_avg:.8f}"
                trade["dca_stage"] = 2
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[DCA DIP] {trade['symbol']} nachgekauft! Neuer Avg: ${new_avg:.8f}")

            elif profit_level == 0 and dca_stage < 3 and current_pnl_pct >= 0.15:
                mom_sol = MAX_ALLOCATION_PER_COIN_SOL * DCA_MOMENTUM_PCT
                buy_slip = random.uniform(SLIPPAGE_BUY_MIN_PCT, SLIPPAGE_BUY_MAX_PCT)
                mom_fill = current_price * (1.0 + buy_slip)
                mom_tokens = (mom_sol * sol_price) / mom_fill

                new_tokens = float(trade["tokens_total_bought"]) + mom_tokens
                new_sol = float(trade["total_sol_invested"]) + mom_sol
                new_avg = (new_sol * sol_price) / new_tokens

                trade["total_sol_invested"] = f"{new_sol:.4f}"
                trade["tokens_total_bought"] = new_tokens
                trade["tokens_remaining"] = float(trade["tokens_remaining"]) + mom_tokens
                trade["avg_entry_price_usd"] = f"{new_avg:.8f}"
                trade["dca_stage"] = 3
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[DCA MOMENTUM] {trade['symbol']} Breakout voll aufgestockt!")

            # --- STAGED PROFIT TAKING[span_14](start_span)[span_14](end_span)[span_15](start_span)[span_15](end_span) ---
            if current_pnl_pct >= 0.80 and profit_level < 1:
                sell_tokens = float(trade["tokens_total_bought"]) * 0.50
                realized = (sell_tokens * sim_price) / sol_price
                trade["tokens_remaining"] = float(trade["tokens_remaining"]) - sell_tokens
                trade["sol_realized"] = float(trade["sol_realized"]) + realized
                trade["stage_profit_level"] = 1
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[STAGE 1: 2x HIT] {trade['symbol']} Initial Out gesichert!")

            elif current_pnl_pct >= 3.00 and profit_level < 2:
                sell_tokens = float(trade["tokens_remaining"]) * 0.50
                realized = (sell_tokens * sim_price) / sol_price
                trade["tokens_remaining"] = float(trade["tokens_remaining"]) - sell_tokens
                trade["sol_realized"] = float(trade["sol_realized"]) + realized
                trade["stage_profit_level"] = 2
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[STAGE 2: 4x HIT] {trade['symbol']} +300% gesichert!")

            # --- EXITS & STOPS[span_16](start_span)[span_16](end_span)[span_17](start_span)[span_17](end_span) ---
            full_exit = False
            exit_reason = ""

            if current_pnl_pct <= STOP_LOSS_HARD_PCT:
                full_exit = True
                exit_reason = f"HARD_STOP ({current_pnl_pct*100:.1f}%)"
            elif peak_gain >= TRAILING_TRIGGER_PCT:
                trailing_price = peak * (1.0 - TRAILING_OFFSET_PCT)
                breakeven_price = avg_entry * (1.0 + BREAKEVEN_PROTECT_PCT)
                effective_stop = max(trailing_price, breakeven_price)
                if current_price <= effective_stop:
                    full_exit = True
                    exit_reason = f"TRAILING_PROFIT ({current_pnl_pct*100:+.1f}%)"
            elif held_seconds >= TIME_STOP_SECONDS:
                full_exit = True
                exit_reason = f"TIME_EXPIRED ({current_pnl_pct*100:+.1f}%)"

            if full_exit:
                rem_tok = float(trade["tokens_remaining"])
                rem_sol = ((rem_tok * sim_price) / sol_price) if rem_tok > 0 else 0.0
                total_realized_sol = float(trade["sol_realized"]) + rem_sol
                invested_sol = float(trade["total_sol_invested"])

                raw_pnl = total_realized_sol - invested_sol
                total_fees = FIXED_PRIORITY_FEES_SOL + ((invested_sol + total_realized_sol) * (DEX_FEE_PCT / 2.0))
                net_pnl = raw_pnl - total_fees

                trade["status"] = "CLOSED"
                trade["exit_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                trade["signal_exit_usd"] = f"{current_price:.8f}"
                trade["simulated_exit_usd"] = f"{sim_price:.8f}"
                trade["exit_reason"] = exit_reason
                trade["raw_pnl_sol"] = f"{raw_pnl:.4f}"
                trade["fees_sol"] = f"{total_fees:.4f}"
                trade["net_pnl_sol"] = f"{net_pnl:.4f}"
                trade["net_pnl_usd"] = f"{net_pnl * sol_price:.2f}"
                trade["tokens_remaining"] = 0.0

                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                git_push_updates(f"Exit: {trade['symbol']} ({exit_reason})")

                stats = get_current_stats(trades, sol_price)
                chart_url = f"https://dexscreener.com/solana/{pair_addr}"
                color = COLOR_EXIT_WIN if net_pnl > 0 else COLOR_EXIT_LOSS
                desc = (
                    f"**Symbol:** [{trade['symbol']}]({chart_url}) | {exit_reason}\n"
                    f"**Net PnL:** **{net_pnl:+.4f} SOL** ({net_pnl*sol_price:+.2f} USD)\n"
                    f"**Investiert:** {invested_sol:.3f} SOL | **Peak Gain:** {trade.get('peak_gain_pct')}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📈 **[DexScreener Live-Chart]({chart_url})**\n"
                    f"💰 **Bankroll:** **{stats['current_sol']:.4f} SOL** (${stats['current_usd']:.2f})\n"
                    f"📊 **Stats:** {stats['wins']}W / {stats['losses']}L ({stats['winrate']:.1f}%)\n"
                    f"💸 **Gezahlte Tx-Fees gesamt:** {stats['total_fees_sol']:.4f} SOL"
                )
                send_discord_alert(f"Trade Closed: {trade['symbol']}", desc, color, chart_url)

        except Exception as e:
            print(f"[TRADE UPDATE ERROR] {e}")

    return trades

def main():
    print("=== Solana Synthese Bot (Batch-Scanner & SOL-Quote-Fix Aktiv) ===")
    send_discord_alert(
        "🚀 Synthese-Strategie neugestartet",
        "Setup aktiv:\n"
        "• DEX: Nur Raydium & Meteora (reine SOL-Paare)[span_18](start_span)[span_18](end_span)\n"
        "• Sweet Spot: $150k - $3.5M MCap & Alter >= 1.5h[span_19](start_span)[span_19](end_span)\n"
        "• Scanner: 30er-Batching (keine HTTP-429 Rate-Limits)\n"
        "• Robust Price Tracking: Direkter Token-Fallback für CLMM-Pools\n"
        "• Stops: -22% Hard Stop & +35% Trailing-Profit[span_20](start_span)[span_20](end_span)"
    )

    start_time = time.time()
    last_git_sync = time.time()

    while True:
        try:
            if time.time() - start_time >= SESSION_DURATION_SECONDS:
                break

            sol_price = get_sol_price()
            trades = read_csv(CSV_TRADES, HEADERS_TRADES)
            rejects = read_csv(CSV_REJECTS, HEADERS_REJECTS)

            trades, rejects = scan_and_enter(trades, rejects, sol_price)
            trades = manage_open_trades(trades, sol_price)

            if time.time() - last_git_sync > 300:
                git_push_updates("Periodic batch sync")
                last_git_sync = time.time()

            time.sleep(12)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[LOOP ERROR] {e}")
            time.sleep(10)

    git_push_updates("Session Finished Push")

if __name__ == "__main__":
    main()
