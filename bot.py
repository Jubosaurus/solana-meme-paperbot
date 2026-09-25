"""
Solana-Memecoin Paper-Bot - Strategie NARRATIV
Regeln aus 13 Lernvideos (siehe STRATEGIE.md). Es wird nur auf Papier gehandelt.

  python bot.py           # normale Schicht
  python bot.py --probe   # Kurztest der Datenquellen, handelt nichts
"""
import argparse
import csv
import json
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone

import requests

# ================================================================ Dateien
PORTFOLIO_FILE = "portfolio.json"
JOURNAL_FILE = "journal.csv"
REJECT_FILE = "abgelehnt.csv"
PHASE_FILE = "marktphase.json"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
JUPITER_API_KEY = (os.environ.get("JUPITER_API_KEY") or "").strip()
JUP_BASE = "https://api.jup.ag" if JUPITER_API_KEY else "https://lite-api.jup.ag"
TRENCH_BASE = "https://trench.bot/api"

WSOL_MINT = "So11111111111111111111111111111111111111112"
IGNORED_MINTS = {
    WSOL_MINT,
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
}

# ================================================================ Schicht
LOOP_SLEEP_SECONDS = 35
SHIFT_DURATION_SECONDS = 20700          # 5h45 bei 6h-Takt
SCAN_EVERY_LOOPS = 2                    # Kandidaten ca. alle 70 s
PHASE_EVERY_LOOPS = 10                  # Marktphase ca. alle 6 min

# ================================================================ Kapital
START_BANKROLL_SOL = 10.0
POSITION_SOL = 0.2                      # Tag 7: feste Groesse, nie aus Frust groesser
TX_FEE_SOL = 0.0015                     # Netzwerk + Priority pro Transaktion

# ================================================================ Einstieg
# Tag 5: frueh, solange sich die Story verbreitet
MIN_AGE_MIN = 15
MAX_AGE_H = 6
MIN_HOLDER_GROWTH_1H = 15.0             # Holder-Zuwachs in % pro Stunde
MIN_NET_BUYERS_5M = 1
MIN_ORGANIC_BUYERS_5M = 3               # echte Menschen statt Bots
MIN_ORGANIC_SCORE = 30
REQUIRE_SOCIAL_LINK = True              # X, Telegram oder Website vorhanden
# Tag 7: nicht hinterherjagen
MAX_MCAP_USD = 3_000_000
MAX_PRICE_CHANGE_1H = 150.0
# Grundsicherung gegen offensichtliche Fallen
MIN_LIQUIDITY_USD = 5_000
IMPERSONATION_SYMBOLS = {"SOL", "WSOL", "USDC", "USDT", "BTC", "WBTC", "ETH", "WETH", "JUP"}
# Tag 1: Bundle-Check
MAX_BUNDLE_HOLDING_PCT = 10.0           # was Bundle-Wallets JETZT noch halten
MAX_BUNDLE_INITIAL_PCT = 30.0           # was beim Launch gebuendelt gekauft wurde
BUNDLE_CHECK_REQUIRED = True            # ohne Check kein Kauf
# Tag 6: Dev pruefen
MAX_CREATOR_RUGS = 0
MAX_CREATOR_HOLDING_PCT = 10.0

# ================================================================ Ausstieg
TP1_MULTIPLE = 2.0                      # Tag 2: bei 2x ...
TP1_SELL_FRACTION = 0.5                 # ... die Haelfte vom Tisch
TRAIL_AFTER_TP1_PCT = 40.0              # Tag 4: Rest laufen lassen, Schutz vom Hoch
THESIS_BREAK_CHECKS = 2                 # Tag 3: These gebrochen, wenn 2x hintereinander
LIQ_DROP_EXIT_PCT = 30.0                # Liquiditaet abgezogen -> raus
EMERGENCY_STOP_PCT = -40.0              # Notbremse
MAX_HOLD_H = 24
DEAD_TOKEN_LOOPS = 10

# ================================================================ Marktphase
# Tag 9 + 13: frische Coins und Volumen messen, bei ruhigem Markt weniger handeln
YOUNG_TOKEN_H = 24
HOT_MCAP_USD = 1_000_000
MAX_POSITIONS = {"heiss": 3, "normal": 2, "ruhig": 1}
PHASE_MIN_HISTORY = 12
PHASE_HISTORY_MAX = 1000

REJECT_REPEAT_SECONDS = 3600

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "narrativ-paperbot/1.0"})

STATS = {"loops": 0, "loop_errors": 0, "last_error": "", "entries": [], "exits": [],
         "partials": [], "rejects": {}, "jup_ok": 0, "jup_fail": 0,
         "trench_ok": 0, "trench_fail": 0}
_jup_last = [0.0]
_trench_last = [0.0]
_trench_cache = {}
_shield_cache = {}
_reject_seen = {}
_symbol_leaders = {}                    # Tag 12: Symbol -> (mint, holder, zeit)
_sol_price = [0.0]


# ================================================================ HTTP

def _throttle(slot, interval):
    wait = interval - (time.time() - slot[0])
    if wait > 0:
        time.sleep(wait)
    slot[0] = time.time()


def jup_get(path):
    _throttle(_jup_last, 1.1 if JUPITER_API_KEY else 2.5)
    headers = {"x-api-key": JUPITER_API_KEY} if JUPITER_API_KEY else {}
    try:
        res = SESSION.get(f"{JUP_BASE}{path}", headers=headers, timeout=12)
    except requests.RequestException as err:
        STATS["jup_fail"] += 1
        print(f"[JUPITER] {path.split('?')[0]} -> {err}")
        return None
    if res.status_code != 200:
        STATS["jup_fail"] += 1
        print(f"[JUPITER HTTP {res.status_code}] {path.split('?')[0]}")
        return None
    STATS["jup_ok"] += 1
    try:
        return res.json()
    except ValueError:
        return None


def trench_get(mint, tries=2):
    res = None
    for attempt in range(tries):
        _throttle(_trench_last, 1.1)
        try:
            res = SESSION.get(f"{TRENCH_BASE}/bundle/bundle_advanced/{mint}", timeout=45)
            break
        except requests.RequestException as err:
            print(f"[TRENCHBOT] Versuch {attempt + 1}: {err}")
            res = None
    if res is None:
        STATS["trench_fail"] += 1
        return None
    if res.status_code != 200:
        STATS["trench_fail"] += 1
        print(f"[TRENCHBOT HTTP {res.status_code}] {res.text[:120]}")
        return None
    try:
        data = res.json()
    except ValueError:
        STATS["trench_fail"] += 1
        return None
    STATS["trench_ok"] += 1
    return data if isinstance(data, dict) else None


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def iso_ts(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    text = re.sub(r"([+-]\d{2})$", r"\1:00", text)
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


# ================================================================ Jupiter-Daten

def jup_category(category, interval, limit=100):
    data = jup_get(f"/tokens/v2/{category}/{interval}?limit={limit}")
    return data if isinstance(data, list) else []


def jup_tokens(mints):
    """Bis zu 100 Token in einer Abfrage. Rueckgabe {mint: token}."""
    result = {}
    mints = [m for m in mints if m]
    for i in range(0, len(mints), 100):
        data = jup_get(f"/tokens/v2/search?query={','.join(mints[i:i + 100])}")
        for tok in data if isinstance(data, list) else []:
            if tok.get("id"):
                result[tok["id"]] = tok
    return result


def sol_price():
    data = jup_get(f"/price/v3?ids={WSOL_MINT}")
    price = as_float(((data or {}).get(WSOL_MINT) or {}).get("usdPrice"))
    if price > 0:
        _sol_price[0] = price
    return _sol_price[0] or 150.0


_social_cache = {}


def has_social(v):
    """Tag 5: Gibt es einen X-, Telegram- oder Website-Link? Jupiter liefert
    diese Felder nicht, daher Rueckfall auf DexScreener."""
    if v["social"]:
        return True
    cached = _social_cache.get(v["mint"])
    if cached is not None:
        return cached
    try:
        res = SESSION.get(f"https://api.dexscreener.com/latest/dex/tokens/{v['mint']}", timeout=10)
        pairs = (res.json() or {}).get("pairs") or [] if res.status_code == 200 else []
    except (requests.RequestException, ValueError):
        return False
    found = any((pair.get("info") or {}).get("socials") or (pair.get("info") or {}).get("websites")
                for pair in pairs)
    _social_cache[v["mint"]] = found
    return found


def shield(mint):
    cached = _shield_cache.get(mint)
    if cached and time.time() - cached[0] < 1800:
        return cached[1]
    data = jup_get(f"/ultra/v1/shield?mints={mint}")
    if not isinstance(data, dict):
        return None
    warnings = (data.get("warnings") or {}).get(mint) or []
    types = [w.get("type") for w in warnings if isinstance(w, dict) and w.get("type")]
    _shield_cache[mint] = (time.time(), types)
    return types


def quote(input_mint, output_mint, raw_amount):
    data = jup_get(f"/swap/v1/quote?inputMint={input_mint}&outputMint={output_mint}"
                   f"&amount={int(raw_amount)}&slippageBps=500")
    try:
        return int((data or {}).get("outAmount") or 0)
    except (TypeError, ValueError):
        return 0


# ================================================================ Token-Kennzahlen

def token_view(tok, now):
    s5, s1 = tok.get("stats5m") or {}, tok.get("stats1h") or {}
    audit = tok.get("audit") or {}
    created = iso_ts((tok.get("firstPool") or {}).get("createdAt"))
    return {
        "mint": tok.get("id"),
        "symbol": str(tok.get("symbol") or "?").strip(),
        "name": str(tok.get("name") or "").strip(),
        "decimals": tok.get("decimals"),
        "price": as_float(tok.get("usdPrice")),
        "mcap": as_float(tok.get("mcap") or tok.get("fdv")),
        "liquidity": as_float(tok.get("liquidity")),
        "holders": int(as_float(tok.get("holderCount"))),
        "age_h": (now - created) / 3600 if created else None,
        "holder_growth_1h": as_float(s1.get("holderChange")),
        "holder_growth_5m": as_float(s5.get("holderChange")),
        "net_buyers_5m": int(as_float(s5.get("numNetBuyers"))),
        "organic_buyers_5m": int(as_float(s5.get("numOrganicBuyers"))),
        "organic_score": as_float(tok.get("organicScore")),
        "price_change_1h": as_float(s1.get("priceChange")),
        "volume_1h": as_float(s1.get("buyVolume")) + as_float(s1.get("sellVolume")),
        "social": bool(tok.get("twitter") or tok.get("telegram") or tok.get("website")),
        "mint_disabled": audit.get("mintAuthorityDisabled"),
        "freeze_disabled": audit.get("freezeAuthorityDisabled"),
        "is_sus": "isSus" in audit and bool(audit.get("isSus", True)),
    }


def norm_symbol(text):
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def update_symbol_leaders(views, now):
    """Tag 12: merkt sich pro Name/Symbol den Coin mit den meisten Holdern."""
    for v in views:
        for key in {norm_symbol(v["symbol"]), norm_symbol(v["name"])} - {""}:
            leader = _symbol_leaders.get(key)
            if (leader is None or now - leader[2] > 6 * 3600
                    or leader[0] == v["mint"] or v["holders"] > leader[1]):
                _symbol_leaders[key] = (v["mint"], v["holders"], now)


def vamp_copy_of(v):
    for key in {norm_symbol(v["symbol"]), norm_symbol(v["name"])} - {""}:
        leader = _symbol_leaders.get(key)
        if leader and leader[0] != v["mint"] and leader[1] > v["holders"]:
            return leader[0]
    return None


# ================================================================ Einstiegspruefung

def quick_checks(v):
    """Guenstige Pruefungen ohne weitere Abfragen. Rueckgabe: Ablehnungsgrund oder None."""
    if v["age_h"] is None:
        return "KEIN_ALTER"
    if v["age_h"] < MIN_AGE_MIN / 60:
        return "ZU_JUNG"
    if v["age_h"] > MAX_AGE_H:
        return "STORY_ZU_ALT"                                   # Tag 5
    if v["mcap"] > MAX_MCAP_USD or v["price_change_1h"] > MAX_PRICE_CHANGE_1H:
        return "SCHON_GELAUFEN"                                 # Tag 7
    if v["holder_growth_1h"] < MIN_HOLDER_GROWTH_1H or v["holder_growth_5m"] <= 0:
        return "VERBREITUNG_STOCKT"                             # Tag 5
    if v["net_buyers_5m"] < MIN_NET_BUYERS_5M or v["organic_buyers_5m"] < MIN_ORGANIC_BUYERS_5M:
        return "KEINE_ECHTEN_KAEUFER"                           # Tag 5
    if v["organic_score"] < MIN_ORGANIC_SCORE:
        return "NICHT_ORGANISCH"
    if v["liquidity"] < MIN_LIQUIDITY_USD:
        return "LIQUIDITAET_ZU_GERING"
    if norm_symbol(v["symbol"]) in IMPERSONATION_SYMBOLS:
        return "NACHAHMER_SYMBOL"
    if v["mint_disabled"] is False or v["freeze_disabled"] is False or v["is_sus"]:
        return "UNSICHERER_CONTRACT"
    copy_of = vamp_copy_of(v)
    if copy_of:
        return "VAMP_KOPIE"                                     # Tag 12
    return None


def bundle_dev_check(mint):
    """Tag 1 + Tag 6. Rueckgabe (Grund oder None, Kennzahlen)."""
    cached = _trench_cache.get(mint)
    if cached and time.time() - cached[0] < 600:
        return cached[1], cached[2]
    data = trench_get(mint)
    if data is None:
        return ("BUNDLE_CHECK_NICHT_MOEGLICH" if BUNDLE_CHECK_REQUIRED else None), {}

    creator = data.get("creator_analysis") or {}
    history = creator.get("history") or {}
    info = {
        "bundle_holding_pct": as_float(data.get("total_holding_percentage")),
        "bundle_initial_pct": as_float(data.get("total_percentage_bundled")),
        "bundles": int(as_float(data.get("total_bundles"))),
        "creator_rugs": int(as_float(history.get("rug_count"))),
        "creator_coins": int(as_float(history.get("total_coins_created"))),
        "creator_holding_pct": as_float(creator.get("holding_percentage")),
        "creator_risk": str(creator.get("risk_level") or ""),
    }
    reason = None
    if info["bundle_holding_pct"] >= MAX_BUNDLE_HOLDING_PCT or \
            info["bundle_initial_pct"] >= MAX_BUNDLE_INITIAL_PCT:
        reason = "GEBUENDELT"
    elif info["creator_rugs"] > MAX_CREATOR_RUGS or info["creator_risk"].upper() == "HIGH":
        reason = "DEV_MIT_RUGS"
    elif info["creator_holding_pct"] > MAX_CREATOR_HOLDING_PCT:
        reason = "DEV_HAELT_ZU_VIEL"
    _trench_cache[mint] = (time.time(), reason, info)
    return reason, info


def safety_shield(mint):
    types = shield(mint) or []
    fees = [t for t in types if "TRANSFER_FEE" in str(t).upper()]
    return "TRANSFERGEBUEHR" if fees else None


# ================================================================ Portfolio

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "bankroll_sol" in data:
                data.setdefault("positions", {})
                data.setdefault("closed", [])
                data.setdefault("cooldown", {})
                return data
        except Exception as err:
            print(f"[PORTFOLIO] {err} -> neues Portfolio")
    return {"strategy": "NARRATIV", "started": datetime.now(timezone.utc).isoformat(),
            "bankroll_sol": START_BANKROLL_SOL, "positions": {}, "closed": [], "cooldown": {}}


def save_portfolio(p):
    tmp = PORTFOLIO_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)
    os.replace(tmp, PORTFOLIO_FILE)


def journal(action, pos, price_usd, sol, reason="", pnl_sol="", pnl_pct=""):
    """Tag 3: Einstieg mit These und Verkaufsbedingung, jeder Verkauf mit Grund."""
    new = not os.path.exists(JOURNAL_FILE)
    with open(JOURNAL_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["zeit", "aktion", "symbol", "mint", "preis_usd", "sol",
                        "these", "verkaufsbedingung", "grund", "pnl_sol", "pnl_pct"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), action,
                    pos["symbol"], pos["mint"], f"{price_usd:.12g}", f"{sol:.4f}",
                    pos.get("thesis", ""), pos.get("exit_rule", ""), reason,
                    pnl_sol if pnl_sol == "" else f"{pnl_sol:+.4f}",
                    pnl_pct if pnl_pct == "" else f"{pnl_pct:+.1f}"])


def log_reject(v, reason):
    STATS["rejects"][reason] = STATS["rejects"].get(reason, 0) + 1
    key = (v.get("mint"), reason)
    if time.time() - _reject_seen.get(key, 0) < REJECT_REPEAT_SECONDS:
        return
    _reject_seen[key] = time.time()
    new = not os.path.exists(REJECT_FILE)
    with open(REJECT_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["zeit", "symbol", "mint", "grund", "alter_h", "mcap", "liq",
                        "holder", "holder_1h_pct", "netto_kaeufer_5m", "preis_usd"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    v.get("symbol"), v.get("mint"), reason,
                    "" if v.get("age_h") is None else f"{v['age_h']:.2f}",
                    f"{v.get('mcap', 0):.0f}", f"{v.get('liquidity', 0):.0f}", v.get("holders"),
                    f"{v.get('holder_growth_1h', 0):.1f}", v.get("net_buyers_5m"),
                    f"{v.get('price', 0):.12g}"])


# ================================================================ Marktphase

def update_phase(now):
    """Tag 13: Wie hoch laufen frische Coins, wie viel Volumen ist da?"""
    tokens = jup_category("toptrending", "1h", 100)
    if not tokens:
        return None
    views = [token_view(t, now) for t in tokens]
    update_symbol_leaders(views, now)
    young = [v for v in views if v["age_h"] is not None and v["age_h"] <= YOUNG_TOKEN_H]
    hot_count = sum(1 for v in young if v["mcap"] >= HOT_MCAP_USD)
    volume = sum(v["volume_1h"] for v in young)

    state = {"history": []}
    if os.path.exists(PHASE_FILE):
        try:
            with open(PHASE_FILE, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
    hist = state.get("history", [])
    phase = "normal"
    if len(hist) >= PHASE_MIN_HISTORY:
        med_count = sorted(h[1] for h in hist)[len(hist) // 2]
        med_vol = sorted(h[2] for h in hist)[len(hist) // 2]
        if hot_count >= med_count and volume >= med_vol and hot_count > 0:
            phase = "heiss"
        elif hot_count < med_count and volume < med_vol:
            phase = "ruhig"
    hist.append([int(now), hot_count, round(volume)])
    state = {"history": hist[-PHASE_HISTORY_MAX:], "phase": phase,
             "hot_count": hot_count, "volume_1h": round(volume), "updated": int(now)}
    with open(PHASE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return state


def current_phase():
    try:
        with open(PHASE_FILE, encoding="utf-8") as f:
            return json.load(f).get("phase", "normal")
    except Exception:
        return "normal"


# ================================================================ Kauf / Verkauf

def open_position(p, v, trench, sol_usd):
    decimals = v.get("decimals")
    if decimals is None:
        log_reject(v, "KEINE_DECIMALS")
        return False
    lamports = int(POSITION_SOL * 1e9)
    raw_out = quote(WSOL_MINT, v["mint"], lamports)
    if raw_out <= 0:
        log_reject(v, "KEIN_KAUFKURS")
        return False
    tokens = raw_out / (10 ** int(decimals))
    fill_usd = (POSITION_SOL * sol_usd) / tokens
    slippage = (fill_usd / v["price"] - 1) * 100 if v["price"] > 0 else 0.0
    back = quote(v["mint"], WSOL_MINT, raw_out)
    roundtrip = round((1 - back / lamports) * 100, 2) if back > 0 else None

    thesis = (f"Story verbreitet sich: Holder +{v['holder_growth_1h']:.0f}%/h, "
              f"{v['net_buyers_5m']} Netto-Kaeufer 5m, {v['organic_buyers_5m']} organisch; "
              f"Bundle haelt {trench.get('bundle_holding_pct', 0):.1f}%, "
              f"Dev-Rugs {trench.get('creator_rugs', 0)}")
    exit_rule = (f"Haelfte bei {TP1_MULTIPLE:.0f}x; Rest raus, wenn Holder schrumpfen und "
                 f"Netto-Verkaeufer {THESIS_BREAK_CHECKS}x in Folge, Liquiditaet -{LIQ_DROP_EXIT_PCT:.0f}%, "
                 f"{EMERGENCY_STOP_PCT:.0f}% oder nach 2x {TRAIL_AFTER_TP1_PCT:.0f}% vom Hoch")

    p["bankroll_sol"] = round(p["bankroll_sol"] - POSITION_SOL - TX_FEE_SOL, 6)
    pos = {"mint": v["mint"], "symbol": v["symbol"], "opened": time.time(),
           "invested_sol": POSITION_SOL, "fees_sol": TX_FEE_SOL,
           "entry_signal_usd": v["price"], "entry_fill_usd": fill_usd,
           "entry_slippage_pct": round(slippage, 2), "roundtrip_cost_pct": roundtrip,
           "tokens_initial": tokens, "tokens_left": tokens, "decimals": int(decimals),
           "proceeds_sol": 0.0, "peak_usd": v["price"], "tp1_done": False,
           "thesis_breaks": 0, "missing_loops": 0, "entry_liquidity": v["liquidity"],
           "entry_view": {k: v[k] for k in ("age_h", "mcap", "holders", "holder_growth_1h",
                                            "net_buyers_5m", "organic_buyers_5m",
                                            "organic_score", "price_change_1h")},
           "trench": trench, "phase": current_phase(), "thesis": thesis, "exit_rule": exit_rule}
    p["positions"][v["mint"]] = pos
    p["cooldown"][v["mint"]] = time.time()
    journal("KAUF", pos, fill_usd, POSITION_SOL)
    STATS["entries"].append({"symbol": v["symbol"], "roundtrip": roundtrip})
    discord(f"🎯 Kauf: {v['symbol']}",
            f"**These:** {thesis}\n**Verkauf wenn:** {exit_rule}\n"
            f"**Marktwert:** ${v['mcap']:,.0f} | **LP:** ${v['liquidity']:,.0f} | "
            f"**Alter:** {v['age_h']:.1f} h\n"
            f"**Einstieg:** {POSITION_SOL} SOL, Slippage {slippage:+.2f}%, "
            f"Hin+zurueck {roundtrip if roundtrip is not None else '?'}%\n"
            f"**Marktphase:** {pos['phase']} | **Bankroll frei:** {p['bankroll_sol']:.4f} SOL\n"
            f"https://jup.ag/tokens/{v['mint']}", 0x3B82F6)
    save_portfolio(p)
    return True


def sell(p, pos, fraction, price_usd, reason, sol_usd):
    """Verkauft einen Anteil der verbleibenden Token zum Jupiter-Kurs."""
    tokens = pos["tokens_left"] * fraction
    if tokens <= 0:
        return 0.0
    raw = int(tokens * (10 ** pos["decimals"]))
    lamports = quote(pos["mint"], WSOL_MINT, raw) if price_usd > 0 else 0
    if lamports > 0:
        proceeds = lamports / 1e9
    else:
        proceeds = max(0.0, tokens * price_usd / sol_usd * 0.95) if price_usd > 0 else 0.0
    proceeds = max(0.0, proceeds - TX_FEE_SOL)
    pos["tokens_left"] -= tokens
    pos["proceeds_sol"] += proceeds
    pos["fees_sol"] += TX_FEE_SOL
    p["bankroll_sol"] = round(p["bankroll_sol"] + proceeds, 6)
    journal("TEILVERKAUF" if pos["tokens_left"] > 1e-12 else "VERKAUF", pos, price_usd,
            proceeds, reason)
    return proceeds


def close_position(p, pos, price_usd, reason, sol_usd):
    sell(p, pos, 1.0, price_usd, reason, sol_usd)
    pnl = pos["proceeds_sol"] - pos["invested_sol"] - TX_FEE_SOL
    pnl_pct = pnl / pos["invested_sol"] * 100
    peak_x = pos["peak_usd"] / pos["entry_fill_usd"] if pos["entry_fill_usd"] else 0
    record = {k: pos[k] for k in ("symbol", "mint", "invested_sol", "entry_fill_usd",
                                  "entry_slippage_pct", "roundtrip_cost_pct", "tp1_done",
                                  "entry_view", "trench", "phase", "thesis")}
    record.update({"proceeds_sol": round(pos["proceeds_sol"], 6), "pnl_sol": round(pnl, 6),
                   "pnl_pct": round(pnl_pct, 2), "peak_multiple": round(peak_x, 2),
                   "exit_usd": price_usd, "exit_reason": reason,
                   "hold_h": round((time.time() - pos["opened"]) / 3600, 2),
                   "closed_at": datetime.now(timezone.utc).isoformat()})
    p["closed"].append(record)
    del p["positions"][pos["mint"]]
    journal("ERGEBNIS", pos, price_usd, pos["proceeds_sol"], reason, pnl, pnl_pct)
    STATS["exits"].append({"symbol": pos["symbol"], "pnl_sol": pnl, "pnl_pct": pnl_pct,
                           "reason": reason})
    discord(f"{'🟢' if pnl > 0 else '🔴'} Verkauf: {pos['symbol']}",
            f"**Grund:** {reason}\n**Ergebnis:** {pnl:+.4f} SOL ({pnl_pct:+.1f}%)\n"
            f"**Hoechststand:** {peak_x:.2f}x | **Teilverkauf bei 2x:** "
            f"{'ja' if pos['tp1_done'] else 'nein'}\n**These war:** {pos['thesis']}\n"
            f"**Bankroll frei:** {p['bankroll_sol']:.4f} SOL",
            0x10B981 if pnl > 0 else 0xEF4444)


def manage_positions(p, sol_usd, now):
    if not p["positions"]:
        return
    data = jup_tokens(list(p["positions"]))
    for mint, pos in list(p["positions"].items()):
        tok = data.get(mint)
        if not tok:
            pos["missing_loops"] += 1
            if pos["missing_loops"] >= DEAD_TOKEN_LOOPS:
                close_position(p, pos, 0.0, "TOKEN_NICHT_MEHR_HANDELBAR", sol_usd)
            continue
        pos["missing_loops"] = 0
        v = token_view(tok, now)
        price = v["price"]
        if price <= 0:
            continue
        pos["peak_usd"] = max(pos["peak_usd"], price)
        multiple = price / pos["entry_fill_usd"]
        change_pct = (multiple - 1) * 100

        # Tag 2: Gewinne mitnehmen
        if not pos["tp1_done"] and multiple >= TP1_MULTIPLE:
            got = sell(p, pos, TP1_SELL_FRACTION, price, f"HAELFTE_BEI_{TP1_MULTIPLE:.0f}X", sol_usd)
            pos["tp1_done"] = True
            STATS["partials"].append({"symbol": pos["symbol"], "sol": got})
            discord(f"💰 Haelfte verkauft: {pos['symbol']}",
                    f"Bei {multiple:.2f}x die Haelfte fuer {got:.4f} SOL verkauft. "
                    f"Der Rest laeuft weiter, solange die Story waechst.", 0xF59E0B)
            continue

        # Tag 3: These pruefen
        thesis_ok = not (v["holder_growth_1h"] < 0 and v["net_buyers_5m"] <= 0)
        pos["thesis_breaks"] = 0 if thesis_ok else pos["thesis_breaks"] + 1

        reason = None
        if change_pct <= EMERGENCY_STOP_PCT:
            reason = f"NOTBREMSE ({change_pct:+.0f}%)"
        elif pos["entry_liquidity"] > 0 and \
                v["liquidity"] < pos["entry_liquidity"] * (1 - LIQ_DROP_EXIT_PCT / 100):
            reason = "LIQUIDITAET_ABGEZOGEN"
        elif pos["thesis_breaks"] >= THESIS_BREAK_CHECKS:
            reason = "THESE_GEBROCHEN (Holder schrumpfen, Netto-Verkaeufer)"
        elif pos["tp1_done"] and price <= pos["peak_usd"] * (1 - TRAIL_AFTER_TP1_PCT / 100):
            reason = f"STORY_ABGEKUEHLT ({TRAIL_AFTER_TP1_PCT:.0f}% vom Hoch)"      # Tag 4
        elif now - pos["opened"] > MAX_HOLD_H * 3600:
            reason = "MAX_HALTEDAUER"
        if reason:
            close_position(p, pos, price, reason, sol_usd)
    save_portfolio(p)


# ================================================================ Scan

def scan(p, sol_usd, now):
    phase = current_phase()
    slots = MAX_POSITIONS.get(phase, 2) - len(p["positions"])          # Tag 9
    if slots <= 0 or p["bankroll_sol"] < POSITION_SOL + TX_FEE_SOL:
        return

    seen = {}
    for interval in ("5m", "1h"):
        for tok in jup_category("toptrending", interval, 100):
            if tok.get("id") and tok["id"] not in IGNORED_MINTS:
                seen[tok["id"]] = tok
    views = [token_view(t, now) for t in seen.values()]
    update_symbol_leaders(views, now)

    passed = []
    for v in views:
        if v["mint"] in p["positions"] or now - p["cooldown"].get(v["mint"], 0) < 24 * 3600:
            continue
        reason = quick_checks(v)
        if reason:
            log_reject(v, reason)
            continue
        passed.append(v)

    # Staerkste Verbreitung zuerst
    passed.sort(key=lambda x: x["holder_growth_1h"], reverse=True)
    for v in passed:
        if slots <= 0:
            break
        if REQUIRE_SOCIAL_LINK and not has_social(v):
            log_reject(v, "KEINE_STORY_LINKS")
            continue
        reason = safety_shield(v["mint"])
        if reason:
            log_reject(v, reason)
            continue
        reason, trench = bundle_dev_check(v["mint"])
        if reason:
            log_reject(v, reason)
            continue
        if open_position(p, v, trench, sol_usd):
            slots -= 1


# ================================================================ Discord / Git

def discord(title, text, color=0x6366F1):
    if not DISCORD_WEBHOOK_URL:
        print(f"[DISCORD] {title}")
        return
    try:
        SESSION.post(DISCORD_WEBHOOK_URL, json={"embeds": [{
            "title": title, "description": text[:4000], "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat()}]}, timeout=8)
    except requests.RequestException as err:
        print(f"[DISCORD] {err}")


def git_push():
    files = [f for f in (PORTFOLIO_FILE, JOURNAL_FILE, REJECT_FILE, PHASE_FILE) if os.path.exists(f)]
    if not files:
        return
    subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=False)
    subprocess.run(["git", "config", "--global", "user.email",
                    "github-actions[bot]@users.noreply.github.com"], check=False)
    subprocess.run(["git", "add", *files], check=False)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        subprocess.run(["git", "commit", "-m", "NARRATIV Update [skip ci]"], check=False)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=False)


def shift_summary(p, start_value, started, reason):
    exits = STATS["exits"]
    wins = sum(1 for e in exits if e["pnl_sol"] > 0)
    locked = sum(pos["invested_sol"] for pos in p["positions"].values())
    top = sorted(STATS["rejects"].items(), key=lambda kv: -kv[1])[:6]
    rts = [e["roundtrip"] for e in STATS["entries"] if e["roundtrip"] is not None]
    lines = [
        f"**Grund:** {reason}",
        f"**Dauer:** {(time.time() - started) / 3600:.2f} h, {STATS['loops']} Loops",
        f"**Marktphase:** {current_phase()}",
        f"**Kaeufe:** {len(STATS['entries'])} | **Teilverkaeufe bei 2x:** {len(STATS['partials'])}",
        f"**Geschlossen:** {len(exits)}" + (f" ({wins}W/{len(exits) - wins}L, "
                                             f"{sum(e['pnl_sol'] for e in exits):+.4f} SOL)" if exits else ""),
        f"**Bankroll:** {start_value:.4f} -> {p['bankroll_sol'] + locked:.4f} SOL "
        f"(offene Positionen zum Einstand)",
        f"**Offen:** {len(p['positions'])} " + ", ".join(pos["symbol"] for pos in p["positions"].values()),
    ]
    if rts:
        lines.append(f"**Hin+zurueck (Ø):** {sum(rts) / len(rts):.2f}%")
    if top:
        lines.append("**Haeufigste Ablehnungen:** " + ", ".join(f"{k} {v}" for k, v in top))
    lines.append(f"**Jupiter:** {STATS['jup_ok']} ok / {STATS['jup_fail']} Fehler | "
                 f"**TrenchBot:** {STATS['trench_ok']} ok / {STATS['trench_fail']} Fehler")
    lines.append(f"**Loop-Fehler:** {STATS['loop_errors']}"
                 + (f" ({STATS['last_error'][:150]})" if STATS["loop_errors"] else ""))
    ok = reason.startswith("regulaer") and STATS["loop_errors"] == 0
    discord("🔴 Schicht beendet" if ok else "⚠️ Schicht beendet (pruefen)", "\n".join(lines),
            0x6366F1 if ok else 0xF59E0B)


# ================================================================ Loop

class Interrupted(Exception):
    pass


def _on_signal(signum, frame):
    raise Interrupted(signal.Signals(signum).name)


def run():
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    started = time.time()
    p = load_portfolio()
    sol_usd = sol_price()
    start_value = p["bankroll_sol"] + sum(x["invested_sol"] for x in p["positions"].values())
    discord("🟢 Schicht gestartet (NARRATIV)",
            f"**Bankroll:** {start_value:.4f} SOL | **Offen:** {len(p['positions'])}\n"
            f"**SOL:** ${sol_usd:,.2f} | **Jupiter:** {'mit Key' if JUPITER_API_KEY else 'ohne Key'}\n"
            f"**Marktphase:** {current_phase()}", 0x22C55E)
    reason = "regulaer (Schichtende)"
    loop = 0
    try:
        while time.time() - started < SHIFT_DURATION_SECONDS:
            loop += 1
            STATS["loops"] = loop
            try:
                now = time.time()
                sol_usd = sol_price()
                p = load_portfolio()
                if loop % PHASE_EVERY_LOOPS == 1:
                    update_phase(now)
                manage_positions(p, sol_usd, now)
                if loop % SCAN_EVERY_LOOPS == 1:
                    scan(p, sol_usd, now)
                save_portfolio(p)
                git_push()
            except Interrupted:
                raise
            except Exception as err:
                STATS["loop_errors"] += 1
                STATS["last_error"] = str(err)
                print(f"[LOOP ERROR] {err}")
            time.sleep(LOOP_SLEEP_SECONDS)
    except Interrupted as sig:
        reason = f"abgebrochen ({sig})"
    except Exception as err:
        reason = f"abgestuerzt ({err})"
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            shift_summary(load_portfolio(), start_value, started, reason)
        except Exception as err:
            print(f"[ENDE] {err}")
        git_push()


def probe():
    print(f"[PROBE] Jupiter: {JUP_BASE} ({'mit Key' if JUPITER_API_KEY else 'ohne Key'})")
    print(f"[PROBE] SOL-Kurs: {sol_price()}")
    tokens = jup_category("toptrending", "1h", 20)
    print(f"[PROBE] Trending 1h: {len(tokens)} Token")
    if not tokens:
        return
    now = time.time()
    print(f"[PROBE] Felder des ersten Tokens: {sorted(tokens[0].keys())}")
    for tok in tokens[:5]:
        v = token_view(tok, now)
        print(f"  {v['symbol']:<12} Alter {v['age_h'] if v['age_h'] is None else round(v['age_h'], 1)} h | "
              f"MC ${v['mcap']:,.0f} | Holder {v['holders']} ({v['holder_growth_1h']:+.1f}%/h) | "
              f"Netto 5m {v['net_buyers_5m']} | Social {v['social']} | Check: {quick_checks(v)}")
    pool = jup_category("toptrending", "5m", 100) + jup_category("toptrending", "1h", 100)
    young = [token_view(t, now) for t in pool]
    young = sorted((v for v in young if v["age_h"] is not None and v["age_h"] <= 24),
                   key=lambda v: v["age_h"])
    print(f"[PROBE] Junge Coins (unter 24 h) in den Trending-Listen: {len(young)}")
    for v in young[:5]:
        print(f"  {v['symbol']:<12} Alter {v['age_h']:.1f} h | MC ${v['mcap']:,.0f} | "
              f"Holder {v['holders']} ({v['holder_growth_1h']:+.1f}%/h) | Check: {quick_checks(v)}")
    if not young:
        print("[PROBE] Kein junger Coin gefunden, TrenchBot-Test entfaellt.")
        return
    test = young[0]
    print(f"[PROBE] Social-Links fuer {test['symbol']} (DexScreener): {has_social(test)}")
    t0 = time.time()
    data = trench_get(test["mint"])
    print(f"[PROBE] TrenchBot fuer {test['symbol']}: "
          f"{'nicht erreichbar' if data is None else 'erreichbar'} nach {time.time() - t0:.1f} s")
    if data:
        print(f"[PROBE] TrenchBot-Felder: {sorted(data.keys())}")
        print(f"[PROBE] Bewertung: {bundle_dev_check(test['mint'])}")
    print("[PROBE] fertig. Diese Ausgabe bitte an Claude schicken.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    probe() if args.probe else run()
