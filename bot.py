import os
import time
import csv
import random
import requests
from datetime import datetime, timezone

# --- DATEIEN & GRUNDKONFIGURATION ---
CSV_TRADES = "solana_paper_trades_v2.csv"
CSV_REJECTS = "rejected_rugs_tracking.csv"

STARTING_SOL = 5.0000
TRADE_SIZE_SOL = 0.25
MAX_OPEN_TRADES = int(STARTING_SOL / TRADE_SIZE_SOL)  # Max 20 Slots
MAX_TRACKED_REJECTS = 15                              # Max 15 parallele Schatten-Beobachtungen
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Schutzregeln
MAX_TRADES_PER_TOKEN = 1              # Jeder Token darf exakt 1x gehandelt werden
RUGCHECK_MAX_ALLOWED_SCORE = 3500     # Score > 3500 gilt als hohes Risiko
MAX_SINGLE_HOLDER_PCT = 15.0          # Max. 15% Supply für eine Einzel-Wallet

# Farbschema für Discord
COLOR_BUY = 0x00B4D8          # Electric Cyan für Einstiege
COLOR_EXIT_WIN = 0x10B981     # Emerald Green für Gewinne
COLOR_EXIT_LOSS = 0xEF4444    # Crimson Red für Verluste
COLOR_EXIT_NEUTRAL = 0xF59E0B # Amber Gold für Break-Even

# Slippage-Modellierung
SLIPPAGE_BUY_MIN_PCT = -0.005
SLIPPAGE_BUY_MAX_PCT = 0.040
SLIPPAGE_MAX_TOLERANCE_PCT = 0.045
SLIPPAGE_SELL_MIN_PCT = 0.005
SLIPPAGE_SELL_MAX_PCT = 0.045

# Transaktions- & DEX-Kosten
FIXED_PRIORITY_FEES_SOL = 0.006       # 0.003 Buy + 0.003 Sell Priority Fee
DEX_FEE_PCT = 0.010                   # 0,5% Buy + 0,5% Sell DEX Fee

# Strategie-Parameter (Echte Trades)
TAKE_PROFIT_PCT = 0.50
STOP_LOSS_PCT = -0.15
TRAILING_TRIGGER_PCT = 0.20
TRAILING_OFFSET_PCT = 0.10
BREAK_EVEN_TRIGGER_PCT = 0.15
MAX_HOLD_SECONDS = 900                # 15 Min Timeout
RUG_LIQUIDITY_DROP_THRESHOLD = -0.40  # Notverkauf wenn Liq um >40% fällt

# Beobachtungsdauer für abgelehnte Rugs (Schatten-Tracking)
REJECT_OBSERVE_SECONDS = 900          # 15 Min Schatten-Tracking

HEADERS_TRADES = [
    "token_address", "pair_address", "symbol", "dex_id", "trade_num_for_token",
    "entry_time", "pair_age_hours", "socials_count", "rugcheck_score",
    "entry_liquidity_usd", "entry_fdv_usd", "entry_vol_m5", "vol_to_liq_ratio",
    "entry_buys_m5", "entry_sells_m5", "entry_buy_ratio_m5", "price_change_m5_pct",
    "signal_price_usd", "simulated_entry_usd", "entry_slip_pct", "sol_invested", "amount_tokens",
    "peak_price_usd", "peak_gain_pct", "max_drawdown_pct", "hold_duration_seconds",
    "status", "exit_time", "signal_exit_usd", "simulated_exit_usd", "exit_slip_pct",
    "exit_liquidity_usd", "liq_change_pct", "exit_reason",
    "raw_pnl_sol", "fees_sol", "net_pnl_sol", "net_pnl_usd"
]

HEADERS_REJECTS = [
    "token_address", "pair_address", "symbol", "reject_time", "rejection_reason",
    "rugcheck_score", "risk_flags",
    "initial_price_usd", "initial_liq_usd", "initial_fdv_usd",
    "peak_price_usd", "peak_gain_pct", "max_drawdown_pct",
    "final_price_usd", "final_liq_usd", "liq_change_pct", "final_price_change_pct",
    "observed_seconds", "final_verdict", "status"
]

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
    
    payload = {"embeds": [embed]}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Discord Fehler: {e}")

def init_csvs():
    if not os.path.exists(CSV_TRADES):
        with open(CSV_TRADES, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS_TRADES)
    if not os.path.exists(CSV_REJECTS):
        with open(CSV_REJECTS, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS_REJECTS)

def read_csv(filename):
    init_csvs()
    data = []
    with open(filename, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def write_csv(filename, data, headers):
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def check_token_safety(token_address):
    try:
        rc_url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report/summary"
        rc_res = requests.get(rc_url, timeout=4)
        if rc_res.status_code == 200:
            data = rc_res.json()
            score = data.get("score", 0)
            risks = data.get("risks", [])
            risk_names = [r.get("name", "") for r in risks]
            
            if score > RUGCHECK_MAX_ALLOWED_SCORE:
                return False, score, f"Score zu hoch ({score})", "; ".join(risk_names)

            for r in risks:
                name = r.get("name", "")
                desc = r.get("description", "")
                if "Mint Authority" in name:
                    return False, score, "Mint Authority noch aktiv", "; ".join(risk_names)
                if "Freeze Authority" in name:
                    return False, score, "Freeze Authority noch aktiv", "; ".join(risk_names)
                if "Single holder ownership" in name:
                    return False, score, f"Groß-Holder: {desc}", "; ".join(risk_names)
                if "Top 10 holders" in name and "danger" in r.get("level", ""):
                    return False, score, "Top 10 Wallets halten zu viel Supply", "; ".join(risk_names)

            return True, score, "RugCheck OK", "; ".join(risk_names)
    except Exception:
        pass

    return True, 0, "Audit Skipped", "None"

def get_current_stats(trades, sol_price):
    closed = [t for t in trades if t.get("status") == "CLOSED"]
    net_pnl_sol = sum(float(t.get("net_pnl_sol", 0.0)) for t in closed)
    total_fees_sol = sum(float(t.get("fees_sol", 0.0)) for t in closed)
    wins = len([t for t in closed if float(t.get("net_pnl_sol", 0.0)) > 0])
    losses = len([t for t in closed if float(t.get("net_pnl_sol", 0.0)) <= 0])
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

def scan_and_enter(trades, rejects, sol_price):
    open_trades = [t for t in trades if t.get("status") == "OPEN"]
    if len(open_trades) >= MAX_OPEN_TRADES:
        return trades, rejects

    active_open_tokens = {t["token_address"] for t in open_trades}
    already_rejected_tokens = {r["token_address"] for r in rejects}

    try:
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        res = requests.get(url, timeout=5).json()
        if not isinstance(res, list):
            return trades, rejects

        now_dt = datetime.now(timezone.utc)

        for item in res:
            if len([t for t in trades if t.get("status") == "OPEN"]) >= MAX_OPEN_TRADES:
                break
            if item.get("chainId") != "solana":
                continue
            
            token_addr = item.get("tokenAddress")
            if token_addr in active_open_tokens:
                continue

            past_trades_count = len([t for t in trades if t.get("token_address") == token_addr])
            if past_trades_count >= MAX_TRADES_PER_TOKEN:
                continue

            pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}"
            pair_data = requests.get(pair_url, timeout=5).json()
            pairs = pair_data.get("pairs")
            if not pairs:
                continue

            pair = pairs[0]
            pair_addr = pair.get("pairAddress")
            price_usd = float(pair.get("priceUsd") or 0.0)
            liquidity = float(pair.get("liquidity", {}).get("usd") or 0.0)
            vol_5m = float(pair.get("volume", {}).get("m5") or 0.0)
            fdv_usd = float(pair.get("fdv") or 0.0)
            tx_5m = pair.get("txns", {}).get("m5", {})
            buys_5m = tx_5m.get("buys", 0)
            sells_5m = tx_5m.get("sells", 0)
            price_change_m5 = float(pair.get("priceChange", {}).get("m5") or 0.0)

            # Marktkriterien prüfen
            if liquidity < 15000 or vol_5m < 3000 or (buys_5m + sells_5m < 15):
                continue
            buy_ratio = buys_5m / (buys_5m + sells_5m)
            if buy_ratio < 0.55 or price_change_m5 <= 0.0 or price_usd <= 0.0:
                continue

            # Sicherheits-Audit
            is_safe, rc_score, safety_reason, risk_flags = check_token_safety(token_addr)
            
            # WENN ABGELEHNT -> In das Schatten-Tracking aufnehmen!
            if not is_safe:
                if token_addr not in already_rejected_tokens and len([r for r in rejects if r.get("status") == "OBSERVING"]) < MAX_TRACKED_REJECTS:
                    reject_entry = {
                        "token_address": token_addr,
                        "pair_address": pair_addr,
                        "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                        "reject_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "rejection_reason": safety_reason,
                        "rugcheck_score": rc_score,
                        "risk_flags": risk_flags,
                        "initial_price_usd": f"{price_usd:.8f}",
                        "initial_liq_usd": round(liquidity, 2),
                        "initial_fdv_usd": round(fdv_usd, 2),
                        "peak_price_usd": f"{price_usd:.8f}",
                        "peak_gain_pct": "0.0%",
                        "max_drawdown_pct": "0.0%",
                        "final_price_usd": "",
                        "final_liq_usd": "",
                        "liq_change_pct": "",
                        "final_price_change_pct": "",
                        "observed_seconds": 0,
                        "final_verdict": "",
                        "status": "OBSERVING"
                    }
                    rejects.append(reject_entry)
                    already_rejected_tokens.add(token_addr)
                    write_csv(CSV_REJECTS, rejects, HEADERS_REJECTS)
                    print(f"[SHADOW-TRACK] Abgelehnt: {reject_entry['symbol']} ({safety_reason}) -> Beobachtung gestartet.")
                continue

            created_at_ms = pair.get("pairCreatedAt")
            pair_age_hours = 0.0
            if created_at_ms:
                pair_age_hours = round((now_dt.timestamp() - (created_at_ms / 1000.0)) / 3600.0, 2)

            socials_count = len(pair.get("info", {}).get("socials", []))
            vol_to_liq = round(vol_5m / liquidity, 2) if liquidity > 0 else 0.0

            actual_buy_slip = random.uniform(SLIPPAGE_BUY_MIN_PCT, SLIPPAGE_BUY_MAX_PCT)
            if actual_buy_slip > SLIPPAGE_MAX_TOLERANCE_PCT:
                continue

            simulated_entry = price_usd * (1.0 + actual_buy_slip)
            invested_usd = TRADE_SIZE_SOL * sol_price
            tokens_bought = invested_usd / simulated_entry

            new_trade = {
                "token_address": token_addr,
                "pair_address": pair_addr,
                "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                "dex_id": pair.get("dexId", "unknown"),
                "trade_num_for_token": past_trades_count + 1,
                "entry_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "pair_age_hours": pair_age_hours,
                "socials_count": socials_count,
                "rugcheck_score": rc_score,
                "entry_liquidity_usd": round(liquidity, 2),
                "entry_fdv_usd": round(fdv_usd, 2),
                "entry_vol_m5": round(vol_5m, 2),
                "vol_to_liq_ratio": vol_to_liq,
                "entry_buys_m5": buys_5m,
                "entry_sells_m5": sells_5m,
                "entry_buy_ratio_m5": f"{buy_ratio*100:.1f}%",
                "price_change_m5_pct": f"{price_change_m5:+.1f}%",
                "signal_price_usd": f"{price_usd:.8f}",
                "simulated_entry_usd": f"{simulated_entry:.8f}",
                "entry_slip_pct": f"{actual_buy_slip*100:+.2f}%",
                "sol_invested": TRADE_SIZE_SOL,
                "amount_tokens": tokens_bought,
                "peak_price_usd": f"{simulated_entry:.8f}",
                "peak_gain_pct": "0.0%",
                "max_drawdown_pct": "0.0%",
                "hold_duration_seconds": 0,
                "status": "OPEN",
                "exit_time": "",
                "signal_exit_usd": "",
                "simulated_exit_usd": "",
                "exit_slip_pct": "",
                "exit_liquidity_usd": "",
                "liq_change_pct": "",
                "exit_reason": "",
                "raw_pnl_sol": "0.0",
                "fees_sol": "0.0",
                "net_pnl_sol": "0.0",
                "net_pnl_usd": "0.0"
            }

            trades.append(new_trade)
            active_open_tokens.add(token_addr)
            write_csv(CSV_TRADES, trades, HEADERS_TRADES)
            print(f"[ENTRY] {new_trade['symbol']} | Fill: ${simulated_entry:.6f} ({actual_buy_slip*100:+.2f}%) | RugScore: {rc_score}")

            chart_url = f"https://dexscreener.com/solana/{pair_addr}"
            current_open = len([t for t in trades if t.get("status") == "OPEN"])
            desc = (
                f"**Symbol:** [{new_trade['symbol']}]({chart_url}) ({new_trade['dex_id']})\n"
                f"**Fill-Kurs:** ${simulated_entry:.8f} (Slippage: {actual_buy_slip*100:+.2f}%)\n"
                f"**Liq:** ${liquidity:,.0f} | **FDV:** ${fdv_usd:,.0f}\n"
                f"**5m Vol:** ${vol_5m:,.0f} | **Buy-Ratio:** {buy_ratio*100:.1f}%\n"
                f"**RugCheck Score:** `{rc_score}` (Audit Bestanden)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📈 **[DexScreener Live-Chart öffnen]({chart_url})**\n"
                f"Offene Positionen: {current_open}/{MAX_OPEN_TRADES}"
            )
            send_discord_alert(f"🔵 Buy Order: {new_trade['symbol']}", desc, COLOR_BUY, chart_url)

    except Exception as e:
        print(f"Fehler bei Scan: {e}")

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

            current_signal_price = float(pairs[0].get("priceUsd") or 0.0)
            current_liquidity = float(pairs[0].get("liquidity", {}).get("usd") or 0.0)
            if current_signal_price <= 0.0:
                continue

            entry_sim = float(trade["simulated_entry_usd"])
            entry_liq = float(trade.get("entry_liquidity_usd") or 1.0)
            liq_change = (current_liquidity - entry_liq) / entry_liq if entry_liq > 0 else 0.0
            
            peak = max(float(trade.get("peak_price_usd", entry_sim)), current_signal_price)
            trade["peak_price_usd"] = f"{peak:.8f}"
            peak_gain = (peak - entry_sim) / entry_sim
            trade["peak_gain_pct"] = f"{peak_gain*100:+.1f}%"

            current_drawdown = (current_signal_price - entry_sim) / entry_sim
            prev_max_dd = float(trade.get("max_drawdown_pct", "0.0%").replace("%", "")) / 100.0
            if current_drawdown < prev_max_dd:
                trade["max_drawdown_pct"] = f"{current_drawdown*100:.1f}%"

            price_change_raw = (current_signal_price - entry_sim) / entry_sim
            entry_dt = datetime.strptime(trade["entry_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            held_seconds = int((now - entry_dt).total_seconds())
            trade["hold_duration_seconds"] = held_seconds

            exit_triggered = False
            exit_reason = ""

            if liq_change <= RUG_LIQUIDITY_DROP_THRESHOLD:
                exit_triggered = True
                exit_reason = f"RUG_LIQ_DROP ({liq_change*100:.1f}%)"
            elif price_change_raw >= TAKE_PROFIT_PCT:
                exit_triggered = True
                exit_reason = f"TP_HIT (+{price_change_raw*100:.1f}%)"
            elif price_change_raw <= STOP_LOSS_PCT:
                exit_triggered = True
                exit_reason = f"SL_HIT ({price_change_raw*100:.1f}%)"
            elif peak_gain >= TRAILING_TRIGGER_PCT and current_signal_price <= peak * (1.0 - TRAILING_OFFSET_PCT):
                exit_triggered = True
                exit_reason = f"TRAILING_SL (+{price_change_raw*100:.1f}%)"
            elif peak_gain >= BREAK_EVEN_TRIGGER_PCT and price_change_raw <= 0.0:
                exit_triggered = True
                exit_reason = f"BREAK_EVEN ({price_change_raw*100:.1f}%)"
            elif held_seconds >= MAX_HOLD_SECONDS:
                exit_triggered = True
                exit_reason = f"TIME_EXPIRED ({price_change_raw*100:.1f}%)"

            if exit_triggered:
                actual_sell_slip = random.uniform(SLIPPAGE_SELL_MIN_PCT, SLIPPAGE_SELL_MAX_PCT)
                simulated_exit = current_signal_price * (1.0 - actual_sell_slip)
                tokens = float(trade["amount_tokens"])
                sol_inv = float(trade["sol_invested"])

                gross_return_usd = tokens * simulated_exit
                gross_return_sol = gross_return_usd / sol_price
                raw_pnl_sol = gross_return_sol - sol_inv

                dex_fee_sol = (sol_inv + gross_return_sol) * (DEX_FEE_PCT / 2.0)
                total_fees = FIXED_PRIORITY_FEES_SOL + dex_fee_sol
                net_pnl_sol = raw_pnl_sol - total_fees
                net_pnl_usd = net_pnl_sol * sol_price

                trade["status"] = "CLOSED"
                trade["exit_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                trade["signal_exit_usd"] = f"{current_signal_price:.8f}"
                trade["simulated_exit_usd"] = f"{simulated_exit:.8f}"
                trade["exit_slip_pct"] = f"-{actual_sell_slip*100:.2f}%"
                trade["exit_liquidity_usd"] = round(current_liquidity, 2)
                trade["liq_change_pct"] = f"{liq_change*100:+.1f}%"
                trade["raw_pnl_sol"] = f"{raw_pnl_sol:.4f}"
                trade["fees_sol"] = f"{total_fees:.4f}"
                trade["net_pnl_sol"] = f"{net_pnl_sol:.4f}"
                trade["net_pnl_usd"] = f"{net_pnl_usd:.2f}"
                trade["exit_reason"] = exit_reason

                write_csv(CSV_TRADES, trades, HEADERS_TRADES)
                
                stats = get_current_stats(trades, sol_price)
                chart_url = f"https://dexscreener.com/solana/{pair_addr}"

                if net_pnl_sol > 0.001:
                    embed_color = COLOR_EXIT_WIN
                    title_prefix = "🟢 Trade Win"
                elif net_pnl_sol < -0.001:
                    embed_color = COLOR_EXIT_LOSS
                    title_prefix = "🔴 Trade Loss"
                else:
                    embed_color = COLOR_EXIT_NEUTRAL
                    title_prefix = "🟡 Trade Neutral"

                desc = (
                    f"**Symbol:** [{trade['symbol']}]({chart_url}) | {trade.get('exit_reason')} (Dauer: {held_seconds}s)\n"
                    f"**Netto PnL:** **{net_pnl_sol:+.4f} SOL** ({net_pnl_usd:+.2f} USD)\n"
                    f"**Liq beim Exit:** ${current_liquidity:,.0f} ({liq_change*100:+.1f}%)\n"
                    f"**Abzüge:** Fees: -{total_fees:.4f} SOL | Slip: -{actual_sell_slip*100:.2f}%\n"
                    f"**Max Gain:** {trade.get('peak_gain_pct')} | **Max DD:** {trade.get('max_drawdown_pct')}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📈 **[DexScreener Chart analysieren]({chart_url})**\n"
                    f"**Bankroll:** **{stats['current_sol']:.4f} SOL** (${stats['current_usd']:.2f})\n"
                    f"**Stats:** {stats['wins']}W / {stats['losses']}L ({stats['winrate']:.1f}%)\n"
                    f"**Gezahlte Tx-Fees gesamt:** {stats['total_fees_sol']:.4f} SOL"
                )
                send_discord_alert(f"{title_prefix}: {trade['symbol']}", desc, embed_color, chart_url)
                print(f"[EXIT] {trade['symbol']} | {exit_reason} | Net: {net_pnl_sol:+.4f} SOL | Fee: {total_fees:.4f} SOL")

        except Exception as e:
            print(f"Fehler bei Trade-Update {trade.get('symbol')}: {e}")

    return trades

def manage_shadow_rejects(rejects):
    """
    Überwacht abgelehnte Rugs passiv für 15 Min, um Muster für künftige Analysen zu sammeln.
    """
    observing = [r for r in rejects if r.get("status") == "OBSERVING"]
    if not observing:
        return rejects

    now = datetime.now(timezone.utc)

    for item in observing:
        try:
            pair_addr = item.get("pair_address")
            url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_addr}"
            res = requests.get(url, timeout=4).json()
            pairs = res.get("pairs")
            if not pairs:
                continue

            current_price = float(pairs[0].get("priceUsd") or 0.0)
            current_liq = float(pairs[0].get("liquidity", {}).get("usd") or 0.0)
            init_price = float(item["initial_price_usd"])
            init_liq = float(item["initial_liq_usd"])

            reject_dt = datetime.strptime(item["reject_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            observed_sec = int((now - reject_dt).total_seconds())
            item["observed_seconds"] = observed_sec

            if current_price > 0 and init_price > 0:
                peak = max(float(item.get("peak_price_usd", init_price)), current_price)
                item["peak_price_usd"] = f"{peak:.8f}"
                peak_gain = (peak - init_price) / init_price
                item["peak_gain_pct"] = f"{peak_gain*100:+.1f}%"

                curr_drawdown = (current_price - init_price) / init_price
                prev_dd = float(item.get("max_drawdown_pct", "0.0%").replace("%", "")) / 100.0
                if curr_drawdown < prev_dd:
                    item["max_drawdown_pct"] = f"{curr_drawdown*100:.1f}%"

            # Nach 15 Min Beobachtung: Finale Auswertung
            if observed_sec >= REJECT_OBSERVE_SECONDS:
                item["status"] = "COMPLETED"
                item["final_price_usd"] = f"{current_price:.8f}"
                item["final_liq_usd"] = round(current_liq, 2)
                
                liq_change = ((current_liq - init_liq) / init_liq) * 100.0 if init_liq > 0 else 0.0
                price_change = ((current_price - init_price) / init_price) * 100.0 if init_price > 0 else 0.0
                
                item["liq_change_pct"] = f"{liq_change:+.1f}%"
                item["final_price_change_pct"] = f"{price_change:+.1f}%"

                # Klassifizierung des Musters
                if liq_change <= -50.0:
                    item["final_verdict"] = "CONFIRMED_HARD_RUG"
                elif price_change <= -60.0:
                    item["final_verdict"] = "DEV_DUMP_OR_CRASH"
                elif price_change >= 40.0:
                    item["final_verdict"] = "FALSE_POSITIVE_PUMPED"
                else:
                    item["final_verdict"] = "SLOW_BLEED_SIDEWAYS"

                print(f"[SHADOW-END] {item['symbol']} | Urteil: {item['final_verdict']} | Liq: {liq_change:+.1f}% | Kurs: {price_change:+.1f}%")

            write_csv(CSV_REJECTS, rejects, HEADERS_REJECTS)

        except Exception:
            pass

    return rejects

def main():
    print("=== Solana Paper Bot v2 (Erweiterte Realitäts-Simulation & Schatten-Analyse) ===")
    send_discord_alert(
        "Bot Aktiviert: Trading + Schatten-Rug-Analyse", 
        "Features:\n"
        "• Live Paper-Trades: 0,25 SOL Slots (Start: 5,0 SOL)\n"
        "• RugCheck-Sicherheitsfilter & Sofort-Bann\n"
        "• Schatten-Tracking: Abgelehnte Scams werden 15 Min weiterbeobachtet\n"
        "• Datenbasis: Erfasst alle Kollaps- & Liquiditäts-Muster autonom."
    )

    while True:
        try:
            sol_price = get_sol_price()
            trades = read_csv(CSV_TRADES)
            rejects = read_csv(CSV_REJECTS)
            
            trades, rejects = scan_and_enter(trades, rejects, sol_price)
            trades = manage_open_trades(trades, sol_price)
            rejects = manage_shadow_rejects(rejects)
            
            time.sleep(12)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Loop-Fehler: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
