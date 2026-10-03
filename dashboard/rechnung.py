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
    return {"key": key, "label": label, "frei": frei, "markt": markt, "kontowert": kontowert,
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


def copy_konto(name, acct, aktiv, journal_rows, korrigiert):
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
    }


def copy_konten(repo=None):
    repo = Path(repo or REPO)
    data = lade_json(repo / cb.ACCOUNTS_FILE, {}) or {}
    aktiv = {n for n, _ in aktive_wallets(repo)}
    korr = korrekturen(repo)
    rows = journal_bereinigen(lade_csv(repo / cb.JOURNAL_FILE), korr)
    korrigiert = korrigierte_positionen(korr)
    konten = [copy_konto(n, a, n in aktiv, rows, korrigiert) for n, a in (data.get("wallets") or {}).items()]
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
