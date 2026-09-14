import os
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

PORTFOLIO_FILE = "portfolio.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- Risikomanagement & Trade-Settings ---
SCOUT_SIZE_SOL = 0.20     # Auf 0.20 SOL angehoben (ca. 20-25 €)
SIMULATED_FEE_SOL = 0.002  # Realistische Swap- & Priority-Gebühr pro Trade
SL_PCT = -20.0            # Dein bewährter Hard-Stop bleibt exakt so!
TRAILING_ACTIVATION = 35.0 # Trailing startet, sobald der Coin +35% erreicht
TRAILING_DISTANCE = 15.0  # Fällt er 15% vom Höchststand (Peak), wird Gewinn mitgenommen
MAX_HOLD_HOURS = 4.0      # Max Haltedauer
MAX_OPEN_POSITIONS = 3    # Max parallele Trades
SOL_USD_PRICE = 100.0     # Fallback-Preis

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
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "bankroll_sol" not in data:
                    data["bankroll_sol"] = 4.9824
                if "total_fees_sol" not in data:
                    data["total_fees_sol"] = 0.1427
                if "wins" not in data:
                    data["wins"] = 18
                if "losses" not in data:
                    data["losses"] = 37
                return data
        except Exception:
            pass
    return {
        "bankroll_sol": 4.9824,
        "total_fees_sol": 0.1427,
        "wins": 18,
        "losses": 37,
        "open_positions": {},
        "closed_positions": []
    }

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def git_push_portfolio():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", PORTFOLIO_FILE], check=False)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Update paper bot portfolio state [skip ci]"], check=False)
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

def get_stats_str(portfolio):
    w = portfolio.get("wins", 0)
    l = portfolio.get("losses", 0)
    total = w + l
    wr = (w / total * 100.0) if total > 0 else 0.0
    return f"{w}W / {l}L ({wr:.1f}%)"

def check_3_momentum_metrics(pair):
    txns_m5 = pair.get("txns", {}).get("m5", {})
    buys_m5 = int(txns_m5.get("buys", 0) or 0)
    sells_m5 = int(txns_m5.get("sells", 0) or 0)
    
    if buys_m5 <= sells_m5 or buys_m5 < 3:
        return False, 0, 0.0

    change_m5 = float(pair.get("priceChange", {}).get("m5", 0.0) or 0.0)
    if change_m5 <= 0.0:
        return False, 0, 0.0

    vol_m5 = float(pair.get("volume", {}).get("m5", 0.0) or 0.0)
    vol_h1 = float(pair.get("volume", {}).get("h1", 0.0) or 1.0)
    if (vol_m5 / max(vol_h1, 1.0)) < 0.10 and vol_m5 < 1000:
        return False, 0, 0.0

    return True, buys_m5, vol_m5

def classify_and_filter_token(pair, has_paid_profile):
    info = pair.get("info") or {}
    socials = info.get("socials") or []
    websites = info.get("websites") or []
    if len(socials) == 0 and len(websites) == 0:
        return None, 0, 0.0

    mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
    vol_h24 = float(pair.get("volume", {}).get("h24") or 0.0)
    pair_created = pair.get("pairCreatedAt", 0)
    age_min = (time.time() * 1000 - pair_created) / (1000 * 60) if pair_created else 9999
    dex_id = pair.get("dexId", "").lower()

    if mcap >= 30000 and (dex_id in ["raydium", "meteora"] or has_paid_profile):
        passed, buys_5m, vol_5m = check_3_momentum_metrics(pair)
        if passed:
            return "MIGRATED", buys_5m, vol_5m

    if mcap >= 20000 and age_min <= 600 and (has_paid_profile or dex_id == "pumpswap"):
        passed, buys_5m, vol_5m = check_3_momentum_metrics(pair)
        if passed:
            return "MID-BONDING", buys_5m, vol_5m

    if 6000 <= mcap <= 60000 and vol_h24 >= 3000:
        passed, buys_5m, vol_5m = check_3_momentum_metrics(pair)
        if passed:
            return "EARLY DEGEN", buys_5m, vol_5m

    return None, 0, 0.0

def scan_and_enter(portfolio, sol_price):
    open_pos = portfolio["open_positions"]
    bankroll = portfolio.get("bankroll_sol", 5.0)

    if len(open_pos) >= MAX_OPEN_POSITIONS or bankroll < SCOUT_SIZE_SOL:
        return

    candidates = {}
    try:
        r_profiles = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=6)
        if r_profiles.status_code == 200:
            for item in r_profiles.json():
                if item.get("chainId") == "solana":
                    candidates[item.get("tokenAddress")] = True

        r_pairs = requests.get("https://api.dexscreener.com/latest/dex/search?q=solana", timeout=6)
        if r_pairs.status_code == 200:
            for p in r_pairs.json().get("pairs", [])[:35]:
                addr = p.get("baseToken", {}).get("address")
                if addr and addr not in candidates:
                    candidates[addr] = False
    except Exception:
        return

    for token_addr, has_paid_profile in candidates.items():
        if token_addr in open_pos:
            continue

        try:
            res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}", timeout=6)
            if res.status_code != 200:
                continue
            pairs = res.json().get("pairs") or []
            if not pairs:
                continue
            pair = pairs[0]
        except Exception:
            continue

        col_name, buys_5m, vol_5m = classify_and_filter_token(pair, has_paid_profile)
        if col_name:
            symbol = pair.get("baseToken", {}).get("symbol", "TOKEN")
            dex_name = pair.get("dexId", "DEX").upper()
            price_usd = float(pair.get("priceUsd") or 0.0)
            mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
            liq = float(pair.get("liquidity", {}).get("usd") or 0.0)
            pair_created = pair.get("pairCreatedAt", 0)
            age_h = (time.time() * 1000 - pair_created) / (1000 * 3600) if pair_created else 0.0
            pair_url = f"https://dexscreener.com/solana/{pair.get('pairAddress')}"

            if price_usd <= 0:
                continue

            portfolio["bankroll_sol"] = round(bankroll - SCOUT_SIZE_SOL, 4)
            bankroll_usd = portfolio["bankroll_sol"] * sol_price

            open_pos[token_addr] = {
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
                f"**Symbol:** {symbol} ({dex_name})\n"
                f"**MCap:** ${mcap:,.0f} | **LP:** ${liq:,.0f} | **Alter:** {age_h:.1f}h\n"
                f"**Vol Surge:** 5m ${vol_5m:,.0f} (Buys: {buys_5m})\n"
                f"**Scout:** {SCOUT_SIZE_SOL:.4f} SOL @ ${price_usd:.8f}\n"
                f"-------------------\n"
                f"[📈 DexScreener Live-Chart]({pair_url})\n"
                f"💰 **Bankroll:** {portfolio['bankroll_sol']:.4f} SOL (${bankroll_usd:.2f})\n"
                f"📊 **Stats:** {get_stats_str(portfolio)}"
            )

            send_discord_raw(f"🎯 Scout Entry: {symbol}", desc, 0x3B82F6)
            save_portfolio(portfolio)
            break

def manage_positions(portfolio, sol_price):
    open_pos = portfolio["open_positions"]
    closed = portfolio["closed_positions"]
    bankroll = portfolio.get("bankroll_sol", 5.0)
    total_fees = portfolio.get("total_fees_sol", 0.1427)
    to_remove = []

    for addr, pos in open_pos.items():
        try:
            res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}", timeout=6)
            if res.status_code != 200:
                continue
            pairs = res.json().get("pairs") or []
            if not pairs:
                continue
            curr_price = float(pairs[0].get("priceUsd") or 0.0)
        except Exception:
            continue

        if curr_price <= 0:
            continue

        entry_price = pos["entry_price"]
        pnl_pct = ((curr_price - entry_price) / entry_price) * 100.0
        hold_hours = (time.time() - pos["entry_time"]) / 3600.0
        invested_sol = pos.get("invested_sol", SCOUT_SIZE_SOL)

        # Höchstkurs tracken
        if curr_price > pos.get("highest_price", entry_price):
            pos["highest_price"] = curr_price

        peak_pct = ((pos["highest_price"] - entry_price) / entry_price) * 100.0

        exit_reason = None

        # 1. Hard Stop (-20%)
        if pnl_pct <= SL_PCT:
            exit_reason = f"HARD_STOP ({pnl_pct:.1f}%)"

        # 2. Trailing Stop (Gewinne maximieren!)
        # Aktiviert ab +35%. Fällt der Kurs 15% unter das bisherige Hoch -> Profit sichern!
        elif peak_pct >= TRAILING_ACTIVATION and (peak_pct - pnl_pct) >= TRAILING_DISTANCE:
            exit_reason = f"TRAILING_TP (+{pnl_pct:.1f}%)"

        # 3. Timeout nach 4h
        elif hold_hours >= MAX_HOLD_HOURS:
            exit_reason = f"TIMEOUT_EXIT ({pnl_pct:.1f}%)"

        if exit_reason:
            pnl_sol = invested_sol * (pnl_pct / 100.0) - SIMULATED_FEE_SOL
            pnl_usd = pnl_sol * sol_price
            payout_sol = invested_sol + pnl_sol
            bankroll = round(bankroll + payout_sol, 4)
            total_fees = round(total_fees + SIMULATED_FEE_SOL, 4)

            portfolio["bankroll_sol"] = bankroll
            portfolio["total_fees_sol"] = total_fees

            if pnl_sol > 0:
                portfolio["wins"] = portfolio.get("wins", 0) + 1
                color = 0x10B981
            else:
                portfolio["losses"] = portfolio.get("losses", 0) + 1
                color = 0xEF4444

            bankroll_usd = bankroll * sol_price
            stats_str = get_stats_str(portfolio)

            desc = (
                f"**Symbol:** {pos['symbol']} | {exit_reason}\n"
                f"**Net PnL:** {pnl_sol:+.4f} SOL ({pnl_usd:+.2f} USD)\n"
                f"**Investiert:** {invested_sol:.3f} SOL | **Peak Gain:** +{peak_pct:.1f}%\n"
                f"-------------------\n"
                f"[📈 DexScreener Live-Chart]({pos.get('url')})\n"
                f"💰 **Bankroll:** {bankroll:.4f} SOL (${bankroll_usd:.2f})\n"
                f"📊 **Stats:** {stats_str}\n"
                f"💸 **Gezahlte Tx-Fees gesamt:** {total_fees:.4f} SOL"
            )

            send_discord_raw(f"Trade Closed: {pos['symbol']}", desc, color)

            closed.append({
                "symbol": pos["symbol"],
                "token_address": addr,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_sol": round(pnl_sol, 4),
                "exit_reason": exit_reason,
                "closed_at": datetime.now(timezone.utc).isoformat()
            })
            to_remove.append(addr)

    for addr in to_remove:
        del open_pos[addr]

    if to_remove:
        save_portfolio(portfolio)

def run_loop():
    start_time = time.time()
    max_duration_seconds = 5 * 3600 - 300  # 4h 55m

    print("🚀 [START] Bot läuft mit Trailing-TP, -20% SL und 0.20 SOL Scout...")

    while True:
        elapsed = time.time() - start_time
        if elapsed >= max_duration_seconds:
            print(f"⏱️ [ENDE] 5-Stunden-Schicht beendet ({elapsed/3600:.2f}h).")
            break

        try:
            sol_price = get_sol_usd_price()
            portfolio = load_portfolio()
            manage_positions(portfolio, sol_price)
            scan_and_enter(portfolio, sol_price)
            save_portfolio(portfolio)
            git_push_portfolio()
        except Exception as e:
            print(f"[LOOP ERROR] {e}")

        time.sleep(35)

if __name__ == "__main__":
    run_loop()
