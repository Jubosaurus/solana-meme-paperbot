"""Wallet-Scout: findet Kandidaten fuer das Copy Trading und erstellt eine Rangliste. Kauft und aendert nichts.

Ablauf (alle 6 Stunden):
1. Gewinner-Coins aus unseren eigenen Daten (Hauptstrategie, Experimente, Kursverlaeufe): Hoch >= 3x.
2. Kandidaten finden: fruehe Kaeufer dieser Coins (Helius, ohne die Kaeufer im ersten Block) und, falls
   verfuegbar, die Top-Trader laut Birdeye (Gratis-Tarif: CU-Zaehler, Stopp bei 28.000 CUs im Monat).
3. Stufe 1 (1 Helius-Credit je Wallet): letzte 1.000 Transaktionen mit Fehlerstatus -> Bots und stille Wallets raus.
4. Stufe 2 (rund 60 Credits je Wallet): letzte 60 erfolgreiche Transaktionen mit der Logik des Copy-Bots auswerten.
5. Rangliste in Discord und in scout/kandidaten.csv.
6. Automatik (seit 04.10., Schalter AUTO_AUFNAHME): gute Kandidaten kommen selbst in copy_wallets.txt, bei vollem
   Limit ersetzen sie eine Wallet, die eine Wallet-Regel erfuellt; sonst Warteliste (scout/warteliste.csv).
Modus --nur-pruefliste: nur die Pruefliste bewerten (ohne Gewinner-Coins und Birdeye), danach die Automatik.
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from statistics import median

import requests

import bot as core
import copy_bot as cb

# ================================================================ Schalter (Entscheidung des Betreibers 04.10.)
AUTO_AUFNAHME = True                # True: Scout nimmt Copy-Wallets selbst auf und ersetzt sie. False: nur melden
AUTO_MAX_WALLETS = 30               # hoechstens so viele aktive Wallets in copy_wallets.txt
AUTO_MAX_PRO_TAG = 3                # hoechstens so viele Aenderungen (Aufnahme oder Ersetzen) pro Tag (UTC)
FLOOD_HINT_DAYS = 7                 # Flutschutz-Abmeldung im Copy-Bot zaehlt so lange als Bot-Hinweis beim Ersetzen

# Zeitplan (seit 04.10.): GitHub laesst geplante Laeufe aus oder startet sie Stunden spaeter. Der Workflow stoesst
# deshalb stuendlich an; mit --wenn-faellig laeuft der Scout nur, wenn im aktuellen 6-h-Fenster (00, 06, 12, 18 UTC)
# noch kein kompletter Lauf war.
RUN_SLOT_S = 6 * 3600

core.HELIUS_INTERVAL = 0.5          # Scout hoechstens ~2 Helius-Anfragen/s, laeuft parallel zu den anderen Bots

SCOUT_DIR = "scout"
STATE_FILE = os.path.join(SCOUT_DIR, "status.json")
CANDIDATES_FILE = os.path.join(SCOUT_DIR, "kandidaten.csv")
# Pruef-Modus (seit 04.10.): einzelne Transaktionen einer Wallet ueber Helius pruefen, ob der Copy-Bot sie erkennt
TX_CHECK_FILE = os.path.join(SCOUT_DIR, "pruefen_tx.txt")
TX_RESULT_FILE = os.path.join(SCOUT_DIR, "tx_pruefung.csv")
TX_RESULT_HEADER = ["zeit", "name", "wallet", "signatur", "block_zeit", "erfolgreich", "copy_bot_erkennt", "sol",
                    "mint", "live_filter", "sol_aenderung", "token_aenderung", "programme"]
TX_CHECK_MAX = 40                   # hoechstens so viele Transaktionen je Wallet (Helius: ~1 Credit je Abfrage)
LIST_FILE = os.path.join(SCOUT_DIR, "pruefen.txt")   # Pruefliste: Wallets, die du selbst gefunden hast
LIST_TX = 150                       # fuer die Pruefliste mehr Transaktionen je Wallet auswerten
SCORING_VERSION = "3"               # 02.10.: 7 Tage, gehaltene Coins zum Kurs, Reibung nach Haltedauer
#                                     04.10.: Kleinstkaeufe (Median unter 0,05 SOL) werden nicht bewertet
DISCORD_WEBHOOK_SCOUT = (os.environ.get("DISCORD_WEBHOOK_SCOUT") or os.environ.get("DISCORD_WEBHOOK_COPY") or "").strip()
BIRDEYE_API_KEY = (os.environ.get("BIRDEYE_API_KEY") or "").strip()
BIRDEYE_BASE = "https://public-api.birdeye.so"
BIRDEYE_CU = {"top_traders": 35}
BIRDEYE_MONTH_LIMIT = 28_000        # Gratis-Tarif 30.000 CUs; Reserve fuer Probelaeufe
BIRDEYE_INTERVAL = 1.2              # Gratis-Tarif: 1 Anfrage pro Sekunde

WINNER_MIN_MULTIPLE = 3.0           # Gewinner-Coin: Hoch mindestens 3x
WINNER_LOOKBACK_H = 48
COINS_PER_RUN = 6
EARLY_TX = 80                       # so viele fruehe erfolgreiche Transaktionen je Coin auswerten
MAX_SIG_PAGES = 5                   # bis zu 5.000 Signaturen zurueck; wird der Start nicht erreicht, Coin ueberspringen
BAD_TAGS = ("bundl", "snip", "bot", "mev", "insider", "dev", "arb")   # Birdeye-Markierungen, die wir nicht kopieren
BIRDEYE_PER_COIN = 5                # hoechstens so viele Birdeye-Kandidaten je Coin

STAGE2_PER_RUN = 15
STAGE2_TX = 60
RECHECK_DAYS = 7                    # eine Wallet fruehestens nach 7 Tagen erneut pruefen

# Stufe 1: Ausschlussgruende
BOT_FAILED_HARD = 0.8               # ueber 80 % fehlgeschlagen: Bot
BOT_FAILED_SOFT = 0.5               # ueber 50 % fehlgeschlagen UND ...
BOT_SOFT_MIN_TX_H = 60              # ... mehr als 60 Transaktionen pro Stunde: Bot
MAX_TX_PER_HOUR = 300
MAX_IDLE_H = 24                     # automatische Suche
LIST_MAX_IDLE_H = 72                # Pruefliste: Trader, die Coins tagelang halten, sind auch mal 2-3 Tage still
MIN_TX = 20
WINDOW_DAYS = 7                     # Stufe 2: letzte 7 Tage wie GMGN 7D
MAX_WINDOW_PAGES = 5
MIN_COINS = 3
MIN_KAUF_SOL = 0.05                 # darunter blaeht die Rendite in % auf (z. B. 0,002 SOL -> 472.633 %), nicht kopierbar
FRICTION_SHORT, FRICTION_MID, FRICTION_LONG = 10.0, 6.0, 3.0   # Reibung in Prozentpunkten je nach Haltedauer

# Automatik: Aufnahme-Kriterien (alle muessen erfuellt sein) und Warteliste
WAIT_FILE = os.path.join(SCOUT_DIR, "warteliste.csv")
WAIT_HEADER = ["seit", "bewertet", "wallet", "name", "quelle", "punkte", "rendite_ohne_besten_pct", "coins",
               "kauf_median_sol", "trades_pro_tag", "inaktiv_h"]
AUTO_MAX_IDLE_H = 24                # letzte Aktivitaet unter 24 h
AUTO_MIN_COINS = 3                  # mindestens 3 Coins im Zeitraum (04.10. abends: gelockert von 5)
AUTO_MAX_TRADES_TAG = 200           # hoechstens 200 Trades pro Tag
AUTO_MIN_KAUF_SOL = 0.1             # Kauf-Median mindestens 0,1 SOL (darunter kaufen wir 0,2 SOL, der Trader viel weniger)
AUTO_SCHONFRIST_TAGE = 7            # unter 7 Tagen UND unter 30 Positionen: nicht wegen Ergebnis ersetzen
WAIT_RECHECK_H = 6                  # Bewertung aelter als 6 h: vor der Aufnahme neu pruefen
WAIT_MAX_TAGE = 7                   # nach 7 Tagen faellt ein Kandidat von der Warteliste
RECHECK_MAX_PRO_LAUF = 5            # hoechstens so viele Neupruefungen (Stufe 1+2, bis ~150 Credits) je Lauf
ADDR_RE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")

_birdeye_last = [0.0]
STATS = {"coins": 0, "kandidaten": 0, "stufe1_raus": {}, "stufe2": 0, "birdeye_cu": 0, "birdeye_fehler": "", "fehler": 0}


# ================================================================ Status

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"coins_erledigt": {}, "wallets_geprueft": {}, "birdeye": {"monat": "", "cu": 0}}


def save_state(state):
    os.makedirs(SCOUT_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE_FILE)


# ================================================================ 1. Gewinner-Coins aus unseren Daten

def winner_coins(state, now):
    """Coins mit Hoch >= 3x aus Portfolios, Experimenten und Kursverlaeufen der letzten 48 Stunden."""
    best = {}
    since = datetime.fromtimestamp(now - WINNER_LOOKBACK_H * 3600, timezone.utc).isoformat()
    for f in ["portfolio.json"] + glob.glob("experimente/*/portfolio.json"):
        try:
            p = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for c in p.get("closed", []):
            if c.get("closed_at", "") >= since and c.get("peak_multiple", 0) >= WINNER_MIN_MULTIPLE:
                best[c["mint"]] = max(best.get(c["mint"], (0, ""))[0], c["peak_multiple"]), c["symbol"]
    days = {datetime.fromtimestamp(now - h * 3600, timezone.utc).strftime("%Y-%m-%d") for h in (0, 24, 48)}
    for f in [p for d in days for p in (f"verlauf/{d}.csv", f"copy/verlauf/{d}.csv")]:
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    m = float(row.get("vielfaches") or 0)
                except ValueError:
                    continue
                if m >= WINNER_MIN_MULTIPLE and row.get("mint"):
                    if m > best.get(row["mint"], (0, ""))[0]:
                        best[row["mint"]] = (m, row.get("symbol", "?"))
    done = state["coins_erledigt"]
    fresh = [(m, s, mint) for mint, (m, s) in best.items() if mint not in done]
    return [(mint, s, m) for m, s, mint in sorted(fresh, reverse=True)[:COINS_PER_RUN]]


# ================================================================ 2. Kandidaten finden

def early_buyers(mint, sol_usd):
    """Fruehe Kaeufer eines Coins: aelteste erfolgreiche Transaktionen, ohne den ersten Block (Bundler)."""
    sigs, before, reached_start = [], None, False
    for _ in range(MAX_SIG_PAGES):
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = core.rpc("getSignaturesForAddress", [mint, opts]) or []
        sigs.extend(page)
        if len(page) < 1000:
            reached_start = True
            break
        before = page[-1].get("signature")
    if not reached_start:
        STATS["coins_zu_aktiv"] = STATS.get("coins_zu_aktiv", 0) + 1
        return []                                   # Start nicht erreicht: das waeren keine fruehen Kaeufer
    ok = [s for s in reversed(sigs) if s.get("err") is None and s.get("signature")]
    if not ok:
        return []
    first_slot = ok[0].get("slot")
    buyers = []
    for s in ok[:EARLY_TX]:
        if s.get("slot") == first_slot:
            continue                                # erster Block: Dev und Bundler
        tx = cb.fetch_tx(s["signature"])
        keys = ((tx or {}).get("transaction") or {}).get("message", {}).get("accountKeys") or []
        if not keys:
            continue
        signer = keys[0].get("pubkey") if isinstance(keys[0], dict) else keys[0]
        t = cb.parse_trade(tx, signer, sol_usd)
        if t and t["kind"] == "KAUF" and t["mint"] == mint:
            buyers.append(signer)
    return list(dict.fromkeys(buyers))


def birdeye_get(path, state, cost):
    if not BIRDEYE_API_KEY:
        return None
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = state["birdeye"]
    if usage.get("monat") != month:
        usage.update(monat=month, cu=0)
    if usage["cu"] + cost > BIRDEYE_MONTH_LIMIT:
        STATS["birdeye_fehler"] = f"Monatsgrenze erreicht ({usage['cu']} CUs)"
        return None
    core._throttle(_birdeye_last, BIRDEYE_INTERVAL)
    try:
        res = core.SESSION.get(f"{BIRDEYE_BASE}{path}", headers={"X-API-KEY": BIRDEYE_API_KEY, "x-chain": "solana",
                                                                 "accept": "application/json"}, timeout=15)
    except requests.RequestException as err:
        STATS["birdeye_fehler"] = str(err)[:80]
        return None
    usage["cu"] += cost
    STATS["birdeye_cu"] += cost
    if res.status_code != 200:
        STATS["birdeye_fehler"] = f"HTTP {res.status_code}: {res.text[:80]}"
        return None
    try:
        return res.json()
    except ValueError:
        return None


def birdeye_top_traders(mint, state):
    data = birdeye_get(f"/defi/v2/tokens/top_traders?address={mint}&time_frame=24h&sort_type=desc"
                       f"&sort_by=volume&offset=0&limit=10", state, BIRDEYE_CU["top_traders"])
    items = ((data or {}).get("data") or {}).get("items") or []
    out = []
    for it in items:
        addr = it.get("owner") or it.get("address") or it.get("wallet")
        if not addr:
            continue
        STATS["birdeye_eintraege"] = STATS.get("birdeye_eintraege", 0) + 1
        tags = " ".join(str(t).lower() for t in (it.get("tags") or []))
        if any(b in tags for b in BAD_TAGS):
            STATS["birdeye_markiert"] = STATS.get("birdeye_markiert", 0) + 1
            continue
        total = it.get("totalPnl")
        total = core.as_float(total) if total is not None else \
            core.as_float(it.get("realizedPnl")) + core.as_float(it.get("unrealizedPnl"))
        if total <= 0:                              # Gesamtgewinn inkl. noch gehaltener Coins
            STATS["birdeye_ohne_gewinn"] = STATS.get("birdeye_ohne_gewinn", 0) + 1
            continue
        out.append(addr)
    return out[:BIRDEYE_PER_COIN]


# ================================================================ 3./4. Wallets pruefen

def stage1(wallet, now, max_idle_h=None):
    """Billige Vorpruefung: Fehleranteil, Takt, letzte Aktivitaet. Gibt (Kennzahlen, Grund zum Ausschluss)."""
    max_idle_h = max_idle_h or MAX_IDLE_H
    sigs = core.rpc("getSignaturesForAddress", [wallet, {"limit": 1000}]) or []
    if len(sigs) < MIN_TX:
        return {"tx": len(sigs), "_page": sigs}, "zu wenig Transaktionen"
    times = [s["blockTime"] for s in sigs if s.get("blockTime")]
    failed = sum(1 for s in sigs if s.get("err") is not None) / len(sigs)
    span_h = max((max(times) - min(times)) / 3600, 1 / 60) if times else 0
    per_h = len(sigs) / span_h if span_h else 0
    idle_h = (now - max(times)) / 3600 if times else 999
    m = {"tx": len(sigs), "fehlgeschlagen": round(failed, 3), "tx_pro_h": round(per_h, 1), "inaktiv_h": round(idle_h, 1),
         "_page": sigs}
    # Bot: fast nur Fehlschlaege, oder viele Fehlschlaege bei hohem Takt. Menschen mit Trading-Bot und
    # Wiederholungen haben oft ueber 50 % Fehlschlaege, aber nur wenige Transaktionen pro Stunde (z. B. Eshi).
    if failed > BOT_FAILED_HARD or (failed > BOT_FAILED_SOFT and per_h > BOT_SOFT_MIN_TX_H):
        return m, "Bot (viele fehlgeschlagene Transaktionen)"
    if per_h > MAX_TX_PER_HOUR:
        return m, "Bot (zu hoher Takt)"
    if idle_h > max_idle_h:
        return m, f"still (laenger als {max_idle_h:.0f} h kein Trade)"
    return m, None


def window_sigs(wallet, first_page, now, max_n):
    """Erfolgreiche Signaturen der letzten 7 Tage (neueste zuerst), hoechstens max_n."""
    since = now - WINDOW_DAYS * 86400
    out, page, pages = [], first_page, 1
    while page:
        for s in page:
            if (s.get("blockTime") or 0) < since:
                return out[:max_n]
            if s.get("err") is None and s.get("signature"):
                out.append(s["signature"])
        if len(page) < 1000 or pages >= MAX_WINDOW_PAGES or len(out) >= max_n:
            break
        page = core.rpc("getSignaturesForAddress", [wallet, {"limit": 1000, "before": page[-1].get("signature")}]) or []
        pages += 1
    return out[:max_n]


def current_prices_sol(mints, sol_usd):
    prices = {}
    mints = list(mints)
    for i in range(0, len(mints), 100):
        for tok in cb.jup(f"/tokens/v2/search?query={','.join(mints[i:i + 100])}") or []:
            if tok.get("id") and sol_usd:
                prices[tok["id"]] = core.as_float(tok.get("usdPrice")) / sol_usd
    return prices


def stage2(wallet, sigs, sol_usd):
    """Auswertung der letzten 7 Tage mit der Logik des Copy-Bots. Wie GMGN: noch gehaltene Coins zum aktuellen
    Kurs bewertet, Rendite auf den gesamten Einsatz. Coins, die vor dem Zeitraum gekauft wurden, zaehlen nicht."""
    trades = []
    for sig in sigs:
        t = cb.parse_trade(cb.fetch_tx(sig), wallet, sol_usd)
        if t and t["kind"] in ("KAUF", "VERKAUF"):
            trades.append(t)
    buys = [t for t in trades if t["kind"] == "KAUF"]
    sells = [t for t in trades if t["kind"] == "VERKAUF"]
    per = {}
    for t in sorted(trades, key=lambda t: t["block_time"] or 0):
        p = per.setdefault(t["mint"], {"aus": 0.0, "ein": 0.0, "gekauft": 0.0, "verkauft": 0.0,
                                       "t0": t["block_time"] or 0, "t1": t["block_time"] or 0})
        p["aus" if t["kind"] == "KAUF" else "ein"] += t["sol"]
        p["gekauft" if t["kind"] == "KAUF" else "verkauft"] += t["tokens"]
        p["t1"] = max(p["t1"], t["block_time"] or p["t1"])
    coins = {m: p for m, p in per.items() if p["aus"] > 0}             # im Zeitraum gekauft
    held = {m for m, p in coins.items() if p["verkauft"] < 0.9 * p["gekauft"]}
    prices = current_prices_sol(held, sol_usd) if held else {}
    gains = []
    for m, p in coins.items():
        value = max(0.0, p["gekauft"] - p["verkauft"]) * prices.get(m, 0.0)   # ohne Kurs: Rest zaehlt als 0
        gains.append((p["ein"] + value - p["aus"], p["aus"]))
    spent = sum(a for _, a in gains)
    total_gain = sum(g for g, _ in gains)
    best = max(gains, default=(0.0, 0.0))
    rest_spent = spent - best[1]
    closed = [p for m, p in coins.items() if m not in held]
    hold_closed = median((p["t1"] - p["t0"]) / 60 for p in closed) if closed else None
    fast = [p for p in closed if p["t1"] - p["t0"] < 60]          # Kauf bis letzter Verkauf unter 60 s (Flip)
    held_share = len(held) / len(coins) if coins else 0
    if held_share >= 0.5 or (hold_closed is not None and hold_closed >= 60):
        friction = FRICTION_LONG
    elif hold_closed is not None and hold_closed < 10:
        friction = FRICTION_SHORT
    else:
        friction = FRICTION_MID
    micro = [t for t in sells if t["pre_raw"] and abs(t["delta_raw"]) / t["pre_raw"] < 0.05]
    times = [t["block_time"] for t in trades if t["block_time"]]
    span_d = max((max(times) - min(times)) / 86400, 1 / 24) if len(times) > 1 else None
    return {
        "trades": len(trades), "kaeufe": len(buys), "verkaeufe": len(sells),
        "trades_pro_tag": round(len(trades) / span_d, 1) if span_d else None,
        "kauf_median_sol": round(median(t["sol"] for t in buys), 3) if buys else None,
        "anteil_kaeufe_ab_0_1": round(sum(t["sol"] >= 0.1 for t in buys) / len(buys), 2) if buys else None,
        "coins": len(coins), "coins_abgeschlossen": len(closed), "coins_gehalten": len(held),
        "trefferquote": round(sum(g > 0 for g, _ in gains) / len(gains), 2) if gains else None,
        "gewinn_sol": round(total_gain, 3),
        "rendite_pct": round(total_gain / spent * 100, 1) if spent else None,
        "rendite_ohne_besten_pct": round((total_gain - best[0]) / rest_spent * 100, 1) if rest_spent > 0 else None,
        "haltedauer_median_min": round(hold_closed, 1) if hold_closed is not None else None,
        "schnelle_verkaeufe_anteil": round(len(fast) / len(closed), 2) if closed else None,   # nur Anzeige, kein Kriterium
        "reibung_pp": friction,
        "mini_verkaeufe_anteil": round(len(micro) / len(sells), 2) if sells else None,
        "bot_gebuehr_anteil": round(sum(t["other"] > 0.003 * t["sol"] for t in trades) / len(trades), 2) if trades else None,
    }


def not_rated_reason(s2):
    """Warum eine Wallet nicht bewertet wird (None = bewertbar)."""
    if s2 and s2.get("kauf_median_sol") is not None and s2["kauf_median_sol"] < MIN_KAUF_SOL:
        return f"Kleinstkaeufe (Median unter {MIN_KAUF_SOL:.2f} SOL)"
    if not s2 or (s2.get("coins") or 0) < MIN_COINS or s2.get("rendite_ohne_besten_pct") is None:
        return "zu wenig Coins im Zeitraum"
    return None


def score(s2):
    """Fuer uns erwartete Rendite: Rendite des Traders auf den Einsatz ohne seinen besten Coin, minus die
    Reibung beim Kopieren (je nach Haltedauer 3 bis 10 Prozentpunkte). Abzuege fuer ueberwiegend
    Mini-Verkaeufe und Kaeufe unter 0,1 SOL. Erst ab 3 im Zeitraum gekauften Coins bewertbar."""
    if not_rated_reason(s2):
        return None
    base = s2["rendite_ohne_besten_pct"] - s2["reibung_pp"]
    if (s2.get("mini_verkaeufe_anteil") or 0) > 0.5:
        base -= 10
    if (s2.get("anteil_kaeufe_ab_0_1") or 0) < 0.5:
        base -= 10
    return round(base, 1)


# ================================================================ Ausgabe

CANDIDATES_HEADER = ["zeit", "wallet", "quelle", "coin", "ergebnis", "grund", "punkte", "tx", "fehlgeschlagen", "tx_pro_h",
                     "inaktiv_h", "trades", "kaeufe", "verkaeufe", "trades_pro_tag", "kauf_median_sol", "anteil_kaeufe_ab_0_1",
                     "coins_abgeschlossen", "trefferquote", "gewinn_sol", "gewinn_ohne_beste_sol", "beste_abgezogen",
                     "rendite_median_pct", "rendite_ohne_beste_pct", "haltedauer_median_min",
                     "mini_verkaeufe_anteil", "bot_gebuehr_anteil", "coins", "coins_gehalten", "rendite_pct",
                     "rendite_ohne_besten_pct", "reibung_pp", "schnelle_verkaeufe_anteil"]
OLD_ROW_LEN = len(CANDIDATES_HEADER) - 1            # Zeilen vor 07.10. ohne schnelle_verkaeufe_anteil


def write_csv(rows):
    os.makedirs(SCOUT_DIR, exist_ok=True)
    header = CANDIDATES_HEADER
    if os.path.exists(CANDIDATES_FILE):
        core.ensure_csv_columns(CANDIDATES_FILE, header)
    new = not os.path.exists(CANDIDATES_FILE)
    with open(CANDIDATES_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        for r in rows:
            w.writerow([r.get(k, "") for k in header])


def notify(title, lines):
    saved = dict(core.CTX)
    core.CTX.update(webhook=DISCORD_WEBHOOK_SCOUT or None, title_prefix="")
    try:
        core.discord(title, "\n".join(l for l in lines if l), 0x0EA5E9)
    finally:
        core.CTX.clear()
        core.CTX.update(saved)


def git_push():
    g = core._git
    g("config", "user.name", "github-actions[bot]")
    g("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    for _ in range(3):
        if g("fetch", "-q", "origin", "main").returncode != 0:
            continue
        g("reset", "-q", "origin/main")
        g("add", SCOUT_DIR)
        if g("diff", "--cached", "--quiet").returncode == 0:
            return
        g("commit", "-q", "-m", "SCOUT Update [skip ci]")
        if g("push", "-q", "origin", "HEAD:main").returncode == 0:
            return


# ================================================================ Pruefliste

def load_list():
    """Liest scout/pruefen.txt. Erlaubt 'Name: Adresse', nur 'Adresse' oder eine eingefuegte Python-Liste."""
    if not os.path.exists(LIST_FILE):
        return []
    entries, seen = [], set()
    for line in open(LIST_FILE, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for addr in re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,44}", line):
            if addr in seen:
                continue
            seen.add(addr)
            name = line.split(":", 1)[0].strip() if ":" in line and addr not in line.split(":", 1)[0] else addr[:6]
            entries.append((name, addr))
    return entries


def _fast_text(s2):
    """Anteil abgeschlossener Coins mit Haltedauer unter 60 s (nur Anzeige, kein Aufnahmekriterium)."""
    v = s2.get("schnelle_verkaeufe_anteil")
    return "Verkaeufe unter 60 s: " + ("-" if v in (None, "") else f"{core.as_float(v):.0%}")


def _rating_line(name, w, s2, pts):
    """(Sortierwert, Discord-Zeile) fuer eine bewertete Wallet."""
    detail = (f"7 Tage: {s2['coins']} Coins ({s2['coins_gehalten']} noch gehalten), Trader {s2.get('rendite_pct')} % "
              f"auf den Einsatz, ohne besten Coin {s2.get('rendite_ohne_besten_pct')} %, Treffer "
              f"{(s2.get('trefferquote') or 0):.0%}, Kauf-Median {s2.get('kauf_median_sol')} SOL, "
              f"{s2.get('trades_pro_tag')} Trades/Tag, Haltedauer {s2.get('haltedauer_median_min')} min, "
              f"{_fast_text(s2)}, Reibung {s2['reibung_pp']:.0f} Punkte")
    if pts is None:
        return -500, f"❔ **{name}** `{w}`\n   {not_rated_reason(s2)} | {detail}"
    return pts, f"{'✅' if pts > 0 else '➖'} **{name}** `{w}`\n   fuer uns {pts:+.0f} % | {detail}"


def _list_digest(entries):
    return hashlib.sha256((SCORING_VERSION + ":" + ",".join(sorted(a for _, a in entries))).encode()).hexdigest()[:16]


def check_list(state, now, sol_usd):
    """Bewertet nur Adressen der Pruefliste, die noch nicht (mit der aktuellen SCORING_VERSION) bewertet sind.
    Bereits bewertete kommen aus dem Speicher (state['liste_bewertet']) und werden nur angezeigt.
    Rueckgabe: (Zeilen fuer kandidaten.csv, nur neue; Discord-Zeilen, neue und gespeicherte; leer = nichts Neues)."""
    entries = load_list()
    if not entries:
        return [], []
    first = "liste_bewertet" not in state
    memo = state.setdefault("liste_bewertet", {})
    if first and state.get("liste_hash") == _list_digest(entries):
        # Uebergang vom alten Listen-Hash: die ganze Liste war mit dieser Version schon bewertet
        for _, w in entries:
            memo[w] = {"version": SCORING_VERSION, "zeit": state["wallets_geprueft"].get(w, now)}
    todo = [(n, w) for n, w in entries if (memo.get(w) or {}).get("version") != SCORING_VERSION]
    STATS["liste_neu"] = len(todo)
    if not todo:
        return [], []
    rows, lines = [], []
    for name, w in todo:
        n_lines = len(lines)
        try:
            m, reason = stage1(w, now, LIST_MAX_IDLE_H)
            row = {"zeit": cb.now_str(), "wallet": w, "quelle": "liste", "coin": name,
                   **{k: v for k, v in m.items() if not k.startswith("_")}}
            if reason:
                rows.append(dict(row, ergebnis="raus", grund=reason))
                lines.append((-999, f"❌ **{name}** `{w}`\n   raus: {reason} ({min(m.get('tx_pro_h') or 0, 9999)} Tx/h, "
                                    f"{(m.get('fehlgeschlagen') or 0):.0%} fehlgeschlagen, {m.get('inaktiv_h')} h inaktiv)"))
            else:
                s2 = stage2(w, window_sigs(w, m["_page"], now, LIST_TX), sol_usd)
                pts = score(s2)
                rows.append(dict(row, **s2, ergebnis="bewertet" if pts is not None else not_rated_reason(s2),
                                 punkte=pts if pts is not None else ""))
                lines.append(_rating_line(name, w, s2, pts))
        except Exception as err:                    # nicht gespeichert: naechster Lauf versucht es erneut
            STATS["fehler"] += 1
            lines.append((-998, f"⚠️ **{name}**: Fehler bei der Pruefung ({str(err)[:60]})"))
            continue
        state["wallets_geprueft"][w] = now
        if rows and rows[-1]["wallet"] == w and str(rows[-1].get("grund", "")).startswith("zu wenig Transaktionen"):
            continue                                # evtl. nur leere Helius-Antwort: naechster Lauf prueft erneut
        if len(lines) > n_lines:
            memo[w] = {"version": SCORING_VERSION, "zeit": now, "sort": lines[-1][0], "zeile": lines[-1][1]}
    new = {w for _, w in todo}
    for name, w in entries:                         # schon bewertete aus dem Speicher anzeigen
        m = memo.get(w)
        if w in new or not m:
            continue
        when = datetime.fromtimestamp(m.get("zeit") or now, timezone.utc).strftime("%d.%m. %H:%M")
        lines.append((m.get("sort", -600), (m.get("zeile") or f"🗂️ **{name}** `{w}`\n   schon bewertet, Ergebnis im Dashboard")
                      + f"\n   (aus dem Speicher, bewertet {when} UTC)"))
    return rows, [l for _, l in sorted(lines, key=lambda x: -x[0])]


# ================================================================ Pruef-Modus fuer einzelne Transaktionen

def load_tx_checks():
    """scout/pruefen_tx.txt: 'Name: Adresse seit JJJJ-MM-TTTHH:MM' (UTC). Ohne 'seit': die letzten 24 h."""
    if not os.path.exists(TX_CHECK_FILE):
        return [], ""
    entries, raw = [], []
    for line in open(TX_CHECK_FILE, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        addr = re.search(r"[1-9A-HJ-NP-Za-km-z]{32,44}", line)
        if not addr:
            continue
        raw.append(line)
        name = line.split(":", 1)[0].strip() if ":" in line and addr.group(0) not in line.split(":", 1)[0] \
            else addr.group(0)[:6]
        seit = None
        m = re.search(r"seit\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", line)
        if m:
            try:
                seit = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                seit = None
        entries.append((name, addr.group(0), seit))
    return entries, hashlib.sha256("\n".join(raw).encode()).hexdigest()[:16]


def _balance_changes(tx, wallet):
    meta = tx.get("meta") or {}
    keys = [k.get("pubkey") if isinstance(k, dict) else k for k in tx["transaction"]["message"]["accountKeys"]]
    sol = None
    if wallet in keys:
        i = keys.index(wallet)
        sol = (meta["postBalances"][i] - meta["preBalances"][i]) / 1e9

    def bal(lst):
        return {b["mint"]: core.as_float(b["uiTokenAmount"].get("uiAmount")) for b in lst or []
                if b.get("owner") == wallet}
    pre, post = bal(meta.get("preTokenBalances")), bal(meta.get("postTokenBalances"))
    tokens = {m[:6]: round(post.get(m, 0) - pre.get(m, 0), 2) for m in set(pre) | set(post)
              if abs(post.get(m, 0) - pre.get(m, 0)) > 0}
    progs = sorted({line.split()[1][:8] for line in meta.get("logMessages") or []
                    if line.startswith("Program ") and " invoke" in line})
    return sol, tokens, progs


def check_transactions(state, now, sol_usd):
    """Prueft jede Transaktion der Wallets aus scout/pruefen_tx.txt (einmal je Dateiinhalt):
    Erkennt der Copy-Bot sie als Kauf/Verkauf, und haette der Live-Filter (Log-Hinweis) sie ueberhaupt geholt?"""
    entries, digest = load_tx_checks()
    if not entries or state.get("tx_pruefung_hash") == digest:
        return []
    rows, lines = [], []
    for name, wallet, seit in entries:
        seit = seit or now - 86400
        try:
            sigs = core.rpc("getSignaturesForAddress", [wallet, {"limit": 100}]) or []
            neu = [x for x in sigs if (x.get("blockTime") or 0) >= seit][:TX_CHECK_MAX]
            zaehler = {}
            for x in reversed(neu):                        # aelteste zuerst
                ok = x.get("err") is None
                tx = cb.fetch_tx(x["signature"]) if ok else None
                t, art = None, "fehlgeschlagen" if not ok else "nicht abrufbar"
                sol = tokens = progs = None
                hint = None
                if tx:
                    try:
                        t = cb.parse_trade(tx, wallet, sol_usd)
                        art = t["kind"] if t else "kein Trade"
                    except Exception as err:               # eine kaputte Transaktion stoppt die Pruefung nicht
                        art = f"Fehler: {str(err)[:60]}"
                    hint = cb.trade_hint({"logs": (tx.get("meta") or {}).get("logMessages") or []})
                    sol, tokens, progs = _balance_changes(tx, wallet)
                zaehler[art] = zaehler.get(art, 0) + 1
                rows.append({"zeit": cb.now_str(), "name": name, "wallet": wallet, "signatur": x["signature"],
                             "block_zeit": datetime.fromtimestamp(x.get("blockTime") or 0, timezone.utc)
                             .strftime("%Y-%m-%d %H:%M:%S"),
                             "erfolgreich": int(ok), "copy_bot_erkennt": art,
                             "sol": f"{t['sol']:.6f}" if t else "", "mint": t["mint"] if t else "",
                             "live_filter": hint or "", "sol_aenderung": f"{sol:+.6f}" if sol is not None else "",
                             "token_aenderung": json.dumps(tokens, ensure_ascii=False) if tokens else "",
                             "programme": " ".join(progs or [])})
            verpasst = sum(1 for r in rows if r["wallet"] == wallet and r["copy_bot_erkennt"] in ("KAUF", "VERKAUF")
                           and r["live_filter"] != "handel")
            lines.append(f"**{name}** `{wallet}`: {len(neu)} Transaktionen seit "
                         f"{datetime.fromtimestamp(seit, timezone.utc):%d.%m. %H:%M} UTC | "
                         + ", ".join(f"{k} {v}" for k, v in sorted(zaehler.items()))
                         + (f" | ⚠️ {verpasst} Trades ohne Log-Hinweis (Live-Filter haette sie nicht geholt)"
                            if verpasst else ""))
        except Exception as err:
            STATS["fehler"] += 1
            lines.append(f"⚠️ **{name}**: Fehler bei der Transaktions-Pruefung ({str(err)[:60]})")
    os.makedirs(SCOUT_DIR, exist_ok=True)
    if os.path.exists(TX_RESULT_FILE):
        core.ensure_csv_columns(TX_RESULT_FILE, TX_RESULT_HEADER)
    neu_datei = not os.path.exists(TX_RESULT_FILE)
    with open(TX_RESULT_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neu_datei:
            w.writerow(TX_RESULT_HEADER)
        for r in rows:
            w.writerow([r.get(k, "") for k in TX_RESULT_HEADER])
    state["tx_pruefung_hash"] = digest
    return lines


# ================================================================ Automatik: Copy-Wallets aufnehmen und ersetzen

def auto_reason(r):
    """Warum ein bewerteter Kandidat NICHT automatisch aufgenommen wird (None = alle Kriterien erfuellt)."""
    def num(k):
        try:
            return float(r.get(k))
        except (TypeError, ValueError):
            return None
    if r.get("ergebnis") != "bewertet":            # Stufe 1 (Bot, still) nicht bestanden oder nicht bewertbar
        return str(r.get("grund") or r.get("ergebnis") or "nicht bewertet")
    checks = [
        (num("inaktiv_h") is not None and num("inaktiv_h") < AUTO_MAX_IDLE_H, f"letzte Aktivitaet nicht unter {AUTO_MAX_IDLE_H} h"),
        ((num("coins") or 0) >= AUTO_MIN_COINS, f"unter {AUTO_MIN_COINS} Coins im Zeitraum"),
        ((num("punkte") or 0) > 0, "fuer uns nicht im Plus nach Reibung"),
        ((num("rendite_ohne_besten_pct") or 0) > 0, "ohne besten Coin nicht im Plus"),
        (num("trades_pro_tag") is not None and num("trades_pro_tag") <= AUTO_MAX_TRADES_TAG,
         f"mehr als {AUTO_MAX_TRADES_TAG} Trades pro Tag"),
        ((num("kauf_median_sol") or 0) >= AUTO_MIN_KAUF_SOL, f"Kauf-Median unter {AUTO_MIN_KAUF_SOL} SOL"),
    ]
    return next((why for ok, why in checks if not ok), None)


def load_waitlist():
    if not os.path.exists(WAIT_FILE):
        return {}
    with open(WAIT_FILE, encoding="utf-8") as f:
        return {r["wallet"]: r for r in csv.DictReader(f) if r.get("wallet")}


def save_waitlist(wait):
    os.makedirs(SCOUT_DIR, exist_ok=True)
    tmp = WAIT_FILE + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(WAIT_HEADER)
        for e in sorted(wait.values(), key=lambda e: -core.as_float(e.get("punkte"))):
            w.writerow([e.get(k, "") for k in WAIT_HEADER])
    os.replace(tmp, WAIT_FILE)


def _wait_entry(r, now, since=None):
    name = r.get("coin") if r.get("quelle") == "liste" else ""
    return {"seit": since or now, "bewertet": now, "wallet": r["wallet"], "name": name or r["wallet"][:4],
            "quelle": r.get("quelle", ""), **{k: r.get(k, "") for k in WAIT_HEADER[5:]}}


def wallet_file_names(text):
    """Alle Namen in copy_wallets.txt, auch auskommentierte."""
    names = set()
    for line in text.splitlines():
        name, _, rest = line.strip().lstrip("#").strip().partition(":")
        if ADDR_RE.match(rest.strip()):
            names.add(name.strip())
    return names


def unique_name(base, addr, taken):
    """Name ohne ':'/'#', der weder in copy_wallets.txt noch in copy/konten.json vorkommt (sonst erbt die neue
    Wallet ein altes Konto). Ist der Name vergeben, kommt der Adressanfang dazu (Croco -> Croco-AXfw)."""
    base = re.sub(r"[^0-9A-Za-z_.\-]", "", base or "")[:20]
    taken_low = {t.lower() for t in taken}
    suffixe = [f"{base}-{addr[:4]}", f"{base}-{addr[:6]}"] if base else []
    for cand in [base] + suffixe + [addr[:4], addr[:6], addr[:8], addr]:
        if cand and cand.lower() not in taken_low:
            return cand
    return addr


def load_copy_accounts():
    try:
        with open(cb.ACCOUNTS_FILE, encoding="utf-8") as f:
            return json.load(f).get("wallets", {})
    except (OSError, ValueError):
        return {}


def load_flood_hints(now):
    """Vom Copy-Bot per Flutschutz abgemeldete Wallets der letzten FLOOD_HINT_DAYS Tage: {Adresse: Datum}."""
    try:
        with open(cb.FLOOD_FILE, encoding="utf-8") as f:
            flood = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for addr, e in (flood.items() if isinstance(flood, dict) else []):
        try:
            last = datetime.strptime(e["zuletzt"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        except (KeyError, TypeError, ValueError):
            continue
        if now - last <= FLOOD_HINT_DAYS * 86400:
            out[addr] = e["zuletzt"][:10]
    return out


def replaceable_wallets(active, accounts, now, check_bots=True):
    """Aktive Wallets, die eine Wallet-Regel erfuellen, in der Reihenfolge Bot, still (laengste Pause zuerst),
    groesster Verlust. [(Name, Adresse, Grund)]. check_bots=False: ohne Helius-Abfrage (nur still/Verlust).
    Bot-Hinweis auch aus dem Flutschutz des Copy-Bots (copy/flutschutz.json, ohne Abfrage)."""
    flood = load_flood_hints(now)
    out = []
    for name, addr in active:
        reason = None
        try:
            if addr in flood:
                reason = f"Bot (Flutschutz im Copy-Bot, zuletzt {flood[addr]})"
            elif check_bots:
                _, reason = stage1(addr, now, max_idle_h=10 ** 6)   # nur die Bot-Regeln von Stufe 1 (1 Credit)
        except Exception as err:
            STATS["fehler"] += 1
            print(f"[SCOUT] Automatik Stufe 1 {name}: {str(err)[:100]}")
        if reason and reason.startswith("Bot"):
            out.append((0, 0, name, addr, reason))
            continue
        a = accounts.get(name)
        if not a:
            continue                                 # Konto noch nicht eroeffnet (gerade aufgenommen)
        try:
            start = datetime.fromisoformat(a["gestartet"]).timestamp()
        except (KeyError, TypeError, ValueError):
            start = now
        idle_h = (now - (a.get("letzter_trade") or start)) / 3600
        if idle_h >= cb.WALLET_SILENT_H:
            out.append((1, -idle_h, name, addr, f"still, seit {idle_h:.0f} h kein eigener Trade"))
            continue
        closed = a.get("geschlossen") or []
        realized = sum(core.as_float(c.get("pnl_sol")) for c in closed)
        schonfrist = now - start < AUTO_SCHONFRIST_TAGE * 86400 and len(closed) < cb.REVIEW_AFTER_CLOSED
        if not schonfrist and len(closed) >= cb.REVIEW_AFTER_CLOSED and realized <= -cb.REVIEW_MIN_LOSS_SOL:
            out.append((2, realized, name, addr, f"Verlust, {len(closed)} Positionen, {realized:+.2f} SOL"))
    return [(n, a, g) for _, _, n, a, g in sorted(out, key=lambda x: (x[0], x[1]))]


def recheck(e, now, sol_usd):
    """Kandidat von der Warteliste vor der Aufnahme frisch bewerten. Rueckgabe: Zeile fuer kandidaten.csv."""
    w = e["wallet"]
    m, reason = stage1(w, now)
    row = {"zeit": cb.now_str(), "wallet": w, "quelle": "warteliste", "coin": e.get("name", ""),
           **{k: v for k, v in m.items() if not k.startswith("_")}}
    if reason:
        return dict(row, ergebnis="raus", grund=reason)
    s2 = stage2(w, window_sigs(w, m["_page"], now, LIST_TX if e.get("quelle") == "liste" else STAGE2_TX), sol_usd)
    pts = score(s2)
    return dict(row, **s2, ergebnis="bewertet" if pts is not None else not_rated_reason(s2),
                punkte=pts if pts is not None else "")


def _add_reason(e):
    return (f"Scout ({e.get('quelle') or '?'}), fuer uns {core.as_float(e.get('punkte')):+.0f} %, ohne besten Coin "
            f"{core.as_float(e.get('rendite_ohne_besten_pct')):+.0f} %, {e.get('coins')} Coins, Kauf-Median "
            f"{e.get('kauf_median_sol')} SOL, {e.get('trades_pro_tag')} Trades/Tag")


def apply_wallet_changes(plans, datum, taken_accounts):
    """Schreibt die geplanten Aenderungen in copy_wallets.txt (frischer Stand). Prueft jede Aenderung gegen die
    Datei: Adresse schon drin, zu ersetzende Wallet nicht mehr aktiv oder Limit voll -> ausgelassen.
    Rueckgabe: tatsaechlich ausgefuehrte Plaene (mit endgueltigem Namen)."""
    path = cb.WALLET_FILE
    raw = open(path, "rb").read() if os.path.exists(path) else b""
    nl = "\r\n" if b"\r\n" in raw else "\n"
    lines = raw.decode("utf-8").splitlines()
    addrs = set(ADDR_RE.findall("\n".join(lines)))
    taken = wallet_file_names("\n".join(lines)) | set(taken_accounts)

    def active_index(addr):
        for i, line in enumerate(lines):
            s = line.strip()
            if s and not s.startswith("#") and s.partition(":")[2].strip() == addr:
                return i
        return None
    active = sum(1 for line in lines if line.strip() and not line.strip().startswith("#")
                 and ADDR_RE.fullmatch(line.strip().partition(":")[2].strip()))
    done = []
    for p in plans:
        if not p.get("adresse"):                     # nur entfernen (still, ohne Ersatz)
            i = active_index(p["raus"]["adresse"])
            if i is None:
                continue
            lines[i] = f"# {lines[i].strip()}   <- entfernt {datum} automatisch: {p['raus']['grund']}; ohne Ersatz"
            active -= 1
            done.append(p)
            continue
        if p["adresse"] in addrs:
            continue
        name = unique_name(p["name"], p["adresse"], taken)
        if p.get("raus"):
            i = active_index(p["raus"]["adresse"])
            if i is None:
                continue
            lines[i] = (f"# {lines[i].strip()}   <- entfernt {datum} automatisch: {p['raus']['grund']}; "
                        f"ersetzt durch {name}")
        elif active >= AUTO_MAX_WALLETS:
            continue
        else:
            active += 1
        lines += [f"# {datum} automatisch aufgenommen: {p['grund']}", f"{name}: {p['adresse']}"]
        addrs.add(p["adresse"])
        taken.add(name)
        done.append(dict(p, name=name))
    if done:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(nl.join(lines) + nl)
    return done


def push_wallet_changes(plans, now, taken_accounts):
    """Aenderungen auf den neuesten Stand von copy_wallets.txt anwenden, NUR diese Datei committen und pushen.
    Rueckgabe: ausgefuehrte Plaene ([] = nichts geaendert oder Push fehlgeschlagen)."""
    g = core._git
    datum = datetime.fromtimestamp(now, timezone.utc).strftime("%d.%m.")
    g("config", "user.name", "github-actions[bot]")
    g("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    for _ in range(3):
        if g("fetch", "-q", "origin", "main").returncode != 0:
            continue
        g("reset", "-q", "origin/main")
        g("checkout", "-q", "origin/main", "--", cb.WALLET_FILE)
        done = apply_wallet_changes(plans, datum, taken_accounts)
        if not done:
            return []
        g("add", cb.WALLET_FILE)
        if g("diff", "--cached", "--quiet").returncode == 0:
            return []
        g("commit", "-q", "-m", f"SCOUT Copy-Wallets automatisch: {', '.join(p['name'] for p in done)} [skip ci]")
        if g("push", "-q", "origin", "HEAD:main").returncode == 0:
            return done
    g("reset", "-q", "origin/main")                     # nichts halb Gespeichertes liegen lassen
    g("checkout", "-q", "origin/main", "--", cb.WALLET_FILE)
    STATS["fehler"] += 1
    return None


def _row_time(r, default):
    try:
        return datetime.strptime(str(r.get("zeit", ""))[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return default


def stored_rows(state):
    """Bewertungen aus dem Speicher (letzte Zeile je Wallet in scout/kandidaten.csv, auch die Pruefliste), die die
    Automatik noch nicht gesehen hat. Keine neue Abfrage. Die Kopfzeile der Datei ist noch die alte (25 Spalten),
    neuere Zeilen haben den Aufbau von CANDIDATES_HEADER: jede Zeile wird nach ihrer Laenge zugeordnet (wie im
    Dashboard), andere Laengen werden uebersprungen."""
    if not os.path.exists(CANDIDATES_FILE):
        return []
    latest = {}
    try:
        with open(CANDIDATES_FILE, newline="", encoding="utf-8") as f:
            rd = csv.reader(f)
            header = next(rd, [])
            for row in rd:
                if len(row) in (len(CANDIDATES_HEADER), OLD_ROW_LEN):      # (Spalte rendite_ohne_besten_pct doppelt: die hintere zaehlt)
                    r = dict(zip(CANDIDATES_HEADER, row))
                elif len(row) == len(header):
                    r = dict(zip(header, row))
                else:
                    continue
                if r.get("wallet") and r.get("zeit", "") >= latest.get(r["wallet"], {}).get("zeit", ""):
                    latest[r["wallet"]] = r
    except (OSError, csv.Error, UnicodeDecodeError) as err:  # kaputte Datei darf die Automatik nie stoppen
        STATS["fehler"] += 1
        print(f"[SCOUT] kandidaten.csv nicht lesbar: {str(err)[:100]}")
        return []
    seen = state.get("speicher_geprueft", {})
    return [r for w, r in latest.items() if seen.get(w) != r.get("zeit")]


def auto_wallets(state, now, sol_usd, rows):
    """Automatik nach jeder Bewertung: Kandidaten aus diesem Lauf (Suche und Pruefliste) und von der Warteliste.
    Aufnahme, wenn Platz ist; sonst eine Wallet ersetzen, die eine Wallet-Regel erfuellt; sonst Warteliste.
    Schreibt nur copy_wallets.txt (eigener Commit) und scout/warteliste.csv. Rueckgabe: Discord-Zeilen."""
    if not AUTO_AUFNAHME:
        return []
    known = set(ADDR_RE.findall(open(cb.WALLET_FILE, encoding="utf-8").read())) \
        if os.path.exists(cb.WALLET_FILE) else set()
    wait = load_waitlist()
    for w, e in list(wait.items()):
        if w in known or now - core.as_float(e.get("seit")) > WAIT_MAX_TAGE * 86400:
            del wait[w]
    stored = stored_rows(state)                      # gespeicherte Bewertungen, auch die alte Pruefliste
    for r in stored:
        w = r["wallet"]
        if w not in known and w not in wait and auto_reason(r) is None:
            wait[w] = dict(_wait_entry(r, now), bewertet=_row_time(r, 0))   # alt -> vor Aufnahme frisch pruefen
    for r in list(rows):
        w = r.get("wallet")
        if not w or w in known:
            continue
        if auto_reason(r) is None:
            wait[w] = _wait_entry(r, now, (wait.get(w) or {}).get("seit"))
        else:
            wait.pop(w, None)                        # frische Bewertung sagt nein
    log = [e for e in state.get("auto_aenderungen", []) if now - e.get("zeit", 0) < 30 * 86400]
    today = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    # Entfernen wegen Stille ohne Ersatz (adresse leer) zaehlt seit 06.10. nicht zum Tageslimit
    budget = AUTO_MAX_PRO_TAG - sum(1 for e in log if e.get("adresse") and datetime.fromtimestamp(e["zeit"], timezone.utc)
                                    .strftime("%Y-%m-%d") == today)
    active = cb.load_wallets() if os.path.exists(cb.WALLET_FILE) else []
    free = AUTO_MAX_WALLETS - len(active)
    accounts = load_copy_accounts()
    repl = None                                      # erst abfragen, wenn ein Kandidat auf einen vollen Platz trifft
    plans, lines, rechecks = [], [], 0
    for e in sorted(wait.values(), key=lambda e: -core.as_float(e.get("punkte"))):
        if budget <= 0:
            break
        if free <= 0 and repl is None:
            repl = replaceable_wallets(active, accounts, now)
        if free <= 0 and not repl:
            break
        if now - core.as_float(e.get("bewertet")) > WAIT_RECHECK_H * 3600:
            if rechecks >= RECHECK_MAX_PRO_LAUF:
                break
            rechecks += 1
            try:
                r = recheck(e, now, sol_usd)
            except Exception as err:
                STATS["fehler"] += 1
                print(f"[SCOUT] Automatik Neupruefung {e['wallet'][:8]}: {str(err)[:100]}")
                continue
            rows.append(r)
            why = auto_reason(r)
            if why:
                del wait[e["wallet"]]
                lines.append(f"➖ **{e.get('name')}** `{e['wallet']}` von der Warteliste gestrichen: {why}")
                continue
            e = wait[e["wallet"]] = dict(_wait_entry(r, now, e.get("seit")), name=e.get("name"), quelle=e.get("quelle"))
        plan = {"name": e.get("name") or e["wallet"][:4], "adresse": e["wallet"], "grund": _add_reason(e)}
        if free > 0:
            free -= 1
        else:
            name, addr, why = repl.pop(0)
            plan["raus"] = {"name": name, "adresse": addr, "grund": why}
        plans.append(plan)
        budget -= 1
    # Stille Wallets (72 h ohne eigenen Trade) auch ohne Ersatz entfernen, ohne Tageslimit (seit 06.10.)
    planned = {p["raus"]["adresse"] for p in plans if p.get("raus")}
    pool = repl if repl is not None else replaceable_wallets(active, accounts, now, check_bots=False)
    for name, addr, why in pool:
        if why.startswith("still") and addr not in planned:
            plans.append({"name": name, "adresse": None, "grund": why,
                          "raus": {"name": name, "adresse": addr, "grund": why}})
    done = push_wallet_changes(plans, now, accounts) if plans else []
    for p in done or []:
        if p.get("adresse"):
            wait.pop(p["adresse"], None)
        log.append({"zeit": now, "name": p["name"], "adresse": p["adresse"], "grund": p["grund"],
                    "raus": p.get("raus")})
        if not p.get("adresse"):
            lines.append(f"➖ **{p['raus']['name']}** `{p['raus']['adresse']}` entfernt, ohne Ersatz ({p['raus']['grund']})")
        elif p.get("raus"):
            lines.append(f"🔁 **{p['name']}** `{p['adresse']}` ersetzt **{p['raus']['name']}** "
                         f"({p['raus']['grund']})\n   {p['grund']}")
        else:
            lines.append(f"➕ **{p['name']}** `{p['adresse']}` aufgenommen\n   {p['grund']}")
    if done is None:
        lines.append("⚠️ copy_wallets.txt konnte nicht gespeichert werden (Push fehlgeschlagen); "
                     "die Kandidaten bleiben auf der Warteliste.")
    state["auto_aenderungen"] = log
    save_waitlist(wait)
    seen = state.setdefault("speicher_geprueft", {})   # erst nach Erfolg als gesehen markieren
    for r in stored:
        seen[r["wallet"]] = r.get("zeit")
    STATS["warteliste"] = len(wait)
    STATS["auto_heute"] = sum(1 for e in log if e.get("adresse") and datetime.fromtimestamp(e["zeit"], timezone.utc)
                              .strftime("%Y-%m-%d") == today)
    if done:
        lines.append("Der Copy-Bot uebernimmt die Aenderung beim naechsten Schichtwechsel.")
    if lines and wait:
        lines.append(f"⏳ Warteliste: {len(wait)} Kandidat(en) (kein freier Platz, keine ersetzbare Wallet "
                     f"oder Tageslimit {AUTO_MAX_PRO_TAG})")
    return lines


# ================================================================ Lauf

def known_wallets():
    known = set()
    if os.path.exists(cb.WALLET_FILE):
        for line in open(cb.WALLET_FILE, encoding="utf-8"):
            part = line.lstrip("# ").split(":", 1)
            if len(part) == 2:
                known.add(part[1].split()[0].strip() if part[1].split() else "")
    return known


def search(state, now, sol_usd):
    """Gewinner-Coins -> Kandidaten -> Stufe 1 und 2. Rueckgabe: (Coins, Zeilen fuer kandidaten.csv, Rangliste)."""
    coins = winner_coins(state, now)
    STATS["coins"] = len(coins)
    known = known_wallets()
    recent = {w for w, ts in state["wallets_geprueft"].items() if now - ts < RECHECK_DAYS * 86400}
    found = {}                                       # Wallet -> (Quelle, Coin)
    for mint, symbol, mult in coins:
        try:
            for w in early_buyers(mint, sol_usd):
                found.setdefault(w, ("frueh", f"{symbol} {mult:.1f}x"))
            for w in birdeye_top_traders(mint, state):
                found.setdefault(w, ("birdeye", f"{symbol} {mult:.1f}x"))
        except Exception as err:
            STATS["fehler"] += 1
            print(f"[SCOUT] {symbol}: {str(err)[:120]}")
        state["coins_erledigt"][mint] = now
    cands = [w for w in found if w not in known and w not in recent]
    STATS["kandidaten"] = len(cands)
    rows, stage2_list = [], []
    for w in cands:
        try:
            m, reason = stage1(w, now)
        except Exception as err:
            STATS["fehler"] += 1
            print(f"[SCOUT] Stufe 1 {w[:8]}: {str(err)[:100]}")
            continue
        state["wallets_geprueft"][w] = now
        row = {"zeit": cb.now_str(), "wallet": w, "quelle": found[w][0], "coin": found[w][1],
               **{k: v for k, v in m.items() if not k.startswith("_")}}
        if reason:
            STATS["stufe1_raus"][reason.split(" (")[0]] = STATS["stufe1_raus"].get(reason.split(" (")[0], 0) + 1
            rows.append(dict(row, ergebnis="raus", grund=reason))
        else:
            stage2_list.append((m["tx_pro_h"], w, row, window_sigs(w, m["_page"], now, STAGE2_TX)))
    ranked = []
    for _, w, row, sigs in sorted(stage2_list)[:STAGE2_PER_RUN]:  # ruhigere Wallets zuerst (eher menschlich)
        try:
            s2 = stage2(w, sigs, sol_usd)
        except Exception as err:
            STATS["fehler"] += 1
            print(f"[SCOUT] Stufe 2 {w[:8]}: {str(err)[:100]}")
            continue
        STATS["stufe2"] += 1
        pts = score(s2)
        r = dict(row, **s2, ergebnis="bewertet" if pts is not None else not_rated_reason(s2),
                 punkte=pts if pts is not None else "")
        rows.append(r)
        if pts is not None:
            ranked.append(r)
    ranked.sort(key=lambda r: -r["punkte"])
    return coins, rows, ranked


def auto_status_line():
    if not AUTO_AUFNAHME:
        return "**Automatik:** aus (AUTO_AUFNAHME = False), copy_wallets.txt wird nicht geaendert"
    return (f"**Automatik:** an | heute {STATS.get('auto_heute', 0)} von {AUTO_MAX_PRO_TAG} Aenderungen | "
            f"Warteliste {STATS.get('warteliste', 0)} | Limit {AUTO_MAX_WALLETS} aktive Wallets")


def run(nur_liste=False):
    """nur_liste=True: nur die Pruefliste bewerten (ohne Gewinner-Coins, Birdeye und Transaktions-Pruefung)."""
    now = time.time()
    core.git_sync_start()
    state = load_state()
    sol_usd = core.sol_price()
    list_rows, list_lines = check_list(state, now, sol_usd)
    coins, rows, ranked = [], [], []
    if not nur_liste:
        try:
            tx_lines = check_transactions(state, now, sol_usd)
        except Exception as err:                     # Pruef-Modus darf den Scout nie stoppen
            STATS["fehler"] += 1
            tx_lines = [f"⚠️ Transaktions-Pruefung fehlgeschlagen: {str(err)[:80]}"]
        if tx_lines:
            notify("🔎 Wallet-Scout: Transaktions-Pruefung", tx_lines)
        coins, rows, ranked = search(state, now, sol_usd)
    all_rows = list_rows + rows
    try:
        auto_lines = auto_wallets(state, now, sol_usd, all_rows)
    except Exception as err:                         # Automatik darf den Scout nie stoppen
        STATS["fehler"] += 1
        auto_lines = [f"⚠️ Automatik fehlgeschlagen, nichts geaendert: {str(err)[:80]}"]
    write_csv(all_rows)
    if not nur_liste:
        state["letzter_lauf"] = now                  # fuer --wenn-faellig (Startzeit, nur kompletter Lauf)
    save_state(state)
    if list_lines:
        good = sum(1 for l in list_lines if l.startswith("✅"))
        notify("📋 Wallet-Scout: deine Pruefliste", [
            f"**{STATS.get('liste_neu', 0)} Wallets neu geprueft, {len(list_lines) - STATS.get('liste_neu', 0)} aus dem "
            f"Speicher, {good} fuer uns im Plus** (Rendite des Traders der letzten 7 Tage "
            f"auf den Einsatz, gehaltene Coins zum aktuellen Kurs, ohne seinen besten Coin, minus 3 bis 10 "
            f"Prozentpunkte Reibung je nach Haltedauer)"] + list_lines)
    elif nur_liste:
        notify("📋 Wallet-Scout: deine Pruefliste", ["Keine neuen Adressen, alle schon bewertet (Ergebnis im Dashboard)."])
    if auto_lines:
        notify("🔁 Wallet-Scout: Copy-Wallets automatisch geaendert", auto_lines)
    if nur_liste:
        git_push()
        return
    lines = [f"**Gewinner-Coins:** {', '.join(f'{s} {m:.1f}x' for _, s, m in coins) or 'keine neuen'}",
             f"**Kandidaten:** {STATS['kandidaten']} neu | **Stufe 1 aussortiert:** {STATS['stufe1_raus'] or 0} | "
             f"**Stufe 2 bewertet:** {STATS['stufe2']}"
             + (f" | Birdeye-Markierte (Bundler, Sniper, Bots) ausgelassen: {STATS['birdeye_markiert']}"
                if STATS.get("birdeye_markiert") else "")
             + (f" | Coins zu aktiv fuer fruehe Kaeufer: {STATS['coins_zu_aktiv']}" if STATS.get("coins_zu_aktiv") else "")]
    top = [r for r in ranked if r["punkte"] > 0][:8]
    if STATS.get("birdeye_eintraege"):
        lines.append(f"**Birdeye Top-Trader:** {STATS['birdeye_eintraege']} gesehen, {STATS.get('birdeye_markiert', 0)} "
                     f"als Bundler/Sniper/Bot markiert, {STATS.get('birdeye_ohne_gewinn', 0)} ohne Gewinn")
    unrated = sum(1 for r in rows if r.get("ergebnis") == "zu wenig Coins im Zeitraum")
    if unrated:
        lines.append(f"**Zu wenig Coins im Zeitraum fuer eine Bewertung:** {unrated}")
    tiny = sum(1 for r in rows if str(r.get("ergebnis", "")).startswith("Kleinstkaeufe"))
    if tiny:
        lines.append(f"**Kleinstkaeufe, nicht bewertet:** {tiny}")
    if top:
        lines.append("**Rangliste** (fuer uns erwartete Rendite nach Reibung | Treffer | Coins | "
                     "Kauf-Median | Trades/Tag | Haltedauer | Verkaeufe unter 60 s):")
        for i, r in enumerate(top, 1):
            lines.append(f"{i}. `{r['wallet']}` ({r['quelle']}, {r['coin']})\n"
                         f"   {r['punkte']:+.0f} % (Trader {r['rendite_pct']:+.0f} %, ohne besten {r['rendite_ohne_besten_pct']:+.0f} %) | "
                         f"{(r['trefferquote'] or 0):.0%} | {r['coins']} | {r['kauf_median_sol']} SOL | "
                         f"{r['trades_pro_tag']} | {r['haltedauer_median_min']} min | {_fast_text(r)}")
        lines.append("Aufnahme entscheidet die Automatik (Kriterien siehe STRATEGIE.md)." if AUTO_AUFNAHME
                     else "Eintragen in copy_wallets.txt als `Name: Adresse`.")
    else:
        lines.append("Keine Wallet, die nach Abzug der Reibung fuer uns im Plus waere.")
    lines.append(f"**Birdeye:** {STATS['birdeye_cu']} CUs in diesem Lauf, {state['birdeye']['cu']} im Monat"
                 + (f" | {STATS['birdeye_fehler']}" if STATS["birdeye_fehler"] else "") if BIRDEYE_API_KEY
                 else "**Birdeye:** kein Key, nur Helius")
    lines.append(auto_status_line())
    if STATS["fehler"]:
        lines.append(f"**Fehler:** {STATS['fehler']}")
    notify("🔭 Wallet-Scout", lines)
    git_push()


def probe():
    print("[SCOUT PROBE] Birdeye-Key:", "gesetzt" if BIRDEYE_API_KEY else "FEHLT")
    print("[SCOUT PROBE] Discord-Kanal:", "Scout" if os.environ.get("DISCORD_WEBHOOK_SCOUT") else
          ("Copy (kein eigener Scout-Kanal)" if DISCORD_WEBHOOK_SCOUT else "FEHLT"))
    state = load_state()
    sol_usd = core.sol_price()
    coins = winner_coins(state, time.time())
    print(f"[SCOUT PROBE] Gewinner-Coins (noch nicht untersucht): {[(s, round(m, 1)) for _, s, m in coins]}")
    if not coins:
        return
    mint, symbol, _ = coins[0]
    buyers = early_buyers(mint, sol_usd)
    print(f"[SCOUT PROBE] Fruehe Kaeufer von {symbol}: {len(buyers)}, z. B. {buyers[:3]}")
    if BIRDEYE_API_KEY:
        data = birdeye_get(f"/defi/v2/tokens/top_traders?address={mint}&time_frame=24h&sort_type=desc"
                           f"&sort_by=volume&offset=0&limit=10", state, BIRDEYE_CU["top_traders"])
        items = ((data or {}).get("data") or {}).get("items") or []
        print(f"[SCOUT PROBE] Birdeye Top-Trader: {len(items)} | Fehler: {STATS['birdeye_fehler'] or 'keiner'}")
        if items:
            tags = sorted({str(t) for it in items for t in (it.get("tags") or [])})
            print(f"        Markierungen in der Liste: {tags or 'keine'}")
            def total(it):
                v = it.get("totalPnl")
                return core.as_float(v) if v is not None else \
                    core.as_float(it.get("realizedPnl")) + core.as_float(it.get("unrealizedPnl"))
            for it in items[:10]:
                print(f"        {it.get('owner', '?')[:8]} Tags {it.get('tags')} | Trades {it.get('trade')} | "
                      f"realisiert {core.as_float(it.get('realizedPnl')):,.0f} $ | gesamt {total(it):,.0f} $")
            kept = [it.get("owner") for it in items if it.get("owner") and total(it) > 0 and not any(
                b in " ".join(str(t).lower() for t in (it.get("tags") or [])) for b in BAD_TAGS)]
            print(f"        Nach Filter (keine Markierung, Gesamtgewinn > 0): {len(kept)} von {len(items)}")
            if kept:
                pnl = birdeye_get(f"/wallet/v2/pnl/summary?wallet={kept[0]}", state, 30)
                print(f"[SCOUT PROBE] Birdeye PnL-Zusammenfassung (30 CUs): "
                      f"{'verfuegbar: ' + json.dumps(pnl)[:250] if pnl else 'nicht verfuegbar: ' + STATS['birdeye_fehler']}")
    if buyers:
        m, reason = stage1(buyers[0], time.time())
        print(f"[SCOUT PROBE] Stufe 1 fuer {buyers[0][:8]}: { {k: v for k, v in m.items() if not k.startswith('_')} } -> {reason or 'weiter'}")
        if not reason:
            print(f"[SCOUT PROBE] Stufe 2: {stage2(buyers[0], window_sigs(buyers[0], m['_page'], time.time(), 20), sol_usd)}")
    entries = load_list()
    print(f"[SCOUT PROBE] Pruefliste {LIST_FILE}: {len(entries)} Wallets" + (f", z. B. {entries[:2]}" if entries else ""))
    save_state(state)                                # nur der CU-Zaehler
    print("[SCOUT PROBE] fertig. Diese Ausgabe bitte an Claude schicken.")


def run_due(state, now):
    """True, wenn im aktuellen 6-h-Fenster noch kein kompletter Lauf war."""
    last = state.get("letzter_lauf")
    if not isinstance(last, (int, float)):
        return True
    return int(last // RUN_SLOT_S) != int(now // RUN_SLOT_S)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--nur-pruefliste", action="store_true", help="nur scout/pruefen.txt bewerten, danach Automatik")
    ap.add_argument("--wenn-faellig", action="store_true",
                    help="nur laufen, wenn im aktuellen 6-h-Fenster noch kein kompletter Lauf war (Zeitplan)")
    args = ap.parse_args(argv)
    if args.probe:
        probe()
    elif args.wenn_faellig and not args.nur_pruefliste and not run_due(load_state(), time.time()):
        print("[SCOUT] In diesem 6-h-Fenster schon gelaufen, nichts zu tun.")
    else:
        run(nur_liste=args.nur_pruefliste)


if __name__ == "__main__":
    main()
