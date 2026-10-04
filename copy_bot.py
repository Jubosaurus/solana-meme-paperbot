"""Copy-Trading-Experiment (Paper Trading, kein echtes Geld).

Folgt den Wallets aus copy_wallets.txt per Helius-WebSocket und handelt jeden ihrer Trades nach:
- jede Wallet hat ein eigenes Konto mit 10 SOL (neue Runde, wenn leer)
- jeder Kauf des Traders = 0,2 SOL bei uns, auch Nachkaeufe
- Verkauf desselben Anteils, den der Trader verkauft; Ueberweisung der Coins = Verkauf zum aktuellen Kurs
- kein Take-Profit, kein Stop-Loss; am Schichtende werden Positionen bei -99 % oder schlechter bereinigt
- alle Pruefungen des Hauptbots laufen mit und werden gespeichert, entscheiden aber nichts

Laeuft getrennt vom Hauptbot (eigener Workflow, eigene Dateien in copy/). Nutzt dessen Funktionen fuer
Jupiter, Helius und die Pruefungen, veraendert ihn aber nicht.
"""
import argparse
import csv
import json
import os
import re
import signal
from contextlib import contextmanager
import time
from collections import deque
from datetime import datetime, timezone

import requests
import websocket                        # Paket websocket-client

import bot as core

core.HELIUS_INTERVAL = 0.33   # Copy-Bot hoechstens ~3 Helius-Anfragen/s, damit beide Bots zusammen unter dem Limit bleiben

WALLET_FILE = "copy_wallets.txt"
COPY_DIR = "copy"
ACCOUNTS_FILE = os.path.join(COPY_DIR, "konten.json")
JOURNAL_FILE = os.path.join(COPY_DIR, "journal.csv")

START_SOL = 10.0
BUY_SOL = 0.2
DEFAULT_FEE_SOL = 0.0001                # nur falls die Gebuehr des Traders unbekannt ist
MIN_TRADER_BUY_SOL = 0.1                # kleinere Kaeufe des Traders (Tests, Staub) werden ignoriert
MAX_PRICE_GAP_PCT = 15.0                # Kauf blockiert, wenn unser Kurs mehr als +-15 % vom Trader abweicht
SELL_BATCH_MIN = 0.20                   # Teilverkaeufe sammeln, bis mindestens 20 % der Position verkauft werden
PATH_EVERY = 60                         # Kursverlauf offener Positionen und Schattenpositionen etwa jede Minute
COPY_VERLAUF_DIR = os.path.join("copy", "verlauf")
# Flugschreiber (seit 04.10.): Holder, Top-10-Anteil, Dev-Bestand, Netto-Kaeufer und Verkaeufe der letzten 5 min
# aus denselben Jupiter-Daten (keine zusaetzliche Abfrage), Spalten hinten angehaengt
COPY_VERLAUF_HEADER = ["zeit", "trader", "art", "symbol", "mint", "minuten_seit_kauf", "preis_sol", "vielfaches",
                       "wert_sol", "liquiditaet", "holder", "top10_pct", "dev_pct", "netto_kaeufer_5m", "verkaeufe_5m"]
_verlauf_geprueft = set()
# Messung seit 03.10. (nur Aufzeichnung): dieselbe Quote 2 s spaeter noch einmal. Laeuft nebenher, nur wenn der
# Jupiter-Takt ohnehin frei ist, damit kein Trader-Signal warten muss. Zu spaete Messungen werden verworfen.
MESSUNG_FILE = os.path.join(COPY_DIR, "messung.csv")
MESSUNG_HEADER = ["zeit", "trader", "aktion", "mint", "trader_signatur", "quote_sofort", "quote_spaeter",
                  "sekunden", "abweichung_pct"]
QUOTE_RECHECK_SECONDS = 2.0
QUOTE_RECHECK_MAX_S = 10.0
WALLET_SILENT_H = 72                    # Wallet-Pruefung: so lange ohne eigenen Trade -> ersetzen
BOT_MIN_MSGS = 200                      # Wallet-Pruefung: ab so vielen Meldungen pro Schicht ...
BOT_FAILED_SHARE = 0.9                  # ... und so viel Anteil fehlgeschlagen ohne eigenen Trade -> Bot-Verdacht
REVIEW_AFTER_CLOSED = 30                # Wallet-Pruefung: Ergebnis erst ab 30 geschlossenen Positionen bewerten ...
REVIEW_MIN_LOSS_SOL = 1.0               # ... und nur, wenn mehr als 1 SOL (10 % des Kontos) verloren ist
RECONCILE_EVERY = 3600                  # Bestandsabgleich offener Positionen: beim Start und dann stuendlich
BACKFILL_MAX_PAGES = 3                  # Nachholen: hoechstens 3 x 100 Signaturen je Wallet und Luecke
MAX_SIGS_PER_POS = 60                   # verarbeitete Trader-Signaturen je Position (Schutz vor Doppelverarbeitung)
CLEANUP_MAX_VALUE_PCT = 1.0             # Schichtende: Positionen mit <= 1 % Restwert (-99 %) bereinigen
SHIFT_SECONDS = core.SHIFT_DURATION_SECONDS
PING_EVERY = 30
PUSH_EVERY = 60
MIN_SWAP_LAMPORTS = 1_000_000           # unter 0,001 SOL gilt eine Bewegung nicht als Kauf/Verkauf
BASE_FEE_LAMPORTS = 5000                # Grundgebuehr pro Signatur
JUP_INTERVAL = 1.6                      # Copy-Bot fragt Jupiter etwas langsamer ab als der Hauptbot
FLOOD_PER_MIN = 30                      # ab so vielen Meldungen pro Minute ...
FLOOD_FAILED_SHARE = 0.8                # ... und so viel Anteil fehlgeschlagen -> Bot, fuer die Schicht abmelden
FLOOD_HARD_PER_MIN = 300                # ab so vielen Meldungen pro Minute immer abmelden (Schutz des Kontingents)
# Seit 04.10.: jede Abmeldung mit Datum festhalten (Schluessel = Adresse), die Scout-Automatik nutzt das als Bot-Hinweis
FLOOD_FILE = os.path.join("copy", "flutschutz.json")
CREDITS_PER_100KB = 2                   # Helius: WebSocket-Daten 2 Credits pro 0,1 MB
SWAP_HINTS = ("buy", "sell", "swap", "route")   # Log-Stichworte fuer Kauf, Verkauf, Tausch
MAX_TRADE_AGE_S = 60                    # Kaeufe, die aelter sind, werden nie nachgekauft
DISCORD_WEBHOOK_COPY = (os.environ.get("DISCORD_WEBHOOK_COPY") or "").strip()
WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={core.HELIUS_API_KEY}"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
# Quelle: Solana Cookbook "MEV protection with Jito" (verweist auf docs.jito.wtf, getTipAccounts)
JITO_TIP_ACCOUNTS = {
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"}

JOURNAL_HEADER = [
    "zeit", "trader", "wallet", "aktion", "symbol", "mint", "runde",
    "trader_signatur", "trader_zeit", "verzoegerung_s",
    "trader_sol", "trader_tokens", "trader_preis_sol", "trader_anteil",
    "trader_gebuehr_basis_sol", "trader_gebuehr_prio_sol", "trader_jito_tip_sol", "trader_sonstige_sol",
    "unser_sol", "unsere_tokens", "unser_preis_sol", "unsere_gebuehr_sol", "preisabstand_pct",
    "pnl_sol", "pnl_pct", "hinweis", "pruefungen", "trader_sol_zugeordnet"]

STATS = {"notifications": 0, "bytes": 0, "failed": 0, "no_hint": 0, "fetched": 0, "muted": [], "muted_info": {}, "abgleich": 0, "nachgeholt": 0, "verpasst_kauf": 0,
         "trades": {}, "skipped": {}, "reconnects": 0, "parse_errors": 0, "wallet": {}, "pfade": 0,
         "delays": [], "git_ok": 0, "git_fail": 0, "jup_429": 0, "errors": 0, "last_error": "",
         "quote_ausfall": 0, "verkauf_verschoben": 0, "messung": [], "messung_verworfen": 0}
_jup_last = [0.0]
_rechecks = deque(maxlen=200)           # (faellig, erste Quote um, Trader, Aktion, von, nach, Menge, erste, Signatur)
_jup_error = [None]                      # Fehlercode der letzten Jupiter-Abfrage (None = keiner bekannt)
# Nur diese Antworten bedeuten "Coin ist wirklich nicht (mehr) handelbar"; alles andere gilt als Ausfall.
NO_ROUTE_CODES = {"TOKEN_NOT_TRADABLE", "COULD_NOT_FIND_ANY_ROUTE", "NO_ROUTES_FOUND"}
_seen = set()
# (Trader, Signatur) aller Trades, die schon im Journal stehen (auch aus frueheren Schichten). Ersetzt beim
# Nachholen die Grenze von 60 Signaturen je Position: kein Verkauf doppelt, kein falscher VERPASST_KAUF.
_done = set()
_rate = {}                              # Wallet -> Zeitpunkte der letzten Meldungen
_gap = {}                               # Wallet -> Beginn einer Luecke, die noch nachgeholt werden muss


class Interrupted(BaseException):
    """Abbruch-Signal. Erbt bewusst nicht von Exception: Die Sicherheitsnetze (except Exception) duerfen es
    nicht verschlucken, sonst laeuft der Bot weiter und speichert am Ende nicht (Fehler C, Zrool 02.10.)."""


_critical = [0]                          # > 0: gerade wird gebucht, Abbruch erst danach
_stop = [None]                           # aufgeschobenes Abbruch-Signal
_stopping = [False]                      # Abbruch laeuft oder Schicht endet: weitere Signale ignorieren


def _on_signal(signum, frame):
    if _stopping[0]:
        return                           # GitHub schickt SIGINT und danach SIGTERM: Speichern nicht stoeren
    _stopping[0] = True
    name = signal.Signals(signum).name
    if _critical[0]:
        _stop[0] = name                  # Buchung erst vollstaendig abschliessen
        return
    raise Interrupted(name)


@contextmanager
def booking():
    """Kauf oder Verkauf wird ganz oder gar nicht gebucht: ein Abbruch-Signal wartet bis zum Ende."""
    _critical[0] += 1
    try:
        yield
    finally:
        _critical[0] -= 1
        if _critical[0] == 0 and _stop[0]:
            name, _stop[0] = _stop[0], None
            raise Interrupted(name)


# ================================================================ Wallets und Konten

def load_wallets(path=WALLET_FILE):
    """Liest 'Name: Adresse' je Zeile. Ungueltige Zeilen werden gemeldet und uebersprungen."""
    wallets = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, addr = line.partition(":")
        name, addr = name.strip(), addr.strip()
        if not name or not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", addr):
            print(f"[COPY] ungueltige Zeile in {path}: {line[:60]}")
            continue
        wallets.append((name, addr))
    return wallets


def load_accounts(wallets):
    data = {"wallets": {}}
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, encoding="utf-8") as f:
            data = json.load(f)                  # unlesbar -> Absturz, lieber nicht still neu anfangen
    for name, addr in wallets:
        acct = data["wallets"].setdefault(name, {
            "adresse": addr, "bankroll_sol": START_SOL, "runde": 1, "positionen": {}, "geschlossen": [],
            "gestartet": datetime.now(timezone.utc).isoformat()})
        acct["adresse"] = addr                   # falls die Adresse in der Liste geaendert wurde
        acct.setdefault("schatten", {})
        acct.setdefault("schatten_geschlossen", [])
    if os.path.exists(JOURNAL_FILE):             # letzter eigener Trade je Wallet, fuer die Wallet-Pruefung
        with open(JOURNAL_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("trader") and row.get("trader_signatur"):
                    _done.add((row["trader"], row["trader_signatur"]))
                a = data["wallets"].get(row.get("trader"))
                if a is not None and row.get("trader_zeit"):
                    try:
                        ts = datetime.strptime(row["trader_zeit"], "%Y-%m-%d %H:%M:%S").replace(
                            tzinfo=timezone.utc).timestamp()
                    except ValueError:
                        continue                 # kaputte Zeile darf den Start nie verhindern
                    a["letzter_trade"] = max(a.get("letzter_trade", 0), ts)
    return data


def save_accounts(data):
    os.makedirs(COPY_DIR, exist_ok=True)
    data["saved_at"] = time.time()
    tmp = ACCOUNTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, ACCOUNTS_FILE)


def journal(row):
    os.makedirs(COPY_DIR, exist_ok=True)
    new = not os.path.exists(JOURNAL_FILE)
    with open(JOURNAL_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(JOURNAL_HEADER)
        w.writerow([row.get(k, "") for k in JOURNAL_HEADER])


def count(kind, key):
    STATS[kind][key] = STATS[kind].get(key, 0) + 1


# ================================================================ Jupiter (eigener Takt, Wiederholung bei 429)

def jup(path):
    headers = {"x-api-key": core.JUPITER_API_KEY} if core.JUPITER_API_KEY else {}
    for attempt in range(3):
        core._throttle(_jup_last, JUP_INTERVAL)
        try:
            res = core.SESSION.get(f"{core.JUP_BASE}{path}", headers=headers, timeout=12)
        except requests.RequestException as err:
            print(f"[COPY JUPITER] {path.split('?')[0]} -> {str(err)[:100]}")
            return None
        if res.status_code == 429:
            STATS["jup_429"] += 1
            time.sleep(2 * (attempt + 1))
            continue
        if res.status_code != 200:
            try:
                body = res.json()
            except ValueError:
                body = None
            _jup_error[0] = (body.get("errorCode") if isinstance(body, dict) else None) or f"HTTP {res.status_code}"
            return None
        try:
            return res.json()
        except ValueError:
            return None
    return None


def schedule_recheck(name, aktion, input_mint, output_mint, raw, first_out, first_at, sig):
    if first_out and first_out > 0 and raw > 0:
        _rechecks.append((first_at + QUOTE_RECHECK_SECONDS, first_at, name, aktion, input_mint, output_mint,
                          int(raw), int(first_out), sig))


def run_rechecks(now):
    """Hoechstens eine faellige Messung je Durchlauf, und nur, wenn Jupiter sofort abgefragt werden kann.
    + = 2 s spaeter haetten wir weniger bekommen (Token beim Kauf, SOL beim Verkauf)."""
    while _rechecks and now - _rechecks[0][0] > QUOTE_RECHECK_MAX_S:
        _rechecks.popleft()
        STATS["messung_verworfen"] += 1
    if not _rechecks or _rechecks[0][0] > now or now - _jup_last[0] < JUP_INTERVAL:
        return
    due, first_at, name, aktion, in_m, out_m, raw, first, sig = _rechecks.popleft()
    later = quote_out(in_m, out_m, raw)
    if not later:
        STATS["messung_verworfen"] += 1
        return
    drift = (1 - later / first) * 100
    STATS["messung"].append(drift)
    os.makedirs(COPY_DIR, exist_ok=True)
    new = not os.path.exists(MESSUNG_FILE)
    with open(MESSUNG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(MESSUNG_HEADER)
        w.writerow([now_str(), name, aktion, in_m if aktion != "KAUF" else out_m, sig, first, later,
                    f"{time.time() - first_at:.1f}", f"{drift:+.2f}"])


def quote_out(input_mint, output_mint, raw_amount):
    """Menge laut Jupiter-Quote. 0 = Jupiter sagt eindeutig "nicht handelbar / keine Route".
    None = keine verwertbare Antwort (Ausfall, 429, Timeout): nie als wertlos buchen, spaeter erneut versuchen."""
    _jup_error[0] = None
    data = jup(f"/swap/v1/quote?inputMint={input_mint}&outputMint={output_mint}"
               f"&amount={int(raw_amount)}&slippageBps=500")
    if isinstance(data, dict) and data.get("outAmount") is not None:
        try:
            return int(data["outAmount"])
        except (TypeError, ValueError):
            pass
    elif _jup_error[0] in NO_ROUTE_CODES:
        return 0
    STATS["quote_ausfall"] += 1
    return None


# ================================================================ Transaktion des Traders auswerten

def _instructions(tx):
    msg, meta = tx["transaction"]["message"], tx.get("meta") or {}
    for ins in msg.get("instructions") or []:
        yield ins, True
    for group in meta.get("innerInstructions") or []:
        for ins in group.get("instructions") or []:
            yield ins, False


def parse_trade(tx, wallet, sol_usd=None):
    """Erkennt Kauf, Verkauf oder Ueberweisung eines Tokens durch die Wallet.
    Gibt None zurueck, wenn es keine eigene Handelsaktion der Wallet ist."""
    if not tx or (tx.get("meta") or {}).get("err") is not None:
        return None
    meta, msg = tx["meta"], tx["transaction"]["message"]
    raw_keys = msg.get("accountKeys") or []
    keys = [k.get("pubkey") if isinstance(k, dict) else k for k in raw_keys]
    if wallet not in keys:
        return None
    i = keys.index(wallet)
    signer = bool(raw_keys[i].get("signer")) if isinstance(raw_keys[i], dict) else i == 0
    if not signer:
        return None                              # fremde Transaktion, die die Wallet nur erwaehnt
    fee = int(meta.get("fee") or 0) if i == 0 else 0
    n_sig = max(1, len(tx["transaction"].get("signatures") or []))
    fee_base = min(fee, BASE_FEE_LAMPORTS * n_sig)

    dec, owned, pre, post = {}, set(), {}, {}
    for entries, store in ((meta.get("preTokenBalances"), pre), (meta.get("postTokenBalances"), post)):
        for e in entries or []:
            if e.get("owner") != wallet:
                continue
            ui = e.get("uiTokenAmount") or {}
            store[e["mint"]] = store.get(e["mint"], 0) + int(ui.get("amount") or 0)
            dec[e["mint"]] = int(ui.get("decimals") or 0)
            if isinstance(e.get("accountIndex"), int) and e["accountIndex"] < len(keys):
                owned.add(keys[e["accountIndex"]])
    deltas = {m: post.get(m, 0) - pre.get(m, 0) for m in set(pre) | set(post)}
    wsol = deltas.pop(core.WSOL_MINT, 0)
    usdc = deltas.pop(USDC_MINT, 0)
    deltas = {m: d for m, d in deltas.items() if d != 0}
    if not deltas:
        return None
    mint = max(deltas, key=lambda m: abs(deltas[m]))
    d = deltas[mint]

    # Token-Konten, die in dieser Transaktion angelegt, befuellt oder geschlossen werden (z. B. temporaeres
    # WSOL-Konto). Eine Ueberweisung dorthin ist Teil des Tauschs, keine Gebuehr.
    token_accounts = set()
    for ins, _outer in _instructions(tx):
        parsed = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
        if not parsed:
            continue
        info = parsed.get("info") or {}
        if ins.get("program") in ("spl-token", "spl-associated-token-account"):
            for k in ("account", "newAccount"):
                if isinstance(info.get(k), str):
                    token_accounts.add(info[k])
        elif ins.get("program") == "system" and str(parsed.get("type", "")).startswith("createAccount"):
            if info.get("source") == wallet and isinstance(info.get("newAccount"), str):
                token_accounts.add(info["newAccount"])

    jito = other = 0
    for ins, outer in _instructions(tx):
        parsed = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
        if ins.get("program") != "system" or not parsed or parsed.get("type") != "transfer":
            continue
        info = parsed.get("info") or {}
        if info.get("source") != wallet:
            continue
        dest, lam = info.get("destination"), int(info.get("lamports") or 0)
        if dest in JITO_TIP_ACCOUNTS:
            jito += lam
        elif outer and dest != wallet and dest not in owned and dest not in token_accounts:
            other += lam                         # z. B. Gebuehr des Trading-Bots oder anderer Tip-Dienst

    sol_change = meta["postBalances"][i] - meta["preBalances"][i] + wsol
    swap = -(sol_change + fee + jito + other)    # > 0: SOL ausgegeben, < 0: SOL erhalten
    quote_asset = "SOL"
    if abs(swap) < MIN_SWAP_LAMPORTS and usdc and sol_usd:
        swap = int(-usdc / 1e6 / sol_usd * 1e9)  # Handel gegen USDC in SOL umgerechnet
        quote_asset = "USDC"
    if d > 0 and swap >= MIN_SWAP_LAMPORTS:
        kind = "KAUF"
    elif d < 0 and swap <= -MIN_SWAP_LAMPORTS:
        kind = "VERKAUF"
    elif d < 0:
        kind = "UEBERWEISUNG"
    else:
        return None                              # Token erhalten ohne zu zahlen (Airdrop, Uebertrag)
    tokens = abs(d) / 10 ** dec.get(mint, 0)
    return {"kind": kind, "mint": mint, "decimals": dec.get(mint, 0), "delta_raw": d,
            "pre_raw": pre.get(mint, 0), "tokens": tokens, "sol": abs(swap) / 1e9,
            "price_sol": (abs(swap) / 1e9 / tokens) if tokens and kind != "UEBERWEISUNG" else None,
            "fee_base": fee_base / 1e9, "fee_prio": (fee - fee_base) / 1e9, "jito": jito / 1e9,
            "other": other / 1e9, "block_time": tx.get("blockTime"), "quote_asset": quote_asset}


def fetch_tx(sig):
    """Die Transaktion ist bei 'confirmed' manchmal noch nicht abrufbar, deshalb bis zu 4 Versuche."""
    for attempt in range(4):
        tx = core.rpc("getTransaction", [sig, {"encoding": "jsonParsed", "commitment": "confirmed",
                                               "maxSupportedTransactionVersion": 1}])
        if tx:
            return tx
        time.sleep(0.6 * (attempt + 1))
    return None


# ================================================================ Pruefungen (nur zur Information)

def run_checks(mint, now):
    """Laeuft die Pruefungen des Hauptbots, ohne etwas zu entscheiden."""
    out = {}
    try:
        data = jup(f"/tokens/v2/search?query={mint}")
        tok = next((t for t in data or [] if t.get("id") == mint), None)
        if not tok:
            return {"fehler": "Token bei Jupiter nicht gefunden"}, None
        v = core.token_view(tok, now)
        out["schnellpruefung"] = core.quick_checks(v) or "bestanden"
        out["social"] = bool(core.has_social(v))
        out["sicherheit"] = core.safety_shield(mint) or "bestanden"
        reason, bundle = core.bundle_dev_check(mint)
        out["bundle_dev"] = reason or "bestanden"
        out["block0"] = {k: bundle.get(k) for k in ("block0_wallets", "block0_supply_pct",
                                                     "block0_still_held_pct") if k in (bundle or {})}
        out["merkmale"] = {k: v.get(k) for k in core.ENTRY_FEATURES}
        return out, v
    except Exception as err:                     # Pruefungen duerfen den Copy-Trade nie verhindern
        return {"fehler": str(err)[:120]}, None


# ================================================================ Nachhandeln

def trader_fields(t, sig):
    return {"trader_signatur": sig, "trader_zeit": datetime.fromtimestamp(t["block_time"], timezone.utc)
            .strftime("%Y-%m-%d %H:%M:%S") if t.get("block_time") else "",
            "trader_sol": f"{t['sol']:.6f}", "trader_tokens": f"{t['tokens']:.6f}",
            "trader_preis_sol": f"{t['price_sol']:.12g}" if t.get("price_sol") else "",
            "trader_gebuehr_basis_sol": f"{t['fee_base']:.6f}", "trader_gebuehr_prio_sol": f"{t['fee_prio']:.6f}",
            "trader_jito_tip_sol": f"{t['jito']:.6f}", "trader_sonstige_sol": f"{t['other']:.6f}"}


def notify(title, lines, color):
    saved = dict(core.CTX)
    core.CTX.update(webhook=DISCORD_WEBHOOK_COPY or None, title_prefix="[Copy] " if not DISCORD_WEBHOOK_COPY else "")
    try:
        core.discord(title, "\n".join(line for line in lines if line), color)
    finally:
        core.CTX.clear()
        core.CTX.update(saved)


def open_value(acct):
    """Aktueller Wert der offenen Positionen. Der Kurs stammt aus dem minuetlichen Kursverlauf;
    Positionen ohne Kurs (gerade gekauft) zaehlen mit dem noch nicht zurueckgeflossenen Einsatz."""
    value = 0.0
    for p in acct["positionen"].values():
        price = p.get("letzter_preis_sol")
        if price is not None:
            value += p["tokens_raw"] / 10 ** p["decimals"] * price
        else:
            value += max(0.0, p["invested_sol"] - p["proceeds_sol"])
    return value


def account_line(acct):
    """Konto-Zeile: frei + aktueller Wert der offenen Positionen = Kontowert."""
    value = open_value(acct)
    n = len(acct["positionen"])
    return (f"**Konto:** frei {acct['bankroll_sol']:.3f} SOL | {n} offen, Wert jetzt ~{value:.2f} SOL | "
            f"**Kontowert ~{acct['bankroll_sol'] + value:.2f} SOL** | Runde {acct['runde']}")

def trade_fee(t):
    """Unsere Gebuehr = die tatsaechliche Netzwerkgebuehr des Traders fuer diesen Trade
    (Grundgebuehr + Prioritaetsgebuehr + Jito-Tip). Bot-Gebuehren zaehlen nicht dazu."""
    fee = t["fee_base"] + t["fee_prio"] + t["jito"]
    return fee if fee > 0 else DEFAULT_FEE_SOL


def skip_buy(name, acct, t, sig, key, text):
    count("skipped", key)
    journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "AUSGELASSEN",
             "mint": t["mint"], "runde": acct["runde"], "hinweis": text, **trader_fields(t, sig)})


def copy_buy(name, acct, t, sig, now):
    if t["sol"] < MIN_TRADER_BUY_SOL:
        skip_buy(name, acct, t, sig, "trader_kauf_unter_0_1", f"Trader-Kauf {t['sol']:.3f} SOL unter 0,1 SOL")
        return
    fee = trade_fee(t)
    if acct["bankroll_sol"] < BUY_SOL + fee:
        # Neue Runde, sobald das Geld fuer keinen Kauf mehr reicht, auch wenn noch Positionen offen sind.
        # Offene Positionen behalten ihre alte Rundennummer; ihre spaeteren Erloese fliessen ins neue Konto.
        still_open = len(acct["positionen"])
        acct["runde"] += 1
        acct["bankroll_sol"] = START_SOL
        notify(f"♻️ {name}: Konto aufgebraucht - Neustart", [
            f"Runde {acct['runde']} beginnt mit 10 SOL."
            + (f" {still_open} Position(en) aus frueheren Runden laufen weiter." if still_open else "")], 0x8B5CF6)
    raw = quote_out(core.WSOL_MINT, t["mint"], int(BUY_SOL * 1e9))
    our_time = time.time()
    if not raw:
        skip_buy(name, acct, t, sig, "keine_quote", "keine Jupiter-Quote")
        return
    tokens = raw / 10 ** t["decimals"]
    our_price = BUY_SOL / tokens
    gap = (our_price / t["price_sol"] - 1) * 100 if t.get("price_sol") else None
    delay = our_time - t["block_time"] if t.get("block_time") else None
    if gap is not None and abs(gap) > MAX_PRICE_GAP_PCT:
        skip_buy(name, acct, t, sig, "preisabstand_ueber_15", f"Preisabstand {gap:+.1f}% (Grenze +-{MAX_PRICE_GAP_PCT:.0f}%)"
                 + (f", {delay:.1f} s nach dem Trader" if delay is not None else "") + "; als Schattenposition verfolgt")
        shadow_buy(name, acct, t, sig, raw, our_price, gap, our_time)
        return
    if delay is not None:
        STATS["delays"].append(delay)
    pos = acct["positionen"].setdefault(t["mint"], {
        "mint": t["mint"], "symbol": t["mint"][:6], "decimals": t["decimals"], "tokens_raw": 0,
        "invested_sol": 0.0, "fees_sol": 0.0, "proceeds_sol": 0.0, "opened": our_time, "kaeufe": 0,
        "verkaeufe": 0, "trader_ausgegeben_sol": 0.0, "trader_erhalten_sol": 0.0, "runde": acct["runde"]})
    if "trader_tokens_aufgezeichnet" not in pos:
        pos["vergleich_alt"] = pos["kaeufe"] > 0     # vor dem 30.09.-Umbau eroeffnet: Vergleich unvollstaendig
        pos["trader_tokens_aufgezeichnet"] = 0.0
    pos.setdefault("behalten", 1.0)
    pos.setdefault("gemerkt", 0)
    remember_sig(pos, sig)
    pos["tokens_raw"] += raw
    pos["tokens_gekauft_raw"] = pos.get("tokens_gekauft_raw", 0) + raw
    pos["invested_sol"] += BUY_SOL
    pos["fees_sol"] += fee
    pos["kaeufe"] += 1
    pos["trader_ausgegeben_sol"] += t["sol"]
    pos["trader_tokens_aufgezeichnet"] += t["tokens"]
    pos["trader_bestand_raw"] = t["pre_raw"] + t["delta_raw"]
    pos["letzte_gebuehr"] = fee
    acct["bankroll_sol"] -= BUY_SOL + fee
    count("trades", "KAUF")
    schedule_recheck(name, "KAUF", core.WSOL_MINT, t["mint"], int(BUY_SOL * 1e9), raw, our_time, sig)
    # Pruefungen sind nur Beobachtung und koennen viele Sekunden dauern: bei Abbruch ueberspringen,
    # damit die Buchung vor dem harten Ende (GitHub: ~10 s nach dem Signal) fertig und gespeichert ist
    checks, v = ({"fehler": "uebersprungen (Abbruch)"}, None) if _stopping[0] else run_checks(t["mint"], now)
    if v:
        pos["symbol"] = v["symbol"]
    journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "KAUF", "symbol": pos["symbol"],
             "mint": t["mint"], "runde": acct["runde"], "verzoegerung_s": f"{delay:.1f}" if delay is not None else "",
             "unser_sol": f"{BUY_SOL:.4f}", "unsere_tokens": f"{tokens:.6f}", "unser_preis_sol": f"{our_price:.12g}",
             "unsere_gebuehr_sol": f"{fee:.6f}", "preisabstand_pct": f"{gap:+.2f}" if gap is not None else "",
             "hinweis": f"Kauf Nr. {pos['kaeufe']}" + (" (USDC)" if t["quote_asset"] == "USDC" else ""),
             "pruefungen": json.dumps(checks, ensure_ascii=False), **trader_fields(t, sig)})
    verdict = "alle Pruefungen bestanden" if all(
        checks.get(k) == "bestanden" for k in ("schnellpruefung", "sicherheit", "bundle_dev")) else \
        f"Pruefungen: {checks.get('schnellpruefung', '?')}, {checks.get('bundle_dev', '?')}"
    notify(f"🎯 {name}: Kauf {pos['symbol']}" + (f" (Nachkauf {pos['kaeufe']})" if pos["kaeufe"] > 1 else ""), [
        f"**Trader:** {t['sol']:.3f} SOL zu {t['price_sol']:.3g} SOL/Token | Prio {t['fee_prio']:.5f}, "
        f"Jito {t['jito']:.5f}, sonstige {t['other']:.5f} SOL",
        f"**Wir:** {BUY_SOL} SOL zu {our_price:.3g} SOL/Token" + (f", {delay:.1f} s spaeter" if delay is not None else ""),
        f"**Preisabstand:** {gap:+.1f}%" if gap is not None else "", f"**{verdict}** (nur Beobachtung)",
        account_line(acct), f"https://jup.ag/tokens/{t['mint']}"], 0x3B82F6)


def close_if_empty(name, acct, pos, reason, now):
    if pos["tokens_raw"] > 0:
        return None
    pnl = pos["proceeds_sol"] - pos["invested_sol"] - pos["fees_sol"]
    no_compare = pos.get("trader_ueberwiesen", False) or pos.get("vergleich_alt", False) \
        or pos.get("abgleich", False)
    trader_pnl = None if no_compare else pos["trader_erhalten_sol"] - pos["trader_ausgegeben_sol"]
    rec = dict(pos, pnl_sol=round(pnl, 6), pnl_pct=round(pnl / pos["invested_sol"] * 100, 2),
               grund=reason, geschlossen=datetime.now(timezone.utc).isoformat(),
               haltedauer_h=round((now - pos["opened"]) / 3600, 2),
               trader_pnl_sol=None if trader_pnl is None else round(trader_pnl, 6),
               trader_pnl_pct=round(trader_pnl / pos["trader_ausgegeben_sol"] * 100, 2)
               if trader_pnl is not None and pos["trader_ausgegeben_sol"] else None)
    acct["geschlossen"].append(rec)
    del acct["positionen"][pos["mint"]]
    return rec


def remember_sig(pos, sig):
    sigs = pos.setdefault("sigs", [])
    sigs.append(sig)
    del sigs[:-MAX_SIGS_PER_POS]


def copy_sell(name, acct, t, sig, now, reason="VERKAUF", nachgeholt=False):
    sh = acct.get("schatten", {}).get(t["mint"])
    shadow_new = sh is not None and sig not in sh.get("sigs", [])
    if shadow_new:
        remember_sig(sh, sig)
        shadow_sell(name, acct, t, sig, now, reason)
    pos = acct["positionen"].get(t["mint"])
    if not pos:
        count("skipped", "verkauf_ohne_position")
        if shadow_new:
            # nur Schattenposition: Zeile mit Signatur, damit spaetere Schichten den Verkauf nicht doppelt zaehlen
            journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "SCHATTEN_VERKAUF",
                     "symbol": sh.get("symbol", ""), "mint": t["mint"], "runde": acct["runde"],
                     "hinweis": f"Schattenposition: {reason}", **trader_fields(t, sig)})
        return
    if sig in pos.get("sigs", []):
        return                                   # schon verarbeitet (z. B. live und beim Nachholen gesehen)
    remember_sig(pos, sig)
    if "trader_tokens_aufgezeichnet" not in pos:
        pos["vergleich_alt"] = True                  # vor dem 30.09.-Umbau eroeffnet: Vergleich unvollstaendig
        pos["trader_tokens_aufgezeichnet"] = 0.0
    pos.setdefault("behalten", 1.0)
    pos.setdefault("gemerkt", 0)
    fraction = 1.0 if reason == "UEBERWEISUNG" else (
        min(1.0, abs(t["delta_raw"]) / t["pre_raw"]) if t["pre_raw"] > 0 else 1.0)

    # Vergleich mit dem Trader: nur der Anteil seines Verkaufs, der aus aufgezeichneten Kaeufen stammt
    attributed = 0.0
    if reason == "VERKAUF":
        holdings = t["pre_raw"] / 10 ** t["decimals"] if t["pre_raw"] > 0 else t["tokens"]
        share = min(1.0, pos["trader_tokens_aufgezeichnet"] / holdings) if holdings > 0 else 1.0
        attributed = t["sol"] * share
        pos["trader_erhalten_sol"] += attributed
        pos["trader_tokens_aufgezeichnet"] = max(0.0, pos["trader_tokens_aufgezeichnet"] - t["tokens"] * share)
    else:
        pos["trader_ueberwiesen"] = True

    pos["trader_bestand_raw"] = max(0, t["pre_raw"] - abs(t["delta_raw"])) if reason == "VERKAUF" else 0

    # Teilverkaeufe sammeln: erst ab 20 % der Position verkaufen, oder sofort beim kompletten Ausstieg
    pos["behalten"] *= (1 - fraction)
    pos["gemerkt"] += 1
    to_sell = 1 - pos["behalten"]
    full_exit = reason == "UEBERWEISUNG" or fraction >= 0.999 or pos["behalten"] < 0.001
    if not full_exit and to_sell < SELL_BATCH_MIN:
        count("skipped", "verkauf_gemerkt")
        if nachgeholt:
            STATS["nachgeholt"] += 1
        journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "VERKAUF_GEMERKT",
                 "symbol": pos["symbol"], "mint": t["mint"], "runde": pos["runde"], "trader_anteil": f"{fraction:.4f}",
                 "trader_sol_zugeordnet": f"{attributed:.6f}",
                 "hinweis": f"gesammelt: {to_sell:.0%} der Position, verkauft wird ab {SELL_BATCH_MIN:.0%}",
                 **trader_fields(t, sig)})
        return

    batch = pos["gemerkt"]
    sell_raw = pos["tokens_raw"] if full_exit else int(pos["tokens_raw"] * to_sell)
    out = quote_out(t["mint"], core.WSOL_MINT, sell_raw) if sell_raw > 0 else 0
    if out is None:
        # Jupiter-Ausfall: nicht als wertlos buchen. Der Anteil bleibt vorgemerkt und wird beim naechsten
        # Verkauf des Traders oder beim stuendlichen Abgleich erneut versucht.
        pos["verkauf_offen"] = True
        STATS["verkauf_verschoben"] += 1
        if nachgeholt:
            STATS["nachgeholt"] += 1
        journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "VERKAUF_GEMERKT",
                 "symbol": pos["symbol"], "mint": t["mint"], "runde": pos["runde"], "trader_anteil": f"{fraction:.4f}",
                 "trader_sol_zugeordnet": f"{attributed:.6f}",
                 "hinweis": f"keine Jupiter-Quote (Ausfall): {to_sell:.0%} der Position vorgemerkt, "
                            "Verkauf wird erneut versucht",
                 **trader_fields(t, sig)})
        return
    pos.pop("verkauf_offen", None)
    our_time = time.time()
    proceeds = out / 1e9
    fee = trade_fee(t)
    delay = our_time - t["block_time"] if t.get("block_time") else None
    if delay is not None and not nachgeholt:
        STATS["delays"].append(delay)
    pos["tokens_raw"] -= sell_raw
    pos["proceeds_sol"] += proceeds
    pos["fees_sol"] += fee
    pos["verkaeufe"] += 1
    pos["letzte_gebuehr"] = fee
    pos["behalten"], pos["gemerkt"] = 1.0, 0
    acct["bankroll_sol"] += proceeds - fee
    count("trades", reason)
    schedule_recheck(name, reason, t["mint"], core.WSOL_MINT, sell_raw, out, our_time, sig)
    tokens = sell_raw / 10 ** pos["decimals"]
    our_price = proceeds / tokens if tokens else None
    gap = (our_price / t["price_sol"] - 1) * 100 if our_price and t.get("price_sol") else None
    rec = close_if_empty(name, acct, pos, reason, now)
    journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": reason, "symbol": pos["symbol"],
             "mint": t["mint"], "runde": pos["runde"], "verzoegerung_s": f"{delay:.1f}" if delay is not None else "",
             "trader_anteil": f"{fraction:.4f}", "unser_sol": f"{proceeds:.6f}", "unsere_tokens": f"{tokens:.6f}",
             "unser_preis_sol": f"{our_price:.12g}" if our_price else "", "unsere_gebuehr_sol": f"{fee:.6f}",
             "preisabstand_pct": f"{gap:+.2f}" if gap is not None else "", "trader_sol_zugeordnet": f"{attributed:.6f}",
             "pnl_sol": f"{rec['pnl_sol']:+.6f}" if rec else "", "pnl_pct": f"{rec['pnl_pct']:+.2f}" if rec else "",
             "hinweis": ("Position geschlossen" if rec else f"Teilverkauf {to_sell:.0%}")
                        + (f", gesammelt aus {batch} Verkaeufen des Traders" if batch > 1 else "")
                        + (f"; nachgeholt, {delay / 60:.0f} min nach dem Trader" if nachgeholt and delay else "")
                        + ("; keine Quote, Wert 0" if sell_raw > 0 and out <= 0 else ""),
             **trader_fields(t, sig)})
    lines = [f"**Trader:** " + (f"steigt aus" if full_exit and reason == "VERKAUF" else
                                 "ueberweist seine Coins" if reason == "UEBERWEISUNG" else
                                 f"hat seit unserem letzten Verkauf {to_sell:.0%} verkauft ({batch} Verkaeufe)"),
             f"**Wir:** {proceeds:.4f} SOL" + (f" zu {our_price:.3g} SOL/Token" if our_price else "")
             + (f", {delay:.1f} s spaeter" if delay is not None and not nachgeholt else "")
             + (f" (nachgeholt, {delay / 60:.0f} min spaeter: Signal war verpasst)" if nachgeholt and delay else "")]
    if rec:
        tp = (f"{rec['trader_pnl_sol']:+.3f} SOL ({rec['trader_pnl_pct']:+.0f}%)" if rec["trader_pnl_pct"] is not None
              else "nicht vergleichbar (" + ("ueberwiesen" if pos.get("trader_ueberwiesen") else
                                              "vor dem Umbau eroeffnet") + ")")
        lines.append(f"**Ergebnis:** {rec['pnl_sol']:+.4f} SOL ({rec['pnl_pct']:+.1f}%) | Trader, nur aufgezeichnete Trades: {tp}")
    lines.append(account_line(acct))
    good = rec is None or rec["pnl_sol"] > 0
    notify(f"{'🟢' if good else '🔴'} {name}: {'Verkauf' if reason == 'VERKAUF' else 'Ueberweisung'} "
           f"{pos['symbol']}" + ("" if rec else f" ({to_sell:.0%})"), lines, 0x10B981 if good else 0xEF4444)


def shadow_buy(name, acct, t, sig, raw, our_price, gap, now):
    """Wegen der Preisgrenze blockierter Kauf: virtuell weiterverfolgen, um die Grenze bewerten zu koennen."""
    sh = acct["schatten"].setdefault(t["mint"], {
        "mint": t["mint"], "symbol": t["mint"][:6], "decimals": t["decimals"], "tokens": 0.0, "invested_sol": 0.0,
        "erloes_sol": 0.0, "behalten": 1.0, "opened": now, "kaeufe": 0, "preisabstand_pct": [],
        "trader_ausgegeben_sol": 0.0, "trader_erhalten_sol": 0.0, "trader_tokens_aufgezeichnet": 0.0, "runde": acct["runde"]})
    sh["tokens"] += raw / 10 ** t["decimals"]
    sh["invested_sol"] += BUY_SOL
    sh["kaeufe"] += 1
    sh["preisabstand_pct"].append(round(gap, 2))
    sh["trader_ausgegeben_sol"] += t["sol"]
    sh["trader_tokens_aufgezeichnet"] += t["tokens"]
    count("trades", "SCHATTEN_KAUF")
    journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "SCHATTEN_KAUF", "mint": t["mint"],
             "runde": acct["runde"], "unser_sol": f"{BUY_SOL:.4f}", "unser_preis_sol": f"{our_price:.12g}",
             "preisabstand_pct": f"{gap:+.2f}", "hinweis": "blockiert wegen Preisgrenze, nur virtuell verfolgt",
             **trader_fields(t, sig)})


def shadow_sell(name, acct, t, sig, now, reason):
    """Verkauf einer Schattenposition zum Kurs des Traders (Naeherung, leicht optimistisch)."""
    sh = acct["schatten"][t["mint"]]
    fraction = 1.0 if reason == "UEBERWEISUNG" else (
        min(1.0, abs(t["delta_raw"]) / t["pre_raw"]) if t["pre_raw"] > 0 else 1.0)
    if reason == "VERKAUF":
        holdings = t["pre_raw"] / 10 ** t["decimals"] if t["pre_raw"] > 0 else t["tokens"]
        share = min(1.0, sh["trader_tokens_aufgezeichnet"] / holdings) if holdings > 0 else 1.0
        sh["trader_erhalten_sol"] += t["sol"] * share
        sh["trader_tokens_aufgezeichnet"] = max(0.0, sh["trader_tokens_aufgezeichnet"] - t["tokens"] * share)
        price = t.get("price_sol") or 0
    else:
        sh["trader_ueberwiesen"] = True
        price = sh.get("letzter_preis_sol") or 0     # Ueberweisung: letzter bekannter Kurs
    sold = sh["tokens"] * sh["behalten"] * fraction
    sh["erloes_sol"] += sold * price
    sh["behalten"] *= (1 - fraction)
    if fraction >= 0.999 or sh["behalten"] < 0.001:
        shadow_close(name, acct, sh, "UEBERWEISUNG" if reason == "UEBERWEISUNG" else "TRADER_AUSSTIEG", now)


def shadow_close(name, acct, sh, reason, now):
    pnl = sh["erloes_sol"] - sh["invested_sol"]
    trader = None if sh.get("trader_ueberwiesen") or not sh["trader_ausgegeben_sol"] else \
        (sh["trader_erhalten_sol"] - sh["trader_ausgegeben_sol"]) / sh["trader_ausgegeben_sol"] * 100
    rec = dict(sh, pnl_sol=round(pnl, 6), pnl_pct=round(pnl / sh["invested_sol"] * 100, 2), grund=reason,
               geschlossen=datetime.now(timezone.utc).isoformat(), haltedauer_h=round((now - sh["opened"]) / 3600, 2),
               trader_pnl_pct=None if trader is None else round(trader, 2))
    acct["schatten_geschlossen"].append(rec)
    del acct["schatten"][sh["mint"]]
    count("trades", "SCHATTEN_GESCHLOSSEN")
    journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "SCHATTEN_ENDE", "mint": sh["mint"],
             "symbol": sh["symbol"], "runde": sh["runde"], "unser_sol": f"{sh['erloes_sol']:.6f}",
             "pnl_sol": f"{pnl:+.6f}", "pnl_pct": f"{rec['pnl_pct']:+.2f}",
             "hinweis": f"{reason}; Ausstieg zum Kurs des Traders (Naeherung)"})


def backfill(name, acct, since, sol_usd):
    """Verpasste Transaktionen einer Wallet seit 'since' nachholen, aeltere zuerst.
    Verkaeufe laufen normal durch (mit echtem Kurs des Traders), Kaeufe werden nur dokumentiert."""
    sigs, before = [], None
    for _ in range(BACKFILL_MAX_PAGES):
        opts = {"limit": 100, "commitment": "confirmed"}   # gleicher Stand wie Live-Meldungen und Bestand
        if before:
            opts["before"] = before
        page = core.rpc("getSignaturesForAddress", [acct["adresse"], opts]) or []
        reached = False
        for s in page:
            if (s.get("blockTime") or 0) < since:
                reached = True
                break
            if s.get("err") is None and s.get("signature"):
                sigs.append(s["signature"])
        if reached or len(page) < 100:
            break
        before = page[-1].get("signature")
    for sig in reversed(sigs):
        handle_signature(name, acct, sig, sol_usd, nachgeholt=True)
    return len(sigs)


def retry_sell(name, acct, pos, now):
    """Nach einem Jupiter-Ausfall vorgemerkten Verkauf erneut versuchen. True, wenn verkauft wurde."""
    behalten = pos.get("behalten", 1.0)
    sell_raw = pos["tokens_raw"] if behalten < 0.001 else int(pos["tokens_raw"] * (1 - behalten))
    if sell_raw <= 0:
        pos.pop("verkauf_offen", None)
        return False
    out = quote_out(pos["mint"], core.WSOL_MINT, sell_raw)
    if out is None:
        return False                                         # weiter vorgemerkt
    proceeds = out / 1e9
    fee = pos.get("letzte_gebuehr", DEFAULT_FEE_SOL) if out > 0 else 0
    pos["tokens_raw"] -= sell_raw
    pos["proceeds_sol"] += proceeds
    pos["fees_sol"] += fee
    pos["verkaeufe"] += 1
    pos["behalten"], pos["gemerkt"] = 1.0, 0
    pos.pop("verkauf_offen", None)
    acct["bankroll_sol"] += proceeds - fee
    count("trades", "VERKAUF")
    tokens = sell_raw / 10 ** pos["decimals"]
    rec = close_if_empty(name, acct, pos, "VERKAUF", now)
    journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "VERKAUF",
             "symbol": pos["symbol"], "mint": pos["mint"], "runde": pos["runde"], "unser_sol": f"{proceeds:.6f}",
             "unsere_tokens": f"{tokens:.6f}",
             "unser_preis_sol": f"{proceeds / tokens:.12g}" if tokens and proceeds else "",
             "unsere_gebuehr_sol": f"{fee:.6f}",
             "pnl_sol": f"{rec['pnl_sol']:+.6f}" if rec else "", "pnl_pct": f"{rec['pnl_pct']:+.2f}" if rec else "",
             "hinweis": ("Position geschlossen" if rec else "Teilverkauf")
                        + "; nach Jupiter-Ausfall nachgeholt, Verkauf zum aktuellen Kurs"
                        + ("; keine Route, Wert 0" if out <= 0 else "")})
    notify(f"🔁 {name}: Verkauf nachgeholt {pos['symbol']}", [
        "Jupiter war beim Verkaufssignal nicht erreichbar, Verkauf jetzt zum aktuellen Kurs.",
        f"**Wir:** {proceeds:.4f} SOL" + (f" | **Ergebnis:** {rec['pnl_sol']:+.4f} SOL ({rec['pnl_pct']:+.1f}%)"
                                           if rec else ""),
        account_line(acct)], 0x8B5CF6)
    return True


def trader_balance_raw(wallet, mint):
    """Aktueller Bestand des Traders an diesem Coin (alle seine Token-Konten), None wenn unbekannt."""
    res = core.rpc("getTokenAccountsByOwner", [wallet, {"mint": mint}, {"encoding": "jsonParsed", "commitment": "confirmed"}])
    if not isinstance(res, dict) or not isinstance(res.get("value"), list):
        return None                              # unerwartete Antwort: lieber nichts tun als faelschlich verkaufen
    total = 0
    for acc in res["value"]:
        try:
            total += int(acc["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"])
        except (KeyError, TypeError, ValueError):
            return None
    return total


def reconcile(data, now, sol_usd=None):
    """Verpasste Verkaeufe nachholen: offene Positionen mit dem tatsaechlichen Bestand des Traders vergleichen.
    Gilt fuer alle Konten, auch fuer Wallets, die nicht mehr beobachtet werden."""
    done, backfilled = 0, set()
    for name, acct in data["wallets"].items():
        for mint in list(acct["positionen"]):
            pos = acct["positionen"].get(mint)
            if pos is None:
                continue
            if pos.get("verkauf_offen"):
                with booking():
                    retry_sell(name, acct, pos, now)      # nach Jupiter-Ausfall vorgemerkten Verkauf nachholen
                pos = acct["positionen"].get(mint)
                if pos is None:
                    continue
            now_raw = trader_balance_raw(acct["adresse"], mint)
            if now_raw is None:
                continue
            last_raw = pos.get("trader_bestand_raw")
            missed = now_raw == 0 or (last_raw is not None and now_raw < last_raw * (1 - SELL_BATCH_MIN))
            if missed and name not in backfilled:
                backfilled.add(name)             # erst versuchen, die Verkaeufe mit echtem Kurs nachzuholen
                try:
                    backfill(name, acct, pos["opened"] - 60, sol_usd)
                except Exception as err:
                    print(f"[COPY] Nachholen {name}: {str(err)[:100]}")
                pos = acct["positionen"].get(mint)
                if pos is None:
                    continue
                last_raw = pos.get("trader_bestand_raw")
            if now_raw == 0:
                fraction = 1.0
            elif last_raw is None or now_raw >= last_raw:
                if last_raw is not None and now_raw > last_raw:
                    pos["trader_bestand_raw"] = now_raw      # Trader hat zugekauft: nur merken, nicht nachkaufen
                continue
            else:
                fraction = 1 - now_raw / last_raw
                if fraction < SELL_BATCH_MIN:
                    continue                                 # kleine Differenz: weiter sammeln
            sell_raw = pos["tokens_raw"] if fraction >= 0.999 else int(pos["tokens_raw"] * fraction)
            out = quote_out(mint, core.WSOL_MINT, sell_raw) if sell_raw > 0 else 0
            if out is None:
                continue                                     # Jupiter-Ausfall: beim naechsten Abgleich erneut
            with booking():
                proceeds, fee = out / 1e9, (pos.get("letzte_gebuehr", DEFAULT_FEE_SOL) if out > 0 else 0)
                pos["tokens_raw"] -= sell_raw
                pos["proceeds_sol"] += proceeds
                pos["fees_sol"] += fee
                pos["verkaeufe"] += 1
                pos["abgleich"] = True
                pos["trader_bestand_raw"] = now_raw
                pos["behalten"], pos["gemerkt"] = 1.0, 0
                acct["bankroll_sol"] += proceeds - fee
                rec = close_if_empty(name, acct, pos, "ABGLEICH", now)
                STATS["abgleich"] += 1
                count("trades", "ABGLEICH")
                journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "ABGLEICH",
                         "symbol": pos["symbol"], "mint": mint, "runde": pos["runde"], "unser_sol": f"{proceeds:.6f}",
                         "unsere_gebuehr_sol": f"{fee:.6f}", "trader_anteil": f"{fraction:.4f}",
                         "pnl_sol": f"{rec['pnl_sol']:+.6f}" if rec else "", "pnl_pct": f"{rec['pnl_pct']:+.2f}" if rec else "",
                         "hinweis": ("Trader haelt nichts mehr" if now_raw == 0 else
                                     f"Trader haelt nur noch {now_raw / last_raw:.0%} seines letzten Bestands")
                                    + "; Verkaufssignal verpasst, Verkauf zum aktuellen Kurs"})
                notify(f"🔄 {name}: Abgleich {pos['symbol']}", [
                    f"Der Trader hat verkauft, ohne dass wir das Signal gesehen haben "
                    f"({'komplett raus' if now_raw == 0 else f'{fraction:.0%} seines Bestands'}).",
                    f"**Wir:** {proceeds:.4f} SOL" + (f" | **Ergebnis:** {rec['pnl_sol']:+.4f} SOL ({rec['pnl_pct']:+.1f}%)"
                                                       if rec else f" ({fraction:.0%} der Position)"),
                    account_line(acct)], 0x8B5CF6)
            done += 1
    return done


def log_paths(data, sol_usd, now):
    """Kursverlauf aller offenen Positionen und Schattenpositionen, eine Datei pro Tag in copy/verlauf/."""
    items = [(n, "offen", p) for n, a in data["wallets"].items() for p in a["positionen"].values()] + \
            [(n, "schatten", s) for n, a in data["wallets"].items() for s in a.get("schatten", {}).values()]
    if not items or not sol_usd:
        return
    mints = sorted({it[2]["mint"] for it in items})
    toks = {}
    for i in range(0, len(mints), 100):
        for tok in jup(f"/tokens/v2/search?query={','.join(mints[i:i + 100])}") or []:
            if tok.get("id"):
                toks[tok["id"]] = tok
    os.makedirs(COPY_VERLAUF_DIR, exist_ok=True)
    path = os.path.join(COPY_VERLAUF_DIR, datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".csv")
    new = not os.path.exists(path)
    if not new and path not in _verlauf_geprueft:            # seit 04.10. Flugschreiber-Spalten hinten
        core.ensure_csv_columns(path, COPY_VERLAUF_HEADER)
        _verlauf_geprueft.add(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COPY_VERLAUF_HEADER)
        for name, art, p in items:
            tok = toks.get(p["mint"])
            if not tok:
                continue
            price = core.as_float(tok.get("usdPrice")) / sol_usd
            if art == "offen":
                p["letzter_preis_sol"] = price           # fuer den Kontowert in den Meldungen
                bought = p.get("tokens_gekauft_raw") or p["tokens_raw"]
                entry = p["invested_sol"] / (bought / 10 ** p["decimals"]) if bought else 0
                value = p["tokens_raw"] / 10 ** p["decimals"] * price
                if p["symbol"] == p["mint"][:6] and tok.get("symbol"):
                    p["symbol"] = tok["symbol"]
            else:
                entry = p["invested_sol"] / p["tokens"] if p["tokens"] else 0
                value = p["tokens"] * p["behalten"] * price
                p["letzter_preis_sol"] = price
                if p["symbol"] == p["mint"][:6] and tok.get("symbol"):
                    p["symbol"] = tok["symbol"]
            audit = tok.get("audit") or {}
            s5 = tok.get("stats5m") or {}
            w.writerow([now_str(), name, art, p["symbol"], p["mint"], f"{(now - p['opened']) / 60:.1f}",
                        f"{price:.12g}", f"{price / entry:.4f}" if entry else "", f"{value:.6f}",
                        f"{core.as_float(tok.get('liquidity')):.0f}",
                        int(core.as_float(tok.get("holderCount"))),
                        f"{core.as_float(audit.get('topHoldersPercentage')):.2f}",
                        f"{core.as_float(audit.get('devBalancePercentage')):.2f}",
                        int(core.as_float(s5.get("numNetBuyers"))), int(core.as_float(s5.get("numSells")))])
            STATS["pfade"] += 1


def wallet_check(data, active, now):
    """Welche Wallets erfuellen eine Regel zum Ersetzen? Nur Meldung; ersetzt wird seit 04.10. von der
    Automatik im Scout (scout_bot.auto_wallets): still und Verlust mit denselben Konstanten, Bot dort nach den
    Regeln von Scout-Stufe 1 (der Flutschutz hier wird nicht gespeichert)."""
    notes = []
    for name in active:
        a, s = data["wallets"][name], STATS["wallet"].get(name, {})
        msgs, failed, trades = s.get("meldungen", 0), s.get("fehlgeschlagen", 0), s.get("trades", 0)
        if name in STATS["muted"]:
            per_min, share = STATS["muted_info"].get(name, (0, 1.0))
            notes.append(f"🤖 {name}: Bot (Flutschutz: {per_min}/min, {share:.0%} fehlgeschlagen) -> ersetzen")
        elif msgs >= BOT_MIN_MSGS and failed / msgs >= BOT_FAILED_SHARE and trades == 0:
            notes.append(f"🤖 {name}: Bot-Verdacht ({msgs} Meldungen, {failed / msgs:.0%} fehlgeschlagen, kein eigener Trade) -> ersetzen")
        last = a.get("letzter_trade") or datetime.fromisoformat(a["gestartet"]).timestamp()
        if (now - last) / 3600 >= WALLET_SILENT_H:
            notes.append(f"💤 {name}: seit {(now - last) / 3600:.0f} h kein eigener Trade -> ersetzen")
        closed = len(a["geschlossen"])
        realized = sum(c["pnl_sol"] for c in a["geschlossen"])
        if closed >= REVIEW_AFTER_CLOSED and realized <= -REVIEW_MIN_LOSS_SOL:
            notes.append(f"📉 {name}: {closed} Positionen geschlossen, {realized:+.2f} SOL -> pruefen, ob noch lehrreich")
    return notes


def handle_signature(name, acct, sig, sol_usd, nachgeholt=False):
    key = (name, sig)
    if key in _seen or key in _done:
        if key in _done and key not in _seen:
            count("skipped", "schon_verarbeitet")    # Nachholen: in einer frueheren Schicht erledigt
        _seen.add(key)
        return
    _seen.add(key)
    tx = fetch_tx(sig)
    if tx is None:
        count("skipped", "transaktion_nicht_abrufbar")
        return
    try:
        t = parse_trade(tx, acct["adresse"], sol_usd)
    except Exception as err:
        STATS["parse_errors"] += 1
        print(f"[COPY] Auswertung {sig[:12]} fehlgeschlagen: {str(err)[:120]}")
        return
    if not t:
        return
    now = time.time()
    acct["letzter_trade"] = t.get("block_time") or now
    w = STATS["wallet"].setdefault(name, {})
    w["trades"] = w.get("trades", 0) + 1
    if t["kind"] == "KAUF":
        if t.get("block_time") and now - t["block_time"] > MAX_TRADE_AGE_S:
            count("skipped", "kauf_zu_alt")     # nie Kaeufe nachholen, die schon laenger zurueckliegen
            if nachgeholt:
                STATS["verpasst_kauf"] += 1
                journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "VERPASST_KAUF",
                         "mint": t["mint"], "runde": acct["runde"],
                         "hinweis": "Kauf des Traders verpasst (Luecke), nur dokumentiert", **trader_fields(t, sig)})
            return
        with booking():
            copy_buy(name, acct, t, sig, now)
    else:
        if nachgeholt:
            STATS["nachgeholt"] += 1
        with booking():
            copy_sell(name, acct, t, sig, now, t["kind"], nachgeholt=nachgeholt)


# ================================================================ Bereinigung am Schichtende

def cleanup(data):
    """Positionen mit hoechstens 1 % Restwert verkaufen (so viel, wie Jupiter noch bietet)."""
    closed = 0
    open_mints = {m for a in data["wallets"].values() for m in a["positionen"]}
    prices = {}
    for chunk in [list(open_mints)[i:i + 100] for i in range(0, len(open_mints), 100)]:
        for tok in jup(f"/tokens/v2/search?query={','.join(chunk)}") or []:
            prices[tok.get("id")] = core.as_float(tok.get("usdPrice"))
    sol_usd = core.sol_price() or 0
    now = time.time()
    for name, acct in data["wallets"].items():
        for mint, pos in list(acct["positionen"].items()):
            est = pos["tokens_raw"] / 10 ** pos["decimals"] * prices.get(mint, 0) / sol_usd if sol_usd else 0
            if est > pos["invested_sol"] * 0.1:              # grob vorsortieren, genau prueft die Quote
                continue
            raw_out = quote_out(mint, core.WSOL_MINT, pos["tokens_raw"])
            if raw_out is None:
                continue                                     # Jupiter-Ausfall: Position bleibt offen
            out = raw_out / 1e9
            if out > pos["invested_sol"] * CLEANUP_MAX_VALUE_PCT / 100:
                continue
            pos["proceeds_sol"] += out
            fee = pos.get("letzte_gebuehr", DEFAULT_FEE_SOL) if out > 0 else 0
            pos["fees_sol"] += fee
            acct["bankroll_sol"] += out - fee
            pos["tokens_raw"] = 0
            rec = close_if_empty(name, acct, pos, "BEREINIGT (-99 %)", now)
            journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "BEREINIGT",
                     "symbol": pos["symbol"], "mint": mint, "runde": pos["runde"], "unser_sol": f"{out:.6f}",
                     "pnl_sol": f"{rec['pnl_sol']:+.6f}", "pnl_pct": f"{rec['pnl_pct']:+.2f}",
                     "hinweis": "Schichtende: Restwert hoechstens 1 %"})
            closed += 1
    for name, acct in data["wallets"].items():
        for mint, sh in list(acct.get("schatten", {}).items()):
            value = sh["tokens"] * sh["behalten"] * (sh.get("letzter_preis_sol") or 0)
            if sh.get("letzter_preis_sol") is not None and value <= sh["invested_sol"] * CLEANUP_MAX_VALUE_PCT / 100:
                sh["erloes_sol"] += value
                shadow_close(name, acct, sh, "BEREINIGT (-99 %)", now)
    return closed


# ================================================================ Git (nur die eigenen Dateien)

def git_push():
    if not os.path.exists(COPY_DIR):
        return
    g = core._git
    g("config", "user.name", "github-actions[bot]")
    g("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    for _ in range(3):
        if g("fetch", "-q", "origin", "main").returncode != 0:
            continue
        g("reset", "-q", "origin/main")          # Index = neuester Stand, eigene Dateien bleiben
        g("add", COPY_DIR)
        if g("diff", "--cached", "--quiet").returncode == 0:
            return
        g("commit", "-q", "-m", "COPY Update [skip ci]")
        if g("push", "-q", "origin", "HEAD:main").returncode == 0:
            STATS["git_ok"] += 1
            return
    STATS["git_fail"] += 1


# ================================================================ WebSocket

def connect(wallets):
    ws = websocket.create_connection(WS_URL, timeout=20)
    for idx, (name, addr) in enumerate(wallets, 1):
        ws.send(json.dumps({"jsonrpc": "2.0", "id": idx, "method": "logsSubscribe",
                            "params": [{"mentions": [addr]}, {"commitment": "confirmed"}]}))
    subs, early, pending, deadline = {}, [], set(range(1, len(wallets) + 1)), time.time() + 20
    while pending and time.time() < deadline:
        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            break                               # fehlende Bestaetigungen: mit den bestaetigten weiterarbeiten
        if not raw:
            raise websocket.WebSocketConnectionClosedException("Verbindung bei der Anmeldung geschlossen")
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        if msg.get("id") in pending:
            pending.discard(msg["id"])
            if "result" in msg:
                subs[msg["result"]] = wallets[msg["id"] - 1]
            else:
                print(f"[COPY] Anmeldung fuer {wallets[msg['id'] - 1][0]} abgelehnt: {str(msg.get('error'))[:120]}")
        elif msg.get("method") == "logsNotification":
            early.append(msg)
    if pending:
        print(f"[COPY] {len(pending)} Anmeldungen ohne Bestaetigung: "
              f"{', '.join(wallets[i - 1][0] for i in sorted(pending))}")
    ws.settimeout(1.0)
    return ws, subs, early


def notification_value(msg):
    return ((msg.get("params") or {}).get("result") or {}).get("value") or {}


def notification_sig(msg):
    value = notification_value(msg)
    if value.get("err") is not None:
        return None
    return value.get("signature")


def trade_hint(value):
    """'handel' bei Kauf/Verkauf/Tausch im Log, 'transfer' bei reiner Token-Ueberweisung, sonst None."""
    kind = None
    for line in value.get("logs") or []:
        low = line.lower()
        if "ray_log" in low or ("instruction:" in low and any(h in low for h in SWAP_HINTS)):
            return "handel"
        if "instruction:" in low and "transfer" in low:
            kind = "transfer"
    return kind


def looks_like_trade(value):
    return trade_hint(value) == "handel"


def run(probe=False):
    wallets = load_wallets()
    if probe:
        return run_probe(wallets)
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    core.git_sync_start()
    core.ensure_csv_columns(JOURNAL_FILE, JOURNAL_HEADER)
    data = load_accounts(wallets)
    save_accounts(data)
    started, sol_usd = time.time(), core.sol_price()
    notify("🟢 Copy-Schicht gestartet", [f"{len(wallets)} Wallets, je eigenes Konto mit {START_SOL:.0f} SOL."], 0x10B981)
    ws, subs, last_ping, last_push, last_sol, normal_end = None, {}, time.time(), time.time(), time.time(), False
    last_path = connected_at = time.time()
    last_reconcile = 0.0                         # erster Abgleich gleich zu Beginn der Schicht
    active = [n for n, _ in wallets]
    for name in active:                          # Luecke seit der letzten Schicht (oder seit Eroeffnung der Positionen)
        a = data["wallets"][name]
        opened = [p["opened"] for p in a["positionen"].values()] + [s["opened"] for s in a.get("schatten", {}).values()]
        _gap[name] = a.get("abgedeckt_bis") or (min(opened) - 60 if opened else None)
    try:
        while time.time() - started < SHIFT_SECONDS:
            if ws is None:
                try:
                    wanted = [w for w in wallets if w[0] not in STATS["muted"]]
                    ws, subs, early = connect(wanted)
                    connected_at = time.time()
                    print(f"[COPY] verbunden, {len(subs)} von {len(wanted)} Wallets angemeldet")
                    for msg in early:
                        process_message(msg, subs, data, sol_usd, ws)
                    for name, _ in list(subs.values()):   # Luecken nachholen (nur wenn Positionen offen sind)
                        a = data["wallets"][name]
                        if _gap.get(name) and (a["positionen"] or a.get("schatten")):
                            try:
                                backfill(name, a, _gap[name], sol_usd)
                            except Exception as err:
                                print(f"[COPY] Nachholen {name}: {str(err)[:100]}")
                        _gap[name] = None
                except Exception as err:
                    STATS["reconnects"] += 1
                    print(f"[COPY] Verbindung fehlgeschlagen: {str(err)[:120]}")
                    ws = None
                    time.sleep(min(30, 3 * STATS["reconnects"]))
                    continue
            try:
                raw = ws.recv()
                if not raw:                      # leere Nachricht: Server hat die Verbindung geschlossen
                    raise websocket.WebSocketConnectionClosedException("leere Nachricht vom Server")
                STATS["bytes"] += len(raw)
                try:
                    msg = json.loads(raw)
                except ValueError:
                    STATS["unlesbar"] = STATS.get("unlesbar", 0) + 1
                    msg = None
                if msg is not None:
                    process_message(msg, subs, data, sol_usd, ws)
            except websocket.WebSocketTimeoutException:
                pass
            except (websocket.WebSocketConnectionClosedException, ConnectionError, OSError) as err:
                STATS["reconnects"] += 1
                print(f"[COPY] Verbindung verloren: {str(err)[:100]}")
                for name, _ in subs.values():
                    _gap[name] = _gap.get(name) or time.time()
                ws = None
                continue
            except Exception as err:             # Sicherheitsnetz: nie wegen einer einzelnen Nachricht abstuerzen
                STATS["errors"] += 1
                STATS["last_error"] = f"{type(err).__name__}: {str(err)[:150]}"
                print(f"[COPY] unerwarteter Fehler, laeuft weiter: {STATS['last_error']}")
            now = time.time()
            if ws is not None and len(subs) < len([w for w in wallets if w[0] not in STATS["muted"]]) \
                    and now - connected_at > 300:
                print("[COPY] nicht alle Wallets angemeldet, neuer Versuch")
                for name, _ in subs.values():
                    _gap[name] = _gap.get(name) or time.time()
                try:
                    ws.close()
                except Exception:
                    pass
                ws = None                        # naechster Durchlauf verbindet und meldet alle neu an
                continue
            if now - last_ping > PING_EVERY and ws is not None:
                try:
                    ws.ping()
                except Exception:
                    ws = None
                last_ping = now
            try:
                run_rechecks(now)
            except Exception as err:             # Messung darf den Copy-Bot nie stoppen
                STATS["errors"] += 1
                print(f"[COPY] Messung: {str(err)[:120]}")
            if now - last_sol > 300:
                sol_usd, last_sol = core.sol_price() or sol_usd, now
            if now - last_reconcile > RECONCILE_EVERY:
                try:
                    reconcile(data, now, sol_usd)
                except Exception as err:         # Abgleich darf den Copy-Bot nie stoppen
                    STATS["errors"] += 1
                    print(f"[COPY] Abgleich: {str(err)[:120]}")
                last_reconcile = now
            if now - last_path > PATH_EVERY:
                try:
                    log_paths(data, sol_usd, now)
                except Exception as err:         # Aufzeichnung darf den Copy-Bot nie stoppen
                    STATS["errors"] += 1
                    print(f"[COPY] Kursverlauf: {str(err)[:120]}")
                last_path = now
            if now - last_push > PUSH_EVERY:
                save_accounts(data)
                git_push()
                last_push = now
        normal_end = True
    except Interrupted as sig:
        print(f"[COPY] Abbruch-Signal erhalten ({sig}), speichere")
    finally:
        _stopping[0] = True                      # ab hier nur noch speichern: weitere Signale ignorieren
        cleaned = 0
        if normal_end:
            try:
                cleaned = cleanup(data)
            except Exception as err:             # Bereinigung darf das Speichern nie verhindern
                STATS["errors"] += 1
                STATS["last_error"] = f"Bereinigung: {str(err)[:150]}"
                print(f"[COPY] Bereinigung fehlgeschlagen: {str(err)[:150]}")
        end_ts = time.time()
        for name in active:                      # bis hierher lueckenlos zugehoert (ausser offene Luecken, Abmeldungen)
            if name not in STATS["muted"]:
                data["wallets"][name]["abgedeckt_bis"] = _gap.get(name) or end_ts
        save_accounts(data)
        git_push()
        try:
            if ws is not None:
                ws.close()
        except Exception:
            pass
        try:
            summary(data, time.time() - started, cleaned, normal_end, active)
        except Exception as err:                 # Endmeldung darf den Kettenstart nie verhindern
            print(f"[COPY] Endmeldung fehlgeschlagen: {str(err)[:150]}")


def process_message(msg, subs, data, sol_usd, ws=None):
    if msg.get("method") != "logsNotification":
        return
    STATS["notifications"] += 1
    sub = (msg.get("params") or {}).get("subscription")
    if sub not in subs:
        return
    name, _ = subs[sub]
    now = time.time()
    w = STATS["wallet"].setdefault(name, {})
    w["meldungen"] = w.get("meldungen", 0) + 1
    if notification_value(msg).get("err") is not None:
        w["fehlgeschlagen"] = w.get("fehlgeschlagen", 0) + 1
    window = _rate.setdefault(name, deque())
    window.append((now, notification_value(msg).get("err") is not None))
    while window and now - window[0][0] > 60:
        window.popleft()
    if len(window) > FLOOD_PER_MIN and name not in STATS["muted"]:
        failed_share = sum(1 for _, f in window if f) / len(window)
        if failed_share >= FLOOD_FAILED_SHARE or len(window) > FLOOD_HARD_PER_MIN:
            mute(ws, subs, sub, name, len(window), failed_share, data)
            return
    value = notification_value(msg)
    if value.get("err") is not None:
        STATS["failed"] += 1
        return
    hint = trade_hint(value)
    has_positions = bool(data["wallets"][name]["positionen"])
    if hint is None or (hint == "transfer" and not has_positions):
        STATS["no_hint"] += 1               # Ueberweisung ist nur relevant, wenn wir etwas halten
        return
    sig = value.get("signature")
    if not sig:
        return
    STATS["fetched"] += 1
    try:
        handle_signature(name, data["wallets"][name], sig, sol_usd)
    except Exception as err:                     # ein fehlerhafter Trade darf den Bot nicht stoppen
        STATS["errors"] += 1
        STATS["last_error"] = str(err)[:200]
        print(f"[COPY] Fehler bei {name} {sig[:12]}: {str(err)[:150]}")


def mute(ws, subs, sub, name, per_min, failed_share=1.0, data=None):
    """Wallet sendet zu viele Meldungen (meist ein Bot mit vielen fehlschlagenden Transaktionen):
    fuer den Rest der Schicht abmelden, damit das Helius-Kontingent nicht aufgebraucht wird."""
    STATS["muted"].append(name)
    STATS["muted_info"][name] = (per_min, failed_share)
    record_flood(name, (subs.get(sub) or (None, None))[1], per_min, failed_share)
    if data is not None:
        data["wallets"][name]["abgedeckt_bis"] = time.time()   # naechste Schicht holt ab hier nach
    subs.pop(sub, None)
    try:
        if ws is not None:
            ws.send(json.dumps({"jsonrpc": "2.0", "id": 9000 + len(STATS["muted"]),
                                "method": "logsUnsubscribe", "params": [sub]}))
    except Exception:
        pass
    notify(f"⚠️ {name} abgemeldet (zu viele Meldungen)", [
        f"{per_min} Meldungen in der letzten Minute, davon {failed_share:.0%} fehlgeschlagen. Die Wallet wird fuer den Rest "
        f"der Schicht nicht mehr beobachtet, damit das Helius-Kontingent nicht aufgebraucht wird.",
        "Vermutlich ein Bot mit sehr vielen, meist fehlschlagenden Transaktionen."], 0xF59E0B)


def record_flood(name, addr, per_min, failed_share):
    """Abmeldung in copy/flutschutz.json festhalten (erste und letzte Abmeldung, Anzahl). Darf nie stoppen."""
    if not addr:
        return
    try:
        try:
            with open(FLOOD_FILE, encoding="utf-8") as f:
                flood = json.load(f)
        except (OSError, ValueError):
            flood = {}
        if not isinstance(flood, dict):
            flood = {}
        e = flood.get(addr) if isinstance(flood.get(addr), dict) else {}
        e.setdefault("erstes", now_str())
        e.update(name=name, zuletzt=now_str(), anzahl=int(e.get("anzahl") or 0) + 1,
                 pro_min=per_min, fehlgeschlagen_anteil=round(failed_share, 3))
        flood[addr] = e
        os.makedirs(COPY_DIR, exist_ok=True)
        tmp = FLOOD_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(flood, f, indent=1)
        os.replace(tmp, FLOOD_FILE)
    except Exception as err:
        STATS["errors"] += 1
        print(f"[COPY] Flutschutz-Datei nicht geschrieben: {str(err)[:100]}")


def credits_used():
    return STATS["bytes"] / 100_000 * CREDITS_PER_100KB + STATS["fetched"] * 1


def summary(data, dur, cleaned, normal_end, active=None):
    lines = [f"**Dauer:** {dur / 3600:.2f} h | **Meldungen:** {STATS['notifications']} | "
             f"**Trades:** {STATS['trades'] or 0}"]
    if STATS["skipped"]:
        lines.append(f"**Ausgelassen:** {STATS['skipped']}")
    if STATS["delays"]:
        d = sorted(STATS["delays"])
        lines.append(f"**Verzoegerung nach dem Trader:** Median {d[len(d) // 2]:.1f} s, "
                     f"90 % unter {d[int(len(d) * 0.9)]:.1f} s")
    lines.append(f"**Bereinigt (-99 %):** {cleaned} | **Nachgeholt:** {STATS['nachgeholt']} Verkaeufe mit Trader-Kurs, "
                 f"{STATS['verpasst_kauf']} verpasste Kaeufe dokumentiert | **Abgleich ohne Kurs:** {STATS['abgleich']}")
    pending = sum(1 for a in data["wallets"].values() for p in a["positionen"].values() if p.get("verkauf_offen"))
    if STATS["quote_ausfall"] or pending:
        lines.append(f"**Jupiter-Ausfall:** {STATS['quote_ausfall']} Quotes ohne Antwort, "
                     f"{STATS['verkauf_verschoben']} Verkaeufe vorgemerkt statt mit Wert 0 gebucht, "
                     f"{pending} Position(en) warten noch auf den Verkauf")
    if STATS["messung"] or STATS["messung_verworfen"]:
        m = sorted(STATS["messung"])
        lines.append("**Messung Quote 2 s spaeter:** " + (
            f"Median {m[len(m) // 2]:+.2f}% schlechter, jeder zehnte ueber {m[int(len(m) * 0.9)]:+.2f}% "
            f"({len(m)} Trades)" if m else "keine") + f", {STATS['messung_verworfen']} verworfen")
    per_day = credits_used() / max(dur, 1) * 86400
    lines.append(f"**Helius:** {STATS['bytes'] / 1e6:.1f} MB empfangen, {STATS['fetched']} Transaktionen abgefragt, "
                 f"~{credits_used():,.0f} Credits (hochgerechnet ~{per_day * 30:,.0f} im Monat) | "
                 f"fehlgeschlagen uebersprungen {STATS['failed']}, ohne Handel {STATS['no_hint']}")
    if STATS["muted"]:
        lines.append(f"**Abgemeldet wegen Flut:** {', '.join(STATS['muted'])}")
    active = active or list(data["wallets"])
    rows = []
    for name in active:
        a = data["wallets"][name]
        total = a["bankroll_sol"] + open_value(a)        # Kontowert wie in den Einzelmeldungen
        diff = total - START_SOL                         # jede Runde startet mit START_SOL
        rows.append((total, f"{name}: **~{total:.2f} SOL** ({diff:+.2f} in Runde {a['runde']}) | "
                            f"{len(a['positionen'])} offen, {len(a['geschlossen'])} geschlossen"))
    rows.sort(key=lambda r: r[0], reverse=True)
    lines.append("**Wallets (Kontowert = frei + offene Positionen zum Kurs):**\n" + "\n".join(r for _, r in rows))
    shadows = [c for n in active for c in data["wallets"][n].get("schatten_geschlossen", [])]
    open_sh = sum(len(data["wallets"][n].get("schatten", {})) for n in active)
    if shadows or open_sh:
        lines.append(f"**Schattenpositionen (Preisgrenze):** {len(shadows)} abgeschlossen, Summe "
                     f"{sum(c['pnl_sol'] for c in shadows):+.3f} SOL (Naeherung), {open_sh} offen")
    checks = wallet_check(data, active, time.time())
    lines.append("**Wallet-Pruefung:**\n" + ("\n".join(checks) if checks else "alle Wallets unauffaellig"))
    if STATS.get("unlesbar") or STATS.get("last_error"):
        lines.append(f"**Unlesbare Nachrichten:** {STATS.get('unlesbar', 0)} | **Letzter Fehler:** {STATS.get('last_error') or '-'}")
    lines.append(f"**Verbindungsabbrueche:** {STATS['reconnects']} | **Auswertungsfehler:** "
                 f"{STATS['parse_errors'] + STATS['errors']} | **Jupiter-Bremse (429):** {STATS['jup_429']} | "
                 f"**GitHub-Sicherung:** {STATS['git_ok']} ok / {STATS['git_fail']} Fehler")
    ok = normal_end and not STATS["errors"] and not STATS["git_fail"]
    notify("🔴 Copy-Schicht beendet" if ok else "⚠️ Copy-Schicht beendet (pruefen)", lines, 0x64748B)


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ================================================================ Probelauf

def run_probe(wallets):
    print(f"[COPY PROBE] {len(wallets)} Wallets aus {WALLET_FILE} gelesen")
    print(f"[COPY PROBE] Discord-Kanal Copy: {'gesetzt' if DISCORD_WEBHOOK_COPY else 'FEHLT (Meldungen gingen in den Hauptkanal)'}")
    sol_usd = core.sol_price()
    print(f"[COPY PROBE] SOL-Kurs: {sol_usd}")
    kinds = {}
    for name, addr in wallets:
        sigs = core.rpc("getSignaturesForAddress", [addr, {"limit": 6}]) or []
        parsed = []
        for s in sigs:
            if s.get("err") is not None:
                continue
            t = parse_trade(fetch_tx(s["signature"]), addr, sol_usd)
            if t:
                kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
                parsed.append(f"{t['kind']} {t['mint'][:6]} {t['sol']:.3f} SOL"
                              + (f" @ {t['price_sol']:.3g}" if t.get("price_sol") else "")
                              + f" (Prio {t['fee_prio']:.5f}, Jito {t['jito']:.5f}, sonst. {t['other']:.5f})")
        last = datetime.fromtimestamp(sigs[0]["blockTime"], timezone.utc).strftime("%d.%m. %H:%M") \
            if sigs and sigs[0].get("blockTime") else "?"
        print(f"  {name:<10} letzte Aktivitaet {last} UTC | erkannt: {parsed[:3] or 'keine Trades in den letzten 6 Tx'}")
    print(f"[COPY PROBE] Erkannte Trades gesamt: {kinds}")
    try:
        ws, subs, early = connect(wallets)
        print(f"[COPY PROBE] WebSocket verbunden, {len(subs)} von {len(wallets)} Wallets angemeldet")
        per = {name: {"alle": 0, "fehlgeschlagen": 0, "handel": 0, "transfer": 0, "bytes": 0, "trades": []}
               for name, _ in wallets}
        t0 = time.time()
        while time.time() - t0 < 90:
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if not raw:
                print("[COPY PROBE] Verbindung vom Server geschlossen")
                break
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if msg.get("method") != "logsNotification":
                continue
            sub = msg["params"]["subscription"]
            if sub not in subs:
                continue
            name, addr = subs[sub]
            s = per[name]
            s["alle"] += 1
            s["bytes"] += len(raw)
            value = notification_value(msg)
            if value.get("err") is not None:
                s["fehlgeschlagen"] += 1
            else:
                hint = trade_hint(value)
                if hint == "handel":
                    s["handel"] += 1
                    if len(s["trades"]) < 2:
                        s["trades"].append(value.get("signature"))
                elif hint == "transfer":
                    s["transfer"] += 1
        ws.close()
        dur = time.time() - t0
        print(f"[COPY PROBE] Meldungen in {dur:.0f} s pro Wallet (sortiert nach Menge):")
        print(f"  {'Wallet':<10} {'pro Min':>8} {'fehlgeschl.':>11} {'Handel':>7} {'Transfer':>8} {'KB':>7}  Stichprobe")
        tot_bytes = tot_trade = 0
        for name, s in sorted(per.items(), key=lambda kv: -kv[1]["alle"]):
            sample = []
            for sig in s["trades"]:
                t = parse_trade(fetch_tx(sig), dict(wallets)[name], sol_usd)
                sample.append(f"{t['kind']} {t['sol']:.2f} SOL" if t else "kein eigener Trade")
            flag = "  <- ZU VIEL" if s["alle"] / dur * 60 > FLOOD_PER_MIN else ""
            print(f"  {name:<10} {s['alle'] / dur * 60:8.1f} {s['fehlgeschlagen']:11} {s['handel']:7} {s['transfer']:8} "
                  f"{s['bytes'] / 1000:7.1f}  {', '.join(sample) or '-'}{flag}")
            tot_bytes += s["bytes"]
            tot_trade += s["handel"]
        ok = {n: s for n, s in per.items() if s["alle"] / dur * 60 <= FLOOD_PER_MIN}
        def month(b, t): return (b / 100_000 * CREDITS_PER_100KB + t) / dur * 86400 * 30
        print(f"[COPY PROBE] Hochrechnung alle Wallets: ~{month(tot_bytes, tot_trade):,.0f} Credits im Monat")
        print(f"[COPY PROBE] Ohne die Wallets ueber {FLOOD_PER_MIN}/min: {len(ok)} Wallets, "
              f"~{month(sum(s['bytes'] for s in ok.values()), sum(s['handel'] for s in ok.values())):,.0f} Credits im Monat")
    except Exception as err:
        print(f"[COPY PROBE] WebSocket FEHLER: {str(err)[:200]}")
    raw = quote_out(core.WSOL_MINT, USDC_MINT, int(0.01 * 1e9))
    print(f"[COPY PROBE] Jupiter-Quote 0,01 SOL -> USDC: {raw / 1e6 if raw else 'FEHLER'}")
    print("[COPY PROBE] fertig. Diese Ausgabe bitte an Claude schicken.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    run(probe=ap.parse_args().probe)
