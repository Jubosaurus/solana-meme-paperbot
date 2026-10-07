"""Verpasste Chancen: echte Zuordnung, Datenluecken, Stichproben und Anzeige."""
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"
sys.path.insert(0, str(DASHBOARD))
import rechnung as r  # noqa: E402

START = datetime(2026, 10, 1, tzinfo=timezone.utc)
HEADER = ["zeit", "symbol", "mint", "grund", "preis_usd"]
KURS_HEADER = ["zeit", "mint", "symbol", "phase", "preis_usd"]


def zeit(sekunden=0):
    return (START + timedelta(seconds=sekunden)).isoformat()


def csv_schreiben(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def daten_schreiben(repo, faelle, kurse, alle=None):
    csv_schreiben(repo / "knapp_abgelehnt.csv", HEADER, faelle)
    csv_schreiben(repo / "abgelehnt.csv", HEADER, faelle if alle is None else alle)
    csv_schreiben(repo / "verlauf/2026-10-01.csv", KURS_HEADER, kurse)


def fall(mint="A", preis=100, grund="FOMO_SPRUNG", sek=0, symbol="X"):
    return [zeit(sek), symbol, mint, grund, preis]


def kurs(mint="A", preis=150, sek=3600, phase="abgelehnt_FOMO_SPRUNG", symbol="X"):
    return [zeit(sek), mint, symbol, phase, preis]


def gruppe(result, quelle="knapp_abgelehnt", grund="FOMO_SPRUNG"):
    return next(g for g in result["quellen"][quelle]["gruende"] if g["grund"] == grund)


def test_erste_ablehnung_mint_grund_utc_und_quellen_getrennt(tmp_path):
    faelle = [fall(sek=120, preis=200), fall(), fall(mint="B", grund="STORY_ZU_ALT")]
    faelle[1][0] = "2026-10-01T02:00:00+02:00"
    daten_schreiben(tmp_path, faelle, [kurs(), kurs(mint="B", preis=10),
                                    kurs(phase="exp_offen", preis=900)], alle=[fall(preis=50)])
    result = r.abgelehnt_rueckblick(tmp_path)
    nah = result["quellen"]["knapp_abgelehnt"]
    assert nah["pruefungen"] == 3 and nah["coins"] == 2
    assert nah["je_tag"] == [{"tag": "2026-10-01", "pruefungen": 3}]
    g = gruppe(result)
    assert g["pruefungen"] == 2 and g["coins"] == 1
    assert g["horizonte"][1]["median_pct"] == pytest.approx(50)
    assert gruppe(result, "abgelehnt")["horizonte"][1]["median_pct"] == pytest.approx(200)
    assert gruppe(result, grund="STORY_ZU_ALT")["horizonte"][1]["n"] == 0
    assert len(nah["faelle"]) == 2


def test_naechster_kurs_toleranz_gleichstand_keine_fortschreibung(tmp_path):
    daten_schreiben(tmp_path, [fall(m) for m in "ABCD"], [
        kurs("A", 120, 3540), kurs("A", 190, 3660),
        kurs("B", 140, 3300), kurs("C", 800, 3299),
        kurs("D", 150, 21600 + 300), kurs("D", 300, 21600 + 301),
    ])
    result = r.abgelehnt_rueckblick(tmp_path)
    g = gruppe(result)
    assert g["horizonte"][1]["n"] == 2
    assert g["horizonte"][1]["fehlend"] == 2
    assert g["horizonte"][1]["median_pct"] == pytest.approx(30)
    assert g["horizonte"][6]["n"] == 1
    assert g["horizonte"][6]["median_pct"] == pytest.approx(50)
    a = next(f for f in result["quellen"]["knapp_abgelehnt"]["faelle"] if f["mint"] == "A")
    assert a["horizonte"][1]["abstand_s"] == -60


def test_stichprobe_richtung_bandbreite_ohne_drei_beste(tmp_path):
    preise = [50, 100, 150, 200, 300, 1100]
    daten_schreiben(tmp_path, [fall(str(i)) for i in range(6)],
                    [kurs(str(i), p) for i, p in enumerate(preise)])
    stats = gruppe(r.abgelehnt_rueckblick(tmp_path))["horizonte"][1]
    assert (stats["n"], stats["hoeher"], stats["niedriger"], stats["gleich"]) == (6, 4, 1, 1)
    assert stats["hoeher_pct"] == pytest.approx(400 / 6)
    assert stats["niedriger_pct"] == pytest.approx(100 / 6)
    assert stats["median_pct"] == pytest.approx(75)
    assert (stats["min_pct"], stats["max_pct"]) == pytest.approx((-50, 1000))
    ohne = stats["ohne_beste_3"]
    assert ohne["n"] == 3 and ohne["median_pct"] == 0 and ohne["mittel_pct"] == 0
    assert ohne["min_pct"] == -50 and ohne["max_pct"] == 50


@pytest.mark.parametrize("preis", ["", "kaputt", "nan", "inf", "-inf", 0, -1])
def test_ungueltiger_start_keine_spaetere_ablehnung_als_ersatz(tmp_path, preis):
    daten_schreiben(tmp_path, [fall(preis=preis), fall(preis=100, sek=1)], [kurs()])
    stats = gruppe(r.abgelehnt_rueckblick(tmp_path))["horizonte"][1]
    assert stats["n"] == 0 and stats["median_pct"] is None and stats["fehlend"] == 1
    assert stats["ohne_beste_3"]["n"] == 0


def test_defekter_naechster_kurs_und_widerspruechliche_messpunkte(tmp_path):
    daten_schreiben(tmp_path, [fall(m) for m in "ABC"], [
        kurs("A", "nan"), kurs("A", 200, 3601),
        kurs("B", 150), kurs("B", 151), kurs("B", 150),
        kurs("C", 150), kurs("C", 150),
    ])
    result = r.abgelehnt_rueckblick(tmp_path)
    assert gruppe(result)["horizonte"][1]["n"] == 1
    assert any("widersprüchliche" in h for h in result["hinweise"])


@pytest.mark.parametrize("preise", [[100, 200, 100], [200, 100, 200]])
def test_widerspruechliche_startpreise_bleiben_unmessbar(tmp_path, preise):
    daten_schreiben(tmp_path, [fall(preis=p) for p in preise], [kurs()])
    result = r.abgelehnt_rueckblick(tmp_path)
    assert gruppe(result)["horizonte"][1]["n"] == 0
    assert any("widersprüchliche Startpreise" in h for h in result["hinweise"])


def test_fehlende_leere_defekte_dateien_und_zeit(tmp_path):
    result = r.abgelehnt_rueckblick(tmp_path)
    assert all(q["pruefungen"] == 0 for q in result["quellen"].values())
    daten_schreiben(tmp_path, [["kaputt", "X", "A", "FOMO_SPRUNG", 1],
                             [zeit(), "X", "", "FOMO_SPRUNG", 1]], [])
    result = r.abgelehnt_rueckblick(tmp_path)
    assert result["quellen"]["knapp_abgelehnt"]["unzuordenbar"] == 2
    assert gruppe(result)["coins"] == 1 and gruppe(result)["horizonte"][1]["fehlend"] == 1
    csv_schreiben(tmp_path / "abgelehnt.csv", ["falsche_spalte"], [[1]])
    csv_schreiben(tmp_path / "verlauf/defekt.csv", ["zeit", "mint"], [[zeit(), "A"]])
    result = r.abgelehnt_rueckblick(tmp_path)
    assert any("Spalten fehlen" in h for h in result["hinweise"])


def test_filter_letzte_faelle_und_dateien_bleiben_unveraendert(tmp_path):
    daten_schreiben(tmp_path, [fall(str(i), sek=i) for i in range(60)] + [fall(grund="STORY_ZU_ALT")], [])
    vorher = {p: p.read_bytes() for p in tmp_path.rglob("*.csv")}
    result = r.abgelehnt_rueckblick(tmp_path, "FOMO_SPRUNG", 1)
    nah = result["quellen"]["knapp_abgelehnt"]
    assert nah["pruefungen"] == 60 and len(nah["faelle"]) == 50
    assert nah["faelle"][0]["mint"] == "59"
    assert result["stunden"] == (1,)
    assert {p: p.read_bytes() for p in tmp_path.rglob("*.csv")} == vorher


def test_cache_liest_beide_quellen_nur_einmal(monkeypatch):
    pytest.importorskip("streamlit")
    import daten
    calls = []
    monkeypatch.setattr(r, "abgelehnt_rueckblick", lambda: calls.append(1) or {"test": True})
    daten.verpasste_chancen.clear()
    assert daten.verpasste_chancen("stand") == {"test": True}
    daten.verpasste_chancen("stand")
    assert calls == [1]
    daten.verpasste_chancen.clear()


@pytest.fixture
def seite(tmp_path, monkeypatch):
    import threading
    import time
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import ansicht
    import daten
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    daten_schreiben(tmp_path, [fall(symbol="<script>fremd</script>")], [kurs()])
    result = r.abgelehnt_rueckblick(tmp_path)
    monkeypatch.setattr(daten, "verpasste_chancen", lambda head: result)
    monkeypatch.setattr(ansicht, "bot_status_eintraege", lambda: [])
    return AppTest.from_file(str(DASHBOARD / "app_pages/verpasste_chancen.py"), default_timeout=15), result


def test_seite_quellenwechsel_datenluecken_und_fremde_texte(seite):
    app, _ = seite
    app.run()
    assert not app.exception
    html = "\n".join(e.value for e in app.get("html"))
    assert "n=1" in html and "n=0" in html
    assert "Papierkurs, ohne Kosten, ohne Rug-Risiko" in html
    assert "&lt;script&gt;" in html and "<script>fremd" not in html
    app.selectbox[0].set_value("abgelehnt").run()
    assert not app.exception
    assert any("ausgewählte Teilmenge" in e.value for e in app.get("html"))


def test_seite_leere_daten_und_ladefehler(seite, tmp_path, monkeypatch):
    import daten
    app, _ = seite
    monkeypatch.setattr(daten, "verpasste_chancen", lambda head: r.abgelehnt_rueckblick(tmp_path / "fehlt"))
    app.run()
    assert not app.exception
    assert any("Noch keine Ablehnungen" in e.value for e in app.get("html"))

    def kaputt(head):
        raise ValueError("Defekte lokale Datei")

    monkeypatch.setattr(daten, "verpasste_chancen", kaputt)
    app.run()
    assert not app.exception
    assert any("konnten nicht geladen" in e.value for e in app.get("html"))
