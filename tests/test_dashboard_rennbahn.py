"""Rennbahn: gemeinsame Zahlen, Kosten, Runden, Datenluecken und Seitenauswahl."""
import copy
import sys
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"
sys.path.insert(0, str(DASHBOARD))
import rechnung as r  # noqa: E402

START = "2026-10-01T00:00:00+00:00"


def trade(pnl=0.1, zeit="2026-10-02T12:00:00+00:00", einsatz=0.2, runde=1):
    return {"pnl_sol": pnl, "closed_at": zeit, "invested_sol": einsatz, "runde": runde}


def konto(key, closed=None, **portfolio):
    p = {"started": START, "bankroll_sol": 10.1, "closed": closed or [], **portfolio}
    return r.konto_strategie(key, key, p, {})


def zeile(rennen, key):
    return next(k for k in rennen["rangliste"] + rennen["beendet"] if k["key"] == key)


def punkte(rennen, key):
    return [p for p in rennen["verlauf"] if p["key"] == key]


@pytest.mark.parametrize("key", ["hauptstrategie", "endspurt", "zweite_welle"])
def test_zahlen_wie_konto_strategie_und_strategieseite(key):
    offene = {"m": {"mint": "m", "symbol": "X", "tokens_initial": 1, "tokens_left": 1,
                    "entry_fill_usd": 0.2, "invested_sol": 0.2}}
    k = r.konto_strategie(key, key, {"started": START, "bankroll_sol": 10.3,
                                   "closed": [trade(), trade(-0.04, einsatz=0.4)], "positions": offene},
                         {"m": (START, 0.4)}, sol_usd=1)
    kg = konto(r.KONTROLLE, [trade(-0.02)])
    before = copy.deepcopy([k, kg])
    rennen = r.rennbahn([k, kg])
    row = zeile(rennen, key)
    assert row["ergebnis"] == pytest.approx(k["ergebnis"])
    assert row["ergebnis_kosten"] == pytest.approx(r.ergebnis_mit_kosten(k))
    assert row["ergebnis_kosten"] == pytest.approx(r.kontowert_mit_kosten(k) - r.START_SOL)
    assert row["trades"] == k["trades"]
    assert row["trades_bis_200"] == r.ZIEL_TRADES - k["trades"]
    vergleich = r.vergleich_mit_kontrolle(k, kg)
    assert row["vergleich"] == vergleich
    assert row["urteil"] == r.urteil_kurz(vergleich)
    assert row["urteil_kosten"] == r.urteil_kurz({**vergleich, **vergleich["kosten"]})
    assert [k, kg] == before


@pytest.mark.parametrize("key,pct", [("hauptstrategie", 2), ("endspurt", 4)])
def test_verlauf_start_null_und_kosten_nur_auf_bisherige_trades(key, pct):
    k = konto(key, [trade(-0.2, "2026-10-03T12:00:00Z", 0.6),
                    trade(0.5, "2026-10-02T12:00:00Z", 0.4)])
    pts = punkte(r.rennbahn([k]), key)
    assert [p["roh"] for p in pts] == pytest.approx([0, 0.5, 0.3])
    assert [p["mit_kosten"] for p in pts] == pytest.approx([0, 0.5 - 0.4 * pct / 100, 0.3 - pct / 100])
    assert [p["roh"] for p in pts] == pytest.approx(
        [p["kontostand"] - r.START_SOL for p in r.kontoverlauf(k)])


def test_kostenschalter_aendert_nur_kurvenwerte_auswahl_und_raenge_bleiben():
    konten = [konto("endspurt", [trade(0.01)]), konto(r.KONTROLLE, [trade(-0.01)])]
    roh = r.rennbahn(konten)
    netto = r.rennbahn(konten, mit_kosten=True)
    assert roh["rangliste"] == netto["rangliste"]
    assert roh["standard"] == netto["standard"]
    assert roh["hinweise"] == netto["hinweise"]
    for p, q in zip(roh["verlauf"], netto["verlauf"]):
        assert p["ergebnis"] == p["roh"]
        assert q["ergebnis"] == q["mit_kosten"]
        assert {k: v for k, v in p.items() if k != "ergebnis"} == {
            k: v for k, v in q.items() if k != "ergebnis"}


def test_runden_table_aktuell_kurve_alle_runden_keine_neustart_gewinne():
    k = konto("hauptstrategie", [trade(-9, runde=1), trade(0.5, runde=2)], runde=2, bankroll_sol=10.5)
    row = zeile(r.rennbahn([k]), "hauptstrategie")
    assert row["ergebnis"] == pytest.approx(0.5)
    assert row["ergebnis_kosten"] == pytest.approx(0.496)
    pts = punkte(r.rennbahn([k]), "hauptstrategie")
    assert pts[-1]["roh"] == pytest.approx(-8.5)
    assert pts[-1]["mit_kosten"] == pytest.approx(-8.508)
    assert row["runde"] == 2


def test_aktive_standard_beendete_getrennt_explizite_leere_auswahl():
    k = konto("hauptstrategie", [trade()])
    alt = konto("ohne_limit", [trade()])
    alt["beendet"] = "04.10.2026"
    rennen = r.rennbahn([k, alt])
    assert rennen["standard"] == ["hauptstrategie"]
    assert [x["key"] for x in rennen["rangliste"]] == ["hauptstrategie"]
    assert [x["key"] for x in rennen["beendet"]] == ["ohne_limit"]
    assert not punkte(rennen, "ohne_limit")
    pts = punkte(r.rennbahn([k, alt], sichtbar=["ohne_limit"]), "ohne_limit")
    assert pts and all(p["beendet"] for p in pts)
    assert r.rennbahn([k, alt], sichtbar=[])["verlauf"] == []


def test_vergleich_200_trades_gleicher_zeitraum_und_ohne_beste():
    k = konto("hauptstrategie", [trade(20)] * 3 + [trade(-0.05)] * 197,
              started="2026-10-02T00:00:00Z")
    kg = konto(r.KONTROLLE, [trade(-0.02)] * 20 + [trade(-50, "2026-10-01T12:00:00Z")])
    row = zeile(r.rennbahn([k, kg]), "hauptstrategie")
    assert row["trades_bis_200"] == 0
    assert row["vergleich"]["kontrolle"]["trades"] == 20
    assert row["vergleich"]["ampel"] == "gemischt"
    assert "hält nicht" in row["urteil"]
    # 200 Trades insgesamt garantieren noch keine 200 Trades im Vergleichszeitraum.
    kg["gestartet"] = "2026-10-03T00:00:00Z"
    row = zeile(r.rennbahn([k, kg]), "hauptstrategie")
    assert row["trades_bis_200"] == 0 and row["vergleich_trades"] == 0
    assert row["vergleich"]["ampel"] == "keine_daten"


def test_leer_fehlende_kontrolle_zeit_kurs_und_unlesbares_konto():
    assert r.rennbahn([])["rangliste"] == []
    leer = r.konto_strategie("hauptstrategie", "Hauptstrategie", {}, {})
    rennen = r.rennbahn([leer, None, {}, {"key": "kaputt", "closed": [None]}])
    row = zeile(rennen, "hauptstrategie")
    assert row["ergebnis"] is None and row["ergebnis_kosten"] is None
    assert not rennen["verlauf"]
    assert row["vergleich"]["ampel"] == "keine_daten"
    assert any("Kontrollgruppe fehlt" in h for h in rennen["hinweise"])
    k = konto("hauptstrategie", [{"pnl_sol": 0.5}], positions={"m": {"mint": "m"}})
    rennen = r.rennbahn([k])
    assert zeile(rennen, "hauptstrategie")["trades"] == 1
    assert not rennen["verlauf"]
    assert any("Trade-Zeit fehlt" in h for h in rennen["hinweise"])
    assert any("fehlt der Kurs" in h for h in rennen["hinweise"])


def test_fehlender_start_utc_sortierung_und_gleiche_verkaufszeiten():
    k = konto("hauptstrategie", [trade(0.2, "2026-10-02T10:30:00Z"),
                                trade(0.1, "2026-10-02T12:00:00+02:00"),
                                trade(-0.1, "2026-10-02T10:30:00Z")], started=None)
    rennen = r.rennbahn([k])
    pts = punkte(rennen, "hauptstrategie")
    assert [p["roh"] for p in pts] == pytest.approx([0, 0.1, 0.3, 0.2])
    assert [p["folge"] for p in pts] == [0, 1, 2, 3]
    assert any("Startzeit fehlt" in h for h in rennen["hinweise"])


def test_daten_cache_nutzt_vorhandene_strategie_konten(monkeypatch):
    pytest.importorskip("streamlit")
    import daten
    konten = [konto("hauptstrategie", [trade()]), konto(r.KONTROLLE, [trade()])]
    calls = []
    monkeypatch.setattr(daten, "strategie_konten", lambda head: calls.append(head) or konten)
    daten.rennbahn.clear()
    assert daten.rennbahn("test") == r.rennbahn(konten, sichtbar=[k["key"] for k in konten])
    daten.rennbahn("test")
    assert calls == ["test"]
    daten.rennbahn.clear()


@pytest.fixture
def seite(monkeypatch):
    import threading
    import time
    # Die globale Test-Sandbox ersetzt sleep; AppTest braucht echte Thread-Pausen.
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import ansicht
    import daten
    konten = [konto("hauptstrategie", [trade(0.03)]), konto(r.KONTROLLE, [trade(-0.02)]),
              konto("ohne_limit", [trade(-0.04)])]
    konten[-1]["beendet"] = "04.10.2026"
    rennen = r.rennbahn(konten, sichtbar=[k["key"] for k in konten])
    monkeypatch.setattr(daten, "rennbahn", lambda head: copy.deepcopy(rennen))
    monkeypatch.setattr(ansicht, "bot_status_eintraege", lambda: [])
    return AppTest.from_file(str(DASHBOARD / "app_pages/rennbahn.py"), default_timeout=15), rennen


def test_seite_schalter_auswahl_und_leere_auswahl(seite):
    app, rennen = seite
    app.run()
    assert not app.exception
    assert app.multiselect[0].value == rennen["standard"]
    html_roh = [e.value for e in app.get("html")]
    app.button_group[0].set_value("mit Kosten").run()
    assert not app.exception
    assert [e.value for e in app.get("html")] == html_roh
    app.multiselect[0].set_value(["ohne_limit"]).run()
    assert not app.exception
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("Noch kein Verlauf" in e.value for e in app.get("html"))


def test_seite_leere_daten_und_ladefehler(seite, monkeypatch):
    import daten
    app, _ = seite
    monkeypatch.setattr(daten, "rennbahn", lambda head: r.rennbahn([]))
    app.run()
    assert not app.exception
    assert any("Noch keine Konten" in e.value for e in app.get("html"))

    def kaputt(head):
        raise ValueError("Unlesbare lokale Daten")

    monkeypatch.setattr(daten, "rennbahn", kaputt)
    app.run()
    assert not app.exception
    assert any("Konten konnten nicht geladen" in e.value for e in app.get("html"))
