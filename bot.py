"""
Solana-Memecoin Paper-Bot - Strategie NARRATIV
Regeln aus 13 Lernvideos (siehe STRATEGIE.md). Es wird nur auf Papier gehandelt.

  python bot.py           # normale Schicht
  python bot.py --probe   # Kurztest der Datenquellen, handelt nichts
"""
import argparse
import csv
import json
import math
import struct
import os
import random
import re
import signal
from collections import deque
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone

import requests

import listings

# ================================================================ Dateien
PORTFOLIO_FILE = "portfolio.json"
JOURNAL_FILE = "journal.csv"
REJECT_FILE = "abgelehnt.csv"
PHASE_FILE = "marktphase.json"
VERLAUF_DIR = "verlauf"                  # eine Datei pro Tag (UTC), z. B. verlauf/2026-09-28.csv
# Flugschreiber (seit 04.10., nur Aufzeichnung): je offene Position etwa jede Minute Liquiditaet, Holder,
# Top-10-Anteil, Dev-Bestand und Handel der letzten 5 min (aus den Jupiter-Daten, 0 Helius-Credits); alle 10 min
# zusaetzlich der Bestand der Block-0-Kaeufer (Bundler) ueber Helius. Fuer spaetere Muster vor Rugs.
FLUG_DIR = "flugschreiber"
FLUG_HEADER = ["zeit", "konto", "mint", "symbol", "minuten_seit_kauf", "vielfaches", "liquiditaet", "holder",
               "top10_pct", "dev_pct", "netto_kaeufer_5m", "kaeufe_5m", "verkaeufe_5m", "kaufvol_5m", "verkaufvol_5m",
               "block0_gehalten_pct", "block0_ausgestiegen", "block0_wallets"]
FLUG_EVERY_S = 60
FLUG_B0_EVERY_S = 600                   # Bundler-Bestand: ~8 Helius-Abfragen je Coin alle 10 min
FLUG_B0_MAX_WALLETS = 8
NEAR_MISS_FILE = "knapp_abgelehnt.csv"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
JUPITER_API_KEY = (os.environ.get("JUPITER_API_KEY") or "").strip()
JUP_BASE = "https://api.jup.ag" if JUPITER_API_KEY else "https://lite-api.jup.ag"
RUGCHECK_BASE = "https://api.rugcheck.xyz/v1"
HELIUS_API_KEY = (os.environ.get("HELIUS_API_KEY") or "").strip()
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}" if HELIUS_API_KEY else None
SOLANA_TRACKER_API_KEY = (os.environ.get("SOLANA_TRACKER_API_KEY") or "").strip()
SOLANA_TRACKER_BASE = "https://data.solanatracker.io"
SOLANA_TRACKER_DAILY_LIMIT = 70         # Gratis-Tarif: 2.500 Abfragen im Monat

WSOL_MINT = "So11111111111111111111111111111111111111112"
IGNORED_MINTS = {
    WSOL_MINT,
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
}

# ================================================================ Schicht
LOOP_SLEEP_SECONDS = 12                 # offene Positionen alle ~12 s (seit 28.09., vorher 35 s)
SHIFT_DURATION_SECONDS = 20700          # 5h45 bei 6h-Takt
SCAN_EVERY_LOOPS = 6                    # Kandidaten ca. alle 70 s
PHASE_EVERY_LOOPS = 30                  # Marktphase ca. alle 6 min
THESIS_EVERY_LOOPS = 3                  # These ca. alle 36 s pruefen (Jupiter-Daten brauchen Zeit)
SOL_PRICE_EVERY_LOOPS = 5
GIT_PUSH_EVERY_LOOPS = 5                # Sicherung ca. jede Minute
WATCH_LOG_EVERY_LOOPS = 3               # Verlauf nach Verkauf ca. alle 36 s
NEAR_MISS_LOG_EVERY_LOOPS = 10          # Verlauf knapp Abgelehnter ca. alle 2 min

# ================================================================ Kapital
START_BANKROLL_SOL = 10.0
POSITION_SOL = 0.2                      # Tag 7: feste Groesse, nie aus Frust groesser
TX_FEE_SOL = 0.0015                     # Netzwerk + Priority pro Transaktion
QUOTE_RECHECK_SECONDS = 2.0             # Messung seit 03.10. (nur Aufzeichnung): Quote 2 s spaeter erneut,
QUOTE_RECHECK_MAX_S = 10.0              # ausgefuehrt in der Pause zwischen zwei Durchlaeufen, nie waehrend des Handels
MESSUNG_FILE = "messung.csv"
# DexScreener-Beobachtung (seit 04.10., nur Aufzeichnung, keine Regel): bezahltes Profil, Werbung, Community-
# Uebernahme und Boosts je gekauftem bzw. knapp abgelehntem Coin, mit Zahlungszeitpunkten relativ zum Ereignis.
# Offizielle API ohne Schluessel (60 Abfragen/min); abgefragt in der Pause zwischen zwei Durchlaeufen.
DEX_BASE = "https://api.dexscreener.com"
DEX_FILE = "dexscreener.csv"
DEX_HEADER = ["zeit", "konto", "art", "symbol", "mint", "grund", "coin_alter_min", "profil", "werbung", "cto",
              "boosts", "erste_zahlung_min_vor_ereignis", "letzte_zahlung_min_vor_ereignis", "zahlungen", "fehler"]
DEX_INTERVAL = 1.1
DEX_REPEAT_H = 6                        # denselben Coin je Art hoechstens alle 6 h aufzeichnen
MESSUNG_HEADER = ["zeit", "konto", "aktion", "symbol", "mint", "quote_sofort", "quote_spaeter", "sekunden",
                  "abweichung_pct"]

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
FOMO_MAX_5M_PCT = 30.0                  # Tag 17 (seit 02.10.): kein Kauf nach > 30 % Anstieg in den letzten 5 min
# Grundsicherung gegen offensichtliche Fallen
MIN_LIQUIDITY_USD = 5_000
IMPERSONATION_SYMBOLS = {"SOL", "WSOL", "USDC", "USDT", "BTC", "WBTC", "ETH", "WETH", "JUP"}
# Tag 1: Bundle-Check
MAX_BUNDLE_HOLDING_PCT = 10.0           # Anteil verbundener Insider-Wallets (RugCheck)
# Eigener Block-0-Check (Methode wie SolBundler): wer hat im Erstellungsblock gekauft?
BUNDLE_MIN_WALLETS = 2                  # ab so vielen Kaeufern in Block 0 ... (seit 28.09.: 2 statt 3)
BUNDLE_MAX_SUPPLY_PCT = 15.0            # ... und diesem Anteil gilt ein Coin als gebuendelt
BUNDLE_MAX_STILL_HELD_PCT = 10.0        # Block-0-Kaeufer halten noch zu viel
# "streng": jeder gebuendelte Launch wird abgelehnt (Tag 1 woertlich)
# "ausstieg": gebuendelt ist ok, wenn die Block-0-Kaeufer ihre Coins schon verkauft haben
BUNDLE_RULE = "streng"
BLOCK0_MAX_PAGES = 40                   # hoechstens 40.000 Transaktionen zurueckgehen
BLOCK0_MAX_TX = 40
BLOCK0_MAX_WALLETS = 25
BUNDLE_CHECK_REQUIRED = True            # ohne Check kein Kauf
# Tag 6: Dev pruefen
MAX_CREATOR_HOLDING_PCT = 10.0
MAX_DEV_MINTS = 50                      # wer hunderte Coins startet, ist ein "sketchy dev"
# Tag 7: Kursanstieg der letzten Stunde erst ab diesem Alter bewerten
CHASE_CHECK_MIN_AGE_H = 2.0


# ================================================================ Ausstieg
TP1_MULTIPLE = 2.0                      # Tag 2: bei 2x ...
TP1_SELL_FRACTION = 0.5                 # ... die Haelfte vom Tisch
# Tag 4: Rest laufen lassen, Schutz vom Hoch. Je hoeher das erreichte Vielfache
# seit dem Kauf, desto enger folgt die Verkaufsgrenze (Stufen, die nie absinken).
# Seit 28.09.2026: 30 % bis 10x, darueber 25 % (vorher 40/30/25). Grundlage: verlauf.csv vom 27.09.
TRAIL_TIERS = [(10.0, 25.0),            # ab 10x Hoch: 25 % Abstand
               (0.0, 30.0)]             # darunter:    30 % Abstand
THESIS_BREAK_CHECKS = 2                 # Tag 3: These gebrochen, wenn 2x hintereinander
LIQ_DROP_EXIT_PCT = 30.0                # Liquiditaet abgezogen -> raus
LIQ_CONFIRM_CHECKS = 2                  # ... in 2 Pruefungen hintereinander (seit 29.09.)
EMERGENCY_STOP_PCT = -40.0              # Notbremse
# Seit 28.09.2026: Wer vor dem Teilverkauf 1,5x erreicht hat, wird nicht mehr unter Einstand verkauft
PROTECT_AT_MULTIPLE = 1.5
PROTECT_FLOOR_MULTIPLE = 1.0
MAX_HOLD_H = 24
WATCH_AFTER_EXIT_H = 6                  # nach dem Verkauf weiter beobachten (nur Aufzeichnung)
DEAD_TOKEN_LOOPS = 30

# ================================================================ Marktphase
# Tag 9 + 13: frische Coins und Volumen messen, bei ruhigem Markt weniger handeln
YOUNG_TOKEN_H = 24
HOT_MCAP_USD = 1_000_000
MAX_POSITIONS = {"heiss": 3, "normal": 2, "ruhig": 1}
PHASE_MIN_HISTORY = 12
PHASE_HISTORY_MAX = 1000

REJECT_REPEAT_SECONDS = 3600

# Kandidaten-Listen (seit 29.09.: zusaetzlich meistgehandelt und organisch, vorher nur Trending)
CANDIDATE_LISTS = {("toptrending", "5m"): "trend5m", ("toptrending", "1h"): "trend1h",
                   ("toptraded", "5m"): "traded5m", ("toptraded", "1h"): "traded1h",
                   ("toporganicscore", "5m"): "organic5m", ("toporganicscore", "1h"): "organic1h"}
DISCORD_ATTEMPTS = 3

# ================================================================ Experimente (seit 30.09., eigene Konten)
EXP_DIR = "experimente"
EXPERIMENTS = {"zweite_welle": "Zweite Welle", "heisse_coins": "Heisse Coins", "ohne_limit": "Ohne Limit",
               "kontrollgruppe": "Kontrollgruppe", "endspurt": "Endspurt viele Trades",
               "endspurt_ohne_filter": "Endspurt ohne Filter", "notbremse_25": "Notbremse 25",
               "offene_tuer": "Offene Tuer", "serien_devs": "Serien-Devs", "grosse_coins": "Grosse Coins",
               "drittel_leiter": "Drittel-Leiter", "listing_welle": "Listing-Welle"}
# Beendete Experimente (Datum): keine neuen Kaeufe, offene Positionen laufen regulaer zu Ende, Daten bleiben.
EXP_BEENDET = {"endspurt_ohne_filter": "04.10.", "ohne_limit": "04.10."}
NOTBREMSE_25_PCT = -25.0                # Experiment Notbremse 25 (seit 04.10.): kauft genau wie die
#                                         Hauptstrategie, nur die Notbremse greift schon bei -25 % statt -40 %
# Experiment Offene Tuer (seit 04.10.): dieselben Story-Filter wie die Hauptstrategie, aber KEINE Sicherheits-
# pruefungen (Dev, Contract, Nachahmer, Vamp, Transfergebuehr, Bundle/Block 0, Links). Kauft bewusst auch Rugs,
# damit ihre Muster aufgezeichnet werden (Flugschreiber, 6 h Nachlauf). Frage: Was sparen/kosten unsere Pruefungen?
OFFENE_TUER_MAX_POSITIONS = 4
SICHERHEITS_GRUENDE = {"DEV_VERDAECHTIG", "NACHAHMER_SYMBOL", "UNSICHERER_CONTRACT", "VAMP_KOPIE"}
# Experiment Serien-Devs (seit 04.10.): Coins von Devs, deren frueherer Coin mindestens 300.000 $ Marktwert erreicht
# hat (eigene Liste aus den Jupiter-Daten, auch wenn der Coin spaeter gerugt wurde). Nur Alter, Liquiditaet und Kurs
# geprueft. Zusaetzlicher Ausstieg: Dev haelt weniger als die Haelfte seines Bestands beim Kauf (Dev verkauft).
SERIEN_MIN_PEAK_MCAP = 300_000
SERIEN_MAX_POSITIONS = 4
SERIEN_DEV_EXIT_ANTEIL = 0.5
SERIEN_DEVS_FILE = os.path.join("experimente", "serien_devs", "devs.json")
SERIEN_DEVS_MAX = 3000                  # hoechstens so viele Devs merken (aelteste zuerst raus)
# Experiment Grosse Coins (seit 04.10., Video-Idee OrangieWEB3): nur Coins UEBER der Marktwert-Grenze von Tag 7
# (MAX_MCAP_USD), sonst alle Pruefungen und Ausstiege wie die Hauptstrategie (inkl. Bundle-Check, Positionslimit
# je Marktphase). Frage: Kostet uns die 3-Mio.-Grenze Gewinner?
# Experiment Drittel-Leiter (seit 04.10., Nachrechnung Video-Idee): kauft genau dann, wenn die Hauptstrategie kauft
# (wie Notbremse 25), verkauft aber je ein Drittel bei 1,5x / 2x / 3x (bei 3x ist alles verkauft) statt der Haelfte
# bei 2x. Abstand zum Hoch (Tag 4) gilt ab der 2x-Stufe wie heute, alle anderen Ausstiege wie die Hauptstrategie.
DRITTEL_LEITER = [1.5, 2.0, 3.0]

# Experiment Listing-Welle (seit 04.10.): Boersen-Listing eines Solana-Tokens (Upbit, Binance, Coinbase; Bithumb nur
# Aufzeichnung). Kauf bei Ankuendigung (juenger als 10 min), Verkauf zum Handelsstart, sonst nach 72 h, Notbremse -40 %.
# Quellen und Grenzen: listings.py. Aufzeichnung: experimente/listing_welle/ereignisse.csv und geruechte.csv.
LISTING_DIR = os.path.join(EXP_DIR, "listing_welle")
LISTING_EREIGNISSE_FILE = os.path.join(LISTING_DIR, "ereignisse.csv")
LISTING_GERUECHTE_FILE = os.path.join(LISTING_DIR, "geruechte.csv")
LISTING_EREIGNISSE_HEADER = ["zeit_erfasst", "typ", "ereignis_id", "boerse", "quelle_typ", "art", "symbol", "titel",
                             "ankuendigung_zeit", "handelsstart_zeit", "entscheidung", "mint", "kurs_usd",
                             "liquiditaet_usd", "anstieg_3h_pct", "anstieg_3d_pct", "url"]
LISTING_GERUECHTE_HEADER = ["zeit_erfasst", "nachricht_zeit", "coin", "quelle", "titel", "link", "offiziell_vorher"]
LISTING_UPBIT_ANKUENDIGUNG = False      # Upbit-Ankuendigungen: von GitHub aus 403 (gesperrt, nicht umgehen) -> aus
LISTING_POLL_SEC = 120                  # Upbit-Ankuendigungen (falls an): hoechstens alle 2 min
LISTING_LISTEN_POLL_SEC = 240           # Marktlisten (Binance, Coinbase, Bithumb): grosse Antworten, seltener
LISTING_NEWS_POLL_SEC = 900             # RSS fuer Geruechte
LISTING_MAX_ALTER_SEC = 600             # nur kaufen, wenn die Ankuendigung juenger als 10 min ist
LISTING_MIN_START_SEC = 120             # Handelsstart muss mindestens so weit weg sein
LISTING_MAX_HOLD_H = 72
LISTING_MIN_LIQ_USD = 100_000
LISTING_MIN_LIQ_NEBEN_USD = 10_000      # Treffer mit weniger Liquiditaet zaehlen bei der Eindeutigkeit nicht mit
LISTING_MEHRDEUTIG_ANTEIL = 0.25        # zweiter Treffer mit >= 25 % der Liquiditaet des ersten -> nicht kaufen
LISTING_MAX_POSITIONS = 6
LISTING_GERUECHT_MAX_ALTER_H = 48

# Experiment Endspurt (seit 30.09.): Pump.fun-Coins kurz vor der Graduation, raus bei der Graduation.
# Grundlage: arXiv 2602.14860 (655.770 Pump.fun-Coins, Sept. 2025). Preis auf der Kurve = vSol^2 / K.
PUMP_K = 30 * 1_073_000_000             # virtuelle SOL x virtuelle Token beim Start (SOL * Token)
PUMP_GRADUATION_VSOL = 115
ENDSPURT_VSOL_MIN, ENDSPURT_VSOL_MAX = 95, 108     # etwa 76-92 % Fortschritt
ENDSPURT_STOP_VSOL = 12                 # raus, wenn die Kurve um 12 vSol zurueckfaellt
ENDSPURT_MAX_MIN = 45                   # raus, wenn nach 45 min nicht graduiert
ENDSPURT_MAX_POSITIONS = 8
# Seit 01.10.: Filter umgekehrt. Die Studie (Sept. 2025) bevorzugte wenige Trades (< 800). In unseren ersten
# 74 Kaeufen graduierten Coins mit vielen Trades deutlich haeufiger (52 % gegenueber 24 %). Test an neuen Daten:
ENDSPURT_MIN_TRADES = 2000              # Filter: mindestens so viele Trades seit Start
ENDSPURT_MAX_SLIPPAGE_PCT = 3.0
KONTROLL_INTERVAL_MIN = 30              # Kontrollgruppe: etwa alle 30 min ein zufaelliger Coin
EXP_WATCH_AFTER_EXIT = {"ohne_limit", "endspurt_ohne_filter", "notbremse_25", "offene_tuer", "serien_devs",
                        "grosse_coins", "drittel_leiter", "listing_welle"}
EXP_LOG_OPEN_EVERY_LOOPS = 3            # Experimente: offene Positionen alle ~36 s aufzeichnen   # nach dem Verkauf 6 h weiter aufzeichnen (fuer Nachrechnungen)
DISCORD_WEBHOOK_EXPERIMENTE = (os.environ.get("DISCORD_WEBHOOK_EXPERIMENTE") or "").strip()

# ================================================================ Knapp abgelehnt (nur Beobachtung)
NEAR_MISS_WATCH_H = 6
NEAR_MISS_MAX_TRACKED = 60

# ================================================================ Mitlaeufer-Verdacht
# Nur Beobachtung, keine Kaufregel: Teilt ein Kandidat einen Namensteil mit einem viel
# groesseren Trending-Coin (z. B. "K/ACC" und "e/acc"), wird er markiert.
NARRATIVE_LEADER_MIN_MCAP = 5_000_000
NARRATIVE_LEADER_FACTOR = 10
NARRATIVE_MIN_PART_LEN = 3
NARRATIVE_STOPWORDS = {"THE", "COIN", "TOKEN", "SOL", "SOLANA", "MEME", "AND", "FOR",
                       "OFFICIAL", "WITH", "FROM", "THIS", "THAT"}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "narrativ-paperbot/1.0"})

def fresh_stats():
    return {"loops": 0, "loop_errors": 0, "last_error": "", "entries": [], "exits": [],
            "partials": [], "rejects": {}, "jup_ok": 0, "jup_fail": 0,
            "rugcheck_ok": 0, "rugcheck_fail": 0, "helius_ok": 0, "helius_fail": 0,
            "git_ok": 0, "git_fail": 0, "discord_fail": 0, "block0_too_many": 0, "graduations": 0,
            "st_ok": 0, "st_fail": 0, "st_skipped": 0, "young_by_list": {}, "resets": 0,
            "exp_errors": 0, "quote_2s": [], "notloesung": 0, "messung_verworfen": 0, "dex": 0, "dex_fehler": 0}


STATS = fresh_stats()
EXP_STATS = {name: fresh_stats() for name in EXPERIMENTS}

# Wohin Kauf, Verkauf, Journal, Verlauf und Discord gerade schreiben. Normal: Hauptstrategie.
CTX = {"name": None, "portfolio": PORTFOLIO_FILE, "journal": JOURNAL_FILE, "verlauf_prefix": "",
       "webhook": None, "title_prefix": "", "watch": True}


@contextmanager
def experiment(name):
    """Alles innerhalb dieses Blocks betrifft nur das Konto des Experiments."""
    global STATS
    saved_stats, saved_ctx = STATS, dict(CTX)
    exp_stats = EXP_STATS[name]
    exp_stats["loops"] = saved_stats["loops"]
    STATS = exp_stats
    folder = os.path.join(EXP_DIR, name)
    os.makedirs(folder, exist_ok=True)
    CTX.update(name=name, portfolio=os.path.join(folder, "portfolio.json"),
               journal=os.path.join(folder, "journal.csv"), verlauf_prefix=f"exp_{name}_",
               webhook=DISCORD_WEBHOOK_EXPERIMENTE or None,
               title_prefix=f"[Experiment {EXPERIMENTS[name]}] ", watch=name in EXP_WATCH_AFTER_EXIT)
    try:
        yield
    finally:
        STATS = saved_stats
        CTX.clear()
        CTX.update(saved_ctx)
_jup_last = [0.0]
_rugcheck_last = [0.0]
_helius_last = [0.0]
HELIUS_INTERVAL = 0.15      # Hauptbot hoechstens ~6,5 Anfragen/s; der Copy-Bot setzt fuer sich einen langsameren Wert
HELIUS_RETRY_WAIT = (0.5, 1.0, 2.0)   # bei 429 (zu viele Anfragen) bis zu drei weitere Versuche
_block0_cache = {}
_bundle_cache = {}
_portfolio_alarm = set()
_shield_cache = {}
_reject_seen = {}
_symbol_leaders = {}                    # Tag 12: Symbol -> (mint, holder, zeit)
_narrative_leaders = {}                 # Namensteil -> (mint, symbol, mcap, zeit)
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


def _hide_key(text):
    return str(text).replace(HELIUS_API_KEY, "***") if HELIUS_API_KEY else str(text)


def rpc(method, params):
    """Solana-RPC ueber Helius. Der API-Key taucht nie im Log auf."""
    if not HELIUS_RPC:
        return None
    for wait in (0.0,) + HELIUS_RETRY_WAIT:
        if wait:
            STATS["helius_429"] = STATS.get("helius_429", 0) + 1
            time.sleep(wait)
        _throttle(_helius_last, HELIUS_INTERVAL)
        try:
            res = SESSION.post(HELIUS_RPC, json={"jsonrpc": "2.0", "id": 1, "method": method,
                                                 "params": params}, timeout=20)
        except requests.RequestException as err:
            STATS["helius_fail"] += 1
            print(f"[HELIUS] {method}: {_hide_key(err)[:160]}")
            return None
        if res.status_code != 429:
            break
    if res.status_code != 200:
        STATS["helius_fail"] += 1
        print(f"[HELIUS HTTP {res.status_code}] {method}: {_hide_key(res.text)[:120]}")
        return None
    try:
        body = res.json()
    except ValueError:
        STATS["helius_fail"] += 1
        return None
    if body.get("error"):
        STATS["helius_fail"] += 1
        print(f"[HELIUS] {method}: {_hide_key(body['error'])[:160]}")
        return None
    STATS["helius_ok"] += 1
    return body.get("result")


def find_creation_block(mint):
    """Geht die Transaktionen des Tokens bis zur ersten zurueck.
    Rueckgabe (Slot, Signaturen in Block 0, Transaktionen in den 2 Folgeslots) oder None."""
    before, prev_page, page = None, [], []
    for _ in range(BLOCK0_MAX_PAGES):
        params = {"limit": 1000, "commitment": "confirmed"}
        if before:
            params["before"] = before
        result = rpc("getSignaturesForAddress", [mint, params])
        if result is None:
            return None
        if not result:
            break
        prev_page, page = page, result
        if len(result) < 1000:
            break
        before = result[-1]["signature"]
    else:
        STATS["block0_too_many"] += 1       # erwartete Grenze, steht in der Endmeldung statt im Log
        return None
    sigs = prev_page + page
    if not sigs:
        return None
    slot = min(s["slot"] for s in sigs)
    block0 = [s for s in sigs if s["slot"] == slot and not s.get("err")]
    early = sum(1 for s in sigs if slot < s["slot"] <= slot + 2 and not s.get("err"))
    return slot, block0, early


def block0_analysis(mint):
    """Tag 1 nach der SolBundler-Methode: Wer hat im Erstellungsblock gekauft,
    wie viel vom Angebot, und halten diese Wallets noch?"""
    base = _block0_cache.get(mint)
    if base is None:
        found = find_creation_block(mint)
        if not found:
            return None
        slot, sigs, early = found
        supply = as_float(((rpc("getTokenSupply", [mint]) or {}).get("value") or {}).get("amount"))
        if supply <= 0:
            return None
        bought = {}
        for s in sigs[:BLOCK0_MAX_TX]:
            tx = rpc("getTransaction", [s["signature"], {"encoding": "json", "commitment": "confirmed",
                                                          "maxSupportedTransactionVersion": 1}])
            meta = (tx or {}).get("meta") or {}
            if not tx or meta.get("err"):
                continue
            pre = {b.get("accountIndex"): b for b in meta.get("preTokenBalances") or []
                   if b.get("mint") == mint}
            for b in meta.get("postTokenBalances") or []:
                if b.get("mint") != mint or not b.get("owner"):
                    continue
                post_amt = as_float((b.get("uiTokenAmount") or {}).get("amount"))
                pre_amt = as_float(((pre.get(b.get("accountIndex")) or {})
                                    .get("uiTokenAmount") or {}).get("amount"))
                if post_amt <= pre_amt:
                    continue
                if post_amt / supply > 0.5:
                    continue                      # Bonding Curve bzw. Pool, kein Kaeufer
                bought[b["owner"]] = bought.get(b["owner"], 0.0) + (post_amt - pre_amt)
        base = {"slot": slot, "block0_tx": len(sigs), "early_tx": early,
                "supply": supply, "bought": bought}
        _block0_cache[mint] = base

    held, exited = 0.0, 0
    for owner, amount in list(base["bought"].items())[:BLOCK0_MAX_WALLETS]:
        res = rpc("getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding": "jsonParsed"}])
        if res is None:
            held += amount                       # unbekannt: vorsichtshalber noch gehalten
            continue
        current = 0.0
        for acc in res.get("value") or []:
            info = ((((acc.get("account") or {}).get("data") or {}).get("parsed") or {})
                    .get("info") or {})
            current += as_float((info.get("tokenAmount") or {}).get("amount"))
        held += current
        if current < amount * 0.1:
            exited += 1
    supply = base["supply"]
    bought_total = sum(base["bought"].values())
    return {
        "quelle": "block0",
        "slot": base["slot"],
        "block0_wallets": len(base["bought"]),
        "block0_supply_pct": round(bought_total / supply * 100, 2),
        "block0_still_held_pct": round(held / supply * 100, 2),
        "block0_exited": exited,
        "early_tx_slot1_2": base["early_tx"],
        "bundle_holding_pct": round(held / supply * 100, 2),
    }


def rugcheck_get(mint):
    _throttle(_rugcheck_last, 1.1)
    try:
        res = SESSION.get(f"{RUGCHECK_BASE}/tokens/{mint}/report", timeout=20)
    except requests.RequestException as err:
        STATS["rugcheck_fail"] += 1
        print(f"[RUGCHECK] {err}")
        return None
    if res.status_code != 200:
        STATS["rugcheck_fail"] += 1
        print(f"[RUGCHECK HTTP {res.status_code}] {res.text[:120]}")
        return None
    try:
        data = res.json()
    except ValueError:
        STATS["rugcheck_fail"] += 1
        return None
    STATS["rugcheck_ok"] += 1
    return data if isinstance(data, dict) else None


def rugcheck_metrics(data):
    """Insider-Anteil aus RugCheck. Insider-Netzwerke sind verbundene Wallets,
    typischerweise vom selben Ursprung finanziert - das On-Chain-Bild von Bundling."""
    holders = data.get("topHolders") or []
    insider_pct = sum(as_float(h.get("pct")) for h in holders if h.get("insider"))
    token = data.get("token") or {}
    supply = as_float(token.get("supply"))
    network_pct = 0.0
    for net in data.get("insiderNetworks") or []:
        amount = as_float(net.get("tokenAmount"))
        if supply > 0 and amount > 0:
            network_pct += amount / supply * 100
    if network_pct > 100:                             # Einheiten passen nicht zusammen
        network_pct = 0.0
    risks = [str(r.get("name") or "") for r in data.get("risks") or []]
    return {
        "quelle": "rugcheck",
        "bundle_holding_pct": round(max(insider_pct, network_pct), 2),
        "insider_holder_pct": round(insider_pct, 2),
        "insider_network_pct": round(network_pct, 2),
        "insider_wallets": int(as_float(data.get("graphInsidersDetected"))),
        "top_holders_listed": len(holders),
        "rugged": bool(data.get("rugged")),
        "risks": risks[:8],
    }


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


_tok_cache = {}                          # mint -> (zeit, token); Hauptstrategie und Experimente teilen
TOK_CACHE_SECONDS = 6


_jup_unanswered = set()                  # Mints der letzten jup_tokens-Abfrage ohne gueltige Jupiter-Antwort


def jup_tokens(mints):
    """Bis zu 100 Token in einer Abfrage. Rueckgabe {mint: token}. Frische Werte kommen aus dem Cache."""
    now = time.time()
    result, missing = {}, []
    for m in dict.fromkeys(m for m in mints if m):
        hit = _tok_cache.get(m)
        if hit and now - hit[0] < TOK_CACHE_SECONDS:
            result[m] = hit[1]
        else:
            missing.append(m)
    _jup_unanswered.clear()
    for i in range(0, len(missing), 100):
        chunk = missing[i:i + 100]
        data = jup_get(f"/tokens/v2/search?query={','.join(chunk)}")
        if not isinstance(data, list):
            _jup_unanswered.update(chunk)       # Ausfall: diese Coins sind nicht verschwunden, nur unbekannt
            continue
        for tok in data:
            if tok.get("id"):
                result[tok["id"]] = tok
                _tok_cache[tok["id"]] = (now, tok)
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
    s5, s1, s24 = tok.get("stats5m") or {}, tok.get("stats1h") or {}, tok.get("stats24h") or {}
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
        "dev_mints": int(as_float(audit.get("devMints"))),
        "dev_balance_pct": as_float(audit.get("devBalancePercentage")),
        "top_holders_pct": as_float(audit.get("topHoldersPercentage")),
        "dev": tok.get("dev"),
        "launchpad": tok.get("launchpad"),
        "graduated": bool(tok.get("graduatedPool")),
        "price_change_5m": as_float(s5.get("priceChange")),
        "buys_5m": int(as_float(s5.get("numBuys"))),
        "sells_5m": int(as_float(s5.get("numSells"))),
        "traders_5m": int(as_float(s5.get("numTraders"))),
        "buy_vol_5m": as_float(s5.get("buyVolume")),
        "sell_vol_5m": as_float(s5.get("sellVolume")),
        "buy_vol_1h": as_float(s1.get("buyVolume")),
        "sell_vol_1h": as_float(s1.get("sellVolume")),
        "organic_buy_vol_1h": as_float(s1.get("buyOrganicVolume")),
        "traders_1h": int(as_float(s1.get("numTraders"))),
        "trades_24h": int(as_float(s24.get("numBuys")) + as_float(s24.get("numSells"))),
        "organic_label": str(tok.get("organicScoreLabel") or ""),
        "buy_organic_vol_5m": as_float(s5.get("buyOrganicVolume")),
        # jup_fees (Jupiter-Feld "fees", seit 04.10. aufgezeichnet) war in allen Daten leer: seit 06.10. nicht mehr befuellt.
        # Die Spalte bleibt (CSV-Spalten nie loeschen), alte Daten bleiben unveraendert.
        "jup_fees": None,
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


def name_parts(v):
    parts = set()
    for text in (v.get("symbol"), v.get("name")):
        for part in re.split(r"[^A-Za-z0-9]+", str(text or "").upper()):
            if len(part) >= NARRATIVE_MIN_PART_LEN and part not in NARRATIVE_STOPWORDS:
                parts.add(part)
    return parts


def update_narrative_leaders(views, now):
    for v in views:
        if v["mcap"] < NARRATIVE_LEADER_MIN_MCAP:
            continue
        for part in name_parts(v):
            cur = _narrative_leaders.get(part)
            if cur is None or now - cur[3] > 24 * 3600 or cur[0] == v["mint"] or v["mcap"] > cur[2]:
                _narrative_leaders[part] = (v["mint"], v["symbol"], v["mcap"], now)


def follower_of(v, now):
    """Mitlaeufer-Verdacht: Namensteil gehoert zu einem viel groesseren Coin."""
    for part in sorted(name_parts(v)):
        lead = _narrative_leaders.get(part)
        if lead and lead[0] != v["mint"] and now - lead[3] <= 24 * 3600 and \
                lead[2] >= max(NARRATIVE_LEADER_MIN_MCAP, v["mcap"] * NARRATIVE_LEADER_FACTOR):
            return {"teil": part, "leader": lead[1], "leader_mint": lead[0],
                    "leader_mcap": round(lead[2])}
    return None


def vamp_copy_of(v):
    for key in {norm_symbol(v["symbol"]), norm_symbol(v["name"])} - {""}:
        leader = _symbol_leaders.get(key)
        if leader and leader[0] != v["mint"] and leader[1] > v["holders"]:
            return leader[0]
    return None


# ================================================================ Einstiegspruefung

def quick_checks(v, ohne_sicherheit=False):
    """Guenstige Pruefungen ohne weitere Abfragen. Rueckgabe: Ablehnungsgrund oder None.
    ohne_sicherheit=True (nur Experiment Offene Tuer): Gruende aus SICHERHEITS_GRUENDE werden uebersprungen."""
    if ohne_sicherheit:
        for _ in range(len(SICHERHEITS_GRUENDE) + 1):
            grund = quick_checks(v)
            if grund not in SICHERHEITS_GRUENDE:
                return grund
            v = {**v, **_ENTSCHAERFT[grund]}         # Sicherheitsgrund ausblenden, Rest weiter pruefen
        return None
    if v["age_h"] is None:
        return "KEIN_ALTER"
    if v["age_h"] < MIN_AGE_MIN / 60:
        return "ZU_JUNG"
    if v["age_h"] > MAX_AGE_H:
        return "STORY_ZU_ALT"                                   # Tag 5
    if v["mcap"] > MAX_MCAP_USD:
        return "SCHON_GELAUFEN"                                 # Tag 7
    if v["age_h"] >= CHASE_CHECK_MIN_AGE_H and v["price_change_1h"] > MAX_PRICE_CHANGE_1H:
        return "SCHON_GELAUFEN"
    if v["dev_mints"] > MAX_DEV_MINTS or v["dev_balance_pct"] > MAX_CREATOR_HOLDING_PCT:
        return "DEV_VERDAECHTIG"                                # Tag 6
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
    if v["price_change_5m"] > FOMO_MAX_5M_PCT:
        return "FOMO_SPRUNG"                                    # Tag 17: nach einem Sprung kaufen ist FOMO
    return None


_ENTSCHAERFT = {   # Felder so setzen, dass der jeweilige Sicherheitsgrund nicht mehr greift (nur fuer ohne_sicherheit)
    "DEV_VERDAECHTIG": {"dev_mints": 0, "dev_balance_pct": 0.0},
    "NACHAHMER_SYMBOL": {"symbol": "~offene_tuer~"},
    "UNSICHERER_CONTRACT": {"mint_disabled": True, "freeze_disabled": True, "is_sus": False},
    "VAMP_KOPIE": {"name": "", "symbol": "~offene_tuer~"},
}


def bundle_dev_check(mint):
    """Tag 1. Entscheidend ist der eigene Block-0-Check. RugCheck prueft zusaetzlich auf
    Insider-Netzwerke, kann den Block-0-Check aber nicht ersetzen (erkennt frische
    Bundles nicht zuverlaessig). Rueckgabe (Grund oder None, Kennzahlen)."""
    cached = _bundle_cache.get(mint)
    if cached and time.time() - cached[0] < cached[3]:
        return cached[1], cached[2]

    b0 = block0_analysis(mint) if HELIUS_RPC else None
    if not b0:
        # 30 min merken: sonst geht der Bot bei Coins mit >40.000 Transaktionen
        # alle 70 Sekunden erneut 40 Seiten zurueck
        reason = "BUNDLE_CHECK_NICHT_MOEGLICH" if BUNDLE_CHECK_REQUIRED else None
        _bundle_cache[mint] = (time.time(), reason, {}, 1800)
        return reason, {}

    info, reason, keep_s = dict(b0), None, 600
    bundled = (b0["block0_wallets"] >= BUNDLE_MIN_WALLETS
               and b0["block0_supply_pct"] >= BUNDLE_MAX_SUPPLY_PCT)
    if b0["block0_still_held_pct"] >= BUNDLE_MAX_STILL_HELD_PCT:
        reason = "BUNDLER_HALTEN_NOCH"
    elif bundled and BUNDLE_RULE == "streng":
        reason, keep_s = "GEBUENDELT", 24 * 3600       # Block 0 aendert sich nie
    info["gebuendelt"] = bundled

    if reason is None:
        rc = rugcheck_get(mint)
        if rc and (rc.get("topHolders") or rc.get("insiderNetworks")):
            m = rugcheck_metrics(rc)
            info["rugcheck_insider_pct"] = m["bundle_holding_pct"]
            if m["rugged"]:
                reason = "BEREITS_GERUGGT"
            elif m["bundle_holding_pct"] >= MAX_BUNDLE_HOLDING_PCT:
                reason = "INSIDER_NETZWERK"

    _bundle_cache[mint] = (time.time(), reason, info, keep_s)
    return reason, info


def safety_shield(mint):
    types = shield(mint) or []
    fees = [t for t in types if "TRANSFER_FEE" in str(t).upper()]
    return "TRANSFERGEBUEHR" if fees else None


# ================================================================ Portfolio

def load_portfolio():
    path = CTX["portfolio"]
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "bankroll_sol" in data:
                data.setdefault("positions", {})
                data.setdefault("closed", [])
                data.setdefault("cooldown", {})
                data.setdefault("watch", {})
                return data
        except Exception as err:
            # Nie still bei null anfangen: das wuerde echte Positionen und Ergebnisse verwerfen
            if path not in _portfolio_alarm:
                _portfolio_alarm.add(path)
                discord(f"🛑 {path} unlesbar - hier wird nicht gehandelt",
                        f"Fehler: {str(err)[:300]}\nBitte Claude Bescheid geben.", 0xEF4444)
            raise RuntimeError(f"{path} unlesbar: {err}")
    fresh = {"strategy": "NARRATIV", "started": datetime.now(timezone.utc).isoformat(),
             "bankroll_sol": START_BANKROLL_SOL, "positions": {}, "closed": [], "cooldown": {},
             "watch": {}}
    if CTX["name"]:
        fresh.update(strategy=f"EXPERIMENT_{CTX['name']}", runde=1)
    return fresh


def save_portfolio(p):
    p["saved_at"] = time.time()
    path = CTX["portfolio"]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)
    os.replace(tmp, path)


# Spalte seit 03.10. hinten: notloesung (1 = Verkauf ohne Quote, Kurs x 0,95 angenommen)
JOURNAL_HEADER = ["zeit", "aktion", "symbol", "mint", "preis_usd", "sol",
                  "these", "verkaufsbedingung", "grund", "pnl_sol", "pnl_pct", "notloesung"]


def journal(action, pos, price_usd, sol, reason="", pnl_sol="", pnl_pct="", notloesung=""):
    """Tag 3: Einstieg mit These und Verkaufsbedingung, jeder Verkauf mit Grund."""
    path = CTX["journal"]
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(JOURNAL_HEADER)
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), action,
                    pos["symbol"], pos["mint"], f"{price_usd:.12g}", f"{sol:.4f}",
                    pos.get("thesis", ""), pos.get("exit_rule", ""), reason,
                    pnl_sol if pnl_sol == "" else f"{pnl_sol:+.4f}",
                    pnl_pct if pnl_pct == "" else f"{pnl_pct:+.1f}", notloesung])


_rechecks = deque(maxlen=200)       # (faellig, erste Quote um, Konto, Aktion, Symbol, von, nach, Menge, erste)


def schedule_recheck(action, symbol, input_mint, output_mint, raw_amount, first_out, first_at):
    """Messung vormerken, keine Regel: Was gaebe es 2 s spaeter? Ausgefuehrt in der Pause zwischen zwei
    Durchlaeufen (sleep_with_rechecks), damit kein Kauf, Verkauf oder Notbremse darauf warten muss."""
    if first_out and first_out > 0 and raw_amount > 0:
        _rechecks.append((first_at + QUOTE_RECHECK_SECONDS, first_at, CTX["name"] or "hauptstrategie", action,
                          symbol, input_mint, output_mint, int(raw_amount), int(first_out)))


def run_recheck():
    """Eine Messung ausfuehren. + = 2 s spaeter haetten wir weniger bekommen (Token beim Kauf, SOL beim Verkauf)."""
    due, first_at, konto, action, symbol, in_m, out_m, raw, first = _rechecks.popleft()
    if time.time() - due > QUOTE_RECHECK_MAX_S:
        STATS["messung_verworfen"] += 1
        return
    later = quote(in_m, out_m, raw)                      # faengt Netzwerkfehler selbst ab (dann 0)
    if not later or later <= 0:
        STATS["messung_verworfen"] += 1
        return
    drift = (1 - later / first) * 100
    STATS["quote_2s"].append(drift)
    new = not os.path.exists(MESSUNG_FILE)
    with open(MESSUNG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(MESSUNG_HEADER)
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), konto, action, symbol,
                    out_m if action == "KAUF" else in_m, first, later, f"{time.time() - first_at:.1f}",
                    f"{drift:+.2f}"])


_dex_queue = deque(maxlen=300)           # (Zeitpunkt, Konto, Art, Symbol, Mint, Grund, Coin-Alter in min)
_dex_seen = {}                           # (Mint, Art) -> Zeitpunkt der letzten Aufzeichnung
_dex_last = [0.0]


def dex_vormerken(art, v, grund=""):
    """DexScreener-Abfrage vormerken (nur Beobachtung). art: 'kauf' oder 'knapp_abgelehnt'."""
    key, now = (v.get("mint"), art), time.time()
    if not v.get("mint") or now - _dex_seen.get(key, 0) < DEX_REPEAT_H * 3600:
        return
    _dex_seen[key] = now
    alter = v.get("age_h")
    _dex_queue.append((now, CTX["name"] or "hauptstrategie", art, v.get("symbol", ""), v["mint"], grund,
                       round(alter * 60) if alter is not None else ""))


def dex_get(path):
    """GET auf die offizielle DexScreener-API (ohne Schluessel). None bei jedem Fehler."""
    _throttle(_dex_last, DEX_INTERVAL)
    try:
        res = SESSION.get(DEX_BASE + path, timeout=8)
        return res.json() if res.status_code == 200 else None
    except (requests.RequestException, ValueError):
        return None


def run_dex():
    """Eine vorgemerkte DexScreener-Abfrage ausfuehren und in dexscreener.csv schreiben."""
    zeit, konto, art, symbol, mint, grund, alter = _dex_queue.popleft()
    data = dex_get(f"/orders/v1/solana/{mint}")
    zeile = {"zeit": datetime.fromtimestamp(zeit, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "konto": konto,
             "art": art, "symbol": symbol, "mint": mint, "grund": grund, "coin_alter_min": alter}
    if not isinstance(data, dict):
        STATS["dex_fehler"] += 1
        zeile["fehler"] = "keine Antwort"
    else:
        orders = [o for o in data.get("orders") or [] if isinstance(o, dict)]
        boosts = [b for b in data.get("boosts") or [] if isinstance(b, dict)]
        typen = [str(o.get("type", "")) for o in orders]
        zahlungen = sorted(as_float(x.get("paymentTimestamp")) / 1000 for x in orders + boosts
                           if as_float(x.get("paymentTimestamp")) > 0)
        zeile.update({
            "profil": int("tokenProfile" in typen),
            "werbung": sum(1 for t in typen if "Ad" in t or "ad" in t.lower().split("_")),
            "cto": int("communityTakeover" in typen), "boosts": len(boosts),
            "erste_zahlung_min_vor_ereignis": round((zeit - zahlungen[0]) / 60, 1) if zahlungen else "",
            "letzte_zahlung_min_vor_ereignis": round((zeit - zahlungen[-1]) / 60, 1) if zahlungen else "",
            "zahlungen": " ".join(f"{t}@{int(as_float(o.get('paymentTimestamp')) / 1000)}"
                                  for t, o in zip(typen, orders)),
        })
        STATS["dex"] += 1
    new = not os.path.exists(DEX_FILE)
    with open(DEX_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(DEX_HEADER)
        w.writerow([zeile.get(k, "") for k in DEX_HEADER])


def sleep_with_rechecks(seconds):
    """Pause zwischen zwei Durchlaeufen; faellige Messungen und DexScreener-Abfragen laufen darin,
    die Pause wird nicht laenger (hoechstens um die Dauer einer Abfrage)."""
    end = time.time() + seconds
    while (_rechecks or _dex_queue) and time.time() < end:
        wait = _rechecks[0][0] - time.time() if _rechecks else None
        try:
            if wait is not None and wait <= 0:
                run_recheck()
            elif _dex_queue and end - time.time() > DEX_INTERVAL + 1:
                run_dex()
            elif wait is not None:
                time.sleep(max(0.0, min(wait, end - time.time())))   # nie negativ (ValueError)
            else:
                break
        except Interrupted:
            raise
        except Exception as err:                         # Messung/Beobachtung darf den Bot nie stoppen
            STATS["messung_verworfen"] += 1
            print(f"[MESSUNG] {str(err)[:100]}")
    rest = end - time.time()
    if rest > 0:
        time.sleep(rest)


ENTRY_FEATURES = ("age_h", "mcap", "liquidity", "holders", "holder_growth_1h", "holder_growth_5m",
                  "net_buyers_5m", "organic_buyers_5m", "organic_score", "price_change_1h",
                  "price_change_5m", "buys_5m", "sells_5m", "traders_5m", "traders_1h",
                  "buy_vol_5m", "sell_vol_5m", "buy_vol_1h", "sell_vol_1h", "organic_buy_vol_1h",
                  "top_holders_pct", "dev_balance_pct", "dev_mints", "launchpad", "graduated",
                  "social", "quelle", "trades_24h", "organic_label", "buy_organic_vol_5m",
                  "jup_fees")                     # neue Merkmale nur hinten anhaengen (CSV-Spalten)


NEAR_MISS_HEADER = ["zeit", "symbol", "mint", "grund", "detail", "preis_usd", *ENTRY_FEATURES]


def verlauf_file():
    return os.path.join(VERLAUF_DIR, datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".csv")


_flug_b0 = {}                           # Mint -> (Zeitpunkt, gehalten %, ausgestiegen, Wallets) – geteilt von allen Konten


def flug_block0(pos, mint, now):
    """Bestand der gespeicherten Block-0-Kaeufer (hoechstens 8) – alle 10 min je Coin, sonst aus dem Zwischenspeicher."""
    b0 = pos.get("block0_flug")
    if not b0 or not b0.get("bought"):
        return None
    hit = _flug_b0.get(mint)
    if hit and now - hit[0] < FLUG_B0_EVERY_S:
        return hit[1:] if hit[3] else None
    held, exited, known = 0.0, 0, 0
    for owner, amount in list(b0["bought"].items())[:FLUG_B0_MAX_WALLETS]:
        res = rpc("getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding": "jsonParsed"}])
        if not isinstance(res, dict):
            continue                              # unbekannt: nicht mitzaehlen
        known += 1
        current = 0.0
        for acc in res.get("value") or []:
            info = ((((acc.get("account") or {}).get("data") or {}).get("parsed") or {}).get("info") or {})
            current += as_float((info.get("tokenAmount") or {}).get("amount"))
        held += current
        if current < amount * 0.1:
            exited += 1
    if not known:
        _flug_b0[mint] = (now, "", "", 0)        # auch Fehlversuch 10 min merken (kein Dauerfeuer bei Ausfall)
        return None
    result = (round(held / b0["supply"] * 100, 3) if b0.get("supply") else None, exited, known)
    _flug_b0[mint] = (now, *result)
    return result


def flug_aufzeichnen(pos, v, now):
    """Flugschreiber: eine Zeile je offene Position etwa jede Minute (nur Aufzeichnung)."""
    if now - pos.get("flug_last", 0) < FLUG_EVERY_S:
        return
    pos["flug_last"] = now
    b0 = flug_block0(pos, v["mint"], now)
    os.makedirs(FLUG_DIR, exist_ok=True)
    path = os.path.join(FLUG_DIR, datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FLUG_HEADER)
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), CTX["name"] or "hauptstrategie",
                    v["mint"], pos.get("symbol", ""), f"{(now - pos['opened']) / 60:.1f}",
                    f"{v['price'] / pos['entry_fill_usd']:.4f}" if pos.get("entry_fill_usd") else "",
                    f"{v['liquidity']:.0f}", v["holders"], f"{v['top_holders_pct']:.2f}", f"{v['dev_balance_pct']:.2f}",
                    v["net_buyers_5m"], v["buys_5m"], v["sells_5m"], f"{v['buy_vol_5m']:.0f}", f"{v['sell_vol_5m']:.0f}",
                    *(b0 if b0 else ("", "", ""))])


def log_path(stage, mint, symbol, v, entry_fill, opened, peak_usd, tp1_done):
    """Kursverlauf als Vielfaches des Einstiegs, fuer die spaetere Bewertung der Ausstiegsregeln."""
    if not entry_fill:
        return
    if CTX["name"] and stage == "offen" and STATS["loops"] % EXP_LOG_OPEN_EVERY_LOOPS != 0:
        return
    stage = CTX["verlauf_prefix"] + stage
    path = verlauf_file()
    os.makedirs(VERLAUF_DIR, exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["zeit", "mint", "symbol", "phase", "minuten_seit_kauf", "vielfaches",
                        "hoch_vielfaches", "teilverkauf", "holder_1h_pct", "netto_kaeufer_5m",
                        "liquiditaet", "preis_usd"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), mint, symbol, stage,
                    f"{(time.time() - opened) / 60:.1f}", f"{v['price'] / entry_fill:.4f}",
                    f"{peak_usd / entry_fill:.4f}", int(bool(tp1_done)),
                    f"{v['holder_growth_1h']:.1f}", v["net_buyers_5m"], f"{v['liquidity']:.0f}",
                    f"{v['price']:.12g}"])


def solana_tracker_summary(data):
    risk = (data or {}).get("risk") or {}
    def pct(key):
        part = risk.get(key)
        return part.get("totalPercentage") if isinstance(part, dict) else None
    return {"score": risk.get("score"), "rugged": risk.get("rugged"), "snipers_pct": pct("snipers"),
            "insiders_pct": pct("insiders"), "bundlers_pct": pct("bundlers"), "top10_pct": risk.get("top10"),
            "risiken": [r.get("name") for r in risk.get("risks") or [] if isinstance(r, dict)][:12]}


def solana_tracker_risk(p, mint):
    """Zweitmeinung von Solana Tracker. Nur Aufzeichnung, beeinflusst den Kauf nicht.
    Hoechstens SOLANA_TRACKER_DAILY_LIMIT Abfragen pro Tag (UTC), gezaehlt im Portfolio."""
    if not SOLANA_TRACKER_API_KEY:
        return None
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage = p.setdefault("st_usage", {})
    if usage.get("date") != today:
        usage.clear()
        usage.update(date=today, count=0)
    if usage["count"] >= SOLANA_TRACKER_DAILY_LIMIT:
        STATS["st_skipped"] += 1
        return None
    usage["count"] += 1
    try:
        res = SESSION.get(f"{SOLANA_TRACKER_BASE}/tokens/{mint}", timeout=8,
                          headers={"x-api-key": SOLANA_TRACKER_API_KEY})
        if res.status_code != 200:
            STATS["st_fail"] += 1
            return {"fehler": f"HTTP {res.status_code}"}
        STATS["st_ok"] += 1
        return solana_tracker_summary(res.json())
    except (requests.RequestException, ValueError) as err:
        STATS["st_fail"] += 1
        return {"fehler": str(err)[:80]}


def near_miss_detail(v, reason, extra=None):
    """Gibt eine kurze Beschreibung zurueck, wenn die Ablehnung knapp war, sonst None."""
    if reason == "VERBREITUNG_STOCKT" and 10 <= v["holder_growth_1h"] < MIN_HOLDER_GROWTH_1H \
            and v["holder_growth_5m"] > 0:
        return f"Holder +{v['holder_growth_1h']:.0f}%/h (Grenze {MIN_HOLDER_GROWTH_1H:.0f})"
    if reason == "KEINE_ECHTEN_KAEUFER":
        if v["organic_buyers_5m"] == MIN_ORGANIC_BUYERS_5M - 1 and v["net_buyers_5m"] >= MIN_NET_BUYERS_5M:
            return f"{v['organic_buyers_5m']} organische Kaeufer (Grenze {MIN_ORGANIC_BUYERS_5M})"
        if v["organic_buyers_5m"] >= MIN_ORGANIC_BUYERS_5M and v["net_buyers_5m"] == 0:
            return "0 Netto-Kaeufer"
    if reason == "SCHON_GELAUFEN":
        if MAX_MCAP_USD < v["mcap"] <= MAX_MCAP_USD * 5 / 3:
            return f"Marktwert ${v['mcap']:,.0f} (Grenze ${MAX_MCAP_USD:,.0f})"
        if v["mcap"] <= MAX_MCAP_USD and MAX_PRICE_CHANGE_1H < v["price_change_1h"] <= 250:
            return f"+{v['price_change_1h']:.0f}% in 1 h (Grenze {MAX_PRICE_CHANGE_1H:.0f})"
    if reason == "STORY_ZU_ALT" and v["age_h"] is not None and MAX_AGE_H < v["age_h"] <= MAX_AGE_H + 2:
        return f"{v['age_h']:.1f} h alt (Grenze {MAX_AGE_H})"
    if reason == "DEV_VERDAECHTIG":
        if MAX_DEV_MINTS < v["dev_mints"] <= 100:
            return f"Dev {v['dev_mints']} Coins (Grenze {MAX_DEV_MINTS})"
        if MAX_CREATOR_HOLDING_PCT < v["dev_balance_pct"] <= 15:
            return f"Dev haelt {v['dev_balance_pct']:.1f}%"
    if reason == "NICHT_ORGANISCH" and 25 <= v["organic_score"] < MIN_ORGANIC_SCORE:
        return f"Organic Score {v['organic_score']:.0f} (Grenze {MIN_ORGANIC_SCORE})"
    if reason == "LIQUIDITAET_ZU_GERING" and 3000 <= v["liquidity"] < MIN_LIQUIDITY_USD:
        return f"Liquiditaet ${v['liquidity']:,.0f}"
    if reason == "GEBUENDELT" and extra and extra.get("block0_supply_pct", 0) < BUNDLE_MAX_SUPPLY_PCT + 5:
        return f"Block 0: {extra.get('block0_wallets')} Kaeufer, {extra.get('block0_supply_pct')}%"
    if reason == "BUNDLE_CHECK_NICHT_MOEGLICH":
        return "Bundle-Check nicht moeglich"
    if reason == "FOMO_SPRUNG":                 # Tag 17: alle verfolgen, um die Regel zu pruefen
        return f"+{v['price_change_5m']:.0f}% in 5 min (Grenze {FOMO_MAX_5M_PCT:.0f})"
    if reason == "KEIN_PLATZ":
        if extra and extra.get("alle_pruefungen"):
            return "alle Pruefungen bestanden, Positionslimit erreicht"
        return "alle Schnellpruefungen bestanden, Positionslimit erreicht (ohne Bundle-Check)"
    return None


def track_near_miss(p, v, reason, now, extra=None):
    """Knapp abgelehnte Coins 6 h weiter beobachten (nur Aufzeichnung, kein Handel)."""
    detail = near_miss_detail(v, reason, extra)
    if not detail or v["price"] <= 0:
        return
    shadow = p.setdefault("shadow", {})
    mint = v["mint"]
    if mint in shadow or mint in p["positions"] or mint in p.get("watch", {}) \
            or len(shadow) >= NEAR_MISS_MAX_TRACKED:
        return
    shadow[mint] = {"symbol": v["symbol"], "reason": reason, "detail": detail,
                    "ref_price": v["price"], "since": now, "peak_usd": v["price"],
                    "until": now + NEAR_MISS_WATCH_H * 3600}
    STATS["near_misses"] = STATS.get("near_misses", 0) + 1
    new = not os.path.exists(NEAR_MISS_FILE)
    with open(NEAR_MISS_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(NEAR_MISS_HEADER)
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), v["symbol"], mint,
                    reason, detail, f"{v['price']:.12g}", *[v.get(k) for k in ENTRY_FEATURES]])
    dex_vormerken("knapp_abgelehnt", v, reason)


REJECT_HEADER = ["zeit", "symbol", "mint", "grund", "alter_h", "mcap", "liq", "holder",
                 "holder_1h_pct", "netto_kaeufer_5m", "preis_usd", "quelle"]


def ensure_csv_columns(path, header):
    """Haengt neue Spalten an eine bestehende CSV an. Alte Zeilen bekommen leere Felder."""
    if not os.path.exists(path):
        return
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows or rows[0] == header or rows[0] != header[:len(rows[0])]:
        return
    extra = len(header) - len(rows[0])
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([header] + [r + [""] * extra for r in rows[1:]])
    os.replace(tmp, path)


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
            w.writerow(REJECT_HEADER)
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    v.get("symbol"), v.get("mint"), reason,
                    "" if v.get("age_h") is None else f"{v['age_h']:.2f}",
                    f"{v.get('mcap', 0):.0f}", f"{v.get('liquidity', 0):.0f}", v.get("holders"),
                    f"{v.get('holder_growth_1h', 0):.1f}", v.get("net_buyers_5m"),
                    f"{v.get('price', 0):.12g}", v.get("quelle", "")])


# ================================================================ Marktphase

def update_phase(now):
    """Tag 13: Wie hoch laufen frische Coins, wie viel Volumen ist da?"""
    tokens = jup_category("toptrending", "1h", 100)
    if not tokens:
        return None
    views = [token_view(t, now) for t in tokens]
    update_symbol_leaders(views, now)
    update_narrative_leaders(views, now)
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

def open_position(p, v, bundle, sol_usd, max_slippage_pct=None, extra_pos=None):
    decimals = v.get("decimals")
    if decimals is None:
        log_reject(v, "KEINE_DECIMALS")
        return False
    lamports = int(POSITION_SOL * 1e9)
    raw_out = quote(WSOL_MINT, v["mint"], lamports)
    quoted_at = time.time()
    if raw_out <= 0:
        log_reject(v, "KEIN_KAUFKURS")
        return False
    tokens = raw_out / (10 ** int(decimals))
    fill_usd = (POSITION_SOL * sol_usd) / tokens
    slippage = (fill_usd / v["price"] - 1) * 100 if v["price"] > 0 else 0.0
    if max_slippage_pct is not None and slippage > max_slippage_pct:
        return False
    back = quote(v["mint"], WSOL_MINT, raw_out)
    roundtrip = round((1 - back / lamports) * 100, 2) if back > 0 else None

    if bundle.get("quelle") == "experiment":
        bundle_txt = bundle.get("text", "Experiment")
    elif bundle.get("quelle") == "block0":
        bundle_txt = (f"Block 0: {bundle['block0_wallets']} Kaeufer, "
                      f"{bundle['block0_supply_pct']:.1f}% gekauft, "
                      f"{bundle['block0_still_held_pct']:.1f}% noch gehalten"
                      + (" (gebuendelt, Bundler ausgestiegen)" if bundle.get("gebuendelt") else ""))
    else:
        bundle_txt = f"Insider halten {bundle.get('bundle_holding_pct', 0):.1f}% (RugCheck)"
    thesis = (f"Story verbreitet sich: Holder +{v['holder_growth_1h']:.0f}%/h, "
              f"{v['net_buyers_5m']} Netto-Kaeufer 5m, {v['organic_buyers_5m']} organisch; "
              f"{bundle_txt}; Dev-Coins {v['dev_mints']}")
    stop_pct = (extra_pos or {}).get("stop_pct", EMERGENCY_STOP_PCT)
    exit_rule = (f"Haelfte bei {TP1_MULTIPLE:.0f}x; Rest raus, wenn Holder schrumpfen und "
                 f"Netto-Verkaeufer {THESIS_BREAK_CHECKS}x in Folge, Liquiditaet -{LIQ_DROP_EXIT_PCT:.0f}%, "
                 f"{stop_pct:.0f}%, nach 1,5x nicht unter Einstand, "
                 f"nach 2x 30 % vom Hoch (ab 10x 25 %)")
    if (extra_pos or {}).get("leiter"):                 # Experiment Drittel-Leiter
        stufen = " / ".join(f"{x:g}x" for x in extra_pos["leiter"]).replace(".", ",")
        exit_rule = f"Je ein Drittel bei {stufen}; sonst" + exit_rule.split(";", 1)[1]

    p["bankroll_sol"] = round(p["bankroll_sol"] - POSITION_SOL - TX_FEE_SOL, 6)
    pos = {"mint": v["mint"], "symbol": v["symbol"], "opened": time.time(),
           "invested_sol": POSITION_SOL, "fees_sol": TX_FEE_SOL,
           "entry_signal_usd": v["price"], "entry_fill_usd": fill_usd,
           "entry_slippage_pct": round(slippage, 2), "roundtrip_cost_pct": roundtrip,
           "tokens_initial": tokens, "tokens_left": tokens, "decimals": int(decimals),
           "proceeds_sol": 0.0, "peak_usd": fill_usd, "tp1_done": False,
           "thesis_breaks": 0, "missing_loops": 0, "entry_liquidity": v["liquidity"],
           "entry_view": {**{k: v.get(k) for k in ENTRY_FEATURES},
                          "hour_utc": datetime.now(timezone.utc).hour},
           "bundle": bundle, "phase": current_phase(), "thesis": thesis, "exit_rule": exit_rule,
           "mitlaeufer": v.get("mitlaeufer"), "solana_tracker": v.get("solana_tracker"),
           "graduated": v.get("graduated", False), "liq_low_checks": 0}
    pos.update(extra_pos or {})
    thesis, exit_rule = pos["thesis"], pos["exit_rule"]        # Experimente duerfen eigene Texte setzen
    b0 = _block0_cache.get(v["mint"]) if (bundle or {}).get("quelle") == "block0" else None
    if b0 and b0.get("bought"):
        top = sorted(b0["bought"].items(), key=lambda x: -x[1])[:FLUG_B0_MAX_WALLETS]
        pos["block0_flug"] = {"supply": b0["supply"], "bought": dict(top)}
    p["positions"][v["mint"]] = pos
    p["cooldown"][v["mint"]] = time.time()
    journal("KAUF", pos, fill_usd, POSITION_SOL)
    schedule_recheck("KAUF", v["symbol"], WSOL_MINT, v["mint"], lamports, raw_out, quoted_at)
    dex_vormerken("kauf", v)
    STATS["entries"].append({"symbol": v["symbol"], "roundtrip": roundtrip,
                             "mitlaeufer": bool(v.get("mitlaeufer"))})
    ml = v.get("mitlaeufer")
    ml_line = (f"**Mitlaeufer-Verdacht:** teilt \"{ml['teil']}\" mit {ml['leader']} "
               f"(${ml['leader_mcap']:,.0f}), nur zur Beobachtung\n") if ml else ""
    st = v.get("solana_tracker") or {}
    if "score" in st:
        fmt = lambda x: "?" if x is None else f"{x:.0f}%"
        ml_line += (f"**Solana Tracker:** Risiko {st['score']}/10, Sniper {fmt(st['snipers_pct'])}, "
                    f"Insider {fmt(st['insiders_pct'])}, Bundler {fmt(st['bundlers_pct'])} (nur Beobachtung)\n")
    discord(f"🎯 Kauf: {v['symbol']}",
            f"**These:** {thesis}\n**Verkauf wenn:** {exit_rule}\n"
            f"**Marktwert:** ${v['mcap']:,.0f} | **LP:** ${v['liquidity']:,.0f} | "
            f"**Alter:** {v['age_h']:.1f} h\n"
            f"**Einstieg:** {POSITION_SOL} SOL, Slippage {slippage:+.2f}%, "
            f"Hin+zurueck {roundtrip if roundtrip is not None else '?'}%\n"
            f"**Marktphase:** {pos['phase']} | **Bankroll frei:** {p['bankroll_sol']:.4f} SOL\n"
            + ml_line +
            f"https://jup.ag/tokens/{v['mint']}", 0x3B82F6, portfolio_embed(p, sol_usd))
    save_portfolio(p)
    return True


def sell(p, pos, fraction, price_usd, reason, sol_usd):
    """Verkauft einen Anteil der verbleibenden Token zum Jupiter-Kurs."""
    tokens = pos["tokens_left"] * fraction
    if tokens <= 0:
        return 0.0
    raw = int(tokens * (10 ** pos["decimals"]))
    lamports = quote(pos["mint"], WSOL_MINT, raw) if price_usd > 0 else 0
    quoted_at = time.time()
    notloesung = ""
    if lamports > 0:
        proceeds = lamports / 1e9
    else:
        proceeds = max(0.0, tokens * price_usd / sol_usd * 0.95) if price_usd > 0 else 0.0
        if price_usd > 0:
            notloesung = "1"                 # keine Quote: Kurs x 0,95 angenommen (wird gezaehlt)
            STATS["notloesung"] += 1
    proceeds = max(0.0, proceeds - TX_FEE_SOL)
    pos["tokens_left"] -= tokens
    pos["proceeds_sol"] += proceeds
    pos["fees_sol"] += TX_FEE_SOL
    p["bankroll_sol"] = round(p["bankroll_sol"] + proceeds, 6)
    journal("TEILVERKAUF" if pos["tokens_left"] > 1e-12 else "VERKAUF", pos, price_usd,
            proceeds, reason, notloesung=notloesung)
    schedule_recheck("VERKAUF", pos["symbol"], pos["mint"], WSOL_MINT, raw, lamports, quoted_at)
    return proceeds


def close_position(p, pos, price_usd, reason, sol_usd):
    sell(p, pos, 1.0, price_usd, reason, sol_usd)
    pnl = pos["proceeds_sol"] - pos["invested_sol"] - TX_FEE_SOL
    pnl_pct = pnl / pos["invested_sol"] * 100
    peak_x = pos["peak_usd"] / pos["entry_fill_usd"] if pos["entry_fill_usd"] else 0
    record = {k: pos[k] for k in ("symbol", "mint", "invested_sol", "entry_fill_usd",
                                  "entry_slippage_pct", "roundtrip_cost_pct", "tp1_done",
                                  "entry_view", "bundle", "phase", "thesis")}
    record["mitlaeufer"] = pos.get("mitlaeufer")
    record["solana_tracker"] = pos.get("solana_tracker")
    record["graduated_waehrend"] = pos.get("graduated_during", False)
    record.update({"proceeds_sol": round(pos["proceeds_sol"], 6), "pnl_sol": round(pnl, 6),
                   "pnl_pct": round(pnl_pct, 2), "peak_multiple": round(peak_x, 2),
                   "exit_usd": price_usd, "exit_reason": reason,
                   "hold_h": round((time.time() - pos["opened"]) / 3600, 2),
                   "closed_at": datetime.now(timezone.utc).isoformat()})
    record["runde"] = p.get("runde")
    for key in ("listing_boerse", "listing_id", "listing_ankuendigung", "listing_start"):   # Experiment Listing-Welle
        if key in pos:
            record[key] = pos[key]
    p["closed"].append(record)
    if CTX["watch"]:
        p.setdefault("watch", {})[pos["mint"]] = {
            "symbol": pos["symbol"], "entry_fill_usd": pos["entry_fill_usd"], "opened": pos["opened"],
            "peak_usd": pos["peak_usd"], "exit_usd": price_usd, "exit_reason": reason,
            "until": time.time() + WATCH_AFTER_EXIT_H * 3600}
    del p["positions"][pos["mint"]]
    journal("ERGEBNIS", pos, price_usd, pos["proceeds_sol"], reason, pnl, pnl_pct)
    STATS["exits"].append({"symbol": pos["symbol"], "pnl_sol": pnl, "pnl_pct": pnl_pct,
                           "reason": reason})
    discord(f"{'🟢' if pnl > 0 else '🔴'} Verkauf: {pos['symbol']}",
            f"**Grund:** {reason}\n**Ergebnis:** {pnl:+.4f} SOL ({pnl_pct:+.1f}%)\n"
            f"**Hoechststand:** {peak_x:.2f}x | **Teilverkauf bei 2x:** "
            f"{'ja' if pos['tp1_done'] else 'nein'}\n**These war:** {pos['thesis']}\n"
            f"**Bankroll frei:** {p['bankroll_sol']:.4f} SOL",
            0x10B981 if pnl > 0 else 0xEF4444, portfolio_embed(p, sol_usd))


def trail_pct(peak_multiple):
    for min_multiple, pct in TRAIL_TIERS:
        if peak_multiple >= min_multiple:
            return pct
    return TRAIL_TIERS[-1][1]


def manage_positions(p, sol_usd, now):
    loop = STATS["loops"]
    watch = p.setdefault("watch", {})
    shadow = p.setdefault("shadow", {})
    for store in (watch, shadow):
        for mint in [m for m, w in store.items() if now > w["until"]]:
            del store[mint]
    log_watch = loop % WATCH_LOG_EVERY_LOOPS == 0
    log_shadow = loop % NEAR_MISS_LOG_EVERY_LOOPS == 0
    wanted = list(p["positions"])
    if log_watch:
        wanted += [m for m in watch if m not in p["positions"]]
    if log_shadow:
        wanted += [m for m in shadow if m not in p["positions"] and m not in watch]
    if not wanted:
        return
    data = jup_tokens(wanted)
    for mint, pos in list(p["positions"].items()):
        tok = data.get(mint)
        if not tok:
            if mint in _jup_unanswered:
                continue                        # Jupiter hat nicht geantwortet: kein Hinweis auf einen toten Coin
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
        log_path("offen", mint, pos["symbol"], v, pos["entry_fill_usd"], pos["opened"],
                 pos["peak_usd"], pos["tp1_done"])
        try:
            flug_aufzeichnen(pos, v, now)
        except Interrupted:
            raise
        except Exception as err:                 # Aufzeichnung darf die Verwaltung nie stoppen
            print(f"[FLUGSCHREIBER] {str(err)[:100]}")
        multiple = price / pos["entry_fill_usd"]
        change_pct = (multiple - 1) * 100

        # Experiment Endspurt: eigene Verkaufsregeln, komplett raus bei der Graduation
        if pos.get("exit_mode") == "endspurt":
            vsol = curve_vsol(price, sol_usd)
            reason = None
            if v["graduated"]:
                reason = "GRADUIERT (Ziel erreicht, komplett raus)"
            elif change_pct <= EMERGENCY_STOP_PCT:
                reason = f"NOTBREMSE ({change_pct:+.0f}%)"
            elif vsol is not None and vsol < pos["entry_vsol"] - ENDSPURT_STOP_VSOL:
                reason = f"KURVE_ZURUECK (vSol {vsol:.0f} statt {pos['entry_vsol']:.0f})"
            elif now - pos["opened"] > ENDSPURT_MAX_MIN * 60:
                reason = f"ZEIT_STOP ({ENDSPURT_MAX_MIN} min ohne Graduation)"
            if reason:
                close_position(p, pos, price, reason, sol_usd)
            continue

        # Experiment Listing-Welle: Verkauf zum Handelsstart, sonst nach 72 h, Notbremse -40 %
        if pos.get("exit_mode") == "listing":
            start = pos.get("listing_start")
            reason = None
            if change_pct <= pos.get("stop_pct", EMERGENCY_STOP_PCT):
                reason = f"NOTBREMSE ({change_pct:+.0f}%)"
            elif start and now >= start:
                reason = "HANDELSSTART (Listing an der Boerse beginnt, komplett raus)"
            elif now - pos["opened"] > LISTING_MAX_HOLD_H * 3600:
                reason = f"ZEIT_STOP ({LISTING_MAX_HOLD_H} h ohne Handelsstart)"
            if reason:
                close_position(p, pos, price, reason, sol_usd)
            continue

        # Graduation: Umzug von der Bonding Curve in einen neuen Pool, kein Liquiditaetsabzug
        if v["graduated"] and not pos.get("graduated"):
            pos["graduated"] = pos["graduated_during"] = True
            pos["entry_liquidity"] = v["liquidity"]
            pos["liq_low_checks"] = 0
            STATS["graduations"] += 1
            journal("GRADUATION", pos, price, 0, "Umzug in neuen Pool, Liquiditaetsbasis neu gesetzt")
        liq_low = pos["entry_liquidity"] > 0 and \
            v["liquidity"] < pos["entry_liquidity"] * (1 - LIQ_DROP_EXIT_PCT / 100)
        pos["liq_low_checks"] = pos.get("liq_low_checks", 0) + 1 if liq_low else 0

        # Experiment Drittel-Leiter: Stufen statt "Haelfte bei 2x" (hoechstens eine Stufe je Durchlauf)
        leiter = pos.get("leiter")
        if leiter:
            stufe = pos.get("leiter_stufe", 0)
            if stufe < len(leiter) and multiple >= leiter[stufe]:
                grund = f"DRITTEL_BEI_{leiter[stufe]:g}X".replace(".", ",")
                if stufe == len(leiter) - 1:
                    close_position(p, pos, price, grund + " (alles verkauft)", sol_usd)
                    continue
                got = sell(p, pos, 1 / (len(leiter) - stufe), price, grund, sol_usd)
                pos["leiter_stufe"] = stufe + 1
                if leiter[stufe] >= TP1_MULTIPLE:
                    pos["tp1_done"] = True               # ab der 2x-Stufe: Abstand zum Hoch wie Tag 4
                STATS["partials"].append({"symbol": pos["symbol"], "sol": got})
                continue

        # Tag 2: Gewinne mitnehmen
        elif not pos["tp1_done"] and multiple >= TP1_MULTIPLE:
            got = sell(p, pos, TP1_SELL_FRACTION, price, f"HAELFTE_BEI_{TP1_MULTIPLE:.0f}X", sol_usd)
            pos["tp1_done"] = True
            STATS["partials"].append({"symbol": pos["symbol"], "sol": got})
            discord(f"💰 Haelfte verkauft: {pos['symbol']}",
                    f"Bei {multiple:.2f}x die Haelfte fuer {got:.4f} SOL verkauft. "
                    f"Der Rest laeuft weiter, solange die Story waechst.", 0xF59E0B,
                    portfolio_embed(p, sol_usd))
            continue

        # Tag 3: These pruefen (im Takt der Jupiter-Daten, nicht bei jeder Kurspruefung)
        if loop % THESIS_EVERY_LOOPS == 0:
            thesis_ok = not (v["holder_growth_1h"] < 0 and v["net_buyers_5m"] <= 0)
            pos["thesis_breaks"] = 0 if thesis_ok else pos["thesis_breaks"] + 1

        reason = None
        if change_pct <= pos.get("stop_pct", EMERGENCY_STOP_PCT):    # Experiment Notbremse 25: eigene Grenze
            reason = f"NOTBREMSE ({change_pct:+.0f}%)"
        elif pos.get("dev_exit") and pos.get("dev_pct_kauf", 0) > 0.5 \
                and v["dev_balance_pct"] < pos["dev_pct_kauf"] * SERIEN_DEV_EXIT_ANTEIL:   # Experiment Serien-Devs
            reason = f"DEV_VERKAUFT ({pos['dev_pct_kauf']:.1f}% -> {v['dev_balance_pct']:.1f}%)"
        elif pos["liq_low_checks"] >= LIQ_CONFIRM_CHECKS:
            reason = "LIQUIDITAET_ABGEZOGEN"
        elif pos["thesis_breaks"] >= THESIS_BREAK_CHECKS:
            reason = "THESE_GEBROCHEN (Holder schrumpfen, Netto-Verkaeufer)"
        elif (not pos["tp1_done"] and pos["peak_usd"] / pos["entry_fill_usd"] >= PROTECT_AT_MULTIPLE
              and multiple <= PROTECT_FLOOR_MULTIPLE):
            reason = (f"GEWINN_GESCHUETZT (Hoch {pos['peak_usd'] / pos['entry_fill_usd']:.1f}x, "
                      f"zurueck auf Einstand)")
        elif pos["tp1_done"]:
            peak_x = pos["peak_usd"] / pos["entry_fill_usd"]
            trail = trail_pct(peak_x)
            if price <= pos["peak_usd"] * (1 - trail / 100):                          # Tag 4
                reason = f"STORY_ABGEKUEHLT ({trail:.0f}% unter dem Hoch von {peak_x:.1f}x)"
        if reason is None and now - pos["opened"] > MAX_HOLD_H * 3600:
            reason = "MAX_HALTEDAUER"
        if reason:
            close_position(p, pos, price, reason, sol_usd)

    # Nach dem Verkauf: nur aufzeichnen, nicht handeln
    for mint, w in list(watch.items()) if log_watch else []:
        if mint in p["positions"] or mint not in data:
            continue
        v = token_view(data[mint], now)
        if v["price"] > 0:
            w["peak_usd"] = max(w["peak_usd"], v["price"])
            log_path("nach_verkauf", mint, w["symbol"], v, w["entry_fill_usd"], w["opened"],
                     w["peak_usd"], True)

    # Knapp abgelehnt: nur aufzeichnen, Vielfaches bezogen auf den Kurs bei der Ablehnung
    for mint, s in list(shadow.items()) if log_shadow else []:
        if mint in p["positions"] or mint in watch or mint not in data:
            continue
        v = token_view(data[mint], now)
        if v["price"] > 0:
            s["peak_usd"] = max(s["peak_usd"], v["price"])
            log_path("abgelehnt_" + s["reason"], mint, s["symbol"], v, s["ref_price"], s["since"],
                     s["peak_usd"], False)
    save_portfolio(p)


# ================================================================ Scan

def scan(p, sol_usd, now, exps=None):
    phase = current_phase()
    slots = MAX_POSITIONS.get(phase, 2) - len(p["positions"])          # Tag 9
    if p["bankroll_sol"] < POSITION_SOL + TX_FEE_SOL:
        slots = 0

    seen, sources = {}, {}
    for (category, interval), short in CANDIDATE_LISTS.items():
        for tok in jup_category(category, interval, 100):
            mint = tok.get("id")
            if mint and mint not in IGNORED_MINTS:
                seen[mint] = tok
                sources.setdefault(mint, set()).add(short)
    views = []
    for tok in seen.values():
        v = token_view(tok, now)
        v["quelle"] = "+".join(sorted(sources[v["mint"]]))
        views.append(v)
        if v["age_h"] is not None and MIN_AGE_MIN / 60 <= v["age_h"] <= MAX_AGE_H:
            for short in sources[v["mint"]]:          # Statistik: junge Kandidaten je Liste
                STATS["young_by_list"].setdefault(short, set()).add(v["mint"])
    update_symbol_leaders(views, now)
    update_narrative_leaders(views, now)
    for name, with_filters in (("endspurt", True), ("endspurt_ohne_filter", False)):
        if exps and name in exps and name not in EXP_BEENDET:
            try:
                with experiment(name):
                    endspurt_picks(exps[name], views, sol_usd, now, with_filters)
            except Exception as err:
                EXP_STATS[name]["exp_errors"] += 1
                EXP_STATS[name]["last_error"] = str(err)
                print(f"[EXPERIMENT {name}] {err}")
    if exps and "kontrollgruppe" in exps:
        try:
            with experiment("kontrollgruppe"):
                control_group_pick(exps["kontrollgruppe"], views, sol_usd, now)
        except Exception as err:
            EXP_STATS["kontrollgruppe"]["exp_errors"] += 1
            EXP_STATS["kontrollgruppe"]["last_error"] = str(err)
            print(f"[EXPERIMENT kontrollgruppe] {err}")

    exps_alle = exps or {}
    e5 = exps_alle.get("offene_tuer") if "offene_tuer" not in EXP_BEENDET else None
    e6 = exps_alle.get("serien_devs") if "serien_devs" not in EXP_BEENDET else None
    if e6 is not None:
        try:
            serien_devs_merken(views, now)
        except Exception as err:
            print(f"[EXPERIMENT serien_devs] Liste: {err}")
    for v in views if (e5 is not None or e6 is not None) else []:
        try:                                     # Experimente duerfen die Hauptstrategie nie aufhalten
            if e5 is not None and len(e5["positions"]) < OFFENE_TUER_MAX_POSITIONS and exp_can_buy(e5, v, now) \
                    and quick_checks(v, ohne_sicherheit=True) is None:
                exp_buy("offene_tuer", e5, v, {"quelle": "experiment", "text":
                        "Offene Tuer: ohne Sicherheits-, Bundle- und Dev-Pruefung"}, sol_usd)
            if e6 is not None and len(e6["positions"]) < SERIEN_MAX_POSITIONS and exp_can_buy(e6, v, now):
                vorgaenger = serien_dev_vorgaenger(v)
                if vorgaenger:
                    exp_buy("serien_devs", e6, v, {"quelle": "experiment", "text":
                            f"Serien-Dev: frueherer Coin {vorgaenger['symbol']} bis {vorgaenger['peak']:,.0f} $"},
                            sol_usd, extra_pos={"dev_exit": True, "dev_pct_kauf": v["dev_balance_pct"],
                                                "serien_vorgaenger": vorgaenger})
        except Interrupted:
            raise
        except Exception as err:
            print(f"[EXPERIMENT offene_tuer/serien_devs] {v.get('symbol')}: {str(err)[:100]}")

    e7 = exps_alle.get("grosse_coins") if "grosse_coins" not in EXP_BEENDET else None
    for v in views if e7 is not None else []:
        try:
            grosse_coins_pick(e7, v, phase, sol_usd, now)
        except Interrupted:
            raise
        except Exception as err:
            EXP_STATS["grosse_coins"]["exp_errors"] += 1
            EXP_STATS["grosse_coins"]["last_error"] = str(err)
            print(f"[EXPERIMENT grosse_coins] {v.get('symbol')}: {str(err)[:100]}")

    passed = []
    for v in views:
        if v["mint"] in p["positions"] or now - p["cooldown"].get(v["mint"], 0) < 24 * 3600:
            continue
        reason = quick_checks(v)
        if reason:
            log_reject(v, reason)
            track_near_miss(p, v, reason, now)
            continue
        passed.append(v)

    # Staerkste Verbreitung zuerst
    passed.sort(key=lambda x: x["holder_growth_1h"], reverse=True)
    exps = exps or {}
    e2 = exps.get("heisse_coins") if "heisse_coins" not in EXP_BEENDET else None
    e3 = exps.get("ohne_limit") if "ohne_limit" not in EXP_BEENDET else None
    e4 = exps.get("notbremse_25") if "notbremse_25" not in EXP_BEENDET else None
    e8 = exps.get("drittel_leiter") if "drittel_leiter" not in EXP_BEENDET else None
    for v in passed:
        main_slot = slots > 0
        e2_ok = e2 is not None and exp_can_buy(e2, v, now, MAX_POSITIONS.get(phase, 2))
        e3_ok = e3 is not None and exp_can_buy(e3, v, now)
        if not (main_slot or e2_ok or e3_ok):
            # Niemand hat Platz: nicht kaufen, aber beobachten (ohne teuren Bundle-Check)
            log_reject(v, "KEIN_PLATZ")
            track_near_miss(p, v, "KEIN_PLATZ", now)
            continue
        if REQUIRE_SOCIAL_LINK and not has_social(v):
            log_reject(v, "KEINE_STORY_LINKS")
            continue
        reason = safety_shield(v["mint"])
        if reason:
            log_reject(v, reason)
            continue
        reason, bundle = bundle_dev_check(v["mint"])
        if reason == "BUNDLE_CHECK_NICHT_MOEGLICH" and e2_ok:        # Experiment Heisse Coins
            exp_buy("heisse_coins", e2, v, {"quelle": "experiment", "text":
                    "Bundle-Check nicht moeglich (zu viele Transaktionen), trotzdem gekauft"}, sol_usd)
        if reason:
            log_reject(v, reason)
            track_near_miss(p, v, reason, now, bundle)
            continue
        if e3_ok:                                                      # Experiment Ohne Limit
            exp_buy("ohne_limit", e3, v, bundle, sol_usd)
        if not main_slot:
            log_reject(v, "KEIN_PLATZ")
            track_near_miss(p, v, "KEIN_PLATZ", now, {"alle_pruefungen": True})
            continue
        v["mitlaeufer"] = follower_of(v, now)
        v["solana_tracker"] = solana_tracker_risk(p, v["mint"])   # nur Beobachtung
        if open_position(p, v, bundle, sol_usd):
            slots -= 1
            if e4 is not None and exp_can_buy(e4, v, now):            # Experiment Notbremse 25: gleicher Kauf
                exp_buy("notbremse_25", e4, v, bundle, sol_usd, extra_pos={"stop_pct": NOTBREMSE_25_PCT})
            if e8 is not None and exp_can_buy(e8, v, now):            # Experiment Drittel-Leiter: gleicher Kauf
                exp_buy("drittel_leiter", e8, v, bundle, sol_usd, extra_pos={"leiter": list(DRITTEL_LEITER),
                                                                             "leiter_stufe": 0})


# ================================================================ Experimente

def load_experiments():
    """Laedt die Experiment-Konten. Ein kaputtes Experiment fehlt einfach, die Hauptstrategie laeuft weiter."""
    exps = {}
    for name in EXPERIMENTS:
        try:
            with experiment(name):
                exps[name] = load_portfolio()
        except Exception as err:
            EXP_STATS[name]["exp_errors"] += 1
            EXP_STATS[name]["last_error"] = str(err)
            print(f"[EXPERIMENT {name}] {err}")
    return exps


def grosse_coins_pick(ep, v, phase, sol_usd, now):
    """Experiment Grosse Coins: wie die Hauptstrategie, nur Marktwert ueber statt unter MAX_MCAP_USD."""
    if v["mcap"] <= MAX_MCAP_USD or not exp_can_buy(ep, v, now, MAX_POSITIONS.get(phase, 2)):
        return
    if quick_checks({**v, "mcap": MAX_MCAP_USD}) is not None:    # alle Schnellpruefungen ausser der Marktwert-Grenze
        return
    if REQUIRE_SOCIAL_LINK and not has_social(v):
        return
    if safety_shield(v["mint"]):
        return
    reason, bundle = bundle_dev_check(v["mint"])
    if reason:
        return
    v = dict(v, mitlaeufer=follower_of(v, now))                  # nur Beobachtung, wie Hauptstrategie
    exp_buy("grosse_coins", ep, v, bundle, sol_usd)


def exp_can_buy(ep, v, now, limit=None):
    return (v["mint"] not in ep["positions"]
            and now - ep["cooldown"].get(v["mint"], 0) >= 24 * 3600
            and ep["bankroll_sol"] >= POSITION_SOL + TX_FEE_SOL
            and (limit is None or len(ep["positions"]) < limit))


def _serien_devs_laden():
    try:
        with open(SERIEN_DEVS_FILE, encoding="utf-8") as f:
            daten = json.load(f)
        return daten if isinstance(daten, dict) else {}
    except (OSError, ValueError):
        return {}


_serien_devs = {"daten": None}


def serien_devs_merken(views, now):
    """Devs merken, deren Coin mindestens SERIEN_MIN_PEAK_MCAP Marktwert erreicht (hoechster gesehener Wert)."""
    devs = _serien_devs["daten"]
    if devs is None:
        devs = _serien_devs["daten"] = _serien_devs_laden()
    geaendert = False
    for v in views:
        dev = v.get("dev")
        if not dev or v["mcap"] < SERIEN_MIN_PEAK_MCAP:
            continue
        coins = devs.setdefault(dev, {})
        alt = coins.get(v["mint"])
        if not alt or v["mcap"] > alt["peak"]:
            coins[v["mint"]] = {"symbol": v["symbol"], "peak": round(v["mcap"]),
                                "zuerst": alt["zuerst"] if alt else int(now)}
            geaendert = True
    if geaendert:
        if len(devs) > SERIEN_DEVS_MAX:
            aelteste = sorted(devs, key=lambda d: min(c["zuerst"] for c in devs[d].values()))
            for d in aelteste[:len(devs) - SERIEN_DEVS_MAX]:
                del devs[d]
        os.makedirs(os.path.dirname(SERIEN_DEVS_FILE), exist_ok=True)
        tmp = SERIEN_DEVS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(devs, f)
        os.replace(tmp, SERIEN_DEVS_FILE)


def serien_dev_vorgaenger(v):
    """Frueherer starker Coin desselben Devs (nicht dieser Coin), sonst None. Nur junge, handelbare Coins."""
    devs = _serien_devs["daten"] or {}
    coins = devs.get(v.get("dev") or "", {})
    andere = [dict(c, mint=m) for m, c in coins.items() if m != v["mint"]]
    if not andere or v["age_h"] is None or not (MIN_AGE_MIN / 60 <= v["age_h"] <= MAX_AGE_H) \
            or v["price"] <= 0 or v["liquidity"] < MIN_LIQUIDITY_USD:
        return None
    return max(andere, key=lambda c: c["peak"])


def exp_buy(name, ep, v, bundle, sol_usd, extra_pos=None):
    try:
        with experiment(name):
            open_position(ep, dict(v), dict(bundle), sol_usd, extra_pos=extra_pos)
    except Exception as err:
        EXP_STATS[name]["exp_errors"] += 1
        EXP_STATS[name]["last_error"] = str(err)
        print(f"[EXPERIMENT {name}] Kauf {v.get('symbol')}: {err}")


def second_wave_entries(p, ep, sol_usd, now):
    """Experiment Zweite Welle: Die Hauptstrategie ist per Notbremse raus, der Coin steigt innerhalb
    der Beobachtungszeit wieder ueber ihren Einstiegskurs -> erneut kaufen."""
    candidates = {m: w for m, w in p.get("watch", {}).items()
                  if str(w.get("exit_reason", "")).startswith("NOTBREMSE")}
    if not candidates:
        return
    data = jup_tokens(list(candidates))
    for mint, w in candidates.items():
        if mint not in data:
            continue
        v = token_view(data[mint], now)
        if v["price"] >= w["entry_fill_usd"] and exp_can_buy(ep, v, now):
            v["quelle"] = "zweite_welle"
            open_position(ep, v, {"quelle": "experiment", "text":
                                  f"Zweite Welle: zurueck ueber dem Einstieg der Hauptstrategie "
                                  f"({w['exit_reason']})"}, sol_usd)


def control_safe(v):
    """Kontrollgruppe: nur Sicherheit und dasselbe Altersfenster, keine Filter der Strategie."""
    return (v["age_h"] is not None and MIN_AGE_MIN / 60 <= v["age_h"] <= MAX_AGE_H
            and v["price"] > 0 and v["liquidity"] >= MIN_LIQUIDITY_USD
            and norm_symbol(v["symbol"]) not in IMPERSONATION_SYMBOLS
            and v["mint_disabled"] is not False and v["freeze_disabled"] is not False and not v["is_sus"])


def control_group_pick(ep, views, sol_usd, now):
    """Experiment Kontrollgruppe: etwa alle 30 min einen zufaelligen sicheren jungen Coin kaufen.
    Beantwortet, ob die Filter der Strategie besser sind als Zufall."""
    if now < ep.get("next_pick", 0):
        return
    pool = [v for v in views if control_safe(v) and exp_can_buy(ep, v, now)]
    random.shuffle(pool)
    for v in pool[:3]:
        if safety_shield(v["mint"]):
            continue
        if open_position(ep, dict(v), {"quelle": "experiment", "text":
                         f"Kontrollgruppe: zufaellig aus {len(pool)} sicheren jungen Coins"}, sol_usd):
            ep["next_pick"] = now + KONTROLL_INTERVAL_MIN * 60
            save_portfolio(ep)          # sofort sichern, sonst geht der Zeitpunkt beim Neuladen verloren
            return


def _listing_iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if ts else ""


def _listing_csv(path, header, row):
    """Eine Zeile anhaengen (Kopfzeile beim ersten Mal). Fremder Text: Zeilenumbrueche raus."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    ensure_csv_columns(path, header)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow([re.sub(r"[\r\n\t]+", " ", str(row.get(k, ""))).strip()[:300] for k in header])


def listing_get(url):
    res = SESSION.get(url, timeout=15)
    res.raise_for_status()
    return res.content


def listing_token(symbol, braucht_verifiziert):
    """Solana-Token zum Boersen-Ticker ueber Jupiter. Rueckgabe (token, None) oder (None, Grund).
    Nur genau gleicher Ticker, genug Liquiditaet und ein eindeutiger Treffer. Ohne Netzwerk-Angabe der Boerse
    (Binance, Coinbase) muss der Token bei Jupiter als verifiziert gelten: sonst koennte ein fremder Coin mit
    demselben Ticker gemeint sein."""
    if not re.fullmatch(r"[A-Z0-9]{2,12}", symbol or ""):
        return None, "kein_gueltiger_ticker"
    data = jup_get(f"/tokens/v2/search?query={symbol}")
    if not isinstance(data, list):
        return None, "jupiter_keine_antwort"
    treffer = sorted((t for t in data if str(t.get("symbol", "")).upper() == symbol and t.get("id")
                      and as_float(t.get("liquidity")) >= LISTING_MIN_LIQ_NEBEN_USD),
                     key=lambda t: -as_float(t.get("liquidity")))
    if not treffer:
        return None, "kein_solana_token"
    best = treffer[0]
    best_liq = as_float(best.get("liquidity"))
    if best_liq < LISTING_MIN_LIQ_USD:
        return None, "zu_wenig_liquiditaet"
    if len(treffer) > 1 and as_float(treffer[1].get("liquidity")) >= best_liq * LISTING_MEHRDEUTIG_ANTEIL:
        return None, "mehrdeutig"
    if braucht_verifiziert and not (best.get("isVerified") or "verified" in (best.get("tags") or [])):
        return None, "nicht_verifiziert"
    return best, None


def listing_ereignis(ep, ev, sol_usd, now):
    """Eine Boersen-Meldung verarbeiten: je Coin entscheiden (kaufen oder Grund), alles in ereignisse.csv."""
    st = ep.setdefault("listing", {})
    for coin in ev.get("coins", []):
        sym, netz, start = coin.get("symbol", ""), coin.get("netzwerk", ""), coin.get("start")
        row = {"zeit_erfasst": _listing_iso(now), "typ": "ankuendigung", "ereignis_id": ev["id"],
               "boerse": ev["boerse"], "quelle_typ": ev["quelle_typ"], "art": ev["art"], "symbol": sym,
               "titel": ev["titel"], "ankuendigung_zeit": _listing_iso(ev["zeit"]),
               "handelsstart_zeit": _listing_iso(start), "url": ev.get("url", "")}
        if ev["art"] == "listing":
            off = st.setdefault("offiziell", {})
            off[sym] = ev["zeit"]
            for k in sorted(off, key=off.get)[:-500]:
                del off[k]
        try:
            if ev["art"] != "listing":
                row["entscheidung"] = ev["art"]
            elif ev["quelle_typ"] == "handelsstart":
                row["entscheidung"] = "nur_aufzeichnung"        # ein neuer Markt ist schon der Handelsstart
                tok, _ = listing_token(sym, braucht_verifiziert=True)
                if tok is not None:                              # Token gefunden: Kursanstieg davor mitschreiben
                    v = token_view(tok, now)
                    vor = listings.kurs_vorlauf(listing_get, v["mint"], ev["zeit"])
                    row.update(mint=v["mint"], kurs_usd=f"{v['price']:.12g}", liquiditaet_usd=round(v["liquidity"]))
                    for k in ("anstieg_3h_pct", "anstieg_3d_pct"):
                        row[k] = "" if vor[k] is None else vor[k]
            elif now - ev["zeit"] > LISTING_MAX_ALTER_SEC:
                row["entscheidung"] = "zu_alt"
            elif netz and "solana" not in netz.lower():
                row["entscheidung"] = "anderes_netzwerk"
            elif start and start - now < LISTING_MIN_START_SEC:
                row["entscheidung"] = "start_zu_nah"
            else:
                _listing_kauf(ep, ev, coin, row, sol_usd, now)
        except Interrupted:
            raise
        except Exception as err:
            row["entscheidung"] = "fehler"
            STATS["exp_errors"] += 1
            STATS["last_error"] = str(err)
            print(f"[EXPERIMENT listing_welle] {sym}: {str(err)[:100]}")
        _listing_csv(LISTING_EREIGNISSE_FILE, LISTING_EREIGNISSE_HEADER, row)


def _listing_kauf(ep, ev, coin, row, sol_usd, now):
    sym, netz, start = coin["symbol"], coin.get("netzwerk", ""), coin.get("start")
    tok, grund = listing_token(sym, braucht_verifiziert=not netz)
    if tok is None:
        row["entscheidung"] = grund
        return
    v = token_view(tok, now)
    row.update(mint=v["mint"], kurs_usd=f"{v['price']:.12g}", liquiditaet_usd=round(v["liquidity"]))
    if v["price"] <= 0:
        row["entscheidung"] = "kein_kurs"
        return
    if not exp_can_buy(ep, v, now, LISTING_MAX_POSITIONS):
        row["entscheidung"] = "kein_platz_oder_geld"
        return
    vor = listings.kurs_vorlauf(listing_get, v["mint"], ev["zeit"])
    h3, d3 = vor["anstieg_3h_pct"], vor["anstieg_3d_pct"]
    row.update(anstieg_3h_pct="" if h3 is None else h3, anstieg_3d_pct="" if d3 is None else d3)
    start_txt = f"Handelsstart {_listing_iso(start)} UTC" if start else "Handelsstart noch offen"
    extra = {"exit_mode": "listing", "listing_boerse": ev["boerse"], "listing_id": ev["id"],
             "listing_ankuendigung": ev["zeit"], "listing_start": start,
             "thesis": f"{ev['boerse']}-Listing angekuendigt ({start_txt}); Anstieg davor: "
                       f"3 h {'?' if h3 is None else f'{h3:+.0f} %'}, 3 Tage {'?' if d3 is None else f'{d3:+.0f} %'}",
             "exit_rule": f"Komplett zum Handelsstart, sonst nach {LISTING_MAX_HOLD_H} h; "
                          f"Notbremse {EMERGENCY_STOP_PCT:.0f} %"}
    ok = open_position(ep, dict(v, quelle="listing"),
                       {"quelle": "experiment", "text": f"Listing-Welle: {ev['boerse']}"}, sol_usd, extra_pos=extra)
    row["entscheidung"] = "gekauft" if ok else "kauf_fehlgeschlagen"
    if ok:
        save_portfolio(ep)


def _listing_quelle(st, name, ok, err=""):
    q = st.setdefault("quellen", {}).setdefault(name, {"ok": 0, "fehler": 0, "letzter_fehler": ""})
    q["ok" if ok else "fehler"] += 1
    if not ok:
        q["letzter_fehler"] = str(err)[:100]


def listing_geruechte(ep, now, items=None):
    """Nachrichten ueber moegliche Listings nur aufzeichnen (geruechte.csv), nie handeln."""
    st = ep.setdefault("listing", {})
    if items is None:
        try:
            items, fehler = listings.hole_news(listing_get)
            for f in fehler:
                _listing_quelle(st, "RSS " + f.split(":")[0], False, f)
            _listing_quelle(st, "RSS", bool(items), "keine Nachrichten")
        except Interrupted:
            raise
        except Exception as err:
            _listing_quelle(st, "RSS", False, err)
            return
    gesehen = st.setdefault("rss_gesehen", [])
    off = st.get("offiziell", {})
    for it in items:
        key = it.get("link") or it["titel"]
        if key in gesehen or now - it["zeit"] > LISTING_GERUECHT_MAX_ALTER_H * 3600 or not listings.ist_geruecht(it):
            continue
        gesehen.append(key)
        for coin in listings.ticker_in_text(f"{it['titel']} {it['anriss']}")[:3]:
            _listing_csv(LISTING_GERUECHTE_FILE, LISTING_GERUECHTE_HEADER, {
                "zeit_erfasst": _listing_iso(now), "nachricht_zeit": _listing_iso(it["zeit"]), "coin": coin,
                "quelle": it["quelle"], "titel": it["titel"][:200], "link": it["link"],
                "offiziell_vorher": "ja" if off.get(coin, now + 1) <= now else "nein"})
    del gesehen[:-600]


def listing_welle_schritt(ep, sol_usd, now):
    """Wird in jedem Durchlauf aufgerufen; die Abfragen selbst laufen nach Zeitplan (Upbit alle 2 min)."""
    st = ep.setdefault("listing", {})
    ereignisse = []
    if LISTING_UPBIT_ANKUENDIGUNG and now >= st.get("next_upbit", 0):
        st["next_upbit"] = now + LISTING_POLL_SEC
        try:
            gesehen = set(st.get("upbit", []))
            ereignisse += listings.upbit_ereignisse(listing_get, gesehen)
            st["upbit"] = sorted(gesehen, key=lambda s: int(s.split(":")[1]))[-300:]
            _listing_quelle(st, "Upbit", True)
        except Interrupted:
            raise
        except Exception as err:
            _listing_quelle(st, "Upbit", False, err)
    if now >= st.get("next_listen", 0):
        st["next_listen"] = now + LISTING_LISTEN_POLL_SEC
        for name, key, fn, als_dict in (("Binance", "binance", listings.binance_ereignisse, False),
                                        ("Upbit-Markt", "upbit_markt", listings.upbit_markt_ereignisse, False),
                                        ("Coinbase", "coinbase", listings.coinbase_ereignisse, True),
                                        ("Bithumb", "bithumb", listings.bithumb_ereignisse, False)):
            try:
                bekannt = dict(st.get(key, {})) if als_dict else set(st.get(key, []))
                ereignisse += fn(listing_get, bekannt)
                st[key] = bekannt if als_dict else sorted(bekannt)
                _listing_quelle(st, name, True)
            except Interrupted:
                raise
            except Exception as err:
                _listing_quelle(st, name, False, err)
        _listing_starts_nachtragen(ep, now)
    for ev in ereignisse:
        try:
            listing_ereignis(ep, ev, sol_usd, now)
        except Interrupted:
            raise
        except Exception as err:                 # ein Ereignis darf die anderen nicht mitreissen
            STATS["exp_errors"] += 1
            STATS["last_error"] = str(err)
            print(f"[EXPERIMENT listing_welle] {ev.get('id')}: {str(err)[:100]}")
    if now >= st.get("next_news", 0):
        st["next_news"] = now + LISTING_NEWS_POLL_SEC
        listing_geruechte(ep, now)


def _listing_starts_nachtragen(ep, now):
    """Binance/Coinbase nennen keinen Starttermin: Der Start ist, wenn das Paar voll handelbar wird."""
    offen = [x for x in ep["positions"].values()
             if x.get("exit_mode") == "listing" and not x.get("listing_start")
             and x.get("listing_boerse") in ("Binance", "Coinbase")]
    if not offen:
        return
    cb_basen = {x["symbol"].upper() for x in offen if x["listing_boerse"] == "Coinbase"}
    bn_basen = {x["symbol"].upper() for x in offen if x["listing_boerse"] == "Binance"}
    jetzt_offen = {("Coinbase", b) for b in listings.coinbase_offen(listing_get, cb_basen)} if cb_basen else set()
    jetzt_offen |= {("Binance", b) for b in listings.binance_offen(listing_get, bn_basen)} if bn_basen else set()
    for pos in offen:
        if (pos["listing_boerse"], pos["symbol"].upper()) in jetzt_offen:
            pos["listing_start"] = now
            _listing_csv(LISTING_EREIGNISSE_FILE, LISTING_EREIGNISSE_HEADER, {
                "zeit_erfasst": _listing_iso(now), "typ": "handelsstart", "ereignis_id": pos.get("listing_id", ""),
                "boerse": pos["listing_boerse"], "symbol": pos["symbol"], "mint": pos["mint"],
                "ankuendigung_zeit": _listing_iso(pos.get("listing_ankuendigung")), "handelsstart_zeit": _listing_iso(now)})


def save_experiments(exps):
    for name, ep in exps.items():
        try:
            with experiment(name):
                save_portfolio(ep)
        except Exception as err:
            EXP_STATS[name]["exp_errors"] += 1
            EXP_STATS[name]["last_error"] = str(err)
            print(f"[EXPERIMENT {name}] Speichern: {err}")


def curve_vsol(price_usd, sol_usd):
    """Virtuelle SOL-Reserven der Pump.fun-Kurve aus dem Preis: Preis in SOL = vSol^2 / K."""
    if price_usd <= 0 or sol_usd <= 0:
        return None
    return math.sqrt(price_usd / sol_usd * PUMP_K)


def endspurt_candidate(v, sol_usd):
    """vSol, wenn der Coin im Endspurt-Fenster auf der Pump.fun-Kurve steht und sicher ist, sonst None."""
    if v.get("launchpad") != "pump.fun" or v.get("graduated"):
        return None
    vsol = curve_vsol(v["price"], sol_usd)
    if vsol is None or not ENDSPURT_VSOL_MIN <= vsol <= ENDSPURT_VSOL_MAX:
        return None
    if v["mint_disabled"] is False or v["freeze_disabled"] is False or v["is_sus"] \
            or norm_symbol(v["symbol"]) in IMPERSONATION_SYMBOLS:
        return None
    return vsol


def endspurt_filters_ok(v):
    """Filter der Variante 'Endspurt viele Trades' (seit 01.10.): mindestens 2.000 Trades seit Start."""
    return v["trades_24h"] >= ENDSPURT_MIN_TRADES


def endspurt_picks(ep, views, sol_usd, now, with_filters):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    devs = ep.setdefault("dev_day", {})
    if devs.get("date") != today:
        devs.clear()
        devs.update(date=today, devs=[])
    cands = [(endspurt_candidate(v, sol_usd), v) for v in views]
    for vsol, v in sorted(((s, v) for s, v in cands if s), key=lambda c: -c[0]):
        if len(ep["positions"]) >= ENDSPURT_MAX_POSITIONS:
            break
        if not exp_can_buy(ep, v, now) or (v.get("dev") and v["dev"] in devs["devs"]):
            continue
        if with_filters and not endspurt_filters_ok(v):
            continue
        if safety_shield(v["mint"]):
            continue
        text = (f"Endspurt: Kurve bei {vsol:.0f} von {PUMP_GRADUATION_VSOL} vSol "
                f"({(vsol - 30) / (PUMP_GRADUATION_VSOL - 30) * 100:.0f}% Fortschritt), "
                f"{v['trades_24h']} Trades, organisch {v['organic_label'] or '?'}")
        if open_position(ep, dict(v), {"quelle": "experiment", "text": text}, sol_usd,
                         max_slippage_pct=ENDSPURT_MAX_SLIPPAGE_PCT,
                         extra_pos={"exit_mode": "endspurt", "entry_vsol": round(vsol, 2)}):
            if v.get("dev"):
                devs["devs"].append(v["dev"])
            save_portfolio(ep)


def check_reset(ep):
    """Konto aufgebraucht: neue Runde mit 10 SOL. Die alten Trades bleiben mit ihrer Rundennummer erhalten."""
    if not ep["positions"] and ep["bankroll_sol"] < POSITION_SOL + TX_FEE_SOL:
        ep["runde"] = ep.get("runde", 1) + 1
        ep["bankroll_sol"] = START_BANKROLL_SOL
        STATS["resets"] += 1
        discord("♻️ Konto aufgebraucht - Neustart", f"Runde {ep['runde']} beginnt mit "
                f"{START_BANKROLL_SOL:.0f} SOL.", 0x8B5CF6)


def manage_experiments(p, exps, sol_usd, now):
    for name, ep in exps.items():
        try:
            with experiment(name):
                manage_positions(ep, sol_usd, now)
                if name == "listing_welle" and name not in EXP_BEENDET:
                    listing_welle_schritt(ep, sol_usd, now)
                if name == "zweite_welle" and STATS["loops"] % WATCH_LOG_EVERY_LOOPS == 0:
                    second_wave_entries(p, ep, sol_usd, now)
                if name not in EXP_BEENDET:              # beendet: keine neue Runde mehr
                    check_reset(ep)
                save_portfolio(ep)
        except Exception as err:
            EXP_STATS[name]["exp_errors"] += 1
            EXP_STATS[name]["last_error"] = str(err)
            print(f"[EXPERIMENT {name}] {err}")


def listing_quellen_text(ep):
    """Endmeldung: wie viele Abfragen je Quelle gelungen sind (zeigt z. B. eine gesperrte Quelle)."""
    q = (ep.get("listing") or {}).get("quellen") or {}
    teile = []
    for name, v in q.items():
        if name.startswith("RSS "):
            continue
        gesamt = v["ok"] + v["fehler"]
        teile.append(f"{name} {v['ok']}/{gesamt}" + (f" (zuletzt: {v['letzter_fehler'][:40]})" if v["fehler"] and not v["ok"] else ""))
    return f" | Listing-Quellen gesamt: {', '.join(teile)}" if teile else ""


def experiment_lines():
    lines = []
    for name, title in EXPERIMENTS.items():
        s = EXP_STATS[name]
        try:
            with experiment(name):
                ep = load_portfolio()
            value = ep["bankroll_sol"] + sum(x["invested_sol"] for x in ep["positions"].values())
            ex = s["exits"]
            if name in EXP_BEENDET:
                title += f" (beendet {EXP_BEENDET[name]}, laeuft aus)"
            lines.append(f"**{title}:** {value:.2f} SOL (Runde {ep.get('runde', 1)}) | Schicht: "
                         f"{len(s['entries'])} Kaeufe, {len(ex)} geschlossen, "
                         f"{sum(e['pnl_sol'] for e in ex):+.3f} SOL, offen {len(ep['positions'])}"
                         + (f" | Fehler {s['exp_errors']}" if s["exp_errors"] else "")
                         + (listing_quellen_text(ep) if name == "listing_welle" else ""))
        except Exception as err:
            lines.append(f"**{title}:** nicht lesbar ({str(err)[:80]})")
    return lines


# ================================================================ Discord / Git

SNAPSHOT_MAX_LINES = 20


def portfolio_embed(p, sol_usd):
    """Zweiter Block unter Kauf- und Verkaufsmeldungen: alle offenen Positionen zum aktuellen Kurs.
    Rechnet wie close_position: Erloese + aktueller Wert - Einsatz - Kauf- und Verkaufsgebuehr."""
    try:
        positions = list(p["positions"].values())
        data = jup_tokens([x["mint"] for x in positions]) if positions else {}
        rows, market, open_pnl = [], 0.0, 0.0
        for x in positions:
            price = as_float((data.get(x["mint"]) or {}).get("usdPrice"))
            hold = (time.time() - x["opened"]) / 3600
            if price > 0 and sol_usd > 0:
                value = max(0.0, x["tokens_left"] * price / sol_usd - TX_FEE_SOL)
                pnl = x["proceeds_sol"] + value - x["invested_sol"] - TX_FEE_SOL
                market += value
                open_pnl += pnl
                rows.append((pnl, f"{'🟢' if pnl >= 0 else '🔴'} **{x['symbol']}** "
                                  f"{price / x['entry_fill_usd']:.2f}x | {pnl:+.3f} SOL "
                                  f"({pnl / x['invested_sol'] * 100:+.0f}%) | {hold:.1f} h"
                                  + (" | Haelfte verkauft" if x.get("tp1_done") else "")))
            else:
                rows.append((float("-inf"), f"⚪ **{x['symbol']}** kein aktueller Kurs | {hold:.1f} h"))
        rows.sort(key=lambda r: -r[0])
        total = p["bankroll_sol"] + market
        since = f"in Runde {p['runde']}" if p.get("runde") else "seit Start"
        lines = [f"**Frei:** {p['bankroll_sol']:.3f} SOL | **Positionen:** {market:.3f} SOL (Marktwert)",
                 f"**Gesamt:** {total:.3f} SOL ({(total / START_BANKROLL_SOL - 1) * 100:+.1f}% {since})"]
        if positions:
            lines.append(f"**Offene Positionen zusammen:** {open_pnl:+.3f} SOL")
            lines += [r[1] for r in rows[:SNAPSHOT_MAX_LINES]]
            if len(rows) > SNAPSHOT_MAX_LINES:
                lines.append(f"... und {len(rows) - SNAPSHOT_MAX_LINES} weitere")
        else:
            lines.append("Keine offenen Positionen.")
        return [{"title": f"{CTX['title_prefix']}📊 Portfolio ({len(positions)} offen)",
                 "description": "\n".join(lines)[:4000], "color": 0x64748B}]
    except Exception as err:                     # Uebersicht darf die eigentliche Meldung nie verhindern
        print(f"[PORTFOLIO-UEBERSICHT] {err}")
        return []


def discord(title, text, color=0x6366F1, extra_embeds=None):
    title = CTX["title_prefix"] + title
    target = CTX["webhook"] or DISCORD_WEBHOOK_URL
    if not target:
        print(f"[DISCORD] {title}")
        return
    payload = {"embeds": [{"title": title, "description": text[:4000], "color": color,
                           "timestamp": datetime.now(timezone.utc).isoformat()}] + (extra_embeds or [])[:9]}
    err = ""
    for attempt in range(DISCORD_ATTEMPTS):
        try:
            res = SESSION.post(target, json=payload, timeout=15)
            if res.status_code < 300:
                return
            err = f"HTTP {res.status_code}"
            if res.status_code == 429:          # Discord bremst: angegebene Wartezeit einhalten
                try:
                    time.sleep(min(float(res.json().get("retry_after", 2)), 10))
                except ValueError:
                    time.sleep(2)
                continue
        except requests.RequestException as e:
            err = str(e)[:120]
        time.sleep(2 * (attempt + 1))
    STATS["discord_fail"] += 1
    print(f"[DISCORD] nicht zugestellt nach {DISCORD_ATTEMPTS} Versuchen: {title} ({err})")


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def _abort_stuck_rebase():
    if os.path.exists(".git/rebase-merge") or os.path.exists(".git/rebase-apply"):
        _git("rebase", "--abort")


def git_sync_start():
    """Vor dem Laden: auf den neuesten Stand von main bringen. Schuetzt davor, mit einem
    veralteten Portfolio zu starten, wenn der Lauf in der Warteschlange gewartet hat."""
    _abort_stuck_rebase()
    res = _git("pull", "--rebase", "origin", "main")
    if res.returncode != 0:
        print(f"[GIT] Aktualisierung beim Start fehlgeschlagen: {res.stderr.strip()[-200:]}")
        _abort_stuck_rebase()
        return False
    return True


def git_push():
    """Sichert die Zustandsdateien auf main. Jede Datei wird als Ganzes ersetzt, nichts
    wird zeilenweise gemischt (das zerstoert JSON). Andere Dateien auf main, etwa eine
    zwischendurch hochgeladene bot.py, bleiben unangetastet."""
    files = [f for f in (PORTFOLIO_FILE, JOURNAL_FILE, REJECT_FILE, PHASE_FILE, VERLAUF_DIR,
                         NEAR_MISS_FILE, "verlauf.csv", EXP_DIR, MESSUNG_FILE, DEX_FILE, FLUG_DIR)
             if os.path.exists(f)]
    if not files:
        return
    _git("config", "user.name", "github-actions[bot]")
    _git("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    _abort_stuck_rebase()
    detail = ""
    for _ in range(2):
        fetch = _git("fetch", "-q", "origin", "main")
        if fetch.returncode != 0:
            detail = f"fetch: {fetch.stderr.strip()[-200:]}"
            continue
        _git("reset", "-q", "origin/main")          # Index = neuester Stand, eigene Dateien bleiben
        _git("add", *files)
        if _git("diff", "--cached", "--quiet").returncode == 0:
            return                                   # nichts Neues
        _git("commit", "-q", "-m", "NARRATIV Update [skip ci]")
        push = _git("push", "-q", "origin", "HEAD:main")
        if push.returncode == 0:
            STATS["git_ok"] += 1
            return
        detail = f"push: {push.stderr.strip()[-200:]}"   # main hat sich bewegt, neuer Versuch
    _git_failed(detail)


def _git_failed(detail):
    STATS["git_fail"] += 1
    print(f"[GIT] {detail}")
    if STATS["git_fail"] in (1, 10):
        discord("⚠️ Speichern auf GitHub fehlgeschlagen",
                f"Der Bot konnte seinen Stand nicht sichern ({STATS['git_fail']}x).\n{detail}",
                0xF59E0B)


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
    drifts = STATS["quote_2s"] + [d for st in EXP_STATS.values() for d in st.get("quote_2s", [])]
    notl = STATS["notloesung"] + sum(st.get("notloesung", 0) for st in EXP_STATS.values())
    if drifts or notl:
        med = sorted(drifts)[len(drifts) // 2] if drifts else None
        lines.append("**Messung (inkl. Experimente):** " + (
            f"Quote 2 s spaeter im Median {med:+.2f}% schlechter ({len(drifts)} Trades)" if drifts else
            "keine Quote-Messung") + f", {STATS['messung_verworfen']} verworfen"
            + f" | 0,95-Notloesung beim Verkauf: {notl}x")
    if STATS["dex"] or STATS["dex_fehler"]:
        lines.append(f"**DexScreener (Beobachtung):** {STATS['dex']} Coins aufgezeichnet"
                     + (f", {STATS['dex_fehler']} ohne Antwort" if STATS["dex_fehler"] else ""))
    ml = sum(1 for e in STATS["entries"] if e.get("mitlaeufer"))
    if ml:
        lines.append(f"**Kaeufe mit Mitlaeufer-Verdacht:** {ml} von {len(STATS['entries'])}")
    if top:
        lines.append("**Haeufigste Ablehnungen:** " + ", ".join(f"{k} {v}" for k, v in top))
    lines.append(f"**Jupiter:** {STATS['jup_ok']} ok / {STATS['jup_fail']} Fehler | "
                 f"**RugCheck:** {STATS['rugcheck_ok']} ok / {STATS['rugcheck_fail']} Fehler | "
                 f"**Helius:** {STATS['helius_ok']} ok / {STATS['helius_fail']} Fehler")
    if STATS.get("near_misses"):
        lines.append(f"**Knapp abgelehnt, neu beobachtet:** {STATS['near_misses']}")
    ybl = STATS["young_by_list"]
    if ybl:
        lines.append("**Junge Kandidaten je Liste:** " + ", ".join(
            f"{k} {len(ybl[k])}" for k in sorted(ybl, key=lambda k: -len(ybl[k]))))
    if STATS["graduations"]:
        lines.append(f"**Graduation waehrend offener Position:** {STATS['graduations']}")
    if STATS["block0_too_many"]:
        lines.append(f"**Bundle-Check wegen zu vieler Transaktionen uebersprungen:** {STATS['block0_too_many']}")
    if SOLANA_TRACKER_API_KEY:
        lines.append(f"**Solana Tracker:** {STATS['st_ok']} ok / {STATS['st_fail']} Fehler"
                     + (f" / {STATS['st_skipped']} wegen Tageslimit ausgelassen" if STATS["st_skipped"] else ""))
    if STATS["discord_fail"]:
        lines.append(f"**Discord-Meldungen nicht zugestellt:** {STATS['discord_fail']}")
    exp_lines = experiment_lines()
    lines.append("**Experimente:**\n" + "\n".join(exp_lines))
    lines.append(f"**GitHub-Sicherung:** {STATS['git_ok']} ok / {STATS['git_fail']} Fehler")
    lines.append(f"**Loop-Fehler:** {STATS['loop_errors']}"
                 + (f" ({STATS['last_error'][:150]})" if STATS["loop_errors"] else ""))
    ok = reason.startswith("regulaer") and STATS["loop_errors"] == 0 and STATS["git_fail"] == 0
    discord("🔴 Schicht beendet" if ok else "⚠️ Schicht beendet (pruefen)", "\n".join(lines),
            0x6366F1 if ok else 0xF59E0B)
    saved = dict(CTX)
    CTX.update(webhook=DISCORD_WEBHOOK_EXPERIMENTE or None, title_prefix="[Experimente] ")
    try:
        discord("Schicht beendet", "\n".join(exp_lines), 0x8B5CF6)
    finally:
        CTX.clear()
        CTX.update(saved)


# ================================================================ Loop

class Interrupted(Exception):
    pass


def _on_signal(signum, frame):
    raise Interrupted(signal.Signals(signum).name)


def run():
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    started = time.time()
    synced = git_sync_start()
    ensure_csv_columns(REJECT_FILE, REJECT_HEADER)
    ensure_csv_columns(NEAR_MISS_FILE, NEAR_MISS_HEADER)
    for path in [JOURNAL_FILE] + [os.path.join(EXP_DIR, n, "journal.csv") for n in EXPERIMENTS]:
        ensure_csv_columns(path, JOURNAL_HEADER)
    p = load_portfolio()
    sol_usd = sol_price()
    age_min = (time.time() - p["saved_at"]) / 60 if p.get("saved_at") else None
    if not synced or (age_min is not None and age_min > 45 and p["positions"]):
        lines = [f"**Aktualisierung von GitHub:** {'ok' if synced else 'FEHLGESCHLAGEN'}"]
        if age_min is not None:
            lines.append(f"**Letzte Speicherung:** vor {age_min:.0f} Minuten")
        if p["positions"]:
            lines.append("**Offen:** " + ", ".join(x["symbol"] for x in p["positions"].values()))
        discord("⚠️ Portfolio-Stand pruefen", "\n".join(lines), 0xF59E0B)
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
                if loop % SOL_PRICE_EVERY_LOOPS == 1:
                    sol_usd = sol_price()
                p = load_portfolio()
                exps = load_experiments()
                if loop % PHASE_EVERY_LOOPS == 1:
                    update_phase(now)
                manage_positions(p, sol_usd, now)
                manage_experiments(p, exps, sol_usd, now)
                if loop % SCAN_EVERY_LOOPS == 1:
                    scan(p, sol_usd, now, exps)
                    save_experiments(exps)
                save_portfolio(p)
                if loop % GIT_PUSH_EVERY_LOOPS == 0:
                    git_push()
            except Interrupted:
                raise
            except Exception as err:
                STATS["loop_errors"] += 1
                STATS["last_error"] = str(err)
                print(f"[LOOP ERROR] {err}")
            sleep_with_rechecks(LOOP_SLEEP_SECONDS)
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
    print(f"[PROBE] Helius: {'Key vorhanden' if HELIUS_API_KEY else 'KEIN KEY - Block-0-Check aus'}")
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
    pool = {t["id"]: t for t in jup_category("toptrending", "5m", 100)
            + jup_category("toptrending", "1h", 100) if t.get("id")}
    young = [token_view(t, now) for t in pool.values()]
    young = sorted((v for v in young if v["age_h"] is not None and v["age_h"] <= 24),
                   key=lambda v: v["age_h"])
    print(f"[PROBE] Junge Coins (unter 24 h) in den Trending-Listen: {len(young)}")
    for v in young[:5]:
        print(f"  {v['symbol']:<12} Alter {v['age_h']:.1f} h | MC ${v['mcap']:,.0f} | "
              f"Holder {v['holders']} ({v['holder_growth_1h']:+.1f}%/h) | Check: {quick_checks(v)}")
    if not young:
        print("[PROBE] Kein junger Coin gefunden, RugCheck-Test entfaellt.")
        return
    test = young[0]
    print(f"[PROBE] Social-Links fuer {test['symbol']} (DexScreener): {has_social(test)}")
    print(f"[PROBE] Jupiter-Dev-Daten: Dev-Coins {test['dev_mints']}, "
          f"Dev haelt {test['dev_balance_pct']:.2f}%, Top-Holder {test['top_holders_pct']:.1f}%")
    for v in young[:3]:
        t0 = time.time()
        rc = rugcheck_get(v["mint"])
        print(f"[PROBE] RugCheck fuer {v['symbol']}: "
              f"{'nicht erreichbar' if rc is None else 'erreichbar'} nach {time.time() - t0:.1f} s")
        if rc:
            print(f"        Felder: {sorted(rc.keys())}")
            nets = rc.get("insiderNetworks") or []
            print(f"        topHolders: {len(rc.get('topHolders') or [])}, "
                  f"Insider markiert: {sum(1 for h in rc.get('topHolders') or [] if h.get('insider'))}, "
                  f"graphInsidersDetected: {rc.get('graphInsidersDetected')}, "
                  f"insiderNetworks: {len(nets)}, Beispiel: {json.dumps(nets[:1])[:200]}")
            print(f"        token.supply: {(rc.get('token') or {}).get('supply')} | "
                  f"Kennzahlen: {rugcheck_metrics(rc)}")
    for v in young[:3]:
        t0 = time.time()
        calls_before = STATS["helius_ok"] + STATS["helius_fail"]
        b0 = block0_analysis(v["mint"]) if HELIUS_RPC else None
        calls = STATS["helius_ok"] + STATS["helius_fail"] - calls_before
        print(f"[PROBE] Block 0 fuer {v['symbol']} ({v['age_h']:.1f} h): "
              f"{b0 if b0 else 'keine Daten'} | {time.time() - t0:.1f} s, {calls} Abfragen")
    print(f"[PROBE] Gesamtbewertung {test['symbol']}: {bundle_dev_check(test['mint'])}")
    probe_solana_tracker(young)
    probe_bonding_curve(now)
    print("[PROBE] fertig. Diese Ausgabe bitte an Claude schicken.")


def probe_bonding_curve(now):
    """Prueft die Endspurt-Rechnung: vSol aus dem Jupiter-Preis gegen den echten Kurvenstand auf der Blockchain."""
    sol_usd = sol_price()
    raw = {}
    for (category, interval) in CANDIDATE_LISTS:
        for t in jup_category(category, interval, 100):
            if t.get("id"):
                raw[t["id"]] = t
    views = [token_view(t, now) for t in raw.values()]
    curve = [v for v in views if v.get("launchpad") == "pump.fun" and not v.get("graduated")]
    window = [v for v in curve if endspurt_candidate(v, sol_usd)]
    filtered = [v for v in window if endspurt_filters_ok(v)]
    print(f"[PROBE] Endspurt: {len(raw)} Coins in 6 Listen, davon {len(curve)} auf der Pump.fun-Kurve, "
          f"{len(window)} im Fenster {ENDSPURT_VSOL_MIN}-{ENDSPURT_VSOL_MAX} vSol, {len(filtered)} davon bestehen die Filter")
    for v in sorted(curve, key=lambda v: -(curve_vsol(v["price"], sol_usd) or 0))[:4]:
        print(f"        {v['symbol']:<12} geschaetzt {curve_vsol(v['price'], sol_usd):6.1f} vSol | MC ${v['mcap']:,.0f} | "
              f"{v['trades_24h']} Trades | organisch '{v['organic_label']}'")


def probe_solana_tracker(young):
    """Testet Solana Tracker mit zwei jungen Coins (zaehlt nicht gegen das Tageslimit des Bots)."""
    if not SOLANA_TRACKER_API_KEY:
        print("[PROBE] Solana Tracker: KEIN KEY (Secret SOLANA_TRACKER_API_KEY fehlt)")
        return
    for v in young[:2]:
        t0 = time.time()
        try:
            res = SESSION.get(f"{SOLANA_TRACKER_BASE}/tokens/{v['mint']}", timeout=8,
                              headers={"x-api-key": SOLANA_TRACKER_API_KEY})
            info = f"HTTP {res.status_code} nach {time.time() - t0:.1f} s"
            data = res.json() if res.status_code == 200 else None
            if res.status_code != 200:
                info += f" | {res.text[:160]}"
        except (requests.RequestException, ValueError) as err:
            info, data = f"Fehler: {str(err)[:120]}", None
        print(f"[PROBE] Solana Tracker fuer {v['symbol']}: {info}")
        if isinstance(data, dict):
            risk = data.get("risk") or {}
            print(f"        Felder: {sorted(data.keys())}")
            print(f"        risk-Felder: {sorted(risk.keys()) if isinstance(risk, dict) else type(risk)}")
            print(f"        Zusammenfassung: {solana_tracker_summary(data)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    probe() if args.probe else run()
