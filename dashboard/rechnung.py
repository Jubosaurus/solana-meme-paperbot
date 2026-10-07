"""Gemeinsame Rechenlogik fuer Dashboard und Tagesauswertung. Liest nur, schreibt nie.

Gleiche Rechnung wie die Bots in Discord:
- Hauptstrategie/Experimente: Kontowert = frei + Marktwert der offenen Positionen, Marktwert wie
  bot.portfolio_embed (Token x Kurs / SOL-Kurs - Verkaufsgebuehr). Kurs = letzter Eintrag in verlauf/.
- Copy: Kontowert = frei + copy_bot.open_value (wird direkt aus copy_bot.py benutzt).
- Korrekturen aus auswertungen/korrekturen.csv werden aus dem Copy-Journal herausgerechnet.
- Positionen, die nach einem Jupiter-Ausfall auf den Verkauf warten, zusaetzlich mit Wert 0 ("vorsichtig").

Kein Streamlit-Import: die Tests und die Tagesauswertung benutzen dieses Modul direkt.
"""
import csv
import json
import statistics
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import bot as core          # noqa: E402  (nur Konstanten, startet nichts)
import copy_bot as cb       # noqa: E402

try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:            # ohne Zeitzonen-Daten: Sommerzeit annehmen
    BERLIN = timezone(timedelta(hours=2))

START_SOL = core.START_BANKROLL_SOL
ZIEL_TRADES = 200            # Urteil ueber ein Experiment fruehestens nach 200 Trades
BESTE_WEGLASSEN = 3          # Ergebnis muss auch ohne die 3 besten Trades halten
KONTROLLE = "kontrollgruppe"
# Kostenaufschlag (Entscheidung 06.10.): Rundlauf = Kauf + Verkauf, in Prozent vom Einsatz. Messung 2 s spaeter und
# Schaetzung 06.10.: Standard 2 %, Endspurt-Konten 4 % (Graduation/Kurve-zurueck rutschen oefter). Immer roh UND mit Kosten zeigen.
KOSTEN_PCT = 2.0
KOSTEN_ENDSPURT_PCT = 4.0
ENDSPURT_KONTEN = {"endspurt", "endspurt_ohne_filter"}
EINSATZ_STANDARD = 0.2
KONTEN = [("hauptstrategie", "Hauptstrategie")] + list(core.EXPERIMENTS.items())
BOT_COMMITS = {"Hauptbot": "NARRATIV", "Copy-Bot": "COPY"}
SCOUT_HEADER = ["zeit", "wallet", "quelle", "coin", "ergebnis", "grund", "punkte", "tx", "fehlgeschlagen",
                "tx_pro_h", "inaktiv_h", "trades", "kaeufe", "verkaeufe", "trades_pro_tag", "kauf_median_sol",
                "anteil_kaeufe_ab_0_1", "coins_abgeschlossen", "trefferquote", "gewinn_sol",
                "gewinn_ohne_beste_sol", "beste_abgezogen", "rendite_median_pct", "rendite_ohne_beste_pct",
                "haltedauer_median_min", "mini_verkaeufe_anteil", "bot_gebuehr_anteil", "coins",
                "coins_gehalten", "rendite_pct", "rendite_ohne_besten_pct", "reibung_pp",
                "schnelle_verkaeufe_anteil"]


# ================================================================ Lesen

def pfad(*teile):
    return REPO.joinpath(*teile)


def lade_json(path, leer=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return leer


def lade_csv(path):
    """Alle Zeilen als dict; fehlende Datei = leere Liste."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def as_float(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


# ================================================================ Zeit und Zahlen (deutsch)

def zeitpunkt(x):
    """ISO-Text, 'JJJJ-MM-TT HH:MM:SS' (UTC) oder Unix-Zeit -> datetime in UTC (None, wenn unlesbar)."""
    if x in (None, ""):
        return None
    if isinstance(x, (int, float)):
        return datetime.fromtimestamp(x, timezone.utc)
    try:
        d = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def zeit_text(x, mit_datum=True):
    """'03.10. 14:31 UTC (16:31 dt. Zeit)'."""
    d = zeitpunkt(x)
    if d is None:
        return "–"
    de = d.astimezone(BERLIN)
    return f"{d:%d.%m.} {d:%H:%M} UTC ({de:%H:%M} dt. Zeit)" if mit_datum else \
        f"{d:%H:%M} UTC ({de:%H:%M} dt. Zeit)"


def dauer_text(sekunden):
    if sekunden is None:
        return "–"
    m = int(sekunden // 60)
    if m < 60:
        return f"{m} min"
    if m < 48 * 60:
        return f"{m // 60} h {m % 60:02d} min"
    return f"{m // 1440} Tage"


def zahl(x, stellen=3, vorzeichen=False):
    """Deutsches Zahlformat mit echtem Minuszeichen: 1234.5 -> '1.234,500'; Vorzeichen auch bei Plus."""
    if x is None:
        return "–"
    s = f"{abs(x):,.{stellen}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if s.strip("0,.") == "":
        return s                                   # gerundet null: ohne Vorzeichen
    if x < 0:
        return "−" + s
    return ("+" + s) if vorzeichen else s


def sol_text(x, stellen=3, vorzeichen=True):
    return f"{zahl(x, stellen, vorzeichen)} SOL"


# ================================================================ Hauptstrategie und Experimente

def letzte_kurse(verlauf_dir=None, tage=2):
    """Letzter aufgezeichneter Kurs (USD) je Mint aus verlauf/ (Phasen 'offen' und 'exp_<name>_offen')."""
    verlauf_dir = Path(verlauf_dir or pfad(core.VERLAUF_DIR))
    try:
        dateien = sorted(p for p in verlauf_dir.glob("*.csv"))[-tage:]
    except OSError:
        return {}
    kurse = {}
    for datei in dateien:
        for r in lade_csv(datei):
            if not str(r.get("phase", "")).endswith("offen"):
                continue
            preis = as_float(r.get("preis_usd"))
            if preis > 0 and r.get("mint"):
                kurse[r["mint"]] = (r.get("zeit", ""), preis)
    return kurse


def sol_usd_beim_kauf(pos):
    """SOL-Kurs beim Kauf, aus dem Kaufpreis zurueckgerechnet (fill_usd = Einsatz x SOL-Kurs / Token)."""
    tokens, einsatz = as_float(pos.get("tokens_initial")), as_float(pos.get("invested_sol"))
    return pos.get("entry_fill_usd", 0) * tokens / einsatz if einsatz > 0 and tokens > 0 else 0.0


def position_wert(pos, preis_usd, sol_usd):
    """Marktwert in SOL wie bot.portfolio_embed: Token x Kurs / SOL-Kurs - Verkaufsgebuehr."""
    if preis_usd <= 0 or sol_usd <= 0:
        return None
    return max(0.0, as_float(pos.get("tokens_left")) * preis_usd / sol_usd - core.TX_FEE_SOL)


def position_pnl(pos, wert):
    """Ergebnis wie bot.portfolio_embed: Erloese + Marktwert - Einsatz - Kaufgebuehr."""
    return as_float(pos.get("proceeds_sol")) + wert - as_float(pos.get("invested_sol")) - core.TX_FEE_SOL


def kosten_pct(key):
    """Kostenaufschlag je Rundlauf in Prozent vom Einsatz fuer ein Konto."""
    return KOSTEN_ENDSPURT_PCT if key in ENDSPURT_KONTEN else KOSTEN_PCT


def trade_kennzahlen(closed, kosten=None):
    """Trades, Summe, SOL je Trade, Gewinner, und dasselbe ohne die 3 besten Trades. Zusaetzlich dieselben Zahlen
    mit Kostenaufschlag (kosten = Prozent vom Einsatz je Rundlauf, Standard KOSTEN_PCT): Felder *_kosten."""
    kosten = KOSTEN_PCT if kosten is None else kosten
    pnls = sorted((as_float(c.get("pnl_sol")) for c in closed), reverse=True)
    netto = sorted((as_float(c.get("pnl_sol")) - as_float(c.get("invested_sol"), EINSATZ_STANDARD) * kosten / 100
                    for c in closed), reverse=True)
    n = len(pnls)
    rest, rest_k = pnls[BESTE_WEGLASSEN:], netto[BESTE_WEGLASSEN:]
    return {"trades": n, "summe": sum(pnls), "pro_trade": sum(pnls) / n if n else None,
            "gewinner": sum(1 for x in pnls if x > 0),
            "ohne_beste_summe": sum(rest), "ohne_beste_pro_trade": sum(rest) / len(rest) if rest else None,
            "kosten_pct": kosten, "summe_kosten": sum(netto), "pro_trade_kosten": sum(netto) / n if n else None,
            "ohne_beste_summe_kosten": sum(rest_k),
            "ohne_beste_pro_trade_kosten": sum(rest_k) / len(rest_k) if rest_k else None,
            "fortschritt": min(1.0, n / ZIEL_TRADES)}


def kosten_abzug(k):
    """Kostenaufschlag der AKTUELLEN Runde eines Strategie-Kontos in SOL. Kontowert und Ergebnis gelten nur fuer die
    laufende Runde (nach Neustart mit 10 SOL); Trades frueherer Runden (Feld runde, ohne Angabe = Runde 1) zaehlen nicht."""
    runde = k.get("runde") or 1
    return sum(as_float(c.get("invested_sol"), EINSATZ_STANDARD) * k["kosten_pct"] / 100
               for c in k["closed"] if (c.get("runde") or 1) == runde)


def kontowert_mit_kosten(k):
    """Kontowert nach Abzug des Kostenaufschlags (2 % je Rundlauf, Endspurt 4 %)."""
    return k["kontowert"] - kosten_abzug(k)


def ergebnis_mit_kosten(k):
    """Plus/Minus seit Start nach Abzug des Kostenaufschlags."""
    return k["ergebnis"] - kosten_abzug(k)


def konto_strategie(key, label, p, kurse, sol_usd=None):
    """Konto der Hauptstrategie oder eines Experiments. sol_usd=None: SOL-Kurs je Position vom Kauf
    (das Dashboard fragt keine Kurse ab). Discord rechnet mit dem aktuellen SOL-Kurs; bewegt sich SOL
    seit dem Kauf, weicht der Wert offener Positionen um diese Bewegung ab (Formel sonst gleich)."""
    p = p or {}
    offen = []
    markt = 0.0
    for pos in (p.get("positions") or {}).values():
        zeit, preis = kurse.get(pos.get("mint"), ("", 0.0))
        su = sol_usd or sol_usd_beim_kauf(pos)
        wert = position_wert(pos, preis, su) if preis else None
        pnl = position_pnl(pos, wert) if wert is not None else None
        if wert is not None:
            markt += wert
        offen.append({"symbol": pos.get("symbol", "?"), "mint": pos.get("mint", ""),
                      "seit": pos.get("opened"), "einsatz": pos.get("invested_sol", 0.0),
                      "vielfaches": preis / pos["entry_fill_usd"] if preis and pos.get("entry_fill_usd") else None,
                      # (fehlende Felder einer Position fuehren zu "kein Wert", nie zum Absturz der Seite)
                      "wert": wert, "pnl": pnl, "kurs_zeit": zeit, "haelfte_verkauft": bool(pos.get("tp1_done"))})
    closed = p.get("closed") or []
    frei = as_float(p.get("bankroll_sol"), START_SOL)
    kontowert = frei + markt
    beendet = getattr(core, "EXP_BEENDET", {}).get(key)
    return {"key": key, "label": label + (f" (beendet {beendet})" if beendet else ""), "beendet": beendet,
            "frei": frei, "markt": markt, "kontowert": kontowert,
            "ergebnis": kontowert - START_SOL, "runde": p.get("runde"), "gestartet": p.get("started"),
            "gespeichert": p.get("saved_at"), "offen": offen, "closed": closed, **trade_kennzahlen(closed, kosten_pct(key))}


def alle_strategie_konten(repo=None):
    repo = Path(repo or REPO)
    kurse = letzte_kurse(repo / core.VERLAUF_DIR)
    konten = []
    for key, label in KONTEN:
        datei = repo / (core.PORTFOLIO_FILE if key == "hauptstrategie" else Path(core.EXP_DIR) / key / "portfolio.json")
        konten.append(konto_strategie(key, label, lade_json(datei, {}), kurse))
    return konten


def vergleich_mit_kontrolle(konto, kontrolle):
    """Testregel: gegen die Kontrollgruppe aus demselben Zeitraum, Urteil erst ab 200 Trades und nur,
    wenn es auch ohne die 3 besten Trades haelt. Ergebnis: Ampel + Kennzahlen beider Seiten."""
    if konto["key"] == KONTROLLE:
        return {"ampel": "basis", "text": "Vergleichsbasis"}
    beginn = max(filter(None, [zeitpunkt(konto.get("gestartet")), zeitpunkt(kontrolle.get("gestartet"))]),
                 default=None)
    eigene = [c for c in konto["closed"] if beginn is None or (zeitpunkt(c.get("closed_at")) or beginn) >= beginn]
    kg = [c for c in kontrolle["closed"] if beginn is None or (zeitpunkt(c.get("closed_at")) or beginn) >= beginn]
    a, b = trade_kennzahlen(eigene, kosten_pct(konto["key"])), trade_kennzahlen(kg, kosten_pct(kontrolle["key"]))
    # "im Plus" bezieht sich auf dieselben Trades wie das Urteil (Vergleichszeitraum), nicht auf den Kontowert
    res = {"beginn": beginn, "eigen": a, "kontrolle": b, "im_plus": a["summe"] > 0}
    if not a["trades"] or not b["trades"]:
        return {**res, "ampel": "keine_daten", "text": "noch keine Trades zum Vergleichen"}
    roh = _urteil(a, b, "")
    kosten = _urteil(a, b, "_kosten")
    return {**res, **roh, "kosten": {**kosten, "im_plus": a["summe_kosten"] > 0}}


def _urteil(a, b, suffix):
    """Ampel und Text fuer eine Zahlenart (suffix '' = roh, '_kosten' = mit Kostenaufschlag)."""
    besser = a["pro_trade" + suffix] > b["pro_trade" + suffix]
    besser_ohne = (a["ohne_beste_pro_trade" + suffix] or 0) > (b["ohne_beste_pro_trade" + suffix] or 0)
    if a["trades"] < ZIEL_TRADES:
        tendenz = "besser" if besser and besser_ohne else "schlechter" if not besser and not besser_ohne else "gemischt"
        return {"ampel": "zu_frueh", "tendenz": tendenz,
                "text": f"zu früh: {a['trades']} von {ZIEL_TRADES} Trades im Vergleichszeitraum, Tendenz {tendenz}"}
    if besser and besser_ohne:
        return {"ampel": "besser", "text": "besser als die Kontrollgruppe, auch ohne die 3 besten"}
    if not besser and not besser_ohne:
        return {"ampel": "schlechter", "text": "schlechter als die Kontrollgruppe"}
    return {"ampel": "gemischt", "text": "nur mit den 3 besten Trades besser – hält nicht"
            if besser else "ohne die 3 besten besser, mit ihnen schlechter"}


PAAR_EXPERIMENTE = {"notbremse_25", "drittel_leiter"}   # kaufen genau mit der Hauptstrategie (gleiche Kaeufe)


def paarvergleich(exp_closed, haupt_closed, toleranz_s=600):
    """Coin fuer Coin: abgeschlossene Trades eines Paar-Experiments gegen denselben Kauf der Hauptstrategie
    (gleiche Mint, Kauf hoechstens 10 min auseinander). Nur Paare, die auf beiden Seiten abgeschlossen sind."""
    def kauf(c):
        zu = zeitpunkt(c.get("closed_at"))
        return zu.timestamp() - as_float(c.get("hold_h")) * 3600 if zu else None
    haupt = {}
    for c in haupt_closed or []:
        haupt.setdefault(c.get("mint"), []).append(c)
    paare = []
    for c in exp_closed or []:
        k = kauf(c)
        treffer = [h for h in haupt.get(c.get("mint"), [])
                   if k is not None and kauf(h) is not None and abs(kauf(h) - k) <= toleranz_s]
        if not treffer:
            continue
        h = min(treffer, key=lambda x: abs(kauf(x) - k))
        e_pnl, h_pnl = as_float(c.get("pnl_sol")), as_float(h.get("pnl_sol"))
        paare.append({"symbol": c.get("symbol", "?"), "mint": c.get("mint"), "kauf": k,
                      "experiment": e_pnl, "haupt": h_pnl, "differenz": e_pnl - h_pnl,
                      "grund_experiment": c.get("exit_reason", ""), "grund_haupt": h.get("exit_reason", "")})
    diffs = sorted((x["differenz"] for x in paare), reverse=True)
    return {"paare": sorted(paare, key=lambda x: x["kauf"] or 0, reverse=True), "anzahl": len(paare),
            "summe_experiment": sum(x["experiment"] for x in paare), "summe_haupt": sum(x["haupt"] for x in paare),
            "differenz": sum(diffs), "differenz_ohne_beste": sum(diffs[BESTE_WEGLASSEN:]),
            "besser": sum(1 for d in diffs if d > 1e-9), "schlechter": sum(1 for d in diffs if d < -1e-9),
            "gleich": sum(1 for d in diffs if abs(d) <= 1e-9)}


def urteil_kurz(v):
    """Kurzes Urteil: besser/schlechter als Zufall (Kontrollgruppe) UND im Plus/Minus getrennt,
    z. B. 'besser als Zufall, aber im Minus'. Plus/Minus = Summe der verglichenen Trades."""
    a = v.get("ampel")
    if a == "basis":
        return "Vergleichsbasis (Zufall)"
    if a == "keine_daten":
        return "noch keine Trades"
    plus = v.get("im_plus")
    if a == "zu_frueh":
        return f"zu früh · Tendenz {v['tendenz']} als Zufall · {'im Plus' if plus else 'im Minus'}"
    if a == "besser":
        return "besser als Zufall, im Plus" if plus else "besser als Zufall, aber im Minus"
    if a == "schlechter":
        return "schlechter als Zufall, aber im Plus" if plus else "schlechter als Zufall, im Minus"
    return "hält nicht (nur dank der 3 besten), " + ("im Plus" if plus else "im Minus")


def urteil_beide(v):
    """Urteil roh und mit Kostenaufschlag nebeneinander: 'roh: ... | mit Kosten: ...'."""
    roh = urteil_kurz(v)
    k = v.get("kosten")
    if not k:
        return roh
    return f"roh: {roh} | mit Kosten: {urteil_kurz({**v, **k})}"


def ausreisser(beitraege, anteil=0.5):
    """Einzelne Konten/Trader, die mehr als die Haelfte des Gesamtergebnisses ausmachen (gleiches Vorzeichen).
    beitraege: [(name, ergebnis)]. Rueckgabe: [(name, ergebnis, anteil am Gesamtergebnis)]."""
    gesamt = sum(x for _, x in beitraege)
    if abs(gesamt) < 1e-9:
        return []
    return [(n, x, x / gesamt) for n, x in beitraege
            if x * gesamt > 0 and abs(x) > anteil * abs(gesamt)]


def kontoverlauf(konto):
    """Kontostand nach jedem geschlossenen Trade (10 SOL + Summe der Ergebnisse), fuer das Diagramm."""
    punkte = [(zeitpunkt(konto.get("gestartet")), 0.0)]
    for c in sorted(konto["closed"], key=lambda c: c.get("closed_at") or ""):
        punkte.append((zeitpunkt(c.get("closed_at")), as_float(c.get("pnl_sol"))))
    stand, out = START_SOL, []
    for t, pnl in punkte:
        if t is None:
            continue
        stand += pnl
        out.append({"zeit": t, "kontostand": stand})
    return out


# ================================================================ Copy Trading

def korrekturen(repo=None):
    return lade_csv(Path(repo or REPO) / "auswertungen" / "korrekturen.csv")


def _korr_schluessel(r):
    return (r.get("trader", ""), r.get("trader_signatur", ""), r.get("aktion", ""), r.get("zeit", ""))


def journal_bereinigen(rows, korr):
    """Copy-Journal ohne die Zeilen aus auswertungen/korrekturen.csv (Fehlbuchungen bis 03.10.)."""
    weg = {_korr_schluessel(k) for k in korr}
    return [r for r in rows if _korr_schluessel(r) not in weg]


def korrigierte_positionen(korr):
    """(Trader, Mint) mit doppelten Verkaeufen: nicht in den Vergleich 'wir gegen Trader' nehmen."""
    return {(k["trader"], k["mint"]) for k in korr if k.get("art") in ("doppelter_verkauf", "doppelt_geschlossen")}


def aktive_wallets(repo=None):
    try:
        return cb.load_wallets(str(Path(repo or REPO) / cb.WALLET_FILE))
    except OSError:
        return []


def _ts(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def exit_liquiditaet(journal_rows):
    """Je Trader: Wie oft verkauft er schnell nach seinem Kauf, waehrend wir noch kaufen (wir = Exit-Liquiditaet)?
    Rueckgabe {Trader: {kaeufe, raus_vor_uns, raus_60s, median_halte_s}} aus den Trader-Zeiten im Journal."""
    verk = {}
    for x in journal_rows:
        if x.get("aktion") in ("VERKAUF", "VERKAUF_GEMERKT", "SCHATTEN_VERKAUF", "UEBERWEISUNG") and x.get("trader_zeit"):
            t = _ts(x["trader_zeit"])
            if t:
                verk.setdefault((x.get("trader"), x.get("mint")), []).append(t)
    erg = {}
    for x in journal_rows:
        if x.get("aktion") != "KAUF" or not x.get("trader_zeit"):
            continue
        tk, wir = _ts(x["trader_zeit"]), _ts(x.get("zeit"))
        if tk is None:
            continue
        e = erg.setdefault(x["trader"], {"kaeufe": 0, "raus_vor_uns": 0, "raus_60s": 0, "_halte": []})
        e["kaeufe"] += 1
        spaeter = sorted(t for t in verk.get((x["trader"], x.get("mint")), []) if t >= tk)
        if spaeter:
            e["_halte"].append(spaeter[0] - tk)
            e["raus_60s"] += spaeter[0] - tk <= 60
            e["raus_vor_uns"] += wir is not None and spaeter[0] <= wir
    for e in erg.values():
        e["median_halte_s"] = statistics.median(e.pop("_halte")) if e["_halte"] else None
    return erg


def copy_konto(name, acct, aktiv, journal_rows, korrigiert, exit_liq=None):
    wert = cb.open_value(acct)                                    # gleiche Rechnung wie die Konto-Zeile in Discord
    wartend = [p for p in acct.get("positionen", {}).values() if p.get("verkauf_offen")]
    wert_wartend = cb.open_value({"positionen": {p["mint"]: p for p in wartend}}) if wartend else 0.0
    frei = as_float(acct.get("bankroll_sol"))
    geschlossen = acct.get("geschlossen") or []
    runde = acct.get("runde", 1)
    in_runde = [g for g in geschlossen if g.get("runde") == runde]
    paare = [(g["pnl_pct"], g["trader_pnl_pct"]) for g in geschlossen
             if g.get("trader_pnl_pct") is not None and (name, g.get("mint")) not in korrigiert]
    verz = [as_float(r.get("verzoegerung_s"), None) for r in journal_rows
            if r.get("trader") == name and r.get("aktion") == "KAUF" and r.get("verzoegerung_s")]
    verz = [v for v in verz if v is not None]
    abstand = [as_float(r.get("preisabstand_pct"), None) for r in journal_rows
               if r.get("trader") == name and r.get("aktion") == "KAUF" and r.get("preisabstand_pct")]
    abstand = [a for a in abstand if a is not None]
    schatten = acct.get("schatten_geschlossen") or []
    # Ergebnis seit Start ueber alle Runden: je Position Erloese + Wert jetzt - Einsatz - Gebuehren.
    # (Kontowert - 10 SOL gilt nur fuer die laufende Runde; beim Rundenwechsel wird das Konto neu aufgefuellt.)
    offen_pnl = offen_pnl_vorsichtig = 0.0
    for p in (acct.get("positionen") or {}).values():
        w = cb.open_value({"positionen": {p.get("mint", ""): p}})
        basis = as_float(p.get("proceeds_sol")) - as_float(p.get("invested_sol")) - as_float(p.get("fees_sol"))
        offen_pnl += basis + w
        offen_pnl_vorsichtig += basis + (0.0 if p.get("verkauf_offen") else w)
    pnl_zu = sum(as_float(g.get("pnl_sol")) for g in geschlossen)
    return {
        "ergebnis_seit_start": pnl_zu + offen_pnl, "ergebnis_seit_start_vorsichtig": pnl_zu + offen_pnl_vorsichtig,
        "name": name, "aktiv": aktiv, "adresse": acct.get("adresse", ""), "runde": runde,
        "frei": frei, "wert_offen": wert, "kontowert": frei + wert, "vorsichtig": frei + wert - wert_wartend,
        "wartend": len(wartend), "ergebnis_runde": frei + wert - START_SOL,
        "offen": len(acct.get("positionen") or {}), "geschlossen": len(geschlossen),
        "geschlossen_runde": len(in_runde), "pnl_geschlossen": sum(as_float(g.get("pnl_sol")) for g in geschlossen),
        "wir_median_pct": statistics.median([a for a, _ in paare]) if paare else None,
        "trader_median_pct": statistics.median([b for _, b in paare]) if paare else None,
        "vergleiche": len(paare),
        "verzoegerung_median_s": statistics.median(verz) if verz else None,
        "preisabstand_median_pct": statistics.median(abstand) if abstand else None,
        "schatten": len(schatten), "schatten_pnl": sum(as_float(s.get("pnl_sol")) for s in schatten),
        "letzter_trade": acct.get("letzter_trade"), "korrigiert": any(t == name for t, _ in korrigiert),
        "exit_liq": (exit_liq or {}).get(name),
    }


def copy_konten(repo=None):
    repo = Path(repo or REPO)
    data = lade_json(repo / cb.ACCOUNTS_FILE, {}) or {}
    aktiv = {n for n, _ in aktive_wallets(repo)}
    korr = korrekturen(repo)
    rows = journal_bereinigen(lade_csv(repo / cb.JOURNAL_FILE), korr)
    korrigiert = korrigierte_positionen(korr)
    exit_liq = exit_liquiditaet(rows)
    konten = [copy_konto(n, a, n in aktiv, rows, korrigiert, exit_liq) for n, a in (data.get("wallets") or {}).items()]
    return sorted(konten, key=lambda k: -k["kontowert"]), data.get("saved_at"), rows


# ================================================================ Scout

def scout_rangliste(repo=None):
    """Neueste Bewertung je Wallet nach aktueller Bewertung (32 Spalten). Aeltere Zeilen mit anderem
    Spaltenaufbau werden ignoriert (Spalten in kandidaten.csv nicht durchgaengig gleich, Pruefbericht 03.10.)."""
    try:
        with open(Path(repo or REPO) / "scout" / "kandidaten.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
    except OSError:
        return []
    neueste = {}
    for r in rows[1:]:
        if len(r) not in (len(SCOUT_HEADER), len(SCOUT_HEADER) - 1):   # 33 Spalten, aeltere Zeilen 32
            continue
        d = dict(zip(SCOUT_HEADER, r))
        if d["wallet"] and d["zeit"] >= neueste.get(d["wallet"], {}).get("zeit", ""):
            neueste[d["wallet"]] = d
    return sorted(neueste.values(), key=lambda d: (d["ergebnis"] != "bewertet", -as_float(d["punkte"], -1e9)))


# ================================================================ Betrieb

def commit_zeiten(repo=None, stunden=48):
    """Zeitpunkte der Daten-Commits je Bot (die Bots pushen etwa jede Minute)."""
    try:
        out = subprocess.run(["git", "log", f"--since={stunden} hours ago", "--format=%ct %s", "origin/main"],
                             cwd=repo or REPO, capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    zeiten = {bot: [] for bot in BOT_COMMITS}
    for line in out.splitlines():
        ts, _, msg = line.partition(" ")
        for bot, marke in BOT_COMMITS.items():
            if msg.startswith(marke) and ts.isdigit():
                zeiten[bot].append(int(ts))
    return {bot: sorted(t) for bot, t in zeiten.items()}


def luecken(zeiten, grenze_min=20, jetzt=None):
    """Abstaende ueber der Grenze zwischen aufeinanderfolgenden Zeitpunkten, plus die laufende Luecke bis jetzt."""
    zeiten = sorted(zeiten)
    out = [(a, b) for a, b in zip(zeiten, zeiten[1:]) if b - a > grenze_min * 60]
    if jetzt is not None and zeiten and jetzt - zeiten[-1] > grenze_min * 60:
        out.append((zeiten[-1], None))
    return out


def bot_status(letzte, jetzt):
    """ok: Daten juenger als 15 min; achtung: bis 60 min; kaputt: aelter oder keine."""
    if letzte is None:
        return "kaputt"
    alter = jetzt - letzte
    return "ok" if alter <= 15 * 60 else "achtung" if alter <= 60 * 60 else "kaputt"


def scout_letzter_lauf(repo=None):
    rows = scout_rangliste(repo)
    zeiten = [z for z in (zeitpunkt(r.get("zeit")) for r in rows) if z is not None]
    return max(zeiten).timestamp() if zeiten else None


def messung(repo=None):
    """Messung seit 03.10.: Quote 2 s spaeter (+ = schlechter fuer uns), je Datei Median und Anzahl."""
    repo = Path(repo or REPO)
    out = {}
    for name, datei in (("Hauptbot und Experimente", repo / "messung.csv"), ("Copy-Bot", repo / cb.MESSUNG_FILE)):
        werte = [as_float(r.get("abweichung_pct"), None) for r in lade_csv(datei)]
        werte = sorted(w for w in werte if w is not None)
        out[name] = {"anzahl": len(werte), "median": statistics.median(werte) if werte else None,
                     "p90": werte[int(len(werte) * 0.9)] if werte else None}
    notl = 0
    for key, _ in KONTEN:
        datei = repo / (core.JOURNAL_FILE if key == "hauptstrategie" else Path(core.EXP_DIR) / key / "journal.csv")
        notl += sum(1 for r in lade_csv(datei) if r.get("notloesung") == "1")
    out["notloesung"] = notl
    return out


def git_pull(repo=None):
    """Neueste Daten holen (nur lesen). Rueckgabe: (ok, Meldung, HEAD)."""
    repo = repo or REPO
    try:
        res = subprocess.run(["git", "pull", "--ff-only", "-q"], cwd=repo, capture_output=True, text=True,
                             timeout=120)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError) as err:
        return False, str(err)[:200], ""
    return res.returncode == 0, (res.stderr or res.stdout).strip()[:300], head


# ================================================================ Ausfuehrungskosten (Messung)

def _schlechteste_zehntel(werte_sortiert):
    """Mittelwert der schlechtesten 10 % (mindestens 1 Wert); werte aufsteigend sortiert, + = schlechter fuer uns."""
    n = max(1, round(len(werte_sortiert) * 0.1))
    return statistics.mean(werte_sortiert[-n:])


def messung_detail(repo=None):
    """Ausfuehrungskosten je Quelle und Aktion (nur KAUF/VERKAUF): Anzahl, Median, schlechteste 10 %
    (Mittel und Schwelle), tatsaechlicher Abstand der zweiten Quote in Sekunden. + = 2 s spaeter schlechter."""
    repo = Path(repo or REPO)
    out = []
    for quelle, datei in (("Hauptbot und Experimente", repo / "messung.csv"), ("Copy-Bot", repo / cb.MESSUNG_FILE)):
        rows = lade_csv(datei)
        for aktion in ("KAUF", "VERKAUF"):
            je = [(as_float(r.get("abweichung_pct"), None), as_float(r.get("sekunden"), None))
                  for r in rows if r.get("aktion") == aktion]
            werte = sorted(w for w, _ in je if w is not None)
            sek = sorted(s for _, s in je if s is not None)
            out.append({
                "quelle": quelle, "aktion": aktion, "anzahl": len(werte),
                "median": statistics.median(werte) if werte else None,
                "schlechteste_10": _schlechteste_zehntel(werte) if werte else None,
                "schwelle_10": werte[min(len(werte) - 1, int(len(werte) * 0.9))] if werte else None,
                "median_s": statistics.median(sek) if sek else None,
                "max_s": sek[-1] if sek else None,
                "schlechter_5": sum(1 for w in werte if w > 5) / len(werte) if werte else None,
            })
    return out


# ================================================================ Flugschreiber

FLUG_ZAHLEN = ["minuten_seit_kauf", "vielfaches", "liquiditaet", "holder", "top10_pct", "dev_pct",
               "netto_kaeufer_5m", "block0_gehalten_pct"]


def _journal_pfad(repo, konto):
    return Path(repo) / (core.JOURNAL_FILE if konto == "hauptstrategie" else Path(core.EXP_DIR) / konto / "journal.csv")


def flug_zeilen(repo=None):
    """Alle Messpunkte aus flugschreiber/*.csv (Aufzeichnung ~1/min je offene Position)."""
    repo = Path(repo or REPO)
    rows = []
    for datei in sorted((repo / core.FLUG_DIR).glob("*.csv")):
        rows += lade_csv(datei)
    return rows


def flug_coins(rows, repo=None):
    """Je (Konto, Coin): Symbol, Anzahl Messpunkte, erste/letzte Zeit, Verkaufsgrund und Ergebnis aus dem Journal."""
    repo = Path(repo or REPO)
    coins = {}
    for r in rows:
        c = coins.setdefault((r["konto"], r["mint"]), {"konto": r["konto"], "mint": r["mint"],
                                                      "symbol": r.get("symbol", "?"), "punkte": 0, "von": r["zeit"],
                                                      "bis": r["zeit"]})
        c["punkte"] += 1
        c["von"], c["bis"] = min(c["von"], r["zeit"]), max(c["bis"], r["zeit"])
    for konto in {k for k, _ in coins}:
        je_mint = {}
        for j in lade_csv(_journal_pfad(repo, konto)):
            if j.get("aktion") == "VERKAUF":
                je_mint.setdefault(j.get("mint"), []).append(j)
        for (k, mint), c in coins.items():
            if k == konto and mint in je_mint:
                c["verkauf_grund"] = je_mint[mint][-1].get("grund", "")
                c["pnl_sol"] = sum(as_float(j.get("pnl_sol")) for j in je_mint[mint])
    return sorted(coins.values(), key=lambda c: c["bis"], reverse=True)


def flug_verlauf(rows, konto, mint):
    """Messpunkte eines Coins mit Zahlen (leere Felder = None), nach Zeit sortiert."""
    out = []
    for r in sorted((r for r in rows if r["konto"] == konto and r["mint"] == mint), key=lambda r: r["zeit"]):
        d = {"zeit": r["zeit"]}
        for k in FLUG_ZAHLEN:
            d[k] = as_float(r.get(k), None)
        out.append(d)
    return out


def flug_verkaeufe(konto, mint, repo=None):
    """Verkaeufe eines Coins aus dem Journal mit Minuten seit dem ersten Kauf: [{minuten, grund, pnl_pct}]."""
    rows = [j for j in lade_csv(_journal_pfad(repo or REPO, konto)) if j.get("mint") == mint]
    kaeufe = [zeitpunkt(j["zeit"]) for j in rows if j.get("aktion") == "KAUF" and zeitpunkt(j.get("zeit"))]
    if not kaeufe:
        return []
    start = min(kaeufe)
    out = []
    for j in rows:
        t = zeitpunkt(j.get("zeit"))
        if j.get("aktion") == "VERKAUF" and t:
            out.append({"minuten": (t - start).total_seconds() / 60, "grund": j.get("grund", ""),
                        "pnl_pct": as_float(j.get("pnl_pct"), None)})
    return out


# ================================================================ Was ist neu

DATEN_COMMITS = ("NARRATIV", "COPY", "SCOUT")
ADRESSE_TEXT = r"[1-9A-HJ-NP-Za-km-z]{32,44}"


def _git_text(repo, *args):
    try:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace").stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def wallet_aenderungen(ab, repo=None):
    """Aus der Git-Historie seit ab (Unix): aufgenommene und entfernte Copy-Wallets, neue Adressen in der Pruefliste."""
    import re
    repo = repo or REPO
    out = {"aufgenommen": [], "entfernt": [], "geprueft_neu": 0}
    text = _git_text(repo, "log", f"--since=@{int(ab)}", "-p", "--format=", "--", "copy_wallets.txt")
    auto = None                     # Kommentar der Scout-Automatik vor einer neuen Zeile: "# 05.10. automatisch aufgenommen: ..."
    for zeile in text.splitlines():
        if zeile.startswith("+++") or not zeile.startswith("+"):
            continue
        z = zeile[1:].strip()
        if z.startswith("#"):
            m = re.match(rf"#\s*([^:]{{1,40}}):\s*{ADRESSE_TEXT}\s*<-\s*(.*)", z)
            if m:
                out["entfernt"].append(f"{m.group(1).strip()}: {m.group(2).strip()}")
            m = re.match(r"#\s*\d\d\.\d\d\.\s*automatisch aufgenommen:\s*(.*)", z)
            auto = m.group(1).strip() if m else None
        else:
            m = re.match(rf"^([^:#]{{1,40}}):\s*{ADRESSE_TEXT}", z)
            if m:
                out["aufgenommen"].append(m.group(1).strip() + (f" (automatisch: {auto})" if auto else ""))
            auto = None
    liste = _git_text(repo, "log", f"--since=@{int(ab)}", "-p", "--format=", "--", "scout/pruefen.txt")
    out["geprueft_neu"] = sum(1 for z in liste.splitlines() if z.startswith("+") and not z.startswith("+++")
                              and re.search(ADRESSE_TEXT, z))
    return out


def projekt_commits(ab, repo=None):
    """Commits seit ab, die keine Daten-Updates der Bots sind: [(Zeit Unix, Text)] neueste zuerst."""
    out = _git_text(repo or REPO, "log", f"--since=@{int(ab)}", "--format=%ct\t%s")
    erg = []
    for z in out.splitlines():
        ts, _, msg = z.partition("\t")
        if ts.isdigit() and not msg.startswith(DATEN_COMMITS):
            erg.append((int(ts), msg))
    return erg


def neu_seit(ab, strategie_konten, copy_zeilen, copy_konten_liste, jetzt, repo=None):
    """Was ist seit ab (Unix, UTC) passiert? Rein lesend, aus schon geladenen Konten, Journal und Git-Historie."""
    trades = []
    for k in strategie_konten:
        neue = [c for c in k["closed"]
                if (zeitpunkt(c.get("closed_at")) or datetime.fromtimestamp(0, timezone.utc)).timestamp() >= ab]
        if neue:
            trades.append({"konto": k["label"], "trades": len(neue),
                           "summe": sum(as_float(c.get("pnl_sol")) for c in neue)})
    je_trader = {}
    for r in copy_zeilen:
        t = zeitpunkt(r.get("zeit"))
        if t and t.timestamp() >= ab and r.get("aktion") in ("KAUF", "VERKAUF"):
            d = je_trader.setdefault(r.get("trader", "?"), {"KAUF": 0, "VERKAUF": 0})
            d[r["aktion"]] += 1
    auffaellig = []
    for c in copy_konten_liste:
        if not c["aktiv"]:
            continue
        if not c.get("letzter_trade"):
            auffaellig.append(f"Copy {c['name']}: noch nie ein Trade")
        elif jetzt - as_float(c["letzter_trade"]) > 72 * 3600:
            auffaellig.append(f"Copy {c['name']}: seit über 72 h kein Trade")
    beendet = []
    for name, datum in getattr(core, "EXP_BEENDET", {}).items():       # Datum als "04.10." (Jahr = aktuelles)
        try:
            tag = datetime.strptime(f"{datum.strip().rstrip('.')}.{datetime.fromtimestamp(jetzt, timezone.utc).year}",
                                    "%d.%m.%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if tag.timestamp() + 86400 > ab:
            beendet.append((name, datum))
    return {"trades": trades, "copy": je_trader, "beendete_experimente": beendet,
            "wallets": wallet_aenderungen(ab, repo), "commits": projekt_commits(ab, repo), "auffaellig": auffaellig}


# ================================================================ Lernen: Urteils-Kalender, Verlust-Lupe, Filter-Trichter

def urteils_kalender(konten, jetzt, tempo_tage=3):
    """Je Experiment: Trades im Vergleichszeitraum (wie das Testurteil), Tempo der letzten Tage und
    voraussichtliches Datum, an dem 200 Trades erreicht sind. Beendete Experimente und die Kontrollgruppe fehlen."""
    out = []
    for k in konten:
        v = k.get("vergleich") or {}
        if k["key"] == KONTROLLE or k.get("beendet"):
            continue
        beginn = v.get("beginn")
        geschlossen = [zeitpunkt(c.get("closed_at")) for c in k["closed"]]
        geschlossen = [t for t in geschlossen if t and (beginn is None or t >= beginn)]
        n = len(geschlossen)
        neu = sum(1 for t in geschlossen if t.timestamp() >= jetzt - tempo_tage * 86400)
        tempo = neu / tempo_tage
        rest = max(0, ZIEL_TRADES - n)
        if rest == 0:
            eta = jetzt
        elif tempo > 0:
            eta = jetzt + rest / tempo * 86400
        else:
            eta = None
        out.append({"key": k["key"], "label": k["label"], "trades": n, "rest": rest, "tempo_pro_tag": tempo,
                    "eta": eta, "tage_bis_urteil": None if eta is None else (eta - jetzt) / 86400,
                    "anteil": min(1.0, n / ZIEL_TRADES), "ampel": v.get("ampel"),
                    "urteil": urteil_kurz(v) if v else ""})
    return sorted(out, key=lambda x: (x["eta"] is None, x["eta"] or 0))


# Merkmale beim Kauf, die sich als Spur fuer neue Regeln eignen: (Name, Weg im closed-Eintrag, Einheit)
LUPE_MERKMALE = [
    ("Alter h", ("entry_view", "age_h"), ""),
    ("Marktwert $", ("entry_view", "mcap"), ""),
    ("Liquidität $", ("entry_view", "liquidity"), ""),
    ("Holder", ("entry_view", "holders"), ""),
    ("Holder +1h %", ("entry_view", "holder_growth_1h"), " %"),
    ("Kurs 5 min %", ("entry_view", "price_change_5m"), " %"),
    ("Kurs 1 h %", ("entry_view", "price_change_1h"), " %"),
    ("Netto-Käufer 5 min", ("entry_view", "net_buyers_5m"), ""),
    ("Organisch-Score", ("entry_view", "organic_score"), ""),
    ("Top-10 %", ("entry_view", "top_holders_pct"), " %"),
    ("Dev %", ("entry_view", "dev_balance_pct"), " %"),
    ("Block 0 gekauft %", ("bundle", "block0_supply_pct"), " %"),
    ("Bundler % (Tracker)", ("solana_tracker", "bundlers_pct"), " %"),
    ("Sniper % (Tracker)", ("solana_tracker", "snipers_pct"), " %"),
]
GEWINN_VERSCHENKT_AB = 1.5      # Hoch mindestens 1,5x, Ende im Minus


def _merkmal(c, weg):
    x = c
    for teil in weg:
        x = x.get(teil) if isinstance(x, dict) else None
    return as_float(x, None)


def grund_kurz(text):
    """'GEWINN_GESCHUETZT (Hoch 1.5x, ...)' -> 'GEWINN_GESCHUETZT'."""
    return (text or "?").split(" (")[0].strip() or "?"


def lupe_trades(konten):
    """Alle abgeschlossenen Trades aller Konten als flache Zeilen (fuer Filter und Tabellen)."""
    out = []
    for k in konten:
        for c in k["closed"]:
            pnl = as_float(c.get("pnl_sol"))
            hoch = as_float(c.get("peak_multiple"), None)
            z = {"konto": k["label"], "key": k["key"], "symbol": c.get("symbol", "?"), "mint": c.get("mint", ""),
                 "pnl_sol": pnl, "pnl_pct": as_float(c.get("pnl_pct"), None), "hoch": hoch,
                 "grund": grund_kurz(c.get("exit_reason")), "grund_lang": c.get("exit_reason", ""),
                 "halte_h": as_float(c.get("hold_h"), None), "zeit": c.get("closed_at"),
                 "phase": c.get("phase") or "?", "verschenkt": pnl < 0 and (hoch or 0) >= GEWINN_VERSCHENKT_AB}
            for name, weg, _ in LUPE_MERKMALE:
                z[name] = _merkmal(c, weg)
            out.append(z)
    return out


def lupe_vergleich(trades):
    """Median je Merkmal: Verlierer gegen Gewinner, mit Anzahl Werte (fehlende Felder zaehlen nicht)."""
    verlierer = [t for t in trades if t["pnl_sol"] < 0]
    gewinner = [t for t in trades if t["pnl_sol"] > 0]
    out = []
    for name, _, einheit in LUPE_MERKMALE:
        v = [t[name] for t in verlierer if t[name] is not None]
        g = [t[name] for t in gewinner if t[name] is not None]
        mv = statistics.median(v) if v else None
        mg = statistics.median(g) if g else None
        out.append({"merkmal": name, "einheit": einheit, "verlierer": mv, "gewinner": mg,
                    "n_verlierer": len(v), "n_gewinner": len(g),
                    "abstand_pct": (mv - mg) / abs(mg) * 100 if mv is not None and mg not in (None, 0) else None})
    return {"verlierer": len(verlierer), "gewinner": len(gewinner), "merkmale": out}


def lupe_gruende(trades):
    """Je Verkaufsgrund: Anzahl, Summe, Anteil Verlierer, schlechtester Trade. Schlechteste Summe zuerst."""
    je = {}
    for t in trades:
        d = je.setdefault(t["grund"], {"grund": t["grund"], "trades": 0, "summe": 0.0, "verlierer": 0,
                                       "schlechtester": 0.0})
        d["trades"] += 1
        d["summe"] += t["pnl_sol"]
        d["verlierer"] += t["pnl_sol"] < 0
        d["schlechtester"] = min(d["schlechtester"], t["pnl_sol"])
    for d in je.values():
        d["anteil_verlierer"] = d["verlierer"] / d["trades"]
    return sorted(je.values(), key=lambda d: d["summe"])


def ablehnungs_dateien(repo=None):
    """Alte Gesamtdatei abgelehnt.csv (bis 07.10.) und Tagesdateien abgelehnt/JJJJ-MM-TT.csv (seit 08.10.)."""
    return [Path(p) for p in core.reject_files(Path(repo or REPO))]


def filter_trichter(repo=None, tage=7, jetzt=None):
    """Hauptstrategie: abgelehnte Coins je Grund (Pruefungen und verschiedene Coins) und Kaeufe, je Tag (UTC).
    tage = Kalendertage einschliesslich heute (1 = nur heute)."""
    repo = Path(repo or REPO)
    jetzt = jetzt or datetime.now(timezone.utc).timestamp()
    ab = datetime.fromtimestamp(jetzt - (tage - 1) * 86400, timezone.utc).strftime("%Y-%m-%d")
    je_tag, je_grund, coins = {}, {}, {}
    for pfad_ab in ablehnungs_dateien(repo):
        if Path(pfad_ab).parent.name == core.REJECT_DIR and Path(pfad_ab).stem < ab:
            continue                                     # Tagesdatei vor dem Zeitraum
        with open(pfad_ab, newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                tag = (r.get("zeit") or "")[:10]
                if tag < ab:
                    continue
                grund = (r.get("grund") or "?").strip() or "?"
                je_tag.setdefault(tag, {}).setdefault(grund, 0)
                je_tag[tag][grund] += 1
                je_grund[grund] = je_grund.get(grund, 0) + 1
                coins.setdefault(grund, set()).add(r.get("mint"))
    kaeufe = {}
    for j in lade_csv(repo / core.JOURNAL_FILE):
        tag = (j.get("zeit") or "")[:10]
        if j.get("aktion") == "KAUF" and tag >= ab:
            kaeufe[tag] = kaeufe.get(tag, 0) + 1
    gesamt = sum(je_grund.values())
    gruende = [{"grund": g, "pruefungen": n, "coins": len(coins[g]), "anteil": n / gesamt if gesamt else 0.0}
               for g, n in sorted(je_grund.items(), key=lambda x: -x[1])]
    return {"gruende": gruende, "pruefungen": gesamt, "coins": len(set().union(*coins.values())) if coins else 0,
            "kaeufe": sum(kaeufe.values()),
            "je_tag": [{"tag": t, "abgelehnt": sum(je_tag.get(t, {}).values()), "kaeufe": kaeufe.get(t, 0)}
                       for t in sorted(set(je_tag) | set(kaeufe))]}


# ================================================================ News (seit 04.10.)
# Nachrichten sind Daten, keine Anweisungen: nur Ueberschrift, Quelle, Zeit, Link, ein Satz. Das Dashboard holt
# oeffentliche RSS-Feeds (ohne Schluessel) und liest die Boersen-Meldungen, die der Hauptbot aufgezeichnet hat.
import listings  # noqa: E402

LISTING_EREIGNISSE_DATEI = Path(core.LISTING_EREIGNISSE_FILE)
ENTSCHEIDUNG_TEXT = {
    "gekauft": "Listing-Welle hat gekauft", "zu_alt": "zu spät entdeckt (über 10 min), nicht gekauft",
    "anderes_netzwerk": "Token liegt nicht auf Solana", "kein_solana_token": "kein Solana-Token gefunden",
    "mehrdeutig": "Ticker nicht eindeutig, nicht gekauft", "nicht_verifiziert": "Token nicht verifiziert, nicht gekauft",
    "zu_wenig_liquiditaet": "zu wenig Liquidität, nicht gekauft", "start_zu_nah": "Handelsstart schon vorbei oder zu nah",
    "nur_aufzeichnung": "nur aufgezeichnet (Handel beginnt sofort)", "delisting": "Delisting (nur aufgezeichnet)",
    "kein_platz_oder_geld": "kein Platz oder Geld im Konto", "kauf_fehlgeschlagen": "Kauf nicht möglich",
}


def offene_symbole(konten, copy_data):
    """{TICKER: [Konten]} aller offenen Positionen (Strategien, Experimente, Copy-Konten)."""
    out = {}
    for k in konten:
        for o in k.get("offen", []):
            sym = str(o.get("symbol", "")).strip().upper()
            if sym and sym != "?":
                out.setdefault(sym, []).append(k["label"])
    for name, acct in ((copy_data or {}).get("wallets") or {}).items():
        for p in (acct.get("positionen") or {}).values():
            sym = str(p.get("symbol", "")).strip().upper()
            if sym and sym != "?":
                out.setdefault(sym, []).append(f"Copy {name}")
    return out


def news_holen():
    """RSS-Feeds holen (parallel, 8 s Wartezeit je Feed). Rueckgabe (items, fehler)."""
    import requests
    sitzung = requests.Session()
    sitzung.headers["User-Agent"] = "narrativ-paperbot-dashboard/1.0 (privat, nur lesen)"

    def get(url):
        res = sitzung.get(url, timeout=8)
        res.raise_for_status()
        return res.content
    return listings.hole_news(get)


def boersen_meldungen(repo=None, jetzt=None, max_alter_h=96):
    """Listing-/Delisting-Meldungen aus experimente/listing_welle/ereignisse.csv als News-Eintraege."""
    repo = Path(repo or REPO)
    out = []
    for r in lade_csv(repo / LISTING_EREIGNISSE_DATEI):
        if r.get("typ") != "ankuendigung" or r.get("art") not in ("listing", "delisting"):
            continue
        zeit = zeitpunkt(r.get("ankuendigung_zeit"))
        if zeit is None or (jetzt and not 0 <= jetzt - zeit.timestamp() <= max_alter_h * 3600):
            continue
        boerse = r.get("boerse", "?")
        out.append({"titel": f"{boerse}: {r.get('symbol', '?')} – {'Delisting' if r['art'] == 'delisting' else 'Listing'}"
                             f" ({r.get('titel', '')[:80]})", "quelle": f"{boerse} (offiziell)",
                    "zeit": zeit.timestamp(), "link": listings.sicherer_link(r.get("url")),
                    "anriss": ENTSCHEIDUNG_TEXT.get(r.get("entscheidung", ""), r.get("entscheidung", "")),
                    "art": r["art"], "symbol": r.get("symbol", "")})
    return out


def news_zusammenstellen(items, meldungen, symbole, jetzt):
    """Alles bewerten (Markierungen: position, listing, rug, solana), doppelte raus, nach Relevanz und Zeit sortieren."""
    alle, gesehen = [], set()
    for it in list(meldungen) + list(items):
        key = it.get("link") or it["titel"]
        if key in gesehen:
            continue
        gesehen.add(key)
        it = dict(it)
        listings.bewerten(it, sorted(symbole))
        if it.get("art") == "delisting" and "listing" not in it["marken"]:
            it["marken"].append("listing")
            it["punkte"] += 60
        if it.get("symbol") and it["symbol"].upper() in symbole and "position" not in it["marken"]:
            it["marken"].insert(0, "position")
            it["punkte"] += 100
            it["positions_coins"] = [it["symbol"].upper()]
        alle.append(it)
    return listings.sortiert(alle, jetzt)


def listing_welle_uebersicht(repo=None, anzahl=15):
    """Letzte Entscheidungen der Listing-Welle + Zahl der Geruechte (fuer die Seite News)."""
    repo = Path(repo or REPO)
    rows = [r for r in lade_csv(repo / LISTING_EREIGNISSE_DATEI) if r.get("typ") == "ankuendigung"]
    gerueche = lade_csv(repo / Path(core.LISTING_GERUECHTE_FILE))
    portfolio = lade_json(repo / Path(core.EXP_DIR) / "listing_welle" / "portfolio.json", {}) or {}
    return {"ereignisse": list(reversed(rows))[:anzahl], "anzahl_ereignisse": len(rows),
            "gekauft": sum(1 for r in rows if r.get("entscheidung") == "gekauft"),
            "geruechte": len(gerueche), "quellen": (portfolio.get("listing") or {}).get("quellen", {})}


# ================================================================ Wissen (nur lokale Markdown-Dateien)
import re as _wissen_re  # noqa: E402
import unicodedata as _wissen_unicode  # noqa: E402


def wissen_links(text):
    """Obsidian-Verweise als lesbaren Text zeigen, Alias und Abschnitt bleiben lesbar."""
    def ersetzen(treffer):
        ziel, trenner, alias = treffer.group(1).partition("|")
        if trenner:
            return alias.strip()
        seite, _, abschnitt = ziel.partition("#")
        seite = seite.rsplit("/", 1)[-1].removesuffix(".md")
        return " – ".join(teil for teil in (seite.strip(), abschnitt.strip()) if teil)
    return _wissen_re.sub(r"!?\[\[([^\]\n]+)\]\]", ersetzen, text or "")


def wissen_titel(text, ersatz="Ohne Titel"):
    """Erste Markdown-Ueberschrift ausserhalb von Code, sonst Dateiname."""
    code = None
    for zeile in (text or "").splitlines():
        zeile = zeile.strip()
        zaun = _wissen_re.match(r"(`{3,}|~{3,})", zeile)
        if zaun:
            if code is None:
                code = zaun.group(1)[0]
            elif zeile.startswith(code * 3):
                code = None
            continue
        if code is not None:
            continue
        titel = _wissen_re.match(r"#{1,6}\s+(.+?)(?:\s+#+)?$", zeile)
        if titel:
            return wissen_links(titel.group(1)).strip() or ersatz
    return ersatz


def _wissen_normal(text):
    """Umlaute, Umschreibungen und Gross/Klein vereinheitlichen."""
    text = _wissen_unicode.normalize("NFKD", str(text or "").casefold())
    text = "".join(c for c in text if not _wissen_unicode.combining(c))
    return text.replace("ae", "a").replace("oe", "o").replace("ue", "u")


def wissen_ausschnitt(text, suche="", laenge=220):
    """Kurzer lesbarer Ausschnitt um den ersten Treffer, auch bei Umlauten."""
    text = " ".join(wissen_links(text).split())
    laenge = max(20, int(laenge))
    zeichen, positionen = [], []
    for index, original in enumerate(text):
        for zeichen_normal in _wissen_unicode.normalize("NFKD", original.casefold()):
            if not _wissen_unicode.combining(zeichen_normal):
                zeichen.append(zeichen_normal)
                positionen.append(index)
    normal, ursprung = [], []
    index = 0
    while index < len(zeichen):
        normal.append(zeichen[index])
        ursprung.append(positionen[index])
        index += 2 if "".join(zeichen[index:index + 2]) in ("ae", "oe", "ue") else 1
    normal = "".join(normal)
    begriffe = [_wissen_normal(b) for b in str(suche or "").split()]
    stellen = [normal.find(b) for b in begriffe if b and b in normal]
    # Normalisierung kann Zeichen zusammenziehen; Originalposition bleibt erhalten.
    position = ursprung[min(stellen)] if stellen else 0
    start = max(0, position - laenge // 3)
    ende = min(len(text), start + laenge)
    if ende == len(text):
        start = max(0, ende - laenge)
    return ("… " if start else "") + text[start:ende].strip() + (" …" if ende < len(text) else "")


def _wissen_innerhalb(path, basis):
    try:
        return path.resolve().is_relative_to(basis)
    except (OSError, RuntimeError):
        return False


def _wissen_markdown_dateien(repo, ordner, rekursiv):
    """Nur Markdown im vorgesehenen Repo-Ordner, keine Verweise nach ausserhalb."""
    import os
    basis = repo / ordner
    try:
        if not _wissen_innerhalb(basis, repo) or not basis.is_dir():
            return []
        grenze = basis.resolve()
        dateien = []
        for wurzel, unterordner, namen in os.walk(basis, followlinks=False):
            unterordner[:] = [name for name in unterordner
                             if rekursiv and not (Path(wurzel) / name).is_symlink()
                             and _wissen_innerhalb(Path(wurzel) / name, grenze)]
            for name in namen:
                path = Path(wurzel) / name
                if path.suffix.lower() == ".md" and _wissen_innerhalb(path, grenze):
                    dateien.append(path)
        return sorted(dateien)
    except (OSError, RuntimeError):
        return []


def _wissen_seite(path, repo, bericht=False):
    try:
        text = path.read_text(encoding="utf-8-sig")
        if not text.strip() or "\x00" in text:
            return None
        relativ = path.relative_to(repo)
        teile = relativ.parts
        art, gruppe = "dokument", "Weitere Dokumente"
        if bericht:
            art, gruppe = "bericht", "Berichte"
        elif teile[1:2] == ("notizen",):
            art, gruppe = "notiz", "Eigene Notizen"
        elif teile[1:2] == ("wiki",):
            art = "wiki"
            gruppe = "/".join(teile[2:-1]) or "Allgemein"
        elif relativ.as_posix() == "wissen/index.md":
            art, gruppe = "index", "Einstieg"
        zeit = path.stat().st_mtime
        if bericht:
            try:
                zeit = datetime.strptime(path.stem[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                pass
        return {"pfad": relativ.as_posix(), "titel": wissen_titel(text, path.stem),
                "inhalt": text, "markdown": wissen_links(text), "art": art, "gruppe": gruppe,
                "eigene_notiz": art == "notiz", "sortierzeit": zeit}
    except (OSError, UnicodeError):
        return None


def wissen_seiten(repo=None):
    """Alle lesbaren Wissensseiten; kaputte und leere Dateien ueberspringen."""
    repo = Path(repo or REPO).resolve()
    seiten = [_wissen_seite(path, repo) for path in _wissen_markdown_dateien(repo, "wissen", True)]
    return sorted((s for s in seiten if s),
                  key=lambda s: (_wissen_normal(s["gruppe"]), _wissen_normal(s["titel"]), s["pfad"]))


def wissen_berichte(repo=None):
    """Berichte neueste zuerst: Datum im Dateinamen, sonst letzte Dateiaenderung."""
    repo = Path(repo or REPO).resolve()
    seiten = [_wissen_seite(path, repo, bericht=True)
              for path in _wissen_markdown_dateien(repo, "auswertungen", False)]
    return sorted((s for s in seiten if s), key=lambda s: (s["sortierzeit"], s["pfad"]), reverse=True)


def wissen_suche(seiten, text):
    """Alle Suchwoerter muessen vorkommen. Reihenfolge bleibt, Eingabedaten bleiben unveraendert."""
    begriffe = [_wissen_normal(b) for b in str(text or "").split()]
    treffer = []
    for seite in seiten or []:
        inhalt = seite.get("markdown", seite.get("inhalt", ""))
        suchtext = _wissen_normal(" ".join((seite.get("titel", ""), seite.get("pfad", ""), inhalt)))
        if all(b in suchtext for b in begriffe):
            treffer.append(dict(seite, ausschnitt=wissen_ausschnitt(inhalt, text)))
    return treffer


def wissen_gruppen(seiten):
    """Seitenliste nach Unterordnern; der Einstieg wird gesondert gezeigt."""
    gruppen = {}
    for seite in seiten or []:
        if seite.get("art") != "index":
            gruppen.setdefault(seite.get("gruppe", "Weitere Dokumente"), []).append(seite)
    return gruppen


# ================================================================ Rennbahn

def rennbahn(konten, sichtbar=None, mit_kosten=False):
    """Rangliste und auf 0 normierte Trade-Verlaeufe aus Strategie-Konten.

    Rangwerte entsprechen konto_strategie (laufende Runde, inklusive offener
    Positionen). Kurven entsprechen kontoverlauf (geschlossene Trades aller
    Runden). Der Kostenschalter waehlt nur den Kurvenwert; Rangfolge, Konten
    und beide Testurteile bleiben gleich. Ohne Auswahl sind aktive Konten sichtbar.
    Eingaben werden nicht veraendert; Dateien werden weder gelesen noch geschrieben.
    """
    from math import isfinite

    hinweise, gueltig = [], []
    for original in konten or []:
        if not isinstance(original, dict) or not original.get("key"):
            hinweise.append("Ein Konto ohne Kennung konnte nicht angezeigt werden.")
            continue
        k = dict(original)
        k.setdefault("label", k["key"])
        k.setdefault("closed", [])
        k.setdefault("offen", [])
        k.setdefault("kosten_pct", kosten_pct(k["key"]))
        if not isinstance(k["closed"], list) or any(not isinstance(c, dict) for c in k["closed"]):
            hinweise.append(f"{k['label']}: Trades sind nicht lesbar; Konto ausgelassen.")
            continue
        gueltig.append(k)

    kontrolle = next((k for k in gueltig if k["key"] == KONTROLLE), None)
    if gueltig and kontrolle is None:
        hinweise.append("Die Kontrollgruppe fehlt; ein Testurteil ist noch nicht möglich.")
    standard = [k["key"] for k in gueltig if not k.get("beendet")]
    auswahl = set(standard if sichtbar is None else sichtbar)
    rangliste, beendet, verlauf = [], [], []

    for k in gueltig:
        label = k["label"]
        try:
            kennzahlen = trade_kennzahlen(k["closed"], k["kosten_pct"])
            vergleich = (vergleich_mit_kontrolle(k, kontrolle) if kontrolle else
                         {"ampel": "keine_daten", "text": "Kontrollgruppe fehlt"})
            wert = as_float(k.get("kontowert"), float("nan"))
            hat_daten = bool(k.get("gestartet") or k.get("gespeichert") or k["closed"] or k["offen"])
            ergebnis = wert - START_SOL if hat_daten and isfinite(wert) else None
            netto = kontowert_mit_kosten(k) - START_SOL if ergebnis is not None else None
            row = {"key": k["key"], "label": label, "beendet": k.get("beendet"),
                   "runde": k.get("runde") or 1, "ergebnis": ergebnis, "ergebnis_kosten": netto,
                   "trades": kennzahlen["trades"],
                   "trades_bis_200": max(0, ZIEL_TRADES - kennzahlen["trades"]),
                   "vergleich_trades": vergleich.get("eigen", {}).get("trades", 0),
                   "kosten_pct": k["kosten_pct"], "vergleich": vergleich,
                   "urteil": urteil_kurz(vergleich),
                   "urteil_kosten": urteil_kurz({**vergleich, **vergleich.get("kosten", {})})}
            (beendet if k.get("beendet") else rangliste).append(row)
            if not hat_daten:
                hinweise.append(f"{label}: Noch keine gespeicherten Kontodaten.")
            fehlende_kurse = sum(o.get("wert") is None for o in k["offen"])
            if fehlende_kurse:
                hinweise.append(f"{label}: Bei {fehlende_kurse} offenen Positionen fehlt der Kurs; "
                                "sie zählen wie auf der Strategieseite mit Wert 0.")

            # UTC-Sortierung verhindert falsche Reihenfolgen bei gemischten Zeitzonen.
            trades = []
            for c in k["closed"]:
                t = zeitpunkt(c.get("closed_at"))
                if t is None:
                    hinweise.append(f"{label}: Mindestens eine Trade-Zeit fehlt; kein zuverlässiger Verlauf.")
                    break
                trades.append({**c, "closed_at": t.astimezone(timezone.utc).isoformat()})
            else:
                trades.sort(key=lambda c: c["closed_at"])
                start = zeitpunkt(k.get("gestartet"))
                if start is None and trades:
                    start = zeitpunkt(trades[0]["closed_at"])
                    hinweise.append(f"{label}: Startzeit fehlt; Verlauf beginnt beim ersten geschlossenen Trade.")
                if start is None or k["key"] not in auswahl:
                    continue
                roh = kontoverlauf({"gestartet": start.isoformat(), "closed": trades})
                abzug = 0.0
                for i, p in enumerate(roh):
                    if i:
                        c = trades[i - 1]
                        abzug += kosten_abzug({"closed": [c], "runde": c.get("runde") or 1,
                                               "kosten_pct": k["kosten_pct"]})
                    brutto = p["kontostand"] - START_SOL
                    netto_punkt = brutto - abzug
                    verlauf.append({"key": k["key"], "konto": label, "zeit": p["zeit"], "folge": i,
                                    "beendet": bool(k.get("beendet")), "kontrolle": k["key"] == KONTROLLE,
                                    "roh": brutto, "mit_kosten": netto_punkt,
                                    "ergebnis": netto_punkt if mit_kosten else brutto})
        except (KeyError, TypeError, ValueError, OverflowError):
            hinweise.append(f"{label}: Unlesbare Kontodaten; einzelne Angaben fehlen.")

    # Feste Reihenfolge: Der Kostenschalter veraendert weder Rang noch Auswahl.
    for gruppe in (rangliste, beendet):
        gruppe.sort(key=lambda row: (row["ergebnis"] is None, -(row["ergebnis"] or 0), row["label"]))
        for rang, row in enumerate(gruppe, 1):
            row["rang"] = rang
    return {"rangliste": rangliste, "beendet": beendet, "verlauf": verlauf,
            "standard": standard, "hinweise": list(dict.fromkeys(hinweise))}


# ================================================================ Verpasste Chancen

ABGELEHNT_TOLERANZ_S = 300


def _rueckblick_csv(path, pflicht, hinweise, zusatz=(), phase_prefix=None):
    """CSV zeilenweise lesen; defekte Dateien/Zeilen melden, andere weiter auswerten."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            if not pflicht.issubset(header):
                hinweise.append(f"{path.name}: Benötigte Spalten fehlen.")
                return
            indizes = [(k, header.index(k)) for k in pflicht | set(zusatz) if k in header]
            phase_i = header.index("phase") if phase_prefix is not None else None
            kaputt = 0
            for row in reader:
                if not row:
                    continue
                if len(row) != len(header):
                    kaputt += 1
                    continue
                if phase_i is not None and not row[phase_i].startswith(phase_prefix):
                    continue
                yield {k: row[i] for k, i in indizes}
            if kaputt:
                hinweise.append(f"{path.name}: {kaputt} unvollständige Zeilen nicht ausgewertet.")
    except FileNotFoundError:
        hinweise.append(f"{path.name}: Datei fehlt.")
    except (OSError, UnicodeError, csv.Error):
        hinweise.append(f"{path.name}: Datei nicht vollständig lesbar.")


def _rueckblick_preis(wert):
    import math
    preis = as_float(wert, None)
    return preis if preis is not None and math.isfinite(preis) and preis > 0 else None


def _rueckblick_statistik(werte):
    """Anteile beziehen sich nur auf messbare Coins, keine Nullwerte fuer Datenluecken."""
    n = len(werte)
    hoeher = sum(x > 0 for x in werte)
    niedriger = sum(x < 0 for x in werte)
    return {"n": n, "hoeher": hoeher, "niedriger": niedriger, "gleich": n - hoeher - niedriger,
            "hoeher_pct": hoeher / n * 100 if n else None,
            "niedriger_pct": niedriger / n * 100 if n else None,
            "median_pct": statistics.median(werte) if n else None,
            "mittel_pct": statistics.mean(werte) if n else None,
            "min_pct": min(werte) if n else None, "max_pct": max(werte) if n else None}


def abgelehnt_rueckblick(repo=None, grund=None, stunden=(1, 6)):
    """Lokaler Papierkurs-Rueckblick, ohne Streamlit, Netzwerk oder Schreibzugriffe.

    Beide Ablehnungsdateien bleiben getrennt (Nahfaelle stehen oft auch in abgelehnt.csv).
    Pro Quelle/Mint/Grund zaehlt die erste zeitlich zuordenbare Ablehnung, auch wenn ihr
    Startpreis fehlt. Kurse nur aus der passenden Phase abgelehnt_<Grund>, nie per Ticker.
    Naechster Messpunkt +/-5 min um das Ziel; Gleichstand nimmt den frueheren Punkt.
    Kein Fortschreiben, Interpolieren oder Ersetzen fehlender Preise. Widerspruechliche
    Kurse am gleichen Zeitpunkt bleiben unmessbar. Quellen werden nur einmal gelesen.
    """
    from bisect import bisect_left
    import math

    repo = Path(repo or REPO)
    if isinstance(stunden, (int, float)):
        stunden = (stunden,)
    stunden = tuple(dict.fromkeys(stunden))
    if not stunden or any(not math.isfinite(h) or h <= 0 for h in stunden):
        raise ValueError("Stunden müssen endlich und größer als null sein.")
    hinweise, quellen, gesucht = [], {}, set()
    zeit_cache = {}

    def zeit_lesen(text):
        if text not in zeit_cache:
            zeit_cache[text] = zeitpunkt(text)
        return zeit_cache[text]

    tag_cache = {}
    for name in ("knapp_abgelehnt", "abgelehnt"):
        gruppen, tage, erste, coins = {}, {}, {}, set()
        n = unzuordenbar = 0
        pfade = [repo / f"{name}.csv"]
        if name == "abgelehnt":
            pfade = ablehnungs_dateien(repo) or pfade      # ohne Dateien bleibt der Hinweis "Datei fehlt"
        zeilen = (row for pfad in pfade
                  for row in _rueckblick_csv(pfad, {"zeit", "mint", "grund"}, hinweise,
                                             zusatz=("symbol", "preis_usd")))
        for row in zeilen:
            g = row["grund"].strip() or "Unbekannt"
            if grund is not None and g != grund:
                continue
            n += 1
            mint = row["mint"].strip()
            gruppe = gruppen.setdefault(g, {"grund": g, "pruefungen": 0, "mints": set()})
            gruppe["pruefungen"] += 1
            if mint:
                gruppe["mints"].add(mint)
                coins.add(mint)
            zeit = zeit_lesen(row["zeit"])
            if zeit:
                if zeit not in tag_cache:
                    tag_cache[zeit] = zeit.astimezone(timezone.utc).strftime("%Y-%m-%d")
                tag = tag_cache[zeit]
                tage[tag] = tage.get(tag, 0) + 1
            if not mint or zeit is None:
                unzuordenbar += 1
                continue
            t = zeit.timestamp()
            key = (mint, g)
            if key not in erste or t < erste[key]["zeit"]:
                erste[key] = {"mint": mint, "grund": g, "symbol": row.get("symbol") or "?",
                              "zeit": t, "preis_usd": _rueckblick_preis(row.get("preis_usd"))}
            elif t == erste[key]["zeit"] and erste[key]["preis_usd"] != _rueckblick_preis(row.get("preis_usd")):
                erste[key]["preis_usd"] = None
                erste[key]["startkonflikt"] = True
            gesucht.add(key)
        quellen[name] = {"pruefungen": n, "coins": len(coins), "unzuordenbar": unzuordenbar,
                        "je_tag": [{"tag": tag, "pruefungen": zahl} for tag, zahl in sorted(tage.items())],
                        "gruppen": gruppen, "erste": erste}

    kurse = {}
    dateien = sorted((repo / "verlauf").glob("*.csv")) if gesucht else []
    if gesucht and not dateien:
        hinweise.append("verlauf/: Keine Kursdateien vorhanden. Nur Ablehnungen zählbar.")
    for path in dateien:
        for row in _rueckblick_csv(path, {"zeit", "mint", "phase", "preis_usd"}, hinweise,
                                  phase_prefix="abgelehnt_"):
            phase = row["phase"]
            if not phase.startswith("abgelehnt_"):
                continue
            key = (row["mint"].strip(), phase[len("abgelehnt_"):])
            if key not in gesucht:
                continue
            zeit = zeit_lesen(row["zeit"])
            if zeit is not None:
                kurse.setdefault(key, []).append((zeit.timestamp(), _rueckblick_preis(row["preis_usd"])))

    konflikt = 0
    for key, punkte in kurse.items():
        eindeutig = {}
        for t, preis in punkte:
            if t in eindeutig and eindeutig[t] != preis:
                konflikt += 1
                eindeutig[t] = None
            else:
                eindeutig[t] = preis
        zeiten = sorted(eindeutig)
        kurse[key] = (zeiten, [eindeutig[t] for t in zeiten])
    if konflikt:
        hinweise.append(f"{konflikt} widersprüchliche Kurszeilen: Messpunkte nicht verwendet.")

    for quelle in quellen.values():
        werte = {}
        erste = quelle.pop("erste")
        startkonflikte = sum(bool(f.get("startkonflikt")) for f in erste.values())
        if startkonflikte:
            hinweise.append(f"{startkonflikte} widersprüchliche Startpreise: Fälle nicht auswertbar.")
        for key, fall in erste.items():
            zeiten, preise = kurse.get(key, ([], []))
            fall["horizonte"] = {}
            for h in stunden:
                ziel = fall["zeit"] + h * 3600
                i = bisect_left(zeiten, ziel)
                kandidaten = [j for j in (i - 1, i) if 0 <= j < len(zeiten)]
                messung = {"rendite_pct": None, "zeit": None, "preis_usd": None, "abstand_s": None}
                if kandidaten:
                    j = min(kandidaten, key=lambda j: (abs(zeiten[j] - ziel), zeiten[j]))
                    preis, start = preise[j], fall["preis_usd"]
                    if (zeiten[j] > fall["zeit"] and abs(zeiten[j] - ziel) <= ABGELEHNT_TOLERANZ_S
                            and preis is not None and start is not None):
                        rendite = (preis / start - 1) * 100
                        if math.isfinite(rendite):
                            messung = {"rendite_pct": rendite, "zeit": zeiten[j], "preis_usd": preis,
                                       "abstand_s": zeiten[j] - ziel}
                            werte.setdefault((fall["grund"], h), []).append(rendite)
                fall["horizonte"][h] = messung
        quelle["gruende"] = []
        for g, gruppe in sorted(quelle.pop("gruppen").items(), key=lambda item: -item[1]["pruefungen"]):
            gruppe["coins"] = len(gruppe.pop("mints"))
            gruppe["horizonte"] = {}
            for h in stunden:
                zahlen = werte.get((g, h), [])
                stats = _rueckblick_statistik(zahlen)
                stats["fehlend"] = gruppe["coins"] - stats["n"]
                stats["ohne_beste_3"] = _rueckblick_statistik(sorted(zahlen)[:-3])
                gruppe["horizonte"][h] = stats
            quelle["gruende"].append(gruppe)
        quelle["faelle"] = sorted(erste.values(), key=lambda fall: fall["zeit"], reverse=True)[:50]
        if quelle["unzuordenbar"]:
            hinweise.append(f"{quelle['unzuordenbar']} Ablehnungen ohne Mint oder lesbare Zeit: nur gezählt.")
    return {"quellen": quellen, "stunden": stunden, "toleranz_s": ABGELEHNT_TOLERANZ_S,
            "hinweise": list(dict.fromkeys(hinweise))}


# ================================================================ Tageszeit (nur Beobachtung)

TAGESZEIT_MIN_TRADES = 10
TAGESZEIT_WOCHENTAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
TAGESZEIT_GRUPPEN = (("Nacht", 0, 8), ("Vormittag", 8, 14),
                    ("Nachmittag", 14, 20), ("Abend", 20, 24))
TAGESZEIT_PHASEN = {"ruhig": "Ruhig", "normal": "Normal", "heiss": "Heiß"}


def _tageszeit_zahl(wert):
    """Fehlende oder nicht endliche Zahlen bleiben fehlend, statt als Null zu zaehlen."""
    import math
    if isinstance(wert, bool) or wert in (None, ""):
        return None
    zahlwert = as_float(wert, None)
    return zahlwert if zahlwert is not None and math.isfinite(zahlwert) else None


def _tageszeit_utc(wert):
    """Auch Offset-Zeiten immer vor der Stunden-/Wochentagszuordnung nach UTC wandeln."""
    try:
        if isinstance(wert, bool):
            return None
        d = wert if isinstance(wert, datetime) else zeitpunkt(wert)
        if d is None:
            return None
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def tageszeit_kaufzeit(trade):
    """Kaufzeit geschlossener Trades, bevorzugt direkt, sonst closed_at minus hold_h.

    hold_h ist eine gespeicherte Haltedauer; die Rueckrechnung kann gerundet sein.
    Fehlende oder widerspruechliche Zeiten werden nicht einer Stunde zugeschlagen.
    """
    if not isinstance(trade, dict):
        return None, False
    ende = _tageszeit_utc(trade.get("closed_at"))
    if ende is None:
        return None, False
    for feld in ("opened", "opened_at", "entry_time"):
        if trade.get(feld) not in (None, ""):
            kauf = _tageszeit_utc(trade[feld])
            return (kauf, False) if kauf is not None and kauf <= ende else (None, False)
    dauer = _tageszeit_zahl(trade.get("hold_h"))
    if dauer is None or dauer < 0:
        return None, False
    try:
        return ende - timedelta(hours=dauer), True
    except (OverflowError, ValueError):
        return None, False


def tageszeit_stunden_text(start, ende=None):
    """UTC und deutsche Sommer-/Winterzeit explizit; kein fester Offset fuer alle Tage."""
    def uhr(stunde):
        return f"{stunde % 24:02d}:00" + (" (+1 Tag)" if stunde >= 24 else "")
    if ende is None:
        return f"{start:02d}:00 UTC ({uhr(start + 2)} MESZ / {uhr(start + 1)} MEZ)"
    return (f"{start:02d}:00–{ende:02d}:00 UTC "
            f"({uhr(start + 2)}–{uhr(ende + 2)} MESZ / {uhr(start + 1)}–{uhr(ende + 1)} MEZ)")


def _tageszeit_statistik(trades, kosten):
    """Kosten immer ueber kosten_abzug; alle Runden und dieselbe Auswahl je Kennzahl."""
    def pnl(t):
        abzug = kosten_abzug({"closed": [{**t, "runde": 1}], "runde": 1, "kosten_pct": kosten})
        return t["pnl_sol"] - abzug
    werte = sorted((pnl(t) for t in trades), reverse=True)
    n = len(werte)
    rest = werte[BESTE_WEGLASSEN:]
    return {"trades": n, "summe": sum(werte) if n else None,
            "pro_trade": sum(werte) / n if n else None,
            "ohne_beste_trades": len(rest), "beste_abgezogen": min(n, BESTE_WEGLASSEN),
            "ohne_beste_summe": sum(rest) if rest else None,
            "ohne_beste_pro_trade": sum(rest) / len(rest) if rest else None,
            "ausreichend": n >= TAGESZEIT_MIN_TRADES,
            "status": "Beobachtung" if n >= TAGESZEIT_MIN_TRADES else "zu wenig Daten"}


def tageszeit_auswertung(trades, kosten=0.0, marktphasen=False):
    """Geschlossene Trades nach Kaufstunde und UTC-Wochentag, ohne Streamlit.

    kosten ist der vorhandene Kontoaufschlag in Prozent (0 = roh). Ein fehlender
    Einsatz nutzt wie kosten_abzug den Standard; unlesbare Werte werden ausgelassen.
    """
    kosten = _tageszeit_zahl(kosten)
    if kosten is None or kosten < 0:
        raise ValueError("Der Kostenaufschlag muss eine endliche Zahl ab Null sein.")
    sauber, hinweise = [], []
    luecken = {"zeit": 0, "ergebnis": 0, "einsatz": 0, "standard": 0, "phase": 0}
    rueckgerechnet = 0
    for trade in trades if isinstance(trades, (list, tuple)) else []:
        kauf, gerechnet = tageszeit_kaufzeit(trade)
        if kauf is None:
            luecken["zeit"] += 1
            continue
        pnl = _tageszeit_zahl(trade.get("pnl_sol"))
        if pnl is None:
            luecken["ergebnis"] += 1
            continue
        einsatz = _tageszeit_zahl(trade.get("invested_sol"))
        if trade.get("invested_sol") is None:
            einsatz = EINSATZ_STANDARD
            luecken["standard"] += 1
        elif einsatz is None or einsatz < 0:
            luecken["einsatz"] += 1
            if kosten:
                continue
            einsatz = 0.0
        phase = trade.get("phase")
        if not isinstance(phase, str) or phase not in TAGESZEIT_PHASEN:
            phase = None
            luecken["phase"] += 1
        sauber.append({"pnl_sol": pnl, "invested_sol": einsatz, "kauf": kauf, "phase": phase})
        rueckgerechnet += int(gerechnet)
    if luecken["zeit"]:
        hinweise.append(f"{luecken['zeit']} Trades ohne verlässliche Kauf-/Verkaufszeit oder Haltedauer: ausgelassen.")
    if luecken["ergebnis"]:
        hinweise.append(f"{luecken['ergebnis']} Trades ohne lesbares SOL-Ergebnis: ausgelassen.")
    if luecken["einsatz"]:
        hinweise.append(f"{luecken['einsatz']} Trades mit unlesbarem Einsatz: mit Kosten ausgelassen, roh enthalten.")
    if luecken["standard"]:
        hinweise.append(f"{luecken['standard']} Trades ohne Einsatz: Kosten mit dem Standard von {zahl(EINSATZ_STANDARD)} SOL berechnet.")
    if rueckgerechnet:
        hinweise.append(f"{rueckgerechnet} Kaufzeiten aus Verkaufszeit minus Haltedauer zurückgerechnet. "
                        "Gerundete Haltedauern können die Zuordnung nahe einer Stundengrenze verschieben.")
    raster = []
    for tag, name in enumerate(TAGESZEIT_WOCHENTAGE):
        for stunde in range(24):
            gruppe = [t for t in sauber if t["kauf"].weekday() == tag and t["kauf"].hour == stunde]
            raster.append({"wochentag": name, "tag": tag, "stunde": stunde,
                           "zeit_text": tageszeit_stunden_text(stunde), **_tageszeit_statistik(gruppe, kosten)})
    gruppen = []
    for name, start, ende in TAGESZEIT_GRUPPEN:
        gruppe = [t for t in sauber if start <= t["kauf"].hour < ende]
        gruppen.append({"name": name, "zeit_text": tageszeit_stunden_text(start, ende),
                        **_tageszeit_statistik(gruppe, kosten)})
    phasen = []
    if marktphasen:
        for key, name in TAGESZEIT_PHASEN.items():
            gruppe = [t for t in sauber if t["phase"] == key]
            phasen.append({"name": name, **_tageszeit_statistik(gruppe, kosten)})
        if luecken["phase"]:
            hinweise.append(f"{luecken['phase']} Trades ohne bekannte gespeicherte Marktphase: nur in der Zeitauswertung enthalten.")
        if not any(p["trades"] for p in phasen):
            phasen = []
            hinweise.append("Marktphasenvergleich weggelassen: keine gespeicherten Trade-Phasen vorhanden.")
    zeiten = [t["kauf"] for t in sauber]
    return {"gesamt": _tageszeit_statistik(sauber, kosten), "raster": raster, "gruppen": gruppen,
            "phasen": phasen, "kosten_pct": kosten, "hinweise": hinweise,
            "beginn": min(zeiten).isoformat() if zeiten else None,
            "ende": max(zeiten).isoformat() if zeiten else None}


def tageszeit_konten(repo=None):
    """Nur lokale geschlossene Trades laden, ohne Kurse, Journal oder Bot-Abrufe.

    Die aktuelle Marktphase wird niemals frueheren Trades zugeordnet. Eine gueltige
    Zustandsdatei und gespeicherte Trade-Phasen erlauben den historischen Vergleich.
    """
    repo = Path(repo or REPO)
    konten, hinweise = [], []
    for key, label in KONTEN:
        datei = repo / (core.PORTFOLIO_FILE if key == "hauptstrategie" else Path(core.EXP_DIR) / key / "portfolio.json")
        p = lade_json(datei)
        if not isinstance(p, dict):
            hinweise.append(f"{label}: lokale Kontodatei fehlt oder ist nicht lesbar.")
            continue
        closed = p.get("closed", [])
        if not isinstance(closed, list):
            hinweise.append(f"{label}: gespeicherte Trades sind nicht lesbar.")
            closed = []
        beendet = getattr(core, "EXP_BEENDET", {}).get(key)
        konten.append({"key": key, "label": label + (" (beendet)" if beendet else ""), "closed": closed})
    markt = lade_json(repo / "marktphase.json")
    phasen_ok = (isinstance(markt, dict) and isinstance(markt.get("phase"), str)
                 and markt["phase"] in TAGESZEIT_PHASEN and _tageszeit_utc(markt.get("updated")) is not None)
    if phasen_ok:
        hinweise.append("Marktphasen stammen aus den geschlossenen Trades. marktphase.json zeigt nur den aktuellen "
                        "Zustand und Messwerte; fehlende frühere Phasen werden daraus nicht ergänzt.")
    else:
        hinweise.append("Marktphasenvergleich weggelassen: marktphase.json fehlt oder enthält keinen lesbaren Zustand mit Zeit.")
    return {"konten": konten, "marktphasen": phasen_ok, "hinweise": hinweise}


# ================================================================ Wallet-Waechter (nur Vorschau)

# Quelle: scout_bot.py, AUTO_MAX_WALLETS (nur gelesen, kein Import); CLAUDE.md,
# "Feste Entscheidungen des Betreibers", Copy Trading / Automatische Aufnahme.
WAECHTER_MAX_WALLETS = 30
WAECHTER_TAGESLIMIT = 3       # Gleicher CLAUDE.md-Abschnitt: Aufnahme/Ersetzen pro UTC-Tag.
WAECHTER_WARTESPALTEN = ("seit", "bewertet", "wallet", "name", "quelle", "punkte",
                        "rendite_ohne_besten_pct", "coins", "kauf_median_sol", "trades_pro_tag", "inaktiv_h")


def _waechter_zahl(wert):
    import math
    try:
        z = as_float(wert, None)
    except OverflowError:
        return None
    return z if z is not None and math.isfinite(z) else None


def _waechter_zeit(wert):
    try:
        if isinstance(wert, datetime):
            return wert.replace(tzinfo=wert.tzinfo or timezone.utc).timestamp()
        # Auch CSV-Zeiten als Unix-Text zulassen.
        z = _waechter_zahl(wert)
        d = zeitpunkt(z if z is not None else wert)
        return d.timestamp() if d else None
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def _waechter_json(path, hinweise):
    try:
        with path.open(encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    hinweise.append(f"{path.name} fehlt oder ist nicht lesbar; betroffene Regeln bleiben offen.")
    return {}


def _waechter_heute(repo, ab, jetzt, hinweise):
    """Lokale Git-Diffs: eine automatische neue Wallet = eine Aufnahme oder ein Tausch.

    Ein Tausch wird nicht doppelt gezaehlt. Reine Entfernungen und manuelle Aufnahmen
    bleiben sichtbar, verbrauchen aber kein Automatik-Tageslimit.
    """
    import re
    # Quelle: CLAUDE.md, Feste Entscheidungen / Automatische Aufnahme; UTC nach
    # Goldene Regeln, Regel 8. Stille Entfernungen ohne Tageslimit seit 06.10.
    args = ["git", "log", f"--since=@{int(ab) - 1}", f"--until=@{int(jetzt)}",
            "--format=WAECHTER:%ct", "-p", "--", "copy_wallets.txt"]
    try:
        proc = subprocess.run(args, cwd=repo, capture_output=True, text=True, timeout=30,
                              encoding="utf-8", errors="replace")
        if proc.returncode:
            raise ValueError("Git-Historie nicht lesbar")
    except (OSError, ValueError, subprocess.SubprocessError):
        hinweise.append("Tageslimit unbekannt: die lokale Git-Historie ist nicht lesbar.")
        return {"anzahl": None, "ereignisse": []}
    ereignisse, zeit, auto = [], None, None
    hinzu, weg, entfernt = {}, set(), []

    def abschliessen():
        if zeit is None or not ab <= zeit <= jetzt:
            return
        for adresse, (name, grund) in hinzu.items():
            if adresse not in weg:
                ereignisse.append({"zeit": zeit, "name": name,
                                   "art": "Aufnahme / Ersetzen" if grund is not None else "Manuelle Aufnahme",
                                   "automatisch": grund is not None, "grund": grund or "ohne Automatik-Vermerk"})
        ereignisse.extend({"zeit": zeit, "name": name, "art": "Entfernung", "automatisch": False,
                           "grund": grund} for name, grund in entfernt)

    for zeile in proc.stdout.splitlines():
        if zeile.startswith("WAECHTER:"):
            abschliessen()
            zeit = _waechter_zahl(zeile.split(":", 1)[1])
            hinzu, weg, entfernt, auto = {}, set(), [], None
        elif zeile.startswith(("+++", "---")):
            continue
        elif zeile.startswith("-"):
            m = re.match(rf"[^:#]+:\s*({ADRESSE_TEXT})\s*$", zeile[1:].strip())
            if m:
                weg.add(m.group(1))
        elif zeile.startswith("+"):
            z = zeile[1:].strip()
            m = re.match(r"#\s*\d\d\.\d\d\.\s*automatisch aufgenommen:\s*(.*)", z)
            if m:
                auto = m.group(1)
                continue
            m = re.match(rf"([^:#]+):\s*({ADRESSE_TEXT})\s*$", z)
            if m:
                hinzu[m.group(2)] = (m.group(1).strip(), auto)
            m = re.match(rf"#\s*([^:]+):\s*{ADRESSE_TEXT}\s*<-\s*(.*)", z)
            if m:
                entfernt.append((m.group(1).strip(), m.group(2)))
            auto = None
        elif not zeile.startswith("@@"):
            auto = None
    abschliessen()
    hinweise.append("Tageslimit aus lokalen Git-Einträgen; eine gekürzte oder veraltete Historie kann Änderungen auslassen.")
    return {"anzahl": sum(e["automatisch"] for e in ereignisse), "ereignisse": ereignisse}


def waechter_uebersicht(repo=None, jetzt=None):
    """Wallet-Regeln aus lokalen Daten, ohne Bot-Import des Scouts und ohne Schreibzugriff."""
    repo = Path(repo or REPO)
    jetzt = _waechter_zeit(jetzt) if jetzt is not None else datetime.now(timezone.utc).timestamp()
    if jetzt is None:
        raise ValueError("Zeitpunkt der Vorschau ist unlesbar")
    hinweise = []
    raw = _waechter_json(repo / "copy" / "konten.json", hinweise)
    wallets = raw.get("wallets")
    if not isinstance(wallets, dict):
        wallets = {}
        hinweise.append("Wallet-Konten fehlen oder haben ein falsches Format.")
    gespeichert = _waechter_zeit(raw.get("saved_at"))
    # Quelle: CLAUDE.md, Feste Entscheidungen / Wallet-Regeln; Schutzkorrektur
    # dokumentiert in STRATEGIE.md, Wallet-Scout / Grenzen (06.10.): hoechstens 2 h.
    frisch = gespeichert is not None and 0 <= jetzt - gespeichert <= 2 * 3600
    if not frisch:
        hinweise.append("Copy-Konten sind älter als 2 Stunden oder ohne gültigen Datenstand. Stille Wallets bleiben gesperrt.")
    liste_ok = (repo / "copy_wallets.txt").exists()
    try:
        aktive = aktive_wallets(repo)
    except (ValueError, TypeError, UnicodeError):
        aktive = []
        liste_ok = False
        hinweise.append("Die Liste aktiver Wallets ist nicht lesbar.")
    if not (repo / "copy_wallets.txt").exists():
        hinweise.append("copy_wallets.txt fehlt; die Zahl aktiver Wallets ist unbekannt.")
    try:
        konten, _, _ = copy_konten(repo)
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError, UnicodeError):
        # Ein defektes Konto darf die anderen Wallets nicht verdecken.
        hinweise.append("Mindestens ein Copy-Konto ist fehlerhaft; lesbare Konten werden einzeln berechnet.")
        konten = []
        for name, acct in wallets.items():
            if isinstance(acct, dict):
                try:
                    konten.append(copy_konto(name, acct, True, [], set()))
                except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
                    pass
    nach_name = {k["name"]: k for k in konten}
    flut = _waechter_json(repo / "copy" / "flutschutz.json", hinweise)
    try:
        scout = {s["wallet"]: s for s in scout_rangliste(repo)}
    except (ValueError, TypeError, UnicodeError):
        scout = {}
        hinweise.append("Scout-Bewertungen sind nicht lesbar.")
    hinweise.append("Bot-Hinweise stammen nur aus gespeicherten Bewertungen und Flutschutz-Abmeldungen. Eine aktuelle Live-Prüfung fehlt.")
    zeilen = []
    for name, adresse in aktive:
        acct = wallets.get(name)
        acct = acct if isinstance(acct, dict) else {}
        k = nach_name.get(name, {})
        luecken, gruende = [], []
        if not acct or acct.get("adresse") != adresse:
            luecken.append("Konto fehlt oder Adresse passt nicht")
            k, acct = {}, {}
        start = _waechter_zeit(acct.get("gestartet"))
        alter_tage = (jetzt - start) / 86400 if start is not None and start <= jetzt else None
        letzter = _waechter_zeit(acct.get("letzter_trade"))
        # Quelle: CLAUDE.md, Feste Entscheidungen / 72 h ohne Trade. Wenn nie
        # gehandelt: seit gespeichertem Start (STRATEGIE.md, Wallet-Scout / Platz).
        if not acct.get("letzter_trade"):
            letzter = start
        pause = (jetzt - letzter) / 3600 if letzter is not None and letzter <= jetzt else None
        n = _waechter_zahl(k.get("geschlossen"))
        # Quelle: STRATEGIE.md, Copy Trading / Wallet-Pruefung: Urteil aus
        # geschlossenen Positionen; Wallet-Scout / Platz: ueber alle Runden.
        pnl = _waechter_zahl(k.get("pnl_geschlossen"))
        geschlossen = acct.get("geschlossen") or []
        if isinstance(geschlossen, list) and any(not isinstance(g, dict) or
                                                _waechter_zahl(g.get("pnl_sol")) is None for g in geschlossen):
            pnl = None
            luecken.append("Ergebnis einzelner Positionen fehlt")
        if pause is None:
            luecken.append("Handelspause unbekannt")
        if n is None or pnl is None:
            luecken.append("Ergebnis oder geschlossene Positionen unbekannt")
        if alter_tage is None:
            luecken.append("Startdatum unbekannt")
        # Quelle: CLAUDE.md, Wallet-Regeln: Flutschutz-Abmeldung als Bot-Hinweis
        # fuer 7 Tage; Grenzwerte (>30/min und >=80 % Fehler, oder >300/min)
        # prueft der Copy-Bot vor dem Speichern, das Dashboard liest nur den Beleg.
        f = flut.get(adresse)
        f = f if isinstance(f, dict) else {}
        flut_zeit = _waechter_zeit(f.get("zuletzt"))
        bot = flut_zeit is not None and 0 <= jetzt - flut_zeit <= 7 * 86400
        if bot:
            gruende.append("Flutschutz-Abmeldung innerhalb von 7 Tagen")
        s = scout.get(adresse, {})
        fehlerquote, takt = _waechter_zahl(s.get("fehlgeschlagen")), _waechter_zahl(s.get("tx_pro_h"))
        scout_zeit = _waechter_zeit(s.get("zeit"))
        # Quelle: CLAUDE.md, Wallet-Regeln / Bot-Regeln Stufe 1, konkretisiert
        # in STRATEGIE.md, Wallet-Scout Stufe 1: >80 % oder >50 % bei >60/h.
        scout_bot = (scout_zeit is not None and scout_zeit <= jetzt and fehlerquote is not None
                     and 0 <= fehlerquote <= 1 and (fehlerquote > 0.8 or
                     (fehlerquote > 0.5 and takt is not None and takt > 60)))
        if scout_bot:
            bot = True
            gruende.append("Bot-Verdacht aus gespeicherter Scout-Bewertung")
        # Datenluecke anzeigen, ohne daraus eine neue Ersetzungsregel zu machen.
        # Quelle fuer die 6-h-Frische: STRATEGIE.md, Wallet-Scout / Warteliste.
        if (scout_zeit is None or not 0 <= jetzt - scout_zeit <= 6 * 3600 or
                fehlerquote is None or not 0 <= fehlerquote <= 1 or takt is None or takt < 0):
            luecken.append("Aktuelle Scout-Prüfung fehlt")
        still = pause is not None and pause >= 72
        if still:
            gruende.append("Mindestens 72 Stunden ohne Trade" + ("; Datenstand sperrt Entfernung" if not frisch else ""))
        # Quelle: CLAUDE.md, Wallet-Regeln / Schonfrist 7 Tage oder 30 Positionen,
        # nur fuer Ergebnis. STRATEGIE.md, Schonfrist: unter BEIDEN Grenzen.
        schonfrist = n is not None and n < 30 and alter_tage is not None and alter_tage < 7
        # Quelle: CLAUDE.md, Wallet-Regeln: >=30 geschlossene Positionen und
        # >1 SOL Verlust; STRATEGIE.md, Platz: ueber alle Runden, groesster zuerst.
        verlust = n is not None and n >= 30 and pnl is not None and pnl < -1 and not schonfrist
        if verlust:
            gruende.append("Mindestens 30 Positionen und mehr als 1 SOL Verlust")
        kandidat = "bot" if bot else "still" if still and frisch else "verlust" if verlust else None
        ampel = "rot" if kandidat else "gelb" if still or schonfrist or luecken else "gruen"
        zeilen.append({"name": name, "wallet": adresse, "ampel": ampel, "kandidat": kandidat,
                       "gruende": gruende, "luecken": luecken, "pause_h": pause, "gestartet": start,
                       "letzter_trade": _waechter_zeit(acct.get("letzter_trade")), "alter_tage": alter_tage,
                       "geschlossen": n, "ergebnis": pnl, "schonfrist": schonfrist,
                       "ergebnis_seit_start": _waechter_zahl(k.get("ergebnis_seit_start")),
                       "scout_zeit": scout_zeit, "flutschutz_zeit": flut_zeit})
    # Quelle: CLAUDE.md, Automatische Aufnahme: Bot -> still -> groesster Verlust.
    # STRATEGIE.md, Platz: stille Wallets nach laengster Pause. Gleichstand nach Name.
    kandidaten = [z for z in zeilen if z["kandidat"]]
    kandidaten.sort(key=lambda z: ({"bot": 0, "still": 1, "verlust": 2}[z["kandidat"]],
                                  -z["pause_h"] if z["kandidat"] == "still" else
                                  z["ergebnis"] if z["kandidat"] == "verlust" else 0, z["name"]))
    warteliste = []
    try:
        with (repo / "scout" / "warteliste.csv").open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not set(WAECHTER_WARTESPALTEN) <= set(reader.fieldnames or []):
                hinweise.append("Warteliste: Spalten fehlen; unbekannte Werte bleiben leer.")
            for row in reader:
                if not row.get("wallet"):
                    hinweise.append("Warteliste: eine Zeile ohne Wallet-Adresse wurde ausgelassen.")
                    continue
                w = {feld: row.get(feld) for feld in WAECHTER_WARTESPALTEN}
                for feld in WAECHTER_WARTESPALTEN[5:]:
                    w[feld] = _waechter_zahl(w[feld])
                w["seit"], w["bewertet"] = _waechter_zeit(w["seit"]), _waechter_zeit(w["bewertet"])
                # Quelle: CLAUDE.md, Automatische Aufnahme (Warteliste), Details in
                # STRATEGIE.md, Warteliste: 7 Tage warten, ab >6 h frisch pruefen.
                w["abgelaufen"] = w["seit"] is not None and jetzt - w["seit"] > 7 * 86400
                w["neu_pruefen"] = w["bewertet"] is None or not 0 <= jetzt - w["bewertet"] <= 6 * 3600
                warteliste.append(w)
    except (OSError, ValueError, csv.Error, UnicodeError):
        hinweise.append("Warteliste fehlt oder ist nicht lesbar.")
    ab = datetime.fromtimestamp(jetzt, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    heute = _waechter_heute(repo, ab, jetzt, hinweise)
    heute["limit"] = WAECHTER_TAGESLIMIT
    heute["rest"] = max(0, WAECHTER_TAGESLIMIT - heute["anzahl"]) if heute["anzahl"] is not None else None
    return {"jetzt": jetzt, "tagesbeginn": ab, "gespeichert": gespeichert, "konten_frisch": frisch,
            "aktiv": len(aktive) if liste_ok else None,
            "maximum": WAECHTER_MAX_WALLETS, "heute": heute, "wallets": zeilen, "kandidaten": kandidaten,
            "naechster": kandidaten[0] if kandidaten else None, "warteliste": warteliste,
            "hinweise": list(dict.fromkeys(hinweise))}
