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
KONTEN = [("hauptstrategie", "Hauptstrategie")] + list(core.EXPERIMENTS.items())
BOT_COMMITS = {"Hauptbot": "NARRATIV", "Copy-Bot": "COPY"}
SCOUT_HEADER = ["zeit", "wallet", "quelle", "coin", "ergebnis", "grund", "punkte", "tx", "fehlgeschlagen",
                "tx_pro_h", "inaktiv_h", "trades", "kaeufe", "verkaeufe", "trades_pro_tag", "kauf_median_sol",
                "anteil_kaeufe_ab_0_1", "coins_abgeschlossen", "trefferquote", "gewinn_sol",
                "gewinn_ohne_beste_sol", "beste_abgezogen", "rendite_median_pct", "rendite_ohne_beste_pct",
                "haltedauer_median_min", "mini_verkaeufe_anteil", "bot_gebuehr_anteil", "coins",
                "coins_gehalten", "rendite_pct", "rendite_ohne_besten_pct", "reibung_pp"]


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


def trade_kennzahlen(closed):
    """Trades, Summe, SOL je Trade, Gewinner, und dasselbe ohne die 3 besten Trades."""
    pnls = sorted((as_float(c.get("pnl_sol")) for c in closed), reverse=True)
    n = len(pnls)
    rest = pnls[BESTE_WEGLASSEN:]
    return {"trades": n, "summe": sum(pnls), "pro_trade": sum(pnls) / n if n else None,
            "gewinner": sum(1 for x in pnls if x > 0),
            "ohne_beste_summe": sum(rest), "ohne_beste_pro_trade": sum(rest) / len(rest) if rest else None,
            "fortschritt": min(1.0, n / ZIEL_TRADES)}


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
            "gespeichert": p.get("saved_at"), "offen": offen, "closed": closed, **trade_kennzahlen(closed)}


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
    a, b = trade_kennzahlen(eigene), trade_kennzahlen(kg)
    # "im Plus" bezieht sich auf dieselben Trades wie das Urteil (Vergleichszeitraum), nicht auf den Kontowert
    res = {"beginn": beginn, "eigen": a, "kontrolle": b, "im_plus": a["summe"] > 0}
    if not a["trades"] or not b["trades"]:
        return {**res, "ampel": "keine_daten", "text": "noch keine Trades zum Vergleichen"}
    besser = a["pro_trade"] > b["pro_trade"]
    besser_ohne = (a["ohne_beste_pro_trade"] or 0) > (b["ohne_beste_pro_trade"] or 0)
    if a["trades"] < ZIEL_TRADES:
        tendenz = "besser" if besser and besser_ohne else "schlechter" if not besser and not besser_ohne else "gemischt"
        return {**res, "ampel": "zu_frueh", "tendenz": tendenz,
                "text": f"zu früh: {a['trades']} von {ZIEL_TRADES} Trades im Vergleichszeitraum, Tendenz {tendenz}"}
    if besser and besser_ohne:
        return {**res, "ampel": "besser", "text": "besser als die Kontrollgruppe, auch ohne die 3 besten"}
    if not besser and not besser_ohne:
        return {**res, "ampel": "schlechter", "text": "schlechter als die Kontrollgruppe"}
    return {**res, "ampel": "gemischt", "text": "nur mit den 3 besten Trades besser – hält nicht"
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
        if len(r) != len(SCOUT_HEADER):
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
