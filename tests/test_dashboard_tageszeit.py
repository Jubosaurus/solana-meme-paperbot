"""Tageszeit: synthetische Trades, UTC-Grenzen, Kosten und robuste Anzeige ohne Netzwerk."""
import copy
import json
import sys
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"
sys.path.insert(0, str(DASHBOARD))
import rechnung as r  # noqa: E402


def trade(pnl=0.1, zeit="2026-10-05T08:00:00Z", **extra):
    return {"pnl_sol": pnl, "closed_at": zeit, "hold_h": 0, "invested_sol": 0.2,
            "phase": "normal", **extra}


def feld(werte, tag, stunde):
    return next(v for v in werte["raster"] if v["tag"] == tag and v["stunde"] == stunde)


def test_utc_grenze_2359_0000_und_offset():
    trades = [trade(zeit="2026-10-05T23:59:59Z"), trade(zeit="2026-10-06T00:00:00Z"),
              trade(zeit="2026-10-06T01:59:59+02:00"),
              trade(zeit="2026-10-05T19:00:00-05:00")]
    werte = r.tageszeit_auswertung(trades)
    assert feld(werte, 0, 23)["trades"] == 2
    assert feld(werte, 1, 0)["trades"] == 2
    assert werte["gesamt"]["trades"] == 4
    assert len(werte["raster"]) == 7 * 24


def test_kaufzeit_statt_verkaufszeit_und_rueckrechnung():
    trades = [trade(zeit="2026-10-06T00:01:00Z", hold_h=2 / 60),
              trade(zeit="2026-10-06T00:01:00Z", opened="2026-10-05T22:30:00Z", hold_h=0),
              trade(zeit="2026-10-06T01:00:00", opened_at="2026-10-06T02:00:00+02:00")]
    werte = r.tageszeit_auswertung(trades)
    assert feld(werte, 0, 23)["trades"] == 1
    assert feld(werte, 0, 22)["trades"] == 1
    assert feld(werte, 1, 0)["trades"] == 1
    assert any("1 Kaufzeiten" in hinweis for hinweis in werte["hinweise"])


@pytest.mark.parametrize("stunde,gruppe", [(0, 0), (7, 0), (8, 1), (13, 1),
                                          (14, 2), (19, 2), (20, 3), (23, 3)])
def test_gruppen_grenzen(stunde, gruppe):
    werte = r.tageszeit_auswertung([trade(zeit=f"2026-10-05T{stunde:02d}:59:59Z")])
    assert [g["trades"] for g in werte["gruppen"]] == [int(i == gruppe) for i in range(4)]


def test_deutsche_zeiten_sommer_winter_und_folgetag():
    assert r.tageszeit_stunden_text(23) == "23:00 UTC (01:00 (+1 Tag) MESZ / 00:00 (+1 Tag) MEZ)"
    assert r.tageszeit_stunden_text(0, 8) == "00:00–08:00 UTC (02:00–10:00 MESZ / 01:00–09:00 MEZ)"
    text = r.tageszeit_stunden_text(20, 24)
    assert "20:00–24:00 UTC" in text and "(+1 Tag)" in text


def test_schwelle_9_10_und_leere_daten():
    neun = r.tageszeit_auswertung([trade()] * 9)
    zehn = r.tageszeit_auswertung([trade()] * 10)
    assert not feld(neun, 0, 8)["ausreichend"]
    assert feld(neun, 0, 8)["status"] == "zu wenig Daten"
    assert feld(zehn, 0, 8)["ausreichend"]
    assert feld(zehn, 0, 8)["pro_trade"] == pytest.approx(0.1)
    leer = r.tageszeit_auswertung([])
    assert leer["gesamt"]["pro_trade"] is None
    assert all(f["status"] == "zu wenig Daten" for f in leer["raster"])
    assert leer["gesamt"]["ohne_beste_summe"] is None


def test_kosten_alle_runden_und_beste_nach_kosten_neu_geordnet(monkeypatch):
    trades = [trade(1, invested_sol=100, runde=7), trade(0.4, runde=1), trade(0.3, runde=2),
              trade(0.2, runde=3), trade(-0.1, runde=4)]
    original = copy.deepcopy(trades)
    calls = []
    kosten_abzug = r.kosten_abzug

    def abzug(konto):
        calls.append(konto)
        return kosten_abzug(konto)

    monkeypatch.setattr(r, "kosten_abzug", abzug)
    roh = r.tageszeit_auswertung(trades)
    netto = r.tageszeit_auswertung(trades, r.kosten_pct("hauptstrategie"))
    assert netto["gesamt"]["summe"] == pytest.approx(1.8 - 2.016)
    assert roh["gesamt"]["ohne_beste_summe"] == pytest.approx(0.1)
    assert netto["gesamt"]["ohne_beste_summe"] == pytest.approx(-1.104)
    assert netto["gesamt"]["ohne_beste_trades"] == 2
    assert netto["gruppen"][1]["ohne_beste_summe"] == pytest.approx(-1.104)
    endspurt = r.tageszeit_auswertung([trade(1, invested_sol=2)], r.kosten_pct("endspurt"))
    assert endspurt["gesamt"]["summe"] == pytest.approx(0.92)
    assert calls
    assert trades == original


def test_defekte_trades_werden_ausgelassen_standard_einsatz_wird_gemeldet():
    trades = [None, {}, trade(pnl=float("nan")), trade(pnl=float("inf")),
              trade(hold_h=-1), trade(hold_h=None), trade(closed_at=float("inf")),
              trade(closed_at="kaputt"), trade(hold_h=1e300),
              trade(opened="2026-10-06T00:00:00Z"), trade(opened="kaputt"),
              trade(invested_sol="kaputt"), trade(invested_sol=-1),
              trade(invested_sol=None), trade(phase=[])]
    werte = r.tageszeit_auswertung(trades, kosten=2, marktphasen=True)
    assert werte["gesamt"]["trades"] == 2
    assert werte["gesamt"]["summe"] == pytest.approx(0.192)
    assert any("Standard" in h for h in werte["hinweise"])
    assert any("ohne bekannte gespeicherte Marktphase" in h for h in werte["hinweise"])
    assert r.tageszeit_auswertung(trades)["gesamt"]["trades"] == 4


def test_ohne_kaufzeit_keine_erfundene_gruppe():
    werte = r.tageszeit_auswertung([{"closed_at": "2026-10-05T12:00:00Z", "pnl_sol": 1}])
    assert werte["gesamt"]["trades"] == 0
    assert any("Haltedauer" in h for h in werte["hinweise"])


def test_marktphasen_nur_aus_trade_keine_aktuelle_phase_uebertragen():
    trades = [trade(1, phase="ruhig"), trade(2, phase="normal"), trade(3, phase="heiss"),
              trade(4, phase=None)]
    werte = r.tageszeit_auswertung(trades, marktphasen=True)
    assert [p["summe"] for p in werte["phasen"]] == [1, 2, 3]
    assert werte["gesamt"]["summe"] == 10
    assert not r.tageszeit_auswertung(trades)["phasen"]
    ohne = r.tageszeit_auswertung([trade(phase=None)], marktphasen=True)
    assert not ohne["phasen"]
    assert any("weggelassen" in h for h in ohne["hinweise"])


def test_daten_laden_fehlende_defekte_konten_und_marktphase(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "KONTEN", [("hauptstrategie", "Hauptstrategie"), ("endspurt", "Endspurt")])
    leer = r.tageszeit_konten(tmp_path)
    assert leer["konten"] == [] and not leer["marktphasen"]
    assert any("weggelassen" in h for h in leer["hinweise"])
    portfolio = tmp_path / "portfolio.json"
    portfolio.write_text(json.dumps({"closed": [trade()]}), encoding="utf-8")
    markt = tmp_path / "marktphase.json"
    markt.write_text(json.dumps({"phase": "heiss", "updated": 1791158400,
                                "history": [[1791158400, 3, 100]]}), encoding="utf-8")
    quelle = r.tageszeit_konten(tmp_path)
    assert quelle["marktphasen"]
    assert quelle["konten"][0]["closed"][0]["phase"] == "normal"
    assert any("Endspurt" in h for h in quelle["hinweise"])
    portfolio.write_text('{"closed": {}}', encoding="utf-8")
    assert r.tageszeit_konten(tmp_path)["konten"][0]["closed"] == []
    markt.write_text('{"phase": []}', encoding="utf-8")
    assert not r.tageszeit_konten(tmp_path)["marktphasen"]
    portfolio.write_text('kaputt', encoding="utf-8")
    assert r.tageszeit_konten(tmp_path)["konten"] == []


def test_cache_laesst_auswahl_ohne_neues_lesen_zu(monkeypatch):
    pytest.importorskip("streamlit")
    import daten
    calls = []
    monkeypatch.setattr(r, "tageszeit_konten", lambda: calls.append(1) or {"konten": []})
    daten.tageszeit.clear()
    assert daten.tageszeit("test") == {"konten": []}
    daten.tageszeit("test")
    assert calls == [1]
    daten.tageszeit.clear()


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
    quelle = {"konten": [{"key": "hauptstrategie", "label": "Hauptstrategie", "closed": [trade()] * 10},
                         {"key": "endspurt", "label": "Endspurt", "closed": [trade(-0.1)] * 9}],
              "marktphasen": True, "hinweise": []}
    monkeypatch.setattr(daten, "tageszeit", lambda head: copy.deepcopy(quelle))
    monkeypatch.setattr(ansicht, "bot_status_eintraege", lambda: [])
    # Die Karte untersagt die Registrierung; die Seite laeuft hier als Test-Einstieg.
    return AppTest.from_file(str(DASHBOARD / "app_pages/tageszeit.py"), default_timeout=15), quelle


def html(app):
    return "\n".join(e.value for e in app.get("html"))


def test_seite_standard_kosten_kontoauswahl_und_graue_felder(seite):
    app, _ = seite
    app.run()
    assert not app.exception
    assert app.selectbox[0].value == "hauptstrategie"
    assert "+0,100 SOL" in html(app)
    assert any("Beobachtung, kein Urteil" in e.value for e in app.caption)
    assert any("zu wenig Daten" in e.value for e in app.caption)
    app.button_group[0].set_value("mit Kosten").run()
    assert not app.exception
    assert "+0,096 SOL" in html(app)
    app.selectbox[0].set_value("endspurt").run()
    assert not app.exception
    assert "zu wenig Daten" in html(app)
    assert any("4 %" in e.value for e in app.caption)
    # Vega-Lite validiert beim Rendern; der Test prueft auch Farbe und Tooltip-Sperre.
    charts = app.get("vega_lite_chart")
    assert charts
    spec = json.loads(charts[0].proto.spec)
    assert spec["layer"][0]["encoding"]["color"]["value"] == __import__("stil").LINIE


def test_seite_leere_trades_konten_und_ladefehler(seite, monkeypatch):
    import daten
    app, quelle = seite
    quelle["konten"][0]["closed"] = []
    app.run()
    assert not app.exception
    assert "Noch keine auswertbaren Trades" in html(app)
    quelle["konten"] = []
    app.run()
    assert not app.exception
    assert "Noch keine Konten" in html(app)

    def kaputt(head):
        raise ValueError("Lokale Daten sind nicht lesbar")

    monkeypatch.setattr(daten, "tageszeit", kaputt)
    app.run()
    assert not app.exception
    assert "Trades konnten nicht geladen" in html(app)


@pytest.mark.parametrize("modus", ["roh", "mit Kosten"])
def test_gruppenkarten_im_vierer_und_dreier_raster_werte_zeiten_details_erhalten(seite, modus):
    import ansicht as a
    import stil
    app, quelle = seite
    app.run()
    if modus == "mit Kosten":
        app.button_group[0].set_value(modus).run()
    assert not app.exception
    werte = r.tageszeit_auswertung(quelle["konten"][0]["closed"],
                                  r.kosten_pct("hauptstrategie") if modus == "mit Kosten" else 0,
                                  marktphasen=quelle["marktphasen"])
    raster = [e.value for e in app.get("html") if " handy-einspaltig" in e.value]
    assert len(raster) == 2
    for text, gruppen, spalten in zip(raster, (werte["gruppen"], werte["phasen"]), (4, 3)):
        assert f"spalten-{spalten}" in text
        assert text.count('class="pb-karte') == len(gruppen)
        assert text.count('class="pb-zahl klein einzeilig"') == len(gruppen)
        for gruppe in gruppen:
            assert a.e(gruppe["name"]) in text
            assert (a.e(a.plusminus(gruppe["pro_trade"])) if gruppe["ausreichend"] else "–") in text
            assert str(gruppe["trades"]) + " Trades" in text
    for gruppe in werte["gruppen"]:
        assert a.e(gruppe["zeit_text"]) in raster[0]
    labels = [e.label for e in app.expander]
    assert all(f"{g['name']} · Ergebnis und Ausreißer" in labels for g in werte["gruppen"] + werte["phasen"])
    assert "Ohne die 3 besten:" in html(app)
    css = stil._css()
    assert ".pb-raster.nx-konten, .pb-raster.handy-einspaltig { grid-template-columns: 1fr; }" in css
    assert "@media (min-width: 641px) and (max-width: 1000px)" in css
    assert ".pb-raster.handy-einspaltig.spalten-3, .pb-raster.handy-einspaltig.spalten-4" in css


def test_tageszeit_zahl_und_einheit_bleiben_zusammen(seite):
    import re
    import stil
    app, quelle = seite
    quelle["konten"][0]["closed"] = [trade(-0.004)] * 10
    app.run()
    assert not app.exception
    assert '<div class="pb-zahl klein einzeilig">▼ −0,004 SOL</div>' in html(app)
    regel = re.search(r'\.pb-zahl\.klein\.einzeilig\s*\{([^}]+)\}', stil._css()).group(1)
    assert "white-space: nowrap" in regel and "overflow-wrap: normal" in regel
    assert "font-size:" in regel
