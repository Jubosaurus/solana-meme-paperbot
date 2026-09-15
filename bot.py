import os
import json
import time
import subprocess
import requests
from datetime import datetime, timezone

PORTFOLIO_FILE = "portfolio.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- Risikomanagement & Trade Settings ---
SCOUT_SIZE_SOL = 0.20          # 0.20 SOL Einsatz
SIMULATED_FEE_SOL = 0.002      # Swap- & Priority-Gebühr pro Trade
SL_PCT = -20.0                 # Hard Stop
TRAILING_ACTIVATION = 35.0      # Trailing startet ab +35%
TRAILING_DISTANCE = 15.0       # 15% Abstand zum Höchstkurs
MAX_HOLD_HOURS = 4.0           # Max Haltedauer
MAX_OPEN_POSITIONS = 3         # Max parallele Trades
TOKEN_COOLDOWN_MINUTES = 120   # 2 Stunden Sperre für denselben Token
MAX_RUGCHECK_SCORE = 600       # Strengerer RugCheck Score
MAX_TOP10_HOLDER_PCT = 35.0    # Kumulierter Grenzwert für Top 10

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
                    data["bankroll_sol"] = 5.0
                if "total_fees_sol" not in data:
                    data["total_fees_sol"] = 0.0
                if "wins" not in data:
                    data["wins"] = 0
                if "losses" not in data:
                    data["losses"] = 0
                if "trade_history_cooldown" not in data:
                    data["trade_history_cooldown"] = {}
                return data
        except Exception:
            pass
    return {
        "bankroll_sol": 5.0,
        "total_fees_sol": 0.0,
        "wins": 0,
        "losses": 0,
        "open_positions": {},
        "closed_positions": [],
        "trade_history_cooldown": {}
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
            subprocess.run(["git", "commit", "-m", "Update bot state & anti-rug tracking [skip ci]"], check=False)
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

def verify_social_links(pair):
    info = pair.get("info") or {}
    links = []
    for soc in info.get("socials", []):
        url = soc.get("url")
        if url:
            links.append(url)
    for site in info.get("websites", []):
        url = site.get("url")
        if url:
            links.append(url)

    if not links:
        return False, "Keine Links hinterlegt"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for link in links[:3]:
        try:
            resp = requests.head(link, timeout=3.5, headers=headers, allow_redirects=True)
            if resp.status_code < 400:
                return True, "Aktiv"
        except Exception:
            try:
                resp = requests.get(link, timeout=3.5, headers=headers, stream=True)
                if resp.status_code < 400:
                    return True, "Aktiv"
            except Exception:
                continue
    return False, "Ungültiger oder toter Link"

def check_advanced_rug_safety(token_address):
    """
    Erkennt Serial Deployer (3000+ Launches) und Bundled Supply ('DEV 22').
    """
    try:
        res = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report", timeout=5)
        if res.status_code == 200:
            data = res.json()
            score = data.get("score", 0)
            if score > MAX_RUGCHECK_SCORE:
                return False, f"Score {score} zu hoch"

            # Top 10 Holder Konzentration
            top_holders = data.get("topHolders", [])
            top_10_pct = sum(float(h.get("pct", 0) or h.get("percentage", 0) or 0) for h in top_holders[:10])
            if top_10_pct > MAX_TOP10_HOLDER_PCT:
                return False, f"Top 10 halten {top_10_pct:.1f}% Supply"

            # Risiken & Flags auslesen
            risks = data.get("risks", [])
            for r in risks:
                name = (r.get("name") or "").lower()
                desc = (r.get("description") or "").lower()
                level = (r.get("level") or "").lower()

                # 1. Serial Deployer Erkennung
                if "creator" in name or "deployer" in name or "creator" in desc:
                    if "high volume" in desc or "many tokens" in desc or level == "danger":
                        return False, "Serial Deployer erkannt"

                # 2. Bundled Supply & Sybil Wallets ('DEV 22')
                if "bundled" in name or "insider" in name or "bundled" in desc or "cluster" in desc:
                    return False, "Bundled Supply / Insider-Cluster ('DEV 22')"

                # 3. Freeze & Mint Authority
                if "freeze authority" in name or "mint authority" in name:
                    return False, "Authority nicht widerrufen"

            return True, "Clean"
    except Exception:
        pass
    return True, "Bypass"

def check_bullish_structure(pair):
    txns_m5 = pair.get("txns", {}).get("m5", {})
    buys_m5 = int(txns_m5.get("buys", 0) or 0)
    sells_m5 = int(txns_m5.get("sells", 0) or 0)
    
    if buys_m5 <= sells_m5 or buys_m5 < 4:
        return False, 0, 0.0

    change_m5 = float(pair.get("priceChange", {}).get("m5", 0.0) or 0.0)
    change_h1 = float(pair.get("priceChange", {}).get("h1", 0.0) or 0.0)
    
    # Schutz vor Forced-Migration-Dumps: Extreme Single-Candle Spikes meiden
    if change_m5 > 250.0:
        return False, 0, 0.0

    # Schutz vor freiem Fall
    if change_m5 <= 0.0 or change_h1 <= -25.0:
        return False, 0, 0.0

    vol_m5 = float(pair.get("volume", {}).get("m5", 0.0) or 0.0)
    vol_h1 = float(pair.get("volume", {}).get("h1", 0.0) or 1.0)
    if (vol_m5 / max(vol_h1, 1.0)) < 0.10 and vol_m5 < 1200:
        return False, 0, 0.0

    return True, buys_m5, vol_m5

def classify_and_filter_token(pair, has_paid_profile):
    mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
    vol_h24 = float(pair.get("volume", {}).get("h24") or 0.0)
    pair_created = pair.get("pairCreatedAt", 0)
    age_min = (time.time() * 1000 - pair_created) / (1000 * 60) if pair_created else 9999
    dex_id = pair.get("dexId", "").lower()

    if mcap >= 30000 and (dex_id in ["raydium", "meteora"] or has_paid_profile):
        passed, buys_5m, vol_5m = check_bullish_structure(pair)
        if passed:
            return "MIGRATED", buys_5m, vol_5m

    if mcap >= 20000 and age_min <= 600 and (has_paid_profile or dex_id == "pumpswap"):
        passed, buys_5m, vol_5m = check_bullish_structure(pair)
        if passed:
            return "MID-BONDING", buys_5m, vol_5m

    if 6000 <= mcap <= 60000 and vol_h24 >= 3000:
        passed, buys_5m, vol_5m = check_bullish_structure(pair)
        if passed:
            return "EARLY DEGEN", buys_5m, vol_5m

    return None, 0, 0.0

def scan_and_enter(portfolio, sol_price):
    open_pos = portfolio["open_positions"]
    bankroll = portfolio.get("bankroll_sol", 5.0)
    cooldowns = portfolio.get("trade_history_cooldown", {})

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
            for p in r_pairs.json().get("pairs", [])[:40]:
                addr = p.get("baseToken", {}).get("address")
                if addr and addr not in candidates:
                    candidates[addr] = False
    except Exception:
        return

    now_ts = time.time()
    valid_candidates = []

    for token_addr, has_paid_profile in candidates.items():
        if token_addr in open_pos:
            continue
        if (now_ts - cooldowns.get(token_addr, 0)) < (TOKEN_COOLDOWN_MINUTES * 60):
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
            mcap = float(pair.get("fdv") or pair.get("marketCap") or 0.0)
            symbol = pair.get("baseToken", {}).get("symbol", "").strip().upper()
            valid_candidates.append({
                "address": token_addr,
                "pair": pair,
                "col_name": col_name,
                "buys_5m": buys_5m,
                "vol_5m": vol_5m,
                "mcap": mcap,
                "symbol": symbol
            })

    if not valid_candidates:
        return

    # PVP-Deduplizierung: Bei gleichem Ticker nur die höchste MCap wählen
    best_by_ticker = {}
    for c in valid_candidates:
        sym = c["symbol"]
        if sym not in best_by_ticker or c["mcap"] > best_by_ticker[sym]["mcap"]:
            best_by_ticker[sym] = c

    sorted_picks = sorted(best_by_ticker.values(), key=lambda x: x["mcap"], reverse=True)

    for pick in sorted_picks:
        pair = pick["pair"]
        token_addr = pick["address"]

        # Social Link Prüfung
        links_ok, _ = verify_social_links(pair)
        if not links_ok:
            continue

        # Erweiterte RugCheck-Prüfung gegen Serial Deployer & Bundles
        is_safe, safety_msg = check_advanced_rug_safety(token_addr)
        if not is_safe:
            print(f"🚫 [BLOCK RUG] ${pick['symbol']}: {safety_msg}")
            continue

        symbol = pick["symbol"]
        col_name = pick["col_name"]
        price_usd = float(pair.get("priceUsd") or 0.0)
        dex_name = pair.get("dexId", "DEX").upper()
        liq = float(pair.get("liquidity", {}).get("usd") or 0.0)
        pair_created = pair.get("pairCreatedAt", 0)
        age_h = (now_ts * 1000 - pair_created) / (1000 * 3600) if pair_created else 0.0
        pair_url = f"https://dexscreener.com/solana/{pair.get('pairAddress')}"

        if price_usd <= 0:
            continue

        portfolio["bankroll_sol"] = round(bankroll - SCOUT_SIZE_SOL, 4)
        bankroll_usd = portfolio["bankroll_sol"] * sol_price
        cooldowns[token_addr] = now_ts

        open_pos[token_addr] = {
            "symbol": symbol,
            "dex": dex_name,
            "entry_price": price_usd,
            "highest_price": price_usd,
            "entry_time": now_ts,
            "invested_sol": SCOUT_SIZE_SOL,
            "url": pair_url,
            "mcap_at_entry": pick["mcap"]
        }

        desc = (
            f"**Symbol:** {symbol} ({dex_name})\n"
            f"**MCap:** ${pick['mcap']:,.0f} | **LP:** ${liq:,.0f} | **Alter:** {age_h:.1f}h\n"
            f"**Vol Surge:** 5m ${pick['vol_5m']:,.0f} (Buys: {pick['buys_5m']})\n"
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
    total_fees = portfolio.get("total_fees_sol", 0.0)
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

        if curr_price > pos.get("highest_price", entry_price):
            pos["highest_price"] = curr_price

        peak_pct = ((pos["highest_price"] - entry_price) / entry_price) * 100.0

        exit_reason = None
        if pnl_pct <= SL_PCT:
            exit_reason = f"HARD_STOP ({pnl_pct:.1f}%)"
        elif peak_pct >= TRAILING_ACTIVATION and (peak_pct - pnl_pct) >= TRAILING_DISTANCE:
            exit_reason = f"TRAILING_TP (+{pnl_pct:.1f}%)"
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
    max_duration_seconds = 5 * 3600 - 300

    print("🚀 [START] Bot läuft mit Anti-Serial-Deployer, Anti-Bundle & PVP-Check...")

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
