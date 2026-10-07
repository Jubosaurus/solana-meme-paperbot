"""Betrieb: drei sichtbare Bot-Karten, auch wenn die Git-Historie fehlt."""
import copy
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


@pytest.mark.parametrize("historie", ["fehlt", "teilweise", "leer", "aktuell", "luecke"])
def test_statuskarten_und_luecken_behalten_datenbasis(monkeypatch, historie):
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    jetzt = time.time()
    commits = {"Hauptbot": [jetzt - 60], "Copy-Bot": [jetzt - 120]}
    if historie == "fehlt":
        commits = {}
    elif historie == "teilweise":
        commits.pop("Copy-Bot")
    elif historie == "leer":
        commits = {bot: [] for bot in r.BOT_COMMITS}
    elif historie == "luecke":
        commits["Hauptbot"] = [jetzt - 3600, jetzt - 60]
    vorher = copy.deepcopy(commits)
    messung = {name: {"median": None, "anzahl": 0, "p90": None}
               for name in ("Hauptbot und Experimente", "Copy-Bot")}
    messung["notloesung"] = 0
    monkeypatch.setattr(daten, "stand", lambda: "betrieb-test")
    monkeypatch.setattr(a, "bot_status_eintraege", lambda: [])
    monkeypatch.setattr(daten, "betrieb", lambda head: (commits, messung, 0))
    # Aktuelle Dateizeiten ersetzen bei fehlender Historie keine Bot-Zeitpunkte.
    monkeypatch.setattr(daten, "strategie_konten", lambda head: [{"key": "hauptstrategie", "gespeichert": jetzt}])
    monkeypatch.setattr(daten, "copy_konten", lambda head: ([], jetzt, jetzt))
    monkeypatch.setattr(daten, "scout", lambda head: ([], jetzt))
    monkeypatch.setattr(daten, "messung_detail", lambda head: [])
    app = AppTest.from_file(str(DASHBOARD / "app_pages/betrieb.py"), default_timeout=15).run()
    assert not app.exception
    html = [e.value for e in app.get("html")]
    karten = next(t for t in html if '<div class="pb-raster' in t)
    assert karten.count('<div class="pb-karte') == 3
    assert all(f'<span>{bot}</span>' in karten for bot in (*r.BOT_COMMITS, "Scout"))
    fehlen = sum(bot not in commits for bot in r.BOT_COMMITS)
    assert karten.count("Datenstand fehlt") == fehlen
    assert karten.count("nicht prüfbar") == fehlen
    for bot, zeiten in commits.items():
        letzte = zeiten[-1] if zeiten else None
        assert a.pille(r.bot_status(letzte, jetzt), "Datenstand") in karten
        assert a.e(r.zeit_text(letzte)) in karten
    alles = "\n".join(html)
    if historie in {"fehlt", "teilweise", "leer"}:
        assert "Lücken nicht prüfbar" in alles
        assert "Keine Lücken über 20 min" not in alles
    elif historie == "aktuell":
        assert "Keine Lücken über 20 min" in alles
    else:
        assert a.e(r.zeit_text(commits["Hauptbot"][0])) in alles
        assert a.e(r.dauer_text(commits["Hauptbot"][1] - commits["Hauptbot"][0])) in alles
    assert commits == vorher


def test_fehler_beim_lesen_der_git_historie_liefert_leeres_ergebnis(monkeypatch):
    def gesperrt(*args, **kwargs):
        raise OSError("Lokaler Git-Prozess nicht verfuegbar")

    monkeypatch.setattr(r.subprocess, "run", gesperrt)
    assert r.commit_zeiten() == {}
