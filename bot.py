import os
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

PORTFOLIO_FILE = "portfolio.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- Trade & Risikomanagement Parameter ---
SL_PCT = -18.0          # Stop Loss bei -18%
TP1_PCT = 40.0          # Take Profit 1 bei +40%
TP2_PCT = 100.0         # Moonbag / Take Profit 2 bei +100%
MAX_HOLD_HOURS = 4.0    # Maximale Haltedauer ohne TP/SL
MAX_OPEN_POSITIONS = 3  # Parallele Trades begrenzen
MAX_RUGCHECK_SCORE = 500 # Sicherheitsgrenze für RugCheck

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
            subprocess.run(["git", "commit", "-m", "Update bot portfolio state [skip ci]"], check=False)
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

def check_rugcheck_safety(token_address):
    """Sicherheits-Check via RugCheck API."""
    try:
        res = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report", timeout=6)
        if res.status_code == 200:
            data = res.json()
            score = data.get("score", 9999)
            if score > MAX_RUGCHECK_SCORE:
                return False, f"RugCheck Score zu hoch ({score})"
            
            # Prüfe Top 10 Holder Konzentration
            top_holders = data.get("topHolders", [])
            top_10_pct = sum(float(h.get("pct", 0) or h.get("percentage", 0) or 0) for h in top_holders[:10])
            if top_10_pct > 35.0:
                return False, f"Top 10 halten {top_10_pct:.1f}% (Cabal-Gefahr)"
            
            return True, f"Score {score} (Clean)"
    except Exception:
        pass
    # Falls RugCheck API hakt, nicht blockieren
    return True, "RugCheck Bypass (API Timeout)"

def check_3_momentum_metrics(pair):
    """
    Der geforderte 5-Sekunden Pre-Entry Check:
    1. Mehr Buys als Sells in den letzten 5 Minuten
    2. Positiver 5m Preistrend (Grüne Kerze)
    3. Frisches 5m Volumen
    """
    txns_m5 = pair.get("txns", {}).get("m5", {})
    buys_m5 = txns_m5.get("buys", 0)
    sells_m5 = txns_m5.get("sells", 0)
    
    if buys_m5 <= sells_m5 or buys_m5 < 3:
        return False, "Zu schwacher Käuferdruck (5m Buys <= Sells)"

    change_m5 = float(pair.get("priceChange", {}).get("m5", 0.0) or 0.0)
    if change_m5 <= 0.0:
        return False, "Negativer 5m Preistrend"

    vol_m5 = float(pair.get("volume", {}).get("m5", 0.0) or 0.0)
    vol_h1 = float(pair.get("volume", {}).get("h1", 0.0) or 1.0)
    if (vol_m5 / max(vol_h1, 1.0)) < 0.10 and vol_m5 < 1200:
        return False, "Kein frischer Volumen-Spike"

    return True, f"+{change_m5:.1f}% 5m | {buys_m5}B/{sells_m5}S"

def classify_and_filter_token(pair):
    """Prüft die Kriterien der 3 Spalten."""
    info = pair.get("info") or {}
    socials = info.get("socials") or []
    websites = info.get("websites") or []
    if len(socials) == 0 and len(websites) == 0:
        return None, "Keine Socials"

    mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
    liq = float(pair.get("liquidity", {}).get("usd") or 0.0)
    vol_h24 = float(pair.get("volume", {}).get("h24") or 0.0)
    pair_created = pair.get("pairCreatedAt", 0)
    age_min = (time.time() * 1000 - pair_created) / (1000 * 60) if pair_created else 9999
    dex_id = pair.get("dexId", "").lower()

    # --- SPALTE 1: Migrated (DEX / Raydium / Meteora) ---
    if mcap >= 30000 and (liq >= 10000 or dex_id in ["raydium", "meteora"]):
        passed, note = check_3_momentum_metrics(pair)
        if passed:
            return "Spalte 1: Migrated", note

    # --- SPALTE 2: Mid-Bonding (Kurz vor Graduation) ---
    if mcap >= 20000 and age_min <= 600 and liq >= 3500:
        passed, note = check_3_momentum_metrics(pair)
        if passed:
            return "Spalte 2: Mid-Bonding", note

    # --- SPALTE 3: Early Degen (Pump.fun Startzone) ---
    if 6000 <= mcap <= 60000 and vol_h24 >= 3000:
        passed, note = check_3_momentum_metrics(pair)
        if passed:
            return "Spalte 3: Early Degen", note

    return None, "Kein Match"

def scan_and_enter(portfolio):
    open_pos = portfolio["open_positions"]
    if len(open_pos) >= MAX_OPEN_POSITIONS:
        print(f"[LIMIT] Bereits {len(open_pos)} offene Positionen.")
        return

    print("[BOT SCAN] Suche nach Einstiegen über 3-Spalten-Matrix...")
    candidates = []

    try:
        # Frische Profile & Boosts von DexScreener
        r_profiles = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=6)
        if r_profiles.status_code == 200:
            for item in r_profiles.json():
                if item.get("chainId") == "solana":
                    candidates.append(item.get("tokenAddress"))

        # Trendende Solana-Pairs ergänzen
        r_pairs = requests.get("https://api.dexscreener.com/latest/dex/search?q=solana", timeout=6)
        if r_pairs.status_code == 200:
            for p in r_pairs.json().get("pairs", [])[:30]:
                addr = p.get("baseToken", {}).get("address")
                if addr and addr not in candidates:
                    candidates.append(addr)
    except Exception as e:
        print(f"[FETCH ERROR] {e}")
        return

    for token_addr in candidates:
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

        col_name, momentum_note = classify_and_filter_token(pair)
        if col_name:
            # Sicherheitscheck vorschalten
            is_safe, safety_msg = check_rugcheck_safety(token_addr)
            if not is_safe:
                print(f" -> Skip {token_addr[:6]}...: {safety_msg}")
                continue

            symbol = pair.get("baseToken", {}).get("symbol", "TOKEN")
            price_usd = float(pair.get("priceUsd") or 0.0)
            mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
            liq = float(pair.get("liquidity", {}).get("usd") or 0.0)
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
                f"• **MCap:** ${mcap:,.0f} | **LP:** ${liq:,.0f}\n"
                f"• **Momentum:** {momentum_note}\n"
                f"• **Security:** {safety_msg}\n"
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

def main():
    portfolio = load_portfolio()
    manage_positions(portfolio)
    scan_and_enter(portfolio)
    save_portfolio(portfolio)
    git_push_portfolio()

if __name__ == "__main__":
    main()
