import os
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

PORTFOLIO_FILE = "portfolio.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- Position Management (TP / SL) ---
SL_PCT = -18.0          # Stop Loss bei -18%
TP1_PCT = 40.0          # Take Profit 1 bei +40%
TP2_PCT = 100.0         # Moonbag / TP2 bei +100%
MAX_HOLD_HOURS = 4.0    # Position nach 4h glattstellen
MAX_OPEN_POSITIONS = 3  # Parallele Trades

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"open_positions": {}, "closed_positions": []}

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
            subprocess.run(["git", "commit", "-m", "Update pure TikTok paper trades [skip ci]"], check=False)
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
            subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception as err:
        print(f"[GIT ERROR] {err}")

def send_discord(title, desc, color):
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

def check_3_momentum_metrics(pair):
    """
    Der 5-Sekunden-Pre-Entry-Check aus dem Transkript:
    1. Mehr Buys als Sells in 5m
    2. Positiver 5m Preistrend
    3. Frisches 5m Volumen
    """
    txns_m5 = pair.get("txns", {}).get("m5", {})
    buys_m5 = int(txns_m5.get("buys", 0) or 0)
    sells_m5 = int(txns_m5.get("sells", 0) or 0)
    
    if buys_m5 <= sells_m5 or buys_m5 < 3:
        return False, f"Zu schwach ({buys_m5}B/{sells_m5}S)"

    change_m5 = float(pair.get("priceChange", {}).get("m5", 0.0) or 0.0)
    if change_m5 <= 0.0:
        return False, f"Rote 5m Kerze ({change_m5:.1f}%)"

    vol_m5 = float(pair.get("volume", {}).get("m5", 0.0) or 0.0)
    vol_h1 = float(pair.get("volume", {}).get("h1", 0.0) or 1.0)
    if (vol_m5 / max(vol_h1, 1.0)) < 0.10 and vol_m5 < 1000:
        return False, "Kein 5m Momentum Spike"

    return True, f"+{change_m5:.1f}% 5m | {buys_m5}B/{sells_m5}S"

def classify_and_filter_token(pair, has_paid_profile):
    """Exakte Filterung der drei TikTok-Spalten."""
    info = pair.get("info") or {}
    socials = info.get("socials") or []
    websites = info.get("websites") or []
    
    # Grundregel: Mindestens ein Social-Link
    if len(socials) == 0 and len(websites) == 0:
        return None, "Keine Socials"

    mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
    vol_h24 = float(pair.get("volume", {}).get("h24") or 0.0)
    pair_created = pair.get("pairCreatedAt", 0)
    age_min = (time.time() * 1000 - pair_created) / (1000 * 60) if pair_created else 9999
    dex_id = pair.get("dexId", "").lower()

    # --- SPALTE 1: MIGRATED ---
    # Mind. 1 Social, mind. 30k MCap, mind. 3 SOL Fees (Dex Profile / Paid DEX)
    if mcap >= 30000 and (dex_id in ["raydium", "meteora"] or has_paid_profile):
        passed, note = check_3_momentum_metrics(pair)
        if passed:
            return "Spalte 1: Migrated", note

    # --- SPALTE 2: MID-BONDING ---
    # Mind. 1 Social, mind. 20k MCap, Alter max. 600 Min (10h), mind. 2 SOL Fees
    if mcap >= 20000 and age_min <= 600 and (has_paid_profile or dex_id == "pumpswap"):
        passed, note = check_3_momentum_metrics(pair)
        if passed:
            return "Spalte 2: Mid-Bonding", note

    # --- SPALTE 3: EARLY DEGEN ---
    # Mind. 1 Social, MCap 6k-60k, Volumen mind. 3k, mind. 0.1 SOL Fees
    if 6000 <= mcap <= 60000 and vol_h24 >= 3000:
        passed, note = check_3_momentum_metrics(pair)
        if passed:
            return "Spalte 3: Early Degen", note

    return None, "Kein Match"

def scan_and_enter(portfolio):
    open_pos = portfolio["open_positions"]
    if len(open_pos) >= MAX_OPEN_POSITIONS:
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
    except Exception as e:
        print(f"[FETCH ERROR] {e}")
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

        col_name, momentum_note = classify_and_filter_token(pair, has_paid_profile)
        if col_name:
            symbol = pair.get("baseToken", {}).get("symbol", "TOKEN")
            price_usd = float(pair.get("priceUsd") or 0.0)
            mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
            pair_url = f"https://dexscreener.com/solana/{pair.get('pairAddress')}"

            if price_usd <= 0:
                continue

            open_pos[token_addr] = {
                "symbol": symbol,
                "entry_price": price_usd,
                "highest_price": price_usd,
                "entry_time": time.time(),
                "setup": col_name,
                "url": pair_url,
                "mcap_at_entry": mcap
            }

            print(f" -> KAUF: ${symbol} ({col_name}) @ ${price_usd:.8f}")
            send_discord(
                f"🟢 Paper Entry: ${symbol} ({col_name})",
                f"• **Entry:** ${price_usd:.8f}\n"
                f"• **MCap:** ${mcap:,.0f}\n"
                f"• **Pre-Entry Check:** {momentum_note}\n"
                f"• **Chart:** [DexScreener]({pair_url})",
                0x10B981
            )
            save_portfolio(portfolio)
            break

def manage_positions(portfolio):
    open_pos = portfolio["open_positions"]
    closed = portfolio["closed_positions"]
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

        if curr_price > pos.get("highest_price", entry_price):
            pos["highest_price"] = curr_price

        exit_reason = None
        if pnl_pct <= SL_PCT:
            exit_reason = f"🛑 Stop Loss ({pnl_pct:.1f}%)"
        elif pnl_pct >= TP2_PCT:
            exit_reason = f"🎯 Moonbag Take Profit ({pnl_pct:.1f}%)"
        elif pnl_pct >= TP1_PCT:
            exit_reason = f"💰 Take Profit 1 ({pnl_pct:.1f}%)"
        elif hold_hours >= MAX_HOLD_HOURS:
            exit_reason = f"⏱️ Max Hold ({pnl_pct:.1f}%)"

        if exit_reason:
            print(f" -> EXIT: ${pos['symbol']} | {exit_reason}")
            closed.append({
                "symbol": pos["symbol"],
                "token_address": addr,
                "setup": pos.get("setup", "Standard"),
                "pnl_pct": round(pnl_pct, 2),
                "exit_reason": exit_reason,
                "closed_at": datetime.now(timezone.utc).isoformat()
            })
            to_remove.append(addr)

            color = 0x10B981 if pnl_pct > 0 else 0xEF4444
            send_discord(
                f"🔴 Paper Exit: ${pos['symbol']} | {exit_reason}",
                f"• **PnL:** {pnl_pct:+.1f}%\n"
                f"• **Setup:** {pos.get('setup')}\n"
                f"• **Preise:** ${entry_price:.8f} $\\rightarrow$ ${curr_price:.8f}\n"
                f"• **Chart:** [DexScreener]({pos.get('url')})",
                color
            )

    for addr in to_remove:
        del open_pos[addr]

    if to_remove:
        save_portfolio(portfolio)

def run_loop():
    start_time = time.time()
    max_duration_seconds = 5 * 3600 - 300  # 4 Stunden 55 Minuten

    print("🚀 [START] Bot läuft in 5-Stunden-Dauerschleife...")

    while True:
        elapsed = time.time() - start_time
        if elapsed >= max_duration_seconds:
            print(f"⏱️ [ENDE] 5-Stunden-Schicht beendet ({elapsed/3600:.2f}h).")
            break

        try:
            portfolio = load_portfolio()
            manage_positions(portfolio)
            scan_and_enter(portfolio)
            save_portfolio(portfolio)
            git_push_portfolio()
        except Exception as e:
            print(f"[LOOP ERROR] {e}")

        time.sleep(35)

if __name__ == "__main__":
    run_loop()
