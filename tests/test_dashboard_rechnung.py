"""Dashboard: gemeinsame Rechenlogik (dashboard/rechnung.py). Gleiche Rechnung wie Discord und Tagesauswertung."""
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

import bot as core
import copy_bot as cb
import scout_bot as scout
from helpers import MINT, WALLET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))
import rechnung as r  # noqa: E402

START = 0.0001


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def closed(pnl, tag="2026-10-02T12:00:00+00:00"):
    return {"pnl_sol": pnl, "closed_at": tag, "symbol": "X"}


# ================================================================ Zahlen und Zeiten

def test_zahlen_deutsch_mit_vorzeichen():
    assert r.zahl(-1234.5, 2) == "−1.234,50"
    assert r.sol_text(0.0123) == "+0,012 SOL"
    assert r.sol_text(-0.0004) == "0,000 SOL"                    # gerundet null: kein Vorzeichen
    assert r.sol_text(2.5, vorzeichen=False) == "2,500 SOL"


def test_zeit_utc_und_deutsche_zeit():
    assert r.zeit_text("2026-10-03 12:31:00") == "03.10. 12:31 UTC (14:31 dt. Zeit)"
    assert r.zeit_text(None) == "–"


# ================================================================ Hauptstrategie und Experimente

def test_kontowert_wie_discord(market):
    """Gleiche Zahl wie die Portfolio-Uebersicht unter den Discord-Meldungen (bot.portfolio_embed)."""
    market.set(MINT, price=START)
    p = core.load_portfolio()
    core.open_position(p, core.token_view(market.tokens[MINT], time.time()),
                       {"quelle": "block0", "block0_wallets": 0, "block0_supply_pct": 0.0,
                        "block0_still_held_pct": 0.0}, market.sol_usd)
    market.price[MINT] = START * 1.7
    text = core.portfolio_embed(p, market.sol_usd)[0]["description"]
    discord_gesamt = float(re.search(r"\*\*Gesamt:\*\* ([\d.]+) SOL", text).group(1))
    k = r.konto_strategie("hauptstrategie", "Hauptstrategie", p, {MINT: ("", START * 1.7)}, sol_usd=market.sol_usd)
    assert round(k["kontowert"], 3) == discord_gesamt
    discord_offen = float(re.search(r"Offene Positionen zusammen:\*\* ([+-][\d.]+) SOL", text).group(1))
    assert round(k["offen"][0]["pnl"], 3) == discord_offen
    # Ohne Live-SOL-Kurs: der SOL-Kurs beim Kauf wird aus dem Kaufpreis zurueckgerechnet
    assert r.sol_usd_beim_kauf(p["positions"][MINT]) == pytest.approx(market.sol_usd, rel=1e-6)
    k2 = r.konto_strategie("hauptstrategie", "Hauptstrategie", p, {MINT: ("", START * 1.7)})
    assert k2["kontowert"] == pytest.approx(k["kontowert"], rel=1e-9)


def test_position_ohne_kurs_zaehlt_wie_in_discord_nicht_mit():
    p = {"bankroll_sol": 9.8, "positions": {"m": {"mint": "m", "symbol": "A", "tokens_left": 1.0, "invested_sol": 0.2,
                                                  "proceeds_sol": 0.0, "entry_fill_usd": 1.0, "tokens_initial": 1.0}},
         "closed": []}
    k = r.konto_strategie("x", "X", p, {})
    assert k["kontowert"] == 9.8 and k["offen"][0]["wert"] is None


def test_trade_kennzahlen_ohne_die_3_besten():
    k = r.trade_kennzahlen([closed(x) for x in (1.0, 0.5, 0.2, -0.1, -0.1)])
    assert k["trades"] == 5 and k["summe"] == pytest.approx(1.5) and k["pro_trade"] == pytest.approx(0.3)
    assert k["ohne_beste_summe"] == pytest.approx(-0.2) and k["ohne_beste_pro_trade"] == pytest.approx(-0.1)
    assert k["gewinner"] == 3 and k["fortschritt"] == pytest.approx(5 / 200)


def konto(key, pnls, gestartet="2026-10-01T00:00:00+00:00", tag="2026-10-02T12:00:00+00:00"):
    return {"key": key, "gestartet": gestartet, "closed": [closed(x, tag) for x in pnls]}


def test_vergleich_nur_gleicher_zeitraum_und_ampel():
    kg = {"key": "kontrollgruppe", "gestartet": "2026-10-01T00:00:00+00:00",
          "closed": [closed(-5.0, "2026-09-30T00:00:00+00:00")] + [closed(-0.01) for _ in range(10)]}
    v = r.vergleich_mit_kontrolle(konto("a", [0.01] * 50), kg)
    assert v["kontrolle"]["trades"] == 10                        # Trade vor dem Start zaehlt nicht
    assert v["ampel"] == "zu_frueh" and v["tendenz"] == "besser" and "50 von 200" in v["text"]
    assert r.vergleich_mit_kontrolle(konto("a", [0.01] * 200), kg)["ampel"] == "besser"
    assert r.vergleich_mit_kontrolle(konto("a", [-0.02] * 200), kg)["ampel"] == "schlechter"
    gluck = konto("a", [10.0, 10.0, 10.0] + [-0.05] * 197)        # nur die 3 besten retten das Ergebnis
    v = r.vergleich_mit_kontrolle(gluck, kg)
    assert v["ampel"] == "gemischt" and "hält nicht" in v["text"]
    assert r.vergleich_mit_kontrolle({"key": "kontrollgruppe", "closed": []}, kg)["ampel"] == "basis"
    assert r.vergleich_mit_kontrolle(konto("a", []), kg)["ampel"] == "keine_daten"


def test_kontoverlauf():
    k = konto("a", [0.5, -0.2])
    pts = r.kontoverlauf(k)
    assert [round(p["kontostand"], 3) for p in pts] == [10.0, 10.5, 10.3]


def test_letzte_kurse_nur_offene_positionen(tmp_path):
    write_csv(tmp_path / "verlauf" / "2026-10-03.csv", ["zeit", "mint", "phase", "preis_usd"], [
        ["2026-10-03 10:00:00", "a", "offen", "1.0"], ["2026-10-03 10:01:00", "a", "offen", "2.0"],
        ["2026-10-03 10:02:00", "b", "exp_kontrollgruppe_offen", "3.0"],
        ["2026-10-03 10:03:00", "c", "nach_verkauf", "9.0"]])
    kurse = r.letzte_kurse(tmp_path / "verlauf")
    assert kurse == {"a": ("2026-10-03 10:01:00", 2.0), "b": ("2026-10-03 10:02:00", 3.0)}


# ================================================================ Copy Trading

KORR_HEADER = ["art", "zeit", "trader", "aktion", "symbol", "mint", "trader_signatur", "unser_sol", "pnl_sol",
               "behandlung"]


def copy_repo(tmp_path):
    acct = {"adresse": WALLET, "bankroll_sol": 9.0, "runde": 1, "letzter_trade": 1.0,
            "positionen": {
                "m1": {"mint": "m1", "tokens_raw": 2_000_000, "decimals": 6, "letzter_preis_sol": 0.1,
                       "invested_sol": 0.2, "proceeds_sol": 0.0},
                "m2": {"mint": "m2", "tokens_raw": 1_000_000, "decimals": 6, "letzter_preis_sol": 0.3,
                       "invested_sol": 0.2, "proceeds_sol": 0.0, "verkauf_offen": True}},
            "geschlossen": [
                {"mint": "ok", "runde": 1, "pnl_sol": 0.1, "pnl_pct": 50.0, "trader_pnl_pct": 20.0},
                {"mint": "ok2", "runde": 1, "pnl_sol": -0.1, "pnl_pct": -50.0, "trader_pnl_pct": -10.0},
                {"mint": "doppelt", "runde": 1, "pnl_sol": 0.5, "pnl_pct": 250.0, "trader_pnl_pct": 1.0}],
            "schatten_geschlossen": [{"pnl_sol": -0.05}, {"pnl_sol": 0.02}]}
    os.makedirs(tmp_path / "copy")
    json.dump({"wallets": {"Alpha": acct}, "saved_at": 100.0}, open(tmp_path / cb.ACCOUNTS_FILE, "w"))
    open(tmp_path / cb.WALLET_FILE, "w").write(f"Alpha: {WALLET}\n")
    write_csv(tmp_path / cb.JOURNAL_FILE, ["zeit", "trader", "aktion", "trader_signatur", "verzoegerung_s",
                                           "preisabstand_pct"], [
        ["2026-10-01 10:00:00", "Alpha", "KAUF", "s1", "1.0", "2.0"],
        ["2026-10-01 10:01:00", "Alpha", "KAUF", "s2", "3.0", "4.0"],
        ["2026-10-01 10:02:00", "Alpha", "VERPASST_KAUF", "s1", "", ""],
        ["2026-10-01 10:03:00", "Alpha", "KAUF", "s3", "100.0", "0.0"]])         # Fehlbuchung (Korrektur)
    write_csv(tmp_path / "auswertungen" / "korrekturen.csv", KORR_HEADER, [
        ["falscher_verpasst_kauf", "2026-10-01 10:02:00", "Alpha", "VERPASST_KAUF", "", "x", "s1", "", "", ""],
        ["verlorene_position", "2026-10-01 10:03:00", "Alpha", "KAUF", "", "x", "s3", "", "", ""],
        ["doppelter_verkauf", "2026-10-01 11:00:00", "Alpha", "VERKAUF", "", "doppelt", "s9", "", "", ""]])
    return tmp_path


def test_copy_konto_wie_discord_und_vorsichtig(tmp_path):
    repo = copy_repo(tmp_path)
    konten, saved, rows = r.copy_konten(repo)
    k = konten[0]
    acct = json.load(open(repo / cb.ACCOUNTS_FILE))["wallets"]["Alpha"]
    assert k["kontowert"] == pytest.approx(acct["bankroll_sol"] + cb.open_value(acct))     # wie Konto-Zeile
    assert k["kontowert"] == pytest.approx(9.0 + 0.2 + 0.3)
    assert k["vorsichtig"] == pytest.approx(9.0 + 0.2) and k["wartend"] == 1               # wartend = Wert 0
    assert k["ergebnis_runde"] == pytest.approx(-0.5) and saved == 100.0 and k["aktiv"]


def test_copy_korrekturen_herausgerechnet(tmp_path):
    repo = copy_repo(tmp_path)
    konten, _, rows = r.copy_konten(repo)
    assert [x["trader_signatur"] for x in rows] == ["s1", "s2"]                          # 2 Fehlbuchungen weg
    k = konten[0]
    assert k["verzoegerung_median_s"] == pytest.approx(2.0)                             # ohne die 100 s
    assert k["vergleiche"] == 2 and k["korrigiert"]                                     # doppelt-Position raus
    assert k["wir_median_pct"] == pytest.approx(0.0) and k["trader_median_pct"] == pytest.approx(5.0)
    assert k["schatten"] == 2 and k["schatten_pnl"] == pytest.approx(-0.03)


def test_echte_korrekturliste_passt_zum_format():
    korr = r.korrekturen()
    assert korr and set(KORR_HEADER) <= set(korr[0])
    assert {k["art"] for k in korr} >= {"doppelter_verkauf", "falscher_verpasst_kauf"}


# ================================================================ Scout

def test_scout_kopfzeile_wie_scout_bot():
    scout.write_csv([{"wallet": "w"}])
    header = next(csv.reader(open(scout.CANDIDATES_FILE, encoding="utf-8")))
    assert header == r.SCOUT_HEADER


def test_scout_rangliste_neueste_bewertung_je_wallet(tmp_path):
    def row(**kw):
        d = dict.fromkeys(r.SCOUT_HEADER, "")
        d.update(kw)
        return [d[k] for k in r.SCOUT_HEADER]
    write_csv(tmp_path / "scout" / "kandidaten.csv", r.SCOUT_HEADER, [
        row(zeit="2026-10-02 10:00:00", wallet="A", ergebnis="bewertet", punkte="5"),
        row(zeit="2026-10-03 10:00:00", wallet="A", ergebnis="bewertet", punkte="9"),
        row(zeit="2026-10-03 10:00:00", wallet="B", ergebnis="bewertet", punkte="20"),
        row(zeit="2026-10-03 10:00:00", wallet="C", ergebnis="raus", punkte=""),
        ["alt", "D", "zu", "wenig", "Spalten"]])
    liste = r.scout_rangliste(tmp_path)
    assert [(x["wallet"], x["punkte"]) for x in liste] == [("B", "20"), ("A", "9"), ("C", "")]


# ================================================================ Betrieb

def test_luecken_und_status():
    t = [0, 60, 120, 120 + 30 * 60, 120 + 31 * 60]
    assert r.luecken(t, 20) == [(120, 120 + 30 * 60)]
    assert r.luecken(t, 20, jetzt=t[-1] + 25 * 60)[-1] == (t[-1], None)                # laufende Luecke
    assert r.bot_status(1000, 1000 + 10 * 60) == "ok"
    assert r.bot_status(1000, 1000 + 30 * 60) == "achtung"
    assert r.bot_status(1000, 1000 + 61 * 60) == "kaputt" and r.bot_status(None, 0) == "kaputt"


def test_messung_und_notloesung(tmp_path):
    write_csv(tmp_path / "messung.csv", ["abweichung_pct"], [["+1.00"], ["+3.00"], ["-1.00"]])
    write_csv(tmp_path / core.JOURNAL_FILE, ["aktion", "notloesung"], [["VERKAUF", "1"], ["VERKAUF", ""]])
    m = r.messung(tmp_path)
    assert m["Hauptbot und Experimente"]["anzahl"] == 3 and m["Hauptbot und Experimente"]["median"] == 1.0
    assert m["Copy-Bot"]["anzahl"] == 0 and m["notloesung"] == 1


def test_dashboard_schreibt_nie_daten():
    """Regel: nur lesen. Kein Schreiben, Loeschen oder Verschieben im Dashboard-Code."""
    ordner = Path(__file__).resolve().parent.parent / "dashboard"
    for datei in ordner.rglob("*.py"):
        if ".venv" in datei.parts:
            continue
        src = datei.read_text(encoding="utf-8")
        assert not re.search(r"open\([^)]*['\"][wax]\+?['\"]", src), f"{datei.name}: Datei wird geschrieben"
        for verboten in ("os.remove", "os.replace", "shutil.", ".unlink(", ".write_text(", "json.dump(",
                         "git push", "git commit", "gh workflow"):
            assert verboten not in src, f"{datei.name}: {verboten}"


def test_dashboard_pakete_fest_und_getrennt_von_den_bots():
    wurzel = Path(__file__).resolve().parent.parent
    zeilen = [z.strip() for z in (wurzel / "dashboard" / "requirements.txt").read_text(encoding="utf-8").splitlines()
              if z.strip() and not z.strip().startswith("#")]
    assert zeilen and all(re.fullmatch(r"[A-Za-z0-9_.\-]+==[0-9][0-9A-Za-z.\-]*", z) for z in zeilen)
    assert any(z.startswith("streamlit==") for z in zeilen)
    bots = (wurzel / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit" not in bots and "pandas" not in bots           # Bots bleiben schlank
    gleich = {z.split("==")[0]: z for z in zeilen}
    for z in bots.split():                                             # gemeinsame Pakete: gleiche Version
        assert gleich.get(z.split("==")[0], z) == z


def test_urteil_trennt_zufall_und_plus_minus():
    kg = {"key": "kontrollgruppe", "gestartet": "2026-10-01T00:00:00+00:00", "closed": [closed(-0.03) for _ in range(10)]}
    v = r.vergleich_mit_kontrolle(konto("a", [-0.01] * 200), kg)
    assert v["ampel"] == "besser" and not v["im_plus"]
    assert r.urteil_kurz(v) == "besser als Zufall, aber im Minus"
    v = r.vergleich_mit_kontrolle(konto("a", [0.01] * 200), kg)
    assert r.urteil_kurz(v) == "besser als Zufall, im Plus"
    v = r.vergleich_mit_kontrolle(konto("a", [-0.05] * 20), kg)
    assert r.urteil_kurz(v) == "zu früh · Tendenz schlechter als Zufall · im Minus"
    assert r.urteil_kurz({"ampel": "basis"}) == "Vergleichsbasis (Zufall)"


def test_ausreisser_mehr_als_haelfte_des_gesamtergebnisses():
    assert r.ausreisser([("A", 24.5), ("B", -10.0), ("C", -5.0)]) == [("A", 24.5, pytest.approx(24.5 / 9.5))]
    assert r.ausreisser([("A", 1.0), ("B", 1.0), ("C", 1.0)]) == []          # keiner ueber der Haelfte
    assert [n for n, _, _ in r.ausreisser([("A", -37.0), ("B", 24.5), ("C", -10.0)])] == ["A"]
    assert r.ausreisser([("A", 1.0), ("B", -1.0)]) == []                   # Gesamt null


def test_copy_ergebnis_seit_start_ueber_alle_runden():
    acct = {"bankroll_sol": 10.0, "runde": 2, "positionen": {
                "o": {"mint": "o", "tokens_raw": 1_000_000, "decimals": 6, "letzter_preis_sol": 0.1, "runde": 1,
                      "invested_sol": 0.2, "proceeds_sol": 0.05, "fees_sol": 0.002, "verkauf_offen": True}},
            "geschlossen": [{"mint": "a", "runde": 1, "pnl_sol": -9.5}, {"mint": "b", "runde": 2, "pnl_sol": 0.3}]}
    k = r.copy_konto("X", acct, True, [], set())
    assert k["ergebnis_seit_start"] == pytest.approx(-9.5 + 0.3 + (0.05 + 0.1 - 0.2 - 0.002))   # beide Runden
    assert k["ergebnis_runde"] == pytest.approx(0.1)                       # nur laufende Runde: 10 + 0,1 - 10
    assert k["ergebnis_seit_start_vorsichtig"] == pytest.approx(-9.5 + 0.3 + (0.05 - 0.2 - 0.002))


def test_exit_liquiditaet_trader_verkauft_schnell():
    rows = [
        {"aktion": "KAUF", "trader": "A", "mint": "m1", "trader_zeit": "2026-10-03 10:00:00", "zeit": "2026-10-03 10:00:05"},
        {"aktion": "VERKAUF", "trader": "A", "mint": "m1", "trader_zeit": "2026-10-03 10:00:03"},   # vor unserem Kauf
        {"aktion": "KAUF", "trader": "A", "mint": "m2", "trader_zeit": "2026-10-03 11:00:00", "zeit": "2026-10-03 11:00:02"},
        {"aktion": "VERKAUF_GEMERKT", "trader": "A", "mint": "m2", "trader_zeit": "2026-10-03 11:30:00"},
        {"aktion": "KAUF", "trader": "B", "mint": "m3", "trader_zeit": "kaputt", "zeit": "x"},
    ]
    e = r.exit_liquiditaet(rows)["A"]
    assert e["kaeufe"] == 2 and e["raus_vor_uns"] == 1 and e["raus_60s"] == 1
    assert e["median_halte_s"] == pytest.approx((3 + 1800) / 2)
    assert "B" not in r.exit_liquiditaet(rows)


def test_paarvergleich_coin_fuer_coin():
    def c(mint, pnl, zu, hold_h=1.0, sym="X"):
        return {"mint": mint, "symbol": sym, "pnl_sol": pnl, "hold_h": hold_h, "exit_reason": "R",
                "closed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(zu))}
    t = 1_790_000_000
    haupt = [c("A", -0.08, t), c("B", 0.10, t), c("C", 0.05, t), c("A", 0.30, t + 3 * 86400)]
    exp = [c("A", -0.05, t + 60, hold_h=1.0 + 60 / 3600), c("B", 0.06, t), c("D", 1.0, t)]
    pv = r.paarvergleich(exp, haupt)
    assert pv["anzahl"] == 2                                      # D ohne Gegenstueck, A nur der fruehe Kauf
    a = next(x for x in pv["paare"] if x["mint"] == "A")
    assert a["haupt"] == -0.08 and a["differenz"] == pytest.approx(0.03)
    assert pv["differenz"] == pytest.approx(-0.01) and pv["besser"] == 1 and pv["schlechter"] == 1
    assert pv["differenz_ohne_beste"] == pytest.approx(0.0)       # nur 2 Paare: ohne die 3 besten bleibt nichts
    assert r.paarvergleich([], haupt)["anzahl"] == 0


# ================================================================ Seite Lernen

def test_urteils_kalender_zaehlt_wie_testurteil_und_schaetzt_datum():
    jetzt = datetime(2026, 10, 4, 12, tzinfo=timezone.utc).timestamp()
    kg = {"key": "kontrollgruppe", "label": "KG", "gestartet": "2026-10-01T00:00:00+00:00", "closed": [closed(0.0)]}
    alt_ = [closed(0.01, "2026-09-30T00:00:00+00:00")]                   # vor dem Start der Kontrollgruppe
    neu = [closed(0.01, "2026-10-03T12:00:00+00:00") for _ in range(30)]  # 30 Trades in den letzten 3 Tagen
    a = {**konto("a", []), "label": "A", "closed": alt_ + neu}
    still = {**konto("b", [0.01] * 5), "label": "B"}                      # 5 Trades am 02.10., noch im 3-Tage-Fenster
    fertig = {**konto("c", [0.01] * 200), "label": "C"}
    beendet = {**konto("d", [0.01]), "label": "D", "beendet": "04.10."}
    for k in (a, still, fertig, beendet):
        k["vergleich"] = r.vergleich_mit_kontrolle(k, kg)
    kal = {z["key"]: z for z in r.urteils_kalender([kg, a, still, fertig, beendet], jetzt)}
    assert set(kal) == {"a", "b", "c"}                                    # ohne Kontrollgruppe und beendete
    assert kal["a"]["trades"] == 30 and kal["a"]["tempo_pro_tag"] == pytest.approx(10)
    assert kal["a"]["tage_bis_urteil"] == pytest.approx(17)               # 170 fehlen / 10 je Tag
    assert kal["c"]["rest"] == 0 and kal["c"]["tage_bis_urteil"] == 0
    assert kal["b"]["tempo_pro_tag"] == pytest.approx(5 / 3)
    kal_spaet = {z["key"]: z for z in r.urteils_kalender([kg, still], jetzt + 5 * 86400)}
    assert kal_spaet["b"]["eta"] is None                                  # kein Trade in 3 Tagen: nicht absehbar


def test_verlust_lupe_merkmale_gruende_und_verschenkt():
    def c(pnl, grund, hoch=1.0, sprung=10.0):
        return {"pnl_sol": pnl, "exit_reason": grund, "peak_multiple": hoch, "symbol": "X", "mint": "M",
                "closed_at": "2026-10-02T12:00:00+00:00", "entry_view": {"price_change_5m": sprung}}
    k = {"key": "hauptstrategie", "label": "Haupt", "closed": [
        c(-0.10, "NOTBREMSE (-25 %)", sprung=5), c(-0.05, "NOTBREMSE (-30 %)", sprung=7),
        c(-0.02, "GEWINN_GESCHUETZT (Hoch 1.6x, zurueck auf Einstand)", hoch=1.6, sprung=9),
        c(0.20, "TP2", hoch=3.0, sprung=30), {"pnl_sol": 0.1, "exit_reason": "", "closed_at": None}]}
    trades = r.lupe_trades([k])
    assert len(trades) == 5 and trades[4]["grund"] == "?" and trades[4]["Kurs 5 min %"] is None
    v = r.lupe_vergleich(trades)
    m = next(x for x in v["merkmale"] if x["merkmal"] == "Kurs 5 min %")
    assert v["verlierer"] == 3 and v["gewinner"] == 2
    assert m["verlierer"] == 7 and m["gewinner"] == 30 and m["n_gewinner"] == 1   # fehlender Wert zaehlt nicht
    g = r.lupe_gruende(trades)
    assert g[0]["grund"] == "NOTBREMSE" and g[0]["trades"] == 2 and g[0]["summe"] == pytest.approx(-0.15)
    assert g[0]["anteil_verlierer"] == 1.0 and g[0]["schlechtester"] == pytest.approx(-0.10)
    assert [t["grund"] for t in trades if t["verschenkt"]] == ["GEWINN_GESCHUETZT"]


def test_filter_trichter_zaehlt_coins_je_grund_und_kaeufe(tmp_path):
    jetzt = datetime(2026, 10, 4, 12, tzinfo=timezone.utc).timestamp()
    write_csv(tmp_path / "abgelehnt.csv", ["zeit", "symbol", "mint", "grund"], [
        ["2026-10-04 10:00:00", "A", "m1", "STORY_ZU_ALT"], ["2026-10-04 10:05:00", "A", "m1", "STORY_ZU_ALT"],
        ["2026-10-04 10:06:00", "B", "m2", "STORY_ZU_ALT"], ["2026-10-03 09:00:00", "C", "m3", "FOMO_SPRUNG"],
        ["2026-09-20 09:00:00", "D", "m4", "ZU_JUNG"]])                       # zu alt fuer 7 Tage
    write_csv(tmp_path / "journal.csv", ["zeit", "aktion", "symbol", "mint"], [
        ["2026-10-04 11:00:00", "KAUF", "E", "m5"], ["2026-10-04 11:30:00", "VERKAUF", "E", "m5"]])
    t = r.filter_trichter(tmp_path, tage=7, jetzt=jetzt)
    assert t["pruefungen"] == 4 and t["coins"] == 3 and t["kaeufe"] == 1
    assert t["gruende"][0] == {"grund": "STORY_ZU_ALT", "pruefungen": 3, "coins": 2, "anteil": 0.75}
    assert t["je_tag"] == [{"tag": "2026-10-03", "abgelehnt": 1, "kaeufe": 0},
                           {"tag": "2026-10-04", "abgelehnt": 3, "kaeufe": 1}]
    heute = r.filter_trichter(tmp_path, tage=1, jetzt=jetzt)               # 1 = nur heute (UTC)
    assert heute["pruefungen"] == 3 and heute["kaeufe"] == 1 and [d["tag"] for d in heute["je_tag"]] == ["2026-10-04"]
    assert r.filter_trichter(tmp_path / "leer", jetzt=jetzt)["pruefungen"] == 0
