"""Scout alt/neu auf denselben Rohdaten vergleichen, ohne Netzwerk.

Aufruf im Repository: python tools/scout_gegenprobe_rechnen.py rohdaten.json bericht.md
Copy-Ergebnisse stammen aus dem lokalen Copy-Kontostand beim Rechnen.
"""
import argparse
import copy
import json
import math
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from statistics import median
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bot as core  # noqa: E402
import copy_bot as cb  # noqa: E402
import scout_bot as scout  # noqa: E402

# Unveraenderte Reibungskonstanten; der wortgleiche Alt-Code nutzt diese Namen.
FRICTION_LONG = scout.FRICTION_LONG
FRICTION_SHORT = scout.FRICTION_SHORT
FRICTION_MID = scout.FRICTION_MID


def current_prices_sol(mints, sol_usd):
    return scout.current_prices_sol(mints, sol_usd)


# Quelle: git show 8d72e20073:scout_bot.py, Zeilen 307-363.
# Funktionskoerper wortgleich, nur der Funktionsname ist stage2_alt.
def stage2_alt(wallet, sigs, sol_usd):
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


def mittelraenge(werte):
    raenge = [0.0] * len(werte)
    sortiert = sorted(range(len(werte)), key=werte.__getitem__)
    i = 0
    while i < len(sortiert):
        j = i + 1
        while j < len(sortiert) and werte[sortiert[j]] == werte[sortiert[i]]:
            j += 1
        rang = (i + 1 + j) / 2
        for index in sortiert[i:j]:
            raenge[index] = rang
        i = j
    return raenge


def spearman(x, y):
    """Pearson-Korrelation der Mittelraenge; ohne Streuung nicht definiert."""
    if len(x) != len(y):
        raise ValueError("Verschiedene Laengen")
    if len(x) < 2:
        return None
    rx, ry = mittelraenge(x), mittelraenge(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    dx, dy = [v - mx for v in rx], [v - my for v in ry]
    nenner = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    return sum(a * b for a, b in zip(dx, dy)) / nenner if nenner else None


def netz_gesperrt(*args, **kwargs):
    raise RuntimeError("Netzwerk ist beim Rechnen gesperrt")


@contextmanager
def ersatzdaten(wallet, kurse):
    """Fehlende TX, Nicht-Handel und Trades bleiben unterscheidbar."""
    signaturen, trades = wallet["signaturen"], wallet["trades"]
    if not isinstance(signaturen, list) or not isinstance(trades, dict):
        raise ValueError("Ungueltige Rohdaten")
    for sig in signaturen:
        t = trades[sig]
        if t is not None and t != "fehlt" and not isinstance(t, dict):
            raise ValueError("Ungueltiger Trade")

    def fetch(sig):
        return None if trades[sig] == "fehlt" else sig

    def parse(tx, adresse, sol_usd):
        return None if tx is None else copy.deepcopy(trades[tx])

    def prices(mints, sol_usd):
        return {m: kurse[m] for m in mints if m in kurse}

    with ExitStack() as stack:
        stack.enter_context(patch.object(cb, "fetch_tx", fetch))
        stack.enter_context(patch.object(cb, "parse_trade", parse))
        stack.enter_context(patch.object(scout, "current_prices_sol", prices))
        yield


def bewerten(funktion, wallet, sol_usd, zeitstempel):
    s2 = funktion(wallet["adresse"], wallet["signaturen"], sol_usd)
    punkte = scout.score(s2)
    letzte = wallet.get("juengste_block_time")
    inaktiv_h = (zeitstempel - letzte) / 3600 if letzte else None
    zeile = dict(s2, ergebnis="bewertet" if punkte is not None else scout.not_rated_reason(s2),
                 punkte=punkte if punkte is not None else "", inaktiv_h=inaktiv_h)
    return dict(s2, punkte=punkte, aufnahme_grund=scout.auto_reason(zeile))


def copy_ergebnis(adresse, accounts):
    konto = next((a for a in accounts.values()
                  if isinstance(a, dict) and a.get("adresse") == adresse), None)
    if konto is None:
        return None
    detail = cb.ergebnis_detail(konto)
    return {"ergebnis": detail["ergebnis"], "ohne_kurs": detail["ohne_kurs"],
            "geschlossen": len(konto.get("geschlossen") or [])}


def auswerten(daten):
    rows = []
    # Auch zukuenftige Hilfsaufrufe duerfen beim Rechnen kein Netz benutzen.
    with ExitStack() as stack:
        for modul, name in ((core, "rpc"), (core, "sol_price"), (core, "jup_get"),
                            (core, "dex_get"), (cb, "jup")):
            stack.enter_context(patch.object(modul, name, netz_gesperrt))
        stack.enter_context(patch("requests.sessions.Session.request", netz_gesperrt))
        accounts = scout.load_copy_accounts()
        for nummer, wallet in enumerate(daten["wallets"], 1):
            row = {"name": f"Wallet {nummer}", "adresse": None, "alt": None, "neu": None,
                   "copy": None, "fehler": []}
            rows.append(row)
            try:
                row["name"] = wallet.get("name") or row["name"]
                row["adresse"] = wallet["adresse"]
                try:
                    row["copy"] = copy_ergebnis(row["adresse"], accounts)
                except Exception as err:
                    row["fehler"].append(("Copy", type(err).__name__))
                if (wallet.get("fehler") or {}).get("anzahl", 0):
                    raise ValueError("Rohdaten der Wallet unvollstaendig")
                with ersatzdaten(wallet, daten["kurse_sol"]):
                    for art, funktion in (("alt", stage2_alt), ("neu", scout.stage2)):
                        try:
                            row[art] = bewerten(funktion, wallet, daten["sol_usd"], daten["zeitstempel"])
                        except Exception as err:
                            row["fehler"].append((art, type(err).__name__))
            except Exception as err:
                row["fehler"].append(("Wallet", type(err).__name__))
    return rows


def korrelation(rows, art, min_geschlossen):
    paare = [(r[art]["punkte"], r["copy"]["ergebnis"]) for r in rows
             if r[art] is not None and r[art]["punkte"] is not None and r["copy"] is not None
             and r["copy"]["geschlossen"] >= min_geschlossen
             and math.isfinite(r[art]["punkte"]) and math.isfinite(r["copy"]["ergebnis"])]
    return spearman([x for x, _ in paare], [y for _, y in paare]), len(paare)


def zahl(wert, stellen=1):
    return "–" if wert is None else f"{wert:.{stellen}f}".replace(".", ",")


def zelle(text):
    return str(text).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def bericht(daten, rows):
    lines = ["# Scout-Gegenprobe alt gegen neu", "",
             f"Rohdaten-Zeitstempel (UTC, Unix-Sekunden): {daten['zeitstempel']}", "",
             "Copy-Ergebnis seit Start aus dem lokalen Kontostand beim Rechnen. "
             "‚Ohne Kurs‘ zählt offene Positionen ohne belastbaren Kurs.", "",
             "| Name | Punkte alt | Punkte neu | Ohne besten % alt/neu | Gewinn SOL alt/neu | "
             "Coins alt/neu | Coins gehalten alt/neu | Überwiesen | Fehlend/abgerufen | "
             "Aufnahme alt | Aufnahme neu + Grund | Copy-Ergebnis SOL | Geschlossen | Ohne Kurs | Fehler |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|"]
    sortiert = sorted(rows, key=lambda r: (r["copy"] is None,
                                           -(r["copy"]["ergebnis"] if r["copy"] else 0)))
    for r in sortiert:
        alt, neu, konto = r["alt"] or {}, r["neu"] or {}, r["copy"]

        def paar(key, stellen=1):
            return f"{zahl(alt.get(key), stellen)}/{zahl(neu.get(key), stellen)}"

        def aufnahme(art, mit_grund=False):
            ergebnis = r[art]
            if ergebnis is None:
                return "Fehler"
            grund = ergebnis["aufnahme_grund"]
            return "ja" if grund is None else "nein" + (f": {grund}" if mit_grund else "")

        cells = [r["name"], zahl(alt.get("punkte")), zahl(neu.get("punkte")),
                 paar("rendite_ohne_besten_pct"), paar("gewinn_sol", 3), paar("coins", 0),
                 paar("coins_gehalten", 0), zahl(neu.get("coins_ueberwiesen"), 0),
                 f"{zahl(neu.get('tx_fehlend'), 0)}/{zahl(neu.get('tx_abgerufen'), 0)}",
                 aufnahme("alt"), aufnahme("neu", True),
                 zahl(konto["ergebnis"], 3) if konto else "–",
                 zahl(konto["geschlossen"], 0) if konto else "–",
                 zahl(konto["ohne_kurs"], 0) if konto else "–",
                 "; ".join(f"Fehler {bereich}: {klasse}" for bereich, klasse in r["fehler"]) or "–"]
        lines.append("| " + " | ".join(zelle(c) for c in cells) + " |")
    lines += ["", "Spearman: Punkte gegen Copy-Ergebnis SOL. Nur Wallets mit beiden Zahlen; "
              "Gleichstände bekommen Mittelränge. Ohne Streuung oder bei n < 2: –.", "",
              "| Gruppe | Alt | n alt | Neu | n neu |", "|---|---:|---:|---:|---:|"]
    for titel, minimum in (("Mindestens 5 geschlossene Positionen", 5), ("Alle mit Copy-Konto", 0)):
        a, na = korrelation(rows, "alt", minimum)
        n, nn = korrelation(rows, "neu", minimum)
        lines.append(f"| {titel} | {zahl(a, 4)} | {na} | {zahl(n, 4)} | {nn} |")
    abgelehnt = [r for r in rows if r["alt"] is not None and r["neu"] is not None
                 and r["alt"]["aufnahme_grund"] is None and r["neu"]["aufnahme_grund"] is not None]
    mit_copy = [r for r in abgelehnt if r["copy"] is not None]
    lines += ["", f"Alt aufgenommen, neu abgelehnt: {len(abgelehnt)}.",
              f"Copy-Summe dieser Wallets: {zahl(sum(r['copy']['ergebnis'] for r in mit_copy), 3) if mit_copy else '–'} SOL "
              f"({len(mit_copy)} mit Copy-Konto, {len(abgelehnt) - len(mit_copy)} ohne Copy-Konto).", "",
              f"Helius-Aufrufe laut Rohdaten (grob): {daten.get('rpc_aufrufe', 0)}.",
              f"Fehler beim Holen: {(daten.get('fehler') or {}).get('anzahl', 0)}.", ""]
    return "\n".join(lines)


def rechnen(rohdaten_file, bericht_file):
    daten = json.loads(Path(rohdaten_file).read_text(encoding="utf-8"))
    rows = auswerten(daten)
    ziel = Path(bericht_file)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(bericht(daten, rows), encoding="utf-8")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scout-Gegenprobe lokal ohne Netzwerk rechnen")
    parser.add_argument("rohdaten")
    parser.add_argument("bericht")
    args = parser.parse_args(argv)
    try:
        rechnen(args.rohdaten, args.bericht)
    except Exception as err:
        print(core._hide_key(f"Abbruch: {type(err).__name__}"))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
