"""Flugschreiber: buendige Diagramme bei verschiedenen Zahlenbreiten und Datenluecken."""
import copy
import json
import sys
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"
sys.path.insert(0, str(DASHBOARD))
import ansicht as a  # noqa: E402
import daten  # noqa: E402
import rechnung as r  # noqa: E402


@pytest.mark.parametrize("mit_verkauf", [False, True])
@pytest.mark.parametrize("fehlende_felder", [False, True])
def test_zeichenflaechen_gleicher_rand_und_zeitbereich(monkeypatch, mit_verkauf, fehlende_felder):
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    monkeypatch.setattr(daten, "stand", lambda: "flug-test")
    monkeypatch.setattr(a, "bot_status_eintraege", lambda: [])
    werte = {"vielfaches": 0.012, "dev_pct": 4.2, "top10_pct": 35.6, "holder": 123456,
             "liquiditaet": 12345678, "block0_gehalten_pct": 100, "netto_kaeufer_5m": -1234}
    if fehlende_felder:
        werte.pop("holder")
        werte.pop("block0_gehalten_pct")
    rows = [{"konto": "Hauptstrategie", "mint": "test-coin", "zeit": f"2026-10-07T10:0{i}:00Z",
             "minuten_seit_kauf": i, **{feld: wert * (i + 1) for feld, wert in werte.items()}}
            for i in range(2)]
    coin = {"konto": "Hauptstrategie", "mint": "test-coin", "symbol": "TEST",
            "von": rows[0]["zeit"], "punkte": 2}
    sales = [{"minuten": 3, "grund": "NOTBREMSE (Test)", "pnl_pct": -40}] if mit_verkauf else []
    vorher = copy.deepcopy((rows, coin, sales))
    monkeypatch.setattr(daten, "flugschreiber", lambda head: (rows, [coin]))
    monkeypatch.setattr(r, "flug_verkaeufe", lambda konto, mint: sales)
    app = AppTest.from_file(str(DASHBOARD / "app_pages/flugschreiber.py"), default_timeout=15).run()
    assert not app.exception
    charts = app.get("vega_lite_chart")
    assert len(charts) == len(werte)
    for chart, feld in zip(charts, werte):
        spec = json.loads(chart.proto.spec)
        enc = spec["layer"][0]["encoding"]
        achse = enc["y"]["axis"]
        assert achse["minExtent"] == achse["maxExtent"] == 72
        assert achse["titlePadding"] == 10
        assert enc["y"]["field"] == feld
        assert enc["y"]["scale"]["zero"] is False
        assert enc["x"]["scale"]["domain"] == [0, 3 if mit_verkauf else 1]
        assert spec["height"] == 110
        if mit_verkauf:
            assert any(layer.get("encoding", {}).get("x", {}).get("field") == "minuten"
                       for layer in spec["layer"])
    assert (rows, coin, sales) == vorher
