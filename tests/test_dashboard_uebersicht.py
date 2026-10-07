"""Uebersicht: Konten vor Nachrichten, Werte und Roh/Kosten-Beschriftungen bleiben erhalten."""
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


@pytest.mark.parametrize("experiment_anzahl", [0, 11])
def test_konten_zuerst_und_roh_kosten_unveraendert(monkeypatch, experiment_anzahl):
    jetzt = time.time()
    konten = []
    for key, label, wert in (("hauptstrategie", "Hauptstrategie", 9.88),
                             (r.KONTROLLE, "Kontrollgruppe", 10.01)):
        k = r.konto_strategie(key, label, {"bankroll_sol": wert, "runde": 1, "closed": [
            {"pnl_sol": wert - 10, "invested_sol": 1.0, "runde": 1,
             "opened": jetzt - 100, "closed_at": jetzt - 50}]}, {})
        k["verlauf"] = []
        konten.append(k)
    for i in range(experiment_anzahl):
        k = r.konto_strategie(f"experiment_{i}", f"Experiment {i}", {"bankroll_sol": 10, "closed": []}, {})
        k["verlauf"] = []
        konten.append(k)
    for k in konten:
        k["vergleich"] = r.vergleich_mit_kontrolle(k, konten[1])
    trader = [{"name": "Alpha", "ergebnis_seit_start": 5.0, "ergebnis_runde": 1.0, "aktiv": True},
              {"name": "Beta", "ergebnis_seit_start": -2.41, "ergebnis_runde": -1.0, "aktiv": False}]
    vorher = copy.deepcopy((konten, trader))
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    monkeypatch.setattr(daten, "strategie_konten", lambda head: konten)
    monkeypatch.setattr(daten, "copy_konten", lambda head: (trader, jetzt, None))
    monkeypatch.setattr(daten, "betrieb", lambda head: ({"Hauptbot": [jetzt], "Copy-Bot": [jetzt]}, {}, 0))
    monkeypatch.setattr(daten, "scout", lambda head: ([], jetzt))
    monkeypatch.setattr(daten, "neu_seit", lambda *args: {
        "trades": [], "copy": {}, "wallets": {"aufgenommen": [], "entfernt": [], "geprueft_neu": 0},
        "beendete_experimente": [], "auffaellig": [], "commits": []})
    monkeypatch.setattr(daten, "news", lambda head: {"liste": [], "fehler": [], "feeds": 1})
    monkeypatch.setattr(a, "bot_status_eintraege", lambda: [])
    # Der Seitentest laeuft ohne die Navigation aus app.py.
    monkeypatch.setattr(a.st, "page_link", lambda *args, **kwargs: None)
    app = AppTest.from_file(str(DASHBOARD / "app_pages/uebersicht.py"), default_timeout=15).run()
    assert not app.exception
    assert [e.value for e in app.subheader] == ["Hauptstrategie und Experimente", "Was ist neu?", "Für dich wichtig"]
    html = [e.value for e in app.get("html")]
    assert "Hauptstrategie" in html[1] and "Kontrollgruppe" in html[1]
    assert all(w in html[1] for w in (">roh</", ">mit Kosten</", "9,88 SOL", "9,86 SOL", "10,01 SOL", "9,99 SOL"))
    assert "Copy seit Start" in html[2] and ">+2,59 SOL</div>" in html[2]
    assert "Copy ohne besten Trader" in html[2] and ">−2,41 SOL</div>" in html[2]
    assert (konten, trader) == vorher
    experimente = next(h for h in html if "nx-experimente" in h)
    assert "spalten-2" in experimente and "nx-konten" in experimente
    assert " ausgleich" not in experimente and " vierer" not in experimente
    assert experimente.count('class="nx-duo"') == len(konten)
    assert experimente.count('class="nx-urteil"') == len(konten)
    for k in konten:
        assert a.urteil_chip(k["vergleich"]) in experimente
        assert a.pm_html(k["ergebnis"]) in experimente
        assert a.pm_html(r.ergebnis_mit_kosten(k)) in experimente
        assert f"{k['trades']}/200 Trades" in experimente
    assert len([h for h in html if "nx-kurzprotokoll" in h]) == 2
