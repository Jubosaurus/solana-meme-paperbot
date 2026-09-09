import os
import time
import requests
import warnings
import pandas as pd
from datetime import datetime, timezone

warnings.filterwarnings("ignore", category=FutureWarning)

# ==========================================
# KONFIGURATION & PARAMETER
# ==========================================
CSV_FILE = "solana_paper_trades_v2.csv"
SOL_PRICE_USD = 101.77
STARTING_SOL = 5.0
TRADE_SIZE_SOL = 0.25

# Discord Webhook via Environment Variable
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# Taktung (Asymmetrisch)
SCAN_INTERVAL_SECONDS = 15               # Neue Token-Suche alle 15 Sekunden
FAST_CHECK_INTERVAL_SECONDS = 4          # Live-Preis- & Exit-Prüfung alle 4 Sekunden

# Strategie- & Momentum-Filter
MIN_LIQUIDITY_USD = 15000.0   
MIN_VOLUME_M5 = 5000.0        
MIN_BUYS_M5 = 30              
BUY_RATIO_MIN = 0.60          

# Exit- & Risikomanagement
TAKE_PROFIT_PCT = 0.50        
BASE_STOP_LOSS_PCT = -0.15    

# Dynamische Absicherung
BREAK_EVEN_TRIGGER = 0.18     
BREAK_EVEN_LOCK = 0.02        
TRAILING_TRIGGER = 0.30       
TRAILING_DISTANCE = 0.12      

# Zeitbasierte Exits
EARLY_PROFIT_MINUTES = 10     
EARLY_PROFIT_THRESHOLD = 0.10 
MAX_HOLD_MINUTES = 15         

HEADERS = {"User-Agent": "Mozilla/5.0"}

DTYPE_DICT = {
    "token_address": "object",
    "pair_address": "object",
    "symbol": "object",
    "entry_time": "object",
    "entry_price_usd": "float64",
    "peak_price_usd": "float64",
    "sol_invested": "float64",
    "amount_tokens": "float64",
    "status": "object",
    "exit_time": "object",
    "exit_price_usd": "float64",
    "pnl_usd": "float64",
    "pnl_sol": "float64",
    "exit_reason": "object"
}

def get_utc_now():
    return datetime.now(timezone.utc)

def send_discord_alert(embed_data):
    if not DISCORD_WEBHOOK_URL:
        return
    payload = {
        "username": "Solana Paper Bot",
        "embeds": [embed_data]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Discord Webhook Fehler: {e}")

def get_current_stats():
    """Berechnet aktuelle Bankroll und Win/Loss Statistik aus der CSV."""
    if not os.path.exists(CSV_FILE):
        return STARTING_SOL, STARTING_SOL * SOL_PRICE_USD, 0, 0
    try:
        df = pd.read_csv(CSV_FILE, dtype=object)
        for col in ["pnl_usd", "pnl_sol"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        closed = df[df["status"] == "CLOSED"]
        if closed.empty:
            return STARTING_SOL, STARTING_SOL * SOL_PRICE_USD, 0, 0
        total_pnl_sol = closed["pnl_sol"].sum()
        current_bankroll_sol = STARTING_SOL + total_pnl_sol
        current_bankroll_usd = current_bankroll_sol * SOL_PRICE_USD
        wins = len(closed[closed["pnl_usd"] > 0])
        losses = len(closed[closed["pnl_usd"] <= 0])
        return current_bankroll_sol, current_bankroll_usd, wins, losses
    except Exception:
        return STARTING_SOL, STARTING_SOL * SOL_PRICE_USD, 0, 0

def init_csv():
    columns = list(DTYPE_DICT.keys())
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=columns)
        df.to_csv(CSV_FILE, index=False)
        print(f"📁 {CSV_FILE} neu initialisiert.")
    else:
        df = pd.read_csv(CSV_FILE, dtype=object)
        if "peak_price_usd" not in df.columns:
            df["peak_price_usd"] = df["entry_price_usd"]
            df.to_csv(CSV_FILE, index=False)
            print(f"🔄 {CSV_FILE} um 'peak_price_usd' migriert.")

def scan_and_enter_trades():
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        profiles = res.json()
    except Exception:
        return

    sol_tokens = [p["tokenAddress"] for p in profiles if p.get("chainId") == "solana"][:30]
    if not sol_tokens:
        return

    tokens_str = ",".join(sol_tokens)
    pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{tokens_str}"
    
    try:
        pair_res = requests.get(pair_url, headers=HEADERS, timeout=8)
        pairs_data = pair_res.json().get("pairs", [])
    except Exception:
        return

    df_csv = pd.read_csv(CSV_FILE, dtype=object)
    known_tokens = set(df_csv["token_address"].dropna().tolist())
    open_trades_count = len(df_csv[df_csv["status"] == "OPEN"])
    max_open_trades = int(STARTING_SOL / TRADE_SIZE_SOL)

    new_rows = []
    for pair in pairs_data:
        if open_trades_count >= max_open_trades:
            break

        token_addr = pair.get("baseToken", {}).get("address")
        symbol = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
        pair_addr = pair.get("pairAddress")
        price_usd = float(pair.get("priceUsd") or 0.0)
        liquidity = float(pair.get("liquidity", {}).get("usd") or 0.0)
        vol_m5 = float(pair.get("volume", {}).get("m5") or 0.0)
        buys_m5 = int(pair.get("txns", {}).get("m5", {}).get("buys") or 0)
        sells_m5 = int(pair.get("txns", {}).get("m5", {}).get("sells") or 0)

        total_txns_m5 = buys_m5 + sells_m5
        buy_ratio = buys_m5 / total_txns_m5 if total_txns_m5 > 0 else 0

        if token_addr in known_tokens or price_usd <= 0:
            continue

        if (liquidity >= MIN_LIQUIDITY_USD and 
            vol_m5 >= MIN_VOLUME_M5 and 
            buys_m5 >= MIN_BUYS_M5 and 
            buy_ratio >= BUY_RATIO_MIN):

            usd_amount = TRADE_SIZE_SOL * SOL_PRICE_USD
            tokens_bought = usd_amount / price_usd

            new_trade = {
                "token_address": token_addr,
                "pair_address": pair_addr,
                "symbol": symbol,
                "entry_time": get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                "entry_price_usd": price_usd,
                "peak_price_usd": price_usd,
                "sol_invested": TRADE_SIZE_SOL,
                "amount_tokens": tokens_bought,
                "status": "OPEN",
                "exit_time": None,
                "exit_price_usd": None,
                "pnl_usd": 0.0,
                "pnl_sol": 0.0,
                "exit_reason": None
            }
            new_rows.append(new_trade)
            known_tokens.add(token_addr)
            open_trades_count += 1

            print(f"🟢 [BUY] ${symbol} zu ${price_usd:.6f} | Liq: ${liquidity:,.0f} | Ratio: {buy_ratio*100:.0f}%")

            cur_sol, cur_usd, wins, losses = get_current_stats()

            send_discord_alert({
                "title": f"🟢 KAUF: ${symbol}",
                "url": f"https://dexscreener.com/solana/{pair_addr}",
                "color": 3066993,
                "fields": [
                    {"name": "Einstiegskurs", "value": f"${price_usd:.6f}", "inline": True},
                    {"name": "Investition", "value": f"{TRADE_SIZE_SOL} SOL (~${usd_amount:.2f})", "inline": True},
                    {"name": "M5 Metriken", "value": f"Liq: ${liquidity:,.0f} | Vol: ${vol_m5:,.0f} | Ratio: {buy_ratio*100:.0f}%", "inline": False},
                    {"name": "Bankroll", "value": f"{cur_sol:.4f} SOL (~${cur_usd:.2f})", "inline": True},
                    {"name": "Performance", "value": f"{wins}W / {losses}L", "inline": True}
                ],
                "footer": {"text": "Solana Paper Bot"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    if new_rows:
        df_csv = pd.concat([df_csv, pd.DataFrame(new_rows)], ignore_index=True)
        df_csv.to_csv(CSV_FILE, index=False)

def resolve_and_fetch_live():
    df = pd.read_csv(CSV_FILE, dtype=object)
    
    numeric_cols = ["entry_price_usd", "peak_price_usd", "sol_invested", "amount_tokens", "exit_price_usd", "pnl_usd", "pnl_sol"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    open_mask = df["status"] == "OPEN"
    live_open_info = []

    if not open_mask.any():
        return live_open_info

    open_indices = df[open_mask].index
    
    token_addresses = df.loc[open_indices, "token_address"].dropna().tolist()
    tokens_str = ",".join(token_addresses[:30])
    url = f"https://api.dexscreener.com/latest/dex/tokens/{tokens_str}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        data = res.json().get("pairs", [])
        
        token_price_map = {}
        for p in data:
            t_addr = p.get("baseToken", {}).get("address")
            p_usd = float(p.get("priceUsd") or 0.0)
            if t_addr and p_usd > 0:
                if t_addr not in token_price_map:
                    token_price_map[t_addr] = p_usd
    except Exception as e:
        print(f"⚠️ API-Fehler bei Live-Abfrage: {e}")
        return live_open_info

    now = get_utc_now()

    for idx in open_indices:
        token_addr = df.loc[idx, "token_address"]
        current_price = token_price_map.get(token_addr)
        
        if not current_price or current_price <= 0:
            continue

        entry_price = float(df.loc[idx, "entry_price_usd"])
        entry_time = datetime.strptime(str(df.loc[idx, "entry_time"]), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        tokens = float(df.loc[idx, "amount_tokens"])
        sol_in = float(df.loc[idx, "sol_invested"])
        symbol = str(df.loc[idx, "symbol"])

        current_peak = float(df.loc[idx, "peak_price_usd"]) if pd.notnull(df.loc[idx, "peak_price_usd"]) else entry_price
        if current_price > current_peak:
            current_peak = current_price
            df.loc[idx, "peak_price_usd"] = current_peak

        pct_change = (current_price - entry_price) / entry_price
        peak_pct_change = (current_peak - entry_price) / entry_price
        age_minutes = (now - entry_time).total_seconds() / 60.0

        current_sl = BASE_STOP_LOSS_PCT
        sl_type = "SL_HIT"

        if peak_pct_change >= TRAILING_TRIGGER:
            trailing_sl = peak_pct_change - TRAILING_DISTANCE
            if trailing_sl > current_sl:
                current_sl = trailing_sl
                sl_type = "TRAILING_SL"
        elif peak_pct_change >= BREAK_EVEN_TRIGGER:
            if BREAK_EVEN_LOCK > current_sl:
                current_sl = BREAK_EVEN_LOCK
                sl_type = "BREAK_EVEN"

        exit_triggered = False
        reason = ""

        if pct_change >= TAKE_PROFIT_PCT:
            exit_triggered = True
            reason = f"TP_HIT (+{pct_change:.1%})"
        elif pct_change <= current_sl:
            exit_triggered = True
            reason = f"{sl_type} ({pct_change:.1%})"
        elif age_minutes >= EARLY_PROFIT_MINUTES and pct_change >= EARLY_PROFIT_THRESHOLD:
            exit_triggered = True
            reason = f"TIME_PROFIT_TAKE (+{pct_change:.1%})"
        elif age_minutes >= MAX_HOLD_MINUTES:
            exit_triggered = True
            reason = f"TIME_EXPIRED ({pct_change:.1%})"

        if exit_triggered:
            exit_usd = tokens * current_price
            invested_usd = sol_in * SOL_PRICE_USD
            pnl_usd = exit_usd - invested_usd
            pnl_sol = pnl_usd / SOL_PRICE_USD

            df.at[idx, "status"] = "CLOSED"
            df.at[idx, "exit_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
            df.at[idx, "exit_price_usd"] = current_price
            df.at[idx, "pnl_usd"] = round(pnl_usd, 2)
            df.at[idx, "pnl_sol"] = round(pnl_sol, 4)
            df.at[idx, "exit_reason"] = reason

            icon = "💰" if pnl_usd > 0 else "🛑"
            print(f"{icon} [EXIT] ${symbol} | Reason: {reason} | PnL: ${pnl_usd:+.2f} ({pnl_sol:+.4f} SOL)")

            # Vorübergehend in CSV speichern für exakte Bankroll-Berechnung
            df.to_csv(CSV_FILE, index=False)
            cur_sol, cur_usd, wins, losses = get_current_stats()

            is_win = pnl_usd > 0
            color = 3066993 if is_win else 15158332
            pair_addr = str(df.loc[idx, "pair_address"])
            
            send_discord_alert({
                "title": f"{icon} TRADE GESCHLOSSEN: ${symbol}",
                "url": f"https://dexscreener.com/solana/{pair_addr}",
                "color": color,
                "fields": [
                    {"name": "Exit Grund", "value": reason, "inline": True},
                    {"name": "PnL", "value": f"${pnl_usd:+.2f} USD ({pnl_sol:+.4f} SOL)", "inline": True},
                    {"name": "Verkaufskurs", "value": f"${current_price:.6f} (In: ${entry_price:.6f})", "inline": False},
                    {"name": "Haltedauer", "value": f"{age_minutes:.1f} Minuten", "inline": True},
                    {"name": "Aktuelle Bankroll", "value": f"{cur_sol:.4f} SOL (~${cur_usd:.2f})", "inline": True},
                    {"name": "Performance", "value": f"{wins}W / {losses}L", "inline": True}
                ],
                "footer": {"text": "Solana Paper Bot"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            live_open_info.append({
                "symbol": symbol,
                "entry": entry_price,
                "peak": current_peak,
                "current": current_price,
                "change": pct_change,
                "sl_level": current_sl,
                "age_min": age_minutes
            })

    df.to_csv(CSV_FILE, index=False)
    return live_open_info

def print_status_log(live_positions):
    cur_sol, cur_usd, wins, losses = get_current_stats()
    now_str = get_utc_now().strftime("%H:%M:%S UTC")

    stats_str = f"Stats: {wins}W/{losses}L | Bankroll: {cur_sol:.4f} SOL (~${cur_usd:.2f})"
    open_summary = f"Offen ({len(live_positions)}): " + ", ".join(
        [f"{p['symbol']} ({p['change']*100:+.1f}%)" for p in live_positions]
    ) if live_positions else "Keine offenen Positionen"

    print(f"[{now_str}] {stats_str} | {open_summary}")

# ==========================================
# AUSFÜHRUNG
# ==========================================
if __name__ == "__main__":
    init_csv()
    print("🚀 Solana Paper Trading Bot gestartet...")
    if DISCORD_WEBHOOK_URL:
        print("🔔 Discord-Benachrichtigungen aktiv.")
    else:
        print("⚠️ Kein Discord Webhook konfiguriert (DISCORD_WEBHOOK_URL ist leer).")

    last_scan_time = 0
    last_log_time = 0

    try:
        while True:
            now_ts = time.time()

            # 1. Token-Suche im 15s-Takt
            if now_ts - last_scan_time >= SCAN_INTERVAL_SECONDS:
                scan_and_enter_trades()
                last_scan_time = now_ts

            # 2. Exits im 4s-Takt prüfen
            live_data = resolve_and_fetch_live()

            # 3. Status-Log alle 30s
            if now_ts - last_log_time >= 30:
                print_status_log(live_data)
                last_log_time = now_ts

            active_interval = FAST_CHECK_INTERVAL_SECONDS if len(live_data) > 0 else 10
            time.sleep(active_interval)

    except KeyboardInterrupt:
        print("\n⏹️ Bot beendet.")
