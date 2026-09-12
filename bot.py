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
MAX_ALLOCATION_PER_COIN_SOL = 0.25  # 5% Portfolio-Regel (Phase 3)
MAX_OPEN_TRADES = int(STARTING_SOL / MAX_ALLOCATION_PER_COIN_SOL)
MAX_TRACKED_REJECTS = 15
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- PARAMETER AUS DEM LEITFADEN ---
# Phase 1 & 2: Tokenomics & Liquidität
MIN_MCAP_USD = 70000.0              # $70k FDV / Market Cap
MAX_MCAP_USD = 11000000.0           # $11M FDV / Market Cap
MIN_LIQ_TO_MCAP_RATIO = 0.10        # LP muss mind. 10% der MCap betragen
MIN_VOL24H_TO_MCAP_RATIO = 0.05     # 24h-Volumen mind. 5% der MCap

# Phase 3: Chart Breakout
MIN_VOLUME_SURGE_MULTIPLIER = 2.0   # 5m-Volumen mind. 2x Durchschnitt

# Phase 3: Tiered Entry (DCA 20% / 40% / 40%)
DCA_SCOUT_PCT = 0.20                # 0.05 SOL Scout-Position
DCA_DIP_PCT = 0.40                  # 0.10 SOL Dip-Kauf
DCA_MOMENTUM_PCT = 0.40             # 0.10 SOL Breakout-Add

# Phase 4: Staged Profit-Taking & Stops
STOP_LOSS_HARD_PCT = -0.40          # Hard Stop bei -40%
TRAILING_STOP_OFFSET_PCT = 0.20     # Trailing Stop bei -20% vom lokalen High
TIME_STOP_SECONDS = 18000           # Session-Timeout

# Slippage & Gebühren
SLIPPAGE_BUY_MIN_PCT = -0.005
SLIPPAGE_BUY_MAX_PCT = 0.035
SLIPPAGE_MAX_TOLERANCE_PCT = 0.040
SLIPPAGE_SELL_MIN_PCT = 0.005
SLIPPAGE_SELL_MAX_PCT = 0.035
FIXED_PRIORITY_FEES_SOL = 0.006
DEX_FEE_PCT = 0.010
SESSION_DURATION_SECONDS = 18000

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
    except Exception as e:
        print(f"[GIT-ERROR] {e}")

def get_sol_price():
    try:
        url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"
        res = requests.get(url, timeout=5).json()
        pairs = res.get("pairs", [])
        for p in pairs:
            if p.get("quoteToken", {}).get("symbol") in ["USDC", "USDT"]:
                return float(p.get("priceUsd", 100.0))
        return float(pairs[0].get("priceUsd", 100.0)) if pairs else 100.0
    except Exception:
        return 100.0

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
                if h not in row:
                    row[h] = ""
            data.append(row)
    return data

def write_csv(filename, data, headers):
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def audit_token_security(token_address):
    """Prüft Phase 2 Kriterien: Mint, Freeze, Top-10-Holder, Honeypot-Risiken."""
    try:
        rc_url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report/summary"
        rc_res = requests.get(rc_url, timeout=4)
        if rc_res.status_code == 200:
            data = rc_res.json()
            score = data.get("score", 0)
            risks = data.get("risks", [])

            for r in risks:
                name = r.get("name", "")
                level = r.get("level", "")
                if "Mint Authority" in name:
                    return False, score, "Hidden Mint Authority aktiv"
                if "Freeze Authority" in name:
                    return False, score, "Freeze Authority aktiv"
                if "Top 10 holders" in name and "danger" in level:
                    return False, score, "Top 10 Wallets halten >40% Supply"
                if "Transfer Fee" in name or "Tax" in name:
                    return False, score, "Zu hohe Buy/Sell-Tax"

            return True, score, "Audit Passed"
    except Exception:
        pass
    return True, 0, "Audit Skipped"

def scan_and_enter(trades, rejects, sol_price):
    open_trades = [t for t in trades if t.get("status") == "OPEN"]
    if len(open_trades) >= MAX_OPEN_TRADES:
        return trades, rejects

    active_tokens = {t["token_address"] for t in open_trades}
    now_dt = datetime.now(timezone.utc)

    try:
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        res = requests.get(url, timeout=5).json()
        if not isinstance(res, list):
            return trades, rejects

        for item in res:
            if len([t for t in trades if t.get("status") == "OPEN"]) >= MAX_OPEN_TRADES:
                break
            if item.get("chainId") != "solana":
                continue

            token_addr = item.get("tokenAddress")
            if token_addr in active_tokens:
                continue

            if any(t.get("token_address") == token_addr for t in trades):
                continue

            pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}"
            pair_data = requests.get(pair_url, timeout=5).json()
            pairs = pair_data.get("pairs")
            if not pairs:
                continue

            pair = pairs[0]
            mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
            liquidity = float(pair.get("liquidity", {}).get("usd") or 0.0)
            vol_24h = float(pair.get("volume", {}).get("h24") or 0.0)
            vol_1h = float(pair.get("volume", {}).get("h1") or 0.0)
            vol_5m = float(pair.get("volume", {}).get("m5") or 0.0)
            price_usd = float(pair.get("priceUsd") or 0.0)

            # 1. Phase 1: MCap Filter ($70k bis $11M)
            if mcap < MIN_MCAP_USD or mcap > MAX_MCAP_USD or price_usd <= 0.0:
                continue

            # 2. Phase 2: LP-Größe (mind. 10% der MCap) & 24h-Volumen (mind. 5% der MCap)
            if (liquidity / mcap) < MIN_LIQ_TO_MCAP_RATIO:
                continue
            if (vol_24h / mcap) < MIN_VOL24H_TO_MCAP_RATIO:
                continue

            # 3. Phase 3: Volume Surge (5m-Volumen mind. 2x Durchschnitt der letzten Stunde)
            expected_avg_5m_vol = (vol_1h / 12.0) if vol_1h > 0 else 0.0
            if expected_avg_5m_vol > 0 and vol_5m < (expected_avg_5m_vol * MIN_VOLUME_SURGE_MULTIPLIER):
                continue

            # 4. Phase 2: Contract-Sicherheit
            is_safe, rc_score, reason = audit_token_security(token_addr)
            if not is_safe:
                rejects.append({
                    "token_address": token_addr,
                    "pair_address": pair.get("pairAddress"),
                    "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "reject_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "rejection_reason": reason,
                    "rugcheck_score": rc_score,
                    "initial_price_usd": f"{price_usd:.8f}",
                    "initial_liq_usd": round(liquidity, 2),
                    "initial_fdv_usd": round(mcap, 2),
                    "status": "REJECTED"
                })
                write_csv(CSV_REJECTS, rejects, HEADERS_REJECTS)
                continue

            # Phase 3: Scout Position (20% Allokation = 0.05 SOL)
            scout_sol = MAX_ALLOCATION_PER_COIN_SOL * DCA_SCOUT_PCT
            actual_buy_slip = random.uniform(SLIPPAGE_BUY_MIN_PCT, SLIPPAGE_BUY_MAX_PCT)
            sim_entry = price_usd * (1.0 + actual_buy_slip)
            tokens_scout = (scout_sol * sol_price) / sim_entry

            new_trade = {
                "token_address": token_addr,
                "pair_address": pair.get("pairAddress"),
                "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                "dex_id": pair.get("dexId", "unknown"),
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
                "dca_stage": 1,  # 1 = Scout gekauft
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
            write_csv(CSV_TRADES, trades, HEADERS_TRADES)
            git_push_updates(f"Scout Entry: {new_trade['symbol']}")

            chart_url = f"https://dexscreener.com/solana/{new_trade['pair_address']}"
            desc = (
                f"**Symbol:** [{new_trade['symbol']}]({chart_url})\n"
                f"**MCap:** ${mcap:,.0f} | **LP:** ${liquidity:,.0f} ({(liquidity/mcap)*100:.1f}%)\n"
                f"**Vol Surge:** 5m ${vol_5m:,.0f} vs Avg ${(expected_avg_5m_vol):,.0f}\n"
                f"**DCA Status:** Tranche 1/3 (Scout: {scout_sol:.2f} SOL @ ${sim_entry:.8f})\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📈 **[DexScreener Chart]({chart_url})**"
            )
            send_discord_alert(f"🎯 Scout Position: {new_trade['symbol']}", desc, COLOR_BUY, chart_url)

    except Exception as e:
        print(f"Scan Fehler: {e}")

    return trades, rejects

def manage_open_trades(trades, sol_price):
    open_trades = [t for t in trades if t.get("status") == "OPEN"]
    if not open_trades:
        return trades

    now = datetime.now(timezone.utc)

    for trade in open_trades:
        try:
            pair_addr = trade.get("pair_address")
            url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
            res = requests.get(url, timeout=5).json()
            pairs = res.get("pairs")
            if not pairs:
                continue

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

            # --- PHASE 3: TIERED DCA BUY-LOGIK ---
            # Tranche 2 (Dip Buying, 40% = 0.10 SOL): Kauf bei -20% bis -35% Rücksetzer
            if dca_stage == 1 and current_pnl_pct <= -0.20 and current_pnl_pct >= -0.35:
                dip_sol = MAX_ALLOCATION_PER_COIN_SOL * DCA_DIP_PCT
                buy_slip = random.uniform(SLIPPAGE_BUY_MIN_PCT, SLIPPAGE_BUY_MAX_PCT)
                dip_fill = current_price * (1.0 + buy_slip)
                dip_tokens = (dip_sol * sol_price) / dip_fill

                new_total_tokens = tokens_tot + dip_tokens
                new_total_sol = total_invested_sol + dip_sol
                new_avg_price = (new_total_sol * sol_price) / new_total_tokens

                trade["total_sol_invested"] = f"{new_total_sol:.4f}"
                trade["tokens_total_bought"] = new_total_tokens
                trade["tokens_remaining"] = tokens_rem + dip_tokens
                trade["avg_entry_price_usd"] = f"{new_avg_price:.8f}"
                trade["dca_stage"] = 2
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[DCA DIP HIT] {trade['symbol']} nachgekauft @ -20%! Neuer Avg: ${new_avg_price:.8f}")

            # Tranche 3 (Momentum Confirmation, 40% = 0.10 SOL): Aufstocken bei Ausbruch (+15%)
            elif dca_stage < 3 and current_pnl_pct >= 0.15:
                mom_sol = MAX_ALLOCATION_PER_COIN_SOL * DCA_MOMENTUM_PCT
                buy_slip = random.uniform(SLIPPAGE_BUY_MIN_PCT, SLIPPAGE_BUY_MAX_PCT)
                mom_fill = current_price * (1.0 + buy_slip)
                mom_tokens = (mom_sol * sol_price) / mom_fill

                new_total_tokens = float(trade["tokens_total_bought"]) + mom_tokens
                new_total_sol = float(trade["total_sol_invested"]) + mom_sol
                new_avg_price = (new_total_sol * sol_price) / new_total_tokens

                trade["total_sol_invested"] = f"{new_total_sol:.4f}"
                trade["tokens_total_bought"] = new_total_tokens
                trade["tokens_remaining"] = float(trade["tokens_remaining"]) + mom_tokens
                trade["avg_entry_price_usd"] = f"{new_avg_price:.8f}"
                trade["dca_stage"] = 3
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[DCA MOMENTUM HIT] {trade['symbol']} Breakout bestätigt! Position voll auf 0.25 SOL.")

            # --- PHASE 4: 4-TIER STAGED PROFIT-TAKING ---
            # 1. Stufe: 2x (+100%) -> Initial Investment komplett rausnehmen (50% der Gesamt-Tokens verkaufen)
            if current_pnl_pct >= 1.00 and profit_level < 1:
                sell_tokens = float(trade["tokens_total_bought"]) * 0.50
                realized = (sell_tokens * sim_price) / sol_price
                trade["tokens_remaining"] = float(trade["tokens_remaining"]) - sell_tokens
                trade["sol_realized"] = float(trade["sol_realized"]) + realized
                trade["stage_profit_level"] = 1
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[STAGE 1: 2x HIT] {trade['symbol']} Initial Investment raus!")

            # 2. Stufe: 5x (+400%) -> 25% des aktuellen Restbestands verkaufen
            elif current_pnl_pct >= 4.00 and profit_level < 2:
                sell_tokens = float(trade["tokens_remaining"]) * 0.25
                realized = (sell_tokens * sim_price) / sol_price
                trade["tokens_remaining"] = float(trade["tokens_remaining"]) - sell_tokens
                trade["sol_realized"] = float(trade["sol_realized"]) + realized
                trade["stage_profit_level"] = 2
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[STAGE 2: 5x HIT] {trade['symbol']} 25% gesichert!")

            # 3. Stufe: 10x (+900%) -> Weitere 25% des aktuellen Restbestands verkaufen
            elif current_pnl_pct >= 9.00 and profit_level < 3:
                sell_tokens = float(trade["tokens_remaining"]) * 0.25
                realized = (sell_tokens * sim_price) / sol_price
                trade["tokens_remaining"] = float(trade["tokens_remaining"]) - sell_tokens
                trade["sol_realized"] = float(trade["sol_realized"]) + realized
                trade["stage_profit_level"] = 3
                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                print(f"[STAGE 3: 10x HIT] {trade['symbol']} Life-Changing Tier gesichert!")

            # --- PHASE 4: STOP-LOSS & FULL-EXIT REGELN ---
            full_exit = False
            exit_reason = ""

            # Hard Stop: -40% ab gewichtetem Einstieg
            if current_pnl_pct <= STOP_LOSS_HARD_PCT:
                full_exit = True
                exit_reason = f"HARD_STOP ({current_pnl_pct*100:.1f}%)"
            # Trailing Stop: Sobald >20% im Gewinn, Ausstieg bei -20% unter Peak
            elif peak_gain >= 0.20 and current_price <= peak * (1.0 - TRAILING_STOP_OFFSET_PCT):
                full_exit = True
                exit_reason = "TRAILING_STOP (-20% from Peak)"
            # Time Stop: Session Timeout
            elif held_seconds >= TIME_STOP_SECONDS:
                full_exit = True
                exit_reason = f"TIME_STOP ({current_pnl_pct*100:.1f}%)"

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

                chart_url = f"https://dexscreener.com/solana/{pair_addr}"
                color = COLOR_EXIT_WIN if net_pnl > 0 else COLOR_EXIT_LOSS
                desc = (
                    f"**Symbol:** [{trade['symbol']}]({chart_url}) | {exit_reason}\n"
                    f"**Net PnL:** **{net_pnl:+.4f} SOL** ({net_pnl*sol_price:+.2f} USD)\n"
                    f"**Investiert:** {invested_sol:.3f} SOL | **DCA Stufen:** {trade['dca_stage']}/3\n"
                    f"**Peak Gain:** {trade.get('peak_gain_pct')}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📈 **[DexScreener Chart]({chart_url})**"
                )
                send_discord_alert(f"Trade Closed: {trade['symbol']}", desc, color, chart_url)

        except Exception as e:
            print(f"Trade Update Fehler: {e}")

    return trades

def main():
    print("=== Solana Ultimate Strategy Bot (Vollständige Implementierung) ===")
    send_discord_alert(
        "🚀 2026 Ultimate Strategy Bot gestartet",
        "Vollständiges Setup aktiv:\n"
        "• MCap: $70k - $11M | LP >= 10% | 24h Vol >= 5%\n"
        "• Chart-Trigger: 5m Vol >= 2x 1h-Durchschnitt\n"
        "• Tiered DCA: 20% Scout -> 40% Dip (-20%) -> 40% Breakout (+15%)\n"
        "• Staged Exits: 2x (Initial Out), 5x, 10x, Moon-Bag Trailing\n"
        "• Stops: -40% Hard Stop & -20% Trailing Stop"
    )

    start_time = time.time()
    while True:
        try:
            if time.time() - start_time >= SESSION_DURATION_SECONDS:
                break

            sol_price = get_sol_price()
            trades = read_csv(CSV_TRADES, HEADERS_TRADES)
            rejects = read_csv(CSV_REJECTS, HEADERS_REJECTS)

            trades, rejects = scan_and_enter(trades, rejects, sol_price)
            trades = manage_open_trades(trades, sol_price)

            time.sleep(12)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Loop Fehler: {e}")
            time.sleep(10)

    git_push_updates("Session Clean Exit Push")

if __name__ == "__main__":
    main()
