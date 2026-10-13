"""Rohdaten fuer die Scout-Gegenprobe holen (nur auf GitHub mit Secrets).

Aufruf im Repository: python tools/scout_gegenprobe_holen.py
"""
import logging
import sys
import warnings

logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")


def _excepthook(klasse, err, traceback):
    print(klasse.__name__, file=sys.stderr)


sys.excepthook = _excepthook

import json
import math
import os
import re
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
core = cb = scout = None

WALLETS_FILE = Path(__file__).with_name("scout_gegenprobe_wallets.txt")
OUTPUT_FILE = Path("gegenprobe/rohdaten.json")
BASE58 = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,90}")
ZAHLEN_FELDER = ("decimals", "delta_raw", "pre_raw", "tokens", "sol", "price_sol",
                 "fee_base", "fee_prio", "jito", "other", "block_time")
TEXT_FELDER = {"kind": ("KAUF", "VERKAUF", "UEBERWEISUNG"),
               "quote_asset": ("SOL", "USDC")}


class _Stumm:
    """Hilfsfunktionen koennen Antworttexte loggen: verwerfen statt speichern."""

    def write(self, text):
        return len(text)

    def flush(self):
        pass


def abruf(funktion, *args):
    with redirect_stdout(_Stumm()), redirect_stderr(_Stumm()):
        return funktion(*args)


def log(text):
    text = core._hide_key(str(text))
    print(re.sub(r"api-key=[^&\s\"']+", "api-key=***", text))


def fehler_zaehlen(ziel, err):
    """Nur Anzahl und Klasse speichern, niemals den Fehlertext."""
    ziel["anzahl"] += 1
    klasse = type(err).__name__
    ziel["klassen"][klasse] = ziel["klassen"].get(klasse, 0) + 1


def gesperrter_inhalt(text):
    for runde in range(6):
        # "%" kommt in gueltigen Rohdaten nie vor (nur Zahlen, Base58, Namen): sperrt jede Kodierungstiefe
        if re.search(r"api-key|helius-rpc\.com|://|http|%", text, re.IGNORECASE):
            return True
        for name in ("HELIUS_API_KEY", "JUPITER_API_KEY"):
            wert = os.environ.get(name)
            if wert and len(wert) >= 8 and wert in text:
                return True
        if runde == 5:
            break
        dekodiert = unquote(text)
        if dekodiert == text:
            break
        text = dekodiert
    return False


def base58(wert):
    return isinstance(wert, str) and BASE58.fullmatch(wert) is not None


def trade_pruefen(trade):
    if trade is None:
        return None
    if not isinstance(trade, dict) or not base58(trade.get("mint")):
        raise ValueError("Ungueltiger Trade")
    ergebnis = {"mint": trade["mint"]}
    for feld, erlaubt in TEXT_FELDER.items():
        if feld in trade:
            wert = trade[feld]
            if type(wert) is not str or wert not in erlaubt:
                raise ValueError("Ungueltiges Textfeld")
            ergebnis[feld] = wert
    for feld in ZAHLEN_FELDER:
        if feld in trade:
            wert = trade[feld]
            if wert is not None and type(wert) not in (int, float):
                raise ValueError("Ungueltiges Zahlenfeld")
            ergebnis[feld] = wert
    return ergebnis


def load_wallets(path):
    entries = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.partition("#")[0].strip()
        if line:
            name, adresse = line.split()
            entries.append((name, adresse))
    return entries


def holen(wallets_file=WALLETS_FILE, output_file=OUTPUT_FILE, jetzt=None):
    jetzt = time.time() if jetzt is None else jetzt
    entries = load_wallets(wallets_file)
    sol_usd = abruf(core.sol_price)
    daten = {"zeitstempel": jetzt, "sol_usd": sol_usd, "wallets": [],
             "kurse_sol": {}, "rpc_aufrufe": 0, "fehler": {"anzahl": 0, "klassen": {}}}
    mints = set()
    for nummer, (name, adresse) in enumerate(entries, 1):
        wallet = {"name": name, "adresse": adresse, "juengste_block_time": None,
                  "signaturen": [], "trades": {}, "rpc_aufrufe": 0,
                  "fehler": {"anzahl": 0, "klassen": {}}}
        daten["wallets"].append(wallet)
        try:
            wallet["rpc_aufrufe"] += 1
            seite = abruf(core.rpc, "getSignaturesForAddress", [adresse, {"limit": 1000}])
            if seite is None:
                raise RuntimeError("Signaturseite fehlt")
            wallet["juengste_block_time"] = max(
                (s["blockTime"] for s in seite if isinstance(s, dict) and type(s.get("blockTime")) is int),
                default=None)                                # nur ganze Zahlen, nie Text aus der Antwort
            signaturen = abruf(scout.window_sigs, adresse, seite, jetzt, 60)
            for sig in signaturen:
                if not base58(sig):
                    wallet["signaturen"].append("fehlt")
                    wallet["trades"]["fehlt"] = "fehlt"
                    err = ValueError("Ungueltige Signatur")
                    fehler_zaehlen(wallet["fehler"], err)
                    fehler_zaehlen(daten["fehler"], err)
                    continue
                wallet["signaturen"].append(sig)
                trade = "fehlt"
                try:
                    wallet["rpc_aufrufe"] += 1
                    tx = abruf(cb.fetch_tx, sig)
                    if tx is not None:
                        roh_trade = abruf(cb.parse_trade, tx, adresse, sol_usd)
                        if gesperrter_inhalt(json.dumps(roh_trade, ensure_ascii=False)):
                            log("Abbruch: Rohdaten enthalten gesperrte Inhalte.")
                            return 1
                        trade = trade_pruefen(roh_trade)
                except Exception as err:
                    trade = None
                    fehler_zaehlen(wallet["fehler"], err)
                    fehler_zaehlen(daten["fehler"], err)
                wallet["trades"][sig] = trade
                if isinstance(trade, dict) and trade.get("mint"):
                    mints.add(trade["mint"])
        except Exception as err:
            fehler_zaehlen(wallet["fehler"], err)
            fehler_zaehlen(daten["fehler"], err)
        daten["rpc_aufrufe"] += wallet["rpc_aufrufe"]
        fehlt = sum(wallet["trades"].get(sig) == "fehlt" for sig in wallet["signaturen"])
        log(f"Wallet {nummer}/{len(entries)}: {len(wallet['signaturen'])} Signaturen, {fehlt} fehlen")
    roh_kurse = abruf(scout.current_prices_sol, mints, sol_usd)
    if gesperrter_inhalt(json.dumps(roh_kurse, ensure_ascii=False)):
        log("Abbruch: Rohdaten enthalten gesperrte Inhalte.")
        return 1
    for mint, wert in roh_kurse.items():
        try:
            if not base58(mint) or mint not in mints or type(wert) not in (int, float):
                raise ValueError("Ungueltiger Kurs")
            kurs = float(wert)
            if not math.isfinite(kurs):
                raise ValueError("Ungueltiger Kurs")
            daten["kurse_sol"][mint] = kurs
        except Exception as err:
            fehler_zaehlen(daten["fehler"], err)
    serialisiert = json.dumps(daten, ensure_ascii=False, indent=2, allow_nan=False)
    if gesperrter_inhalt(serialisiert):
        log("Abbruch: Rohdaten enthalten gesperrte Inhalte.")
        return 1
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(serialisiert + "\n", encoding="utf-8")
    return 0


def main():
    global core, cb, scout
    try:
        logging.disable(logging.CRITICAL)
        warnings.filterwarnings("ignore")
        with redirect_stdout(_Stumm()), redirect_stderr(_Stumm()):
            import bot as core
            import copy_bot as cb
            import scout_bot as scout
        return holen()
    except BaseException as err:
        print(f"Abbruch: {type(err).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
