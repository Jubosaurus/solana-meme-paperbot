import os
import time
import csv
import random
import requests
from datetime import datetime, timezone

# --- KONFIGURATION & SIMULATIONSPARAMETER ---
CSV_FILE = "solana_paper_trades_v2.csv"
STARTING_SOL = 5.0000
TRADE_SIZE_SOL = 0.25
MAX_OPEN_TRADES = int(STARTING_SOL / TRADE_SIZE_SOL)  # Max 20 parallele Slots
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Realistische, variable Slippage-Korridore
SLIPPAGE_BUY_MIN_PCT = -0.005         # Best-Case Buy: 0,5% günstiger
SLIPPAGE_BUY_MAX_PCT = 0.040          # Worst-Case Buy: 4,0% teurer
SLIPPAGE_MAX_TOLERANCE_PCT = 0.045    # Reject bei > 4,5% Drift

SLIPPAGE_SELL_MIN_PCT = 0.005         # Best-Case Sell: nur 0,5% unter Signal
SLIPPAGE_SELL_MAX_PCT = 0.045         # Worst-Case Sell: 4,5% unter Signal

# Feste Transaktions- & DEX-Kosten
FIXED_PRIORITY_FEES_SOL = 0.006       # 0.003 SOL Buy + 0.003 SOL Sell Priority Fee
DEX_FEE_PCT = 0.010                   # 0,5% DEX-Fee Buy + 0,5% Sell

# Strategie-Parameter
TAKE_PROFIT_PCT = 0.50                # +50% TP
STOP_LOSS_PCT = -0.15                 # -15% SL
TRAILING_TRIGGER_PCT = 0.20           # Trailing SL ab +20%
TRAILING_OFFSET_PCT = 0.10            # 10% Abstand vom Peak
BREAK_EVEN_TRIGGER_PCT = 0.15         # Break-Even ab +15%
MAX_HOLD_SECONDS = 900                # 15 Min Timeout

CSV_HEADERS = [
    "token_address", "pair_address", "symbol", "dex_id",
    "entry_time", "pair_age_hours", "socials_count",
    "entry_liquidity_usd", "entry_fdv_usd", "entry_vol_m5", "vol_to_liq_ratio",
    "entry_buys_m5", "entry_sells_m5", "entry_buy_ratio_m5", "price_change_m5_pct",
    "signal_price_usd", "simulated_entry_usd", "entry_slip_pct", "sol_invested", "amount_tokens",
    "peak_price_usd", "peak_gain_pct", "max_drawdown_pct", "hold_duration_seconds",
    "status", "exit_time", "signal_exit_usd", "simulated_exit_usd", "exit_slip_pct", "exit_reason",
    "raw_pnl_sol", "fees_sol", "net_pnl_sol", "net_pnl_usd"
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

def send_discord_alert(title, description, color=0x3498db):
    if not DISCORD_WEBHOOK_URL:
        return
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Discord Fehler: {e}")

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)

def read_trades():
    init_csv()
    trades = []
    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)
    return trades

def write_trades(trades):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(trades)

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

def scan_and_enter(trades, sol_price):
    open_count = len([t for t in trades if t.get("status") == "OPEN"])
    if open_count >= MAX_OPEN_TRADES:
        return trades

    try:
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        res = requests.get(url, timeout=5).json()
        if not isinstance(res, list):
            return trades

        existing_tokens = {t["token_address"] for t in trades}
        now_dt = datetime.now(timezone.utc)

        for item in res:
            if open_count >= MAX_OPEN_TRADES:
                break
            if item.get("chainId") != "solana":
                continue
            
            token_addr = item.get("tokenAddress")
            if token_addr in existing_tokens:
                continue

            pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}"
            pair_data = requests.get(pair_url, timeout=5).json()
            pairs = pair_data.get("pairs")
            if not pairs:
                continue

            pair = pairs[0]
            price_usd = float(pair.get("priceUsd") or 0.0)
            liquidity = float(pair.get("liquidity", {}).get("usd") or 0.0)
            vol_5m = float(pair.get("volume", {}).get("m5") or 0.0)
            fdv_usd = float(pair.get("fdv") or 0.0)
            tx_5m = pair.get("txns", {}).get("m5", {})
            buys_5m = tx_5m.get("buys", 0)
            sells_5m = tx_5m.get("sells", 0)
            price_change_m5 = float(pair.get("priceChange", {}).get("m5") or 0.0)

            # Filterkriterien
            if liquidity < 15000 or vol_5m < 3000 or (buys_5m + sells_5m < 15):
                continue
            buy_ratio = buys_5m / (buys_5m + sells_5m)
            if buy_ratio < 0.55 or price_usd <= 0.0:
                continue

            # Pool-Alter in Stunden berechnen
            created_at_ms = pair.get("pairCreatedAt")
            pair_age_hours = 0.0
            if created_at_ms:
                pair_age_hours = round((now_dt.timestamp() - (created_at_ms / 1000.0)) / 3600.0, 2)

            socials_count = len(pair.get("info", {}).get("socials", []))
            vol_to_liq = round(vol_5m / liquidity, 2) if liquidity > 0 else 0.0

            # Variable Entry-Slippage
            actual_buy_slip = random.uniform(SLIPPAGE_BUY_MIN_PCT, SLIPPAGE_BUY_MAX_PCT)
            if actual_buy_slip > SLIPPAGE_MAX_TOLERANCE_PCT:
                print(f"[REJECT] {pair.get('baseToken', {}).get('symbol')}: Slippage drift too high ({actual_buy_slip*100:.2f}%)")
                continue

            simulated_entry = price_usd * (1.0 + actual_buy_slip)
            invested_usd = TRADE_SIZE_SOL * sol_price
            tokens_bought = invested_usd / simulated_entry

            new_trade = {
                "token_address": token_addr,
                "pair_address": pair.get("pairAddress"),
                "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                "dex_id": pair.get("dexId", "unknown"),
                "entry_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "pair_age_hours": pair_age_hours,
                "socials_count": socials_count,
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
                "exit_reason": "",
                "raw_pnl_sol": "0.0",
                "fees_sol": "0.0",
                "net_pnl_sol": "0.0",
                "net_pnl_usd": "0.0"
            }

            trades.append(new_trade)
            open_count += 1
            existing_tokens.add(token_addr)
            write_trades(trades)
            print(f"[ENTRY] {new_trade['symbol']} | Fill: ${simulated_entry:.6f} ({actual_buy_slip*100:+.2f}%)")

            # Discord Alert bei Kauf
            desc = (
                f"**Symbol:** {new_trade['symbol']} ({new_trade['dex_id']})\n"
                f"**Fill-Kurs:** ${simulated_entry:.8f} (Slippage: {actual_buy_slip*100:+.2f}%)\n"
                f"**Liq:** ${liquidity:,.0f} | **FDV:** ${fdv_usd:,.0f}\n"
                f"**5m Vol:** ${vol_5m:,.0f} | **Buy-Ratio:** {buy_ratio*100:.1f}%\n"
                f"**Pool-Alter:** {pair_age_hours:.1f}h | **Socials:** {socials_count}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Offene Positionen: {open_count}/{MAX_OPEN_TRADES}"
            )
            send_discord_alert(f"🟢 Buy Executed: {new_trade['symbol']}", desc, 0x3498db)

    except Exception as e:
        print(f"Fehler bei Scan: {e}")

    return trades

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
            if current_signal_price <= 0.0:
                continue

            entry_sim = float(trade["simulated_entry_usd"])
            
            # Peak & Max Drawdown dynamisch tracken
            peak = max(float(trade.get("peak_price_usd", entry_sim)), current_signal_price)
            trade["peak_price_usd"] = f"{peak:.8f}"
            peak_gain = (peak - entry_sim) / entry_sim
            trade["peak_gain_pct"] = f"{peak_gain*100:+.1f}%"

            # Drawdown vom Einstieg
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

            if price_change_raw >= TAKE_PROFIT_PCT:
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
                # Variabler Slippage-Abzug beim Verkauf
                actual_sell_slip = random.uniform(SLIPPAGE_SELL_MIN_PCT, SLIPPAGE_SELL_MAX_PCT)
                simulated_exit = current_signal_price * (1.0 - actual_sell_slip)

                tokens = float(trade["amount_tokens"])
                sol_inv = float(trade["sol_invested"])

                gross_return_usd = tokens * simulated_exit
                gross_return_sol = gross_return_usd / sol_price
                raw_pnl_sol = gross_return_sol - sol_inv

                # Reale Netzwerk- & DEX-Gebühren
                dex_fee_sol = (sol_inv + gross_return_sol) * (DEX_FEE_PCT / 2.0)
                total_fees = FIXED_PRIORITY_FEES_SOL + dex_fee_sol
                net_pnl_sol = raw_pnl_sol - total_fees
                net_pnl_usd = net_pnl_sol * sol_price

                trade["status"] = "CLOSED"
                trade["exit_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                trade["signal_exit_usd"] = f"{current_signal_price:.8f}"
                trade["simulated_exit_usd"] = f"{simulated_exit:.8f}"
                trade["exit_slip_pct"] = f"-{actual_sell_slip*100:.2f}%"
                trade["raw_pnl_sol"] = f"{raw_pnl_sol:.4f}"
                trade["fees_sol"] = f"{total_fees:.4f}"
                trade["net_pnl_sol"] = f"{net_pnl_sol:.4f}"
                trade["net_pnl_usd"] = f"{net_pnl_usd:.2f}"
                trade["exit_reason"] = exit_reason

                write_trades(trades)
                
                stats = get_current_stats(trades, sol_price)
                desc = (
                    f"**Symbol:** {trade['symbol']}\n"
                    f"**Grund:** {exit_reason} (Dauer: {held_seconds}s)\n"
                    f"**Netto PnL:** {net_pnl_sol:+.4f} SOL ({net_pnl_usd:+.2f} USD)\n"
                    f"**Abzüge:** Fees: -{total_fees:.4f} SOL | Slip: -{actual_sell_slip*100:.2f}%\n"
                    f"**Max Gain:** {trade.get('peak_gain_pct')} | **Max DD:** {trade.get('max_drawdown_pct')}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"**Bankroll:** {stats['current_sol']:.4f} SOL (${stats['current_usd']:.2f})\n"
                    f"**Stats:** {stats['wins']}W / {stats['losses']}L ({stats['winrate']:.1f}%)\n"
                    f"**Gezahlte Tx-Fees gesamt:** {stats['total_fees_sol']:.4f} SOL"
                )
                color = 0x2ecc71 if net_pnl_sol > 0 else 0xe74c3c
                send_discord_alert(f"Trade Closed: {trade['symbol']}", desc, color)
                print(f"[EXIT] {trade['symbol']} | {exit_reason} | Net: {net_pnl_sol:+.4f} SOL | Fee: {total_fees:.4f} SOL")

        except Exception as e:
            print(f"Fehler bei Trade-Update {trade.get('symbol')}: {e}")

    return trades

def main():
    print("=== Solana Paper Bot v2 (Erweiterte Realitäts-Simulation) ===")
    send_discord_alert(
        "Bot Neu Gestartet (Vollständige Simulation)", 
        "Alle Datenpunkte & Filterkriterien aktiv.\n"
        "Startkapital: **5,0000 SOL**\n"
        "Tracking: Alter, Socials, Drawdowns, Duration, Slippage & Fees.\n"
        "Live-Benachrichtigung: Bei jedem Kauf 🟢 und Verkauf 🔴."
    )

    while True:
        try:
            sol_price = get_sol_price()
            trades = read_trades()
            trades = scan_and_enter(trades, sol_price)
            trades = manage_open_trades(trades, sol_price)
            time.sleep(12)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Loop-Fehler: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
