"""Schmale Tabellen behalten alle Kennzahlen, Formatierungen und Detailspalten."""
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


@pytest.fixture
def seite(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    monkeypatch.setattr(daten, "stand", lambda: "tabellen-test")
    monkeypatch.setattr(a, "bot_status_eintraege", lambda: [])

    def laden(name):
        app = AppTest.from_file(str(DASHBOARD / "app_pages" / name), default_timeout=15).run()
        assert not app.exception
        return app, [e.value for e in app.get("html") if '<div class="nx-tabelle"' in e.value]

    return laden


def konto(key, label, pnl):
    k = r.konto_strategie(key, label, {"bankroll_sol": 10 + pnl, "runde": 1, "closed": [
        {"pnl_sol": pnl / 4, "invested_sol": 0.2, "closed_at": time.time() - 50} for _ in range(4)]}, {})
    k["verlauf"] = []
    return k


def test_testurteil_alle_roh_kosten_werte_und_summen_sichtbar(monkeypatch, seite):
    konten = [konto("hauptstrategie", "Hauptstrategie", -0.01), konto(r.KONTROLLE, "Kontrollgruppe", -0.03)]
    for k in konten:
        k["vergleich"] = r.vergleich_mit_kontrolle(k, konten[1])
    vorher = copy.deepcopy(konten)
    monkeypatch.setattr(daten, "strategie_konten", lambda head: konten)
    app, tabellen = seite("strategie.py")
    kopf = next(e.value for e in app.get("html") if 'class="pb-raster' in e.value)
    assert "spalten-2" in kopf and "nx-konten" in kopf
    assert " vierer" not in kopf and kopf.count('class="pb-karte') == 4
    assert kopf.index("Hauptstrategie") < kopf.index("SOL je Trade") < kopf.index("Fortschritt bis zum Urteil") < kopf.index("Gewinner")
    assert [t.count("<th ") for t in tabellen] == [4, 5]
    assert "Summe mit Kosten" in tabellen[1] and "je Trade mit Kosten" in tabellen[0]
    for werte in (konten[0]["vergleich"]["eigen"], konten[0]["vergleich"]["kontrolle"]):
        for feld in ("pro_trade", "pro_trade_kosten"):
            assert a.pm_html(werte[feld], 4, "") in tabellen[0]
        for feld in ("ohne_beste_pro_trade", "ohne_beste_pro_trade_kosten"):
            assert a.pm_html(werte[feld], 4, "") in tabellen[1]
        for feld in ("summe", "summe_kosten"):
            assert a.pm_html(werte[feld], 3, " SOL") in tabellen[1]
    assert konten == vorher


def test_scout_90_zeilen_begrenzt_und_adressen_im_detail(monkeypatch, seite):
    rangliste = [{"wallet": f"Wallet{i:04d}Ende", "ergebnis": "bewertet", "quelle": "Testquelle",
                  "punkte": "12.5", "coins_abgeschlossen": "30", "trades_pro_tag": "6",
                  "trefferquote": "0.5", "rendite_ohne_besten_pct": "-1.2", "reibung_pp": "2.1",
                  "haltedauer_median_min": "5", "schnelle_verkaeufe_anteil": "0.25",
                  "kauf_median_sol": "0.3", "bot_gebuehr_anteil": "0.1", "zeit": time.time()}
                 for i in range(90)]
    vorher = copy.deepcopy(rangliste)
    monkeypatch.setattr(daten, "scout", lambda head: (rangliste, time.time()))
    monkeypatch.setattr(r, "aktive_wallets", lambda: [])
    app, tabellen = seite("scout.py")
    haupt = tabellen[0]
    assert haupt.count("<th ") == 7 and haupt.count("<tr>") == 91
    assert "90 Zeilen – in der Tabelle scrollen" in haupt and "max-height:none" not in haupt
    assert "Weitere Kennzahlen und Hinweise" in [e.label for e in app.expander]
    assert all(z["wallet"] in "".join(tabellen) for z in rangliste)
    assert "Verkäufe &lt; 60 s" in "".join(tabellen) and "25 %" in "".join(tabellen)
    assert all(t.count("<th ") <= 7 for t in tabellen)
    adresse = rangliste[0]["wallet"][:4] + "…" + rangliste[0]["wallet"][-4:]
    wallet_tabellen = [t for t in tabellen if '>Wallet</th>' in t]
    assert len(wallet_tabellen) == 3
    assert all(f'<td class="text einzeilig">{adresse}</td>' in t for t in wallet_tabellen)
    assert rangliste == vorher


def test_copy_haupttabelle_schmal_und_weitere_werte_erreichbar(monkeypatch, seite):
    acct = {"bankroll_sol": 10.1, "runde": 2, "positionen": {},
            "geschlossen": [{"mint": "a", "pnl_sol": -1.25, "pnl_pct": -3.2, "trader_pnl_pct": -2.1}]}
    trader = r.copy_konto("Trader mit langem Namen", acct, True, [], set())
    vorher = copy.deepcopy(trader)
    monkeypatch.setattr(daten, "copy_konten", lambda head: ([trader], time.time(), None))
    monkeypatch.setattr(daten, "copy_rohdaten", lambda head: {})
    app, tabellen = seite("copy_trading.py")
    assert tabellen[0].count("<th ") == 7
    assert "laufende Runde" in tabellen[0] and "einzeilig" not in tabellen[0]
    assert a.pm_html(-1.25, 2, " SOL") in tabellen[0]
    assert a.pm_html(0.1, 2, " SOL") in tabellen[0]
    text = "".join(tabellen)
    assert all(a.e(s) in text for s in ("vorsichtig", "wir %", "Trader %", "Verzögerung s", "Preisabstand %",
                                      "Schatten", "Schatten SOL", "Trader raus ≤ 60 s", "raus vor uns",
                                      "letzter Trade", "Hinweise"))
    assert "Weitere Kennzahlen und Hinweise" in [e.label for e in app.expander]
    assert all(t.count("<th ") <= 7 for t in tabellen)
    assert trader == vorher


def test_betrieb_letzte_kostenspalte_sichtbar_quote_abstand_im_detail(monkeypatch, seite):
    haupt = konto("hauptstrategie", "Hauptstrategie", 0)
    messung = {name: {"median": 0, "anzahl": 1, "p90": 5} for name in ("Hauptbot und Experimente", "Copy-Bot")}
    messung.update(notloesung=0)
    detail = [{"quelle": "Copy-Bot", "aktion": "VERKAUF", "anzahl": 17, "median": 0.25,
               "schlechteste_10": 6.2, "schwelle_10": 5.1, "schlechter_5": 0.2, "median_s": 2.5, "max_s": 7.3}]
    vorher = copy.deepcopy(detail)
    monkeypatch.setattr(daten, "betrieb", lambda head: ({}, messung, 0))
    monkeypatch.setattr(daten, "strategie_konten", lambda head: [haupt])
    monkeypatch.setattr(daten, "copy_konten", lambda head: ([], None, None))
    monkeypatch.setattr(daten, "scout", lambda head: ([], None))
    monkeypatch.setattr(daten, "messung_detail", lambda head: detail)
    _, tabellen = seite("betrieb.py")
    kosten = next(t for t in tabellen if "schlechteste 10 % im Mittel" in t)
    assert kosten.count("<th ") == 7
    assert "über 5 % schlechter" in kosten and "20 %" in kosten
    abstand = next(t for t in tabellen if "Abstand der 2. Quote, Median" in t)
    assert abstand.count("<th ") == 4 and "2,5 s" in abstand and "7,3 s" in abstand
    assert detail == vorher


def test_pruefliste_schmal_zeit_einzeilig_alle_details_ohne_schreiben(monkeypatch, seite):
    import wallets
    zeilen = [{"name": "Wallet mit Namen", "status": "geprueft", "ergebnis": "bewertet", "grund": "",
               "punkte": 12.5, "haltedauer_min": 4.5, "schnell_anteil": 0.25,
               "rendite_ohne_besten": -1.2, "coins": 30, "copy": "Warteliste", "zeit": 1791066150,
               "wallet": "H2Ag" + "X" * 36 + "ByLV"},
              {"name": "Wartend", "status": "wartet", "ergebnis": "", "grund": "",
               "punkte": None, "haltedauer_min": None, "schnell_anteil": None,
               "rendite_ohne_besten": None, "coins": None, "copy": "", "zeit": None, "wallet": "Adresse2"},
              {"name": "Abgelehnt", "status": "geprueft", "ergebnis": "Kleinstkaeufe", "grund": "zu kleine Kaeufe",
               "punkte": None, "haltedauer_min": None, "schnell_anteil": None,
               "rendite_ohne_besten": None, "coins": None, "copy": "", "zeit": 1791066150, "wallet": "Adresse3"}]
    vorher = copy.deepcopy(zeilen)
    monkeypatch.setattr(wallets, "ist_lokal", lambda *args: False)
    monkeypatch.setattr(wallets, "pruefliste_status", lambda: zeilen)

    def verboten(*args, **kwargs):
        pytest.fail("Die Darstellungspruefung darf keine Schreib- oder Git-Funktion aufrufen")

    for name in ("eingabe_pruefen", "zur_pruefung_schicken", "scout_anstossen"):
        monkeypatch.setattr(wallets, name, verboten)
    app, tabellen = seite("wallets_pruefen.py")
    haupt, kennzahlen, adressen = tabellen
    assert haupt.count("<th ") == 7 and haupt.count("<tr>") == len(zeilen) + 1
    assert "pruefliste" in haupt
    assert f'<td class="text einzeilig">{r.zeit_text(zeilen[0]["zeit"])}</td>' in haupt
    assert "wartet auf den nächsten Scout-Lauf" in haupt and "abgelehnt: zu kleine Kaeufe" in haupt
    assert "Haltedauer min" not in haupt and "Adresse" not in haupt
    assert all(z["wallet"] in adressen for z in zeilen)
    assert "4,5" in kennzahlen and "25%" in kennzahlen and "−1,2" in kennzahlen
    assert "Weitere Kennzahlen und Hinweise" in [e.label for e in app.expander]
    assert zeilen == vorher


def test_lernen_konto_lesbar_zahlen_zeit_einzeilig_werte_unveraendert(monkeypatch, seite):
    import re
    konten = [konto("hauptstrategie", "Hauptstrategie", -0.01),
              konto("endspurt", "Endspurt viele Trades", -0.03)]
    vorher = copy.deepcopy(konten)
    monkeypatch.setattr(daten, "strategie_konten", lambda head: konten)
    monkeypatch.setattr(r, "lupe_trades", lambda konten: [])
    monkeypatch.setattr(daten, "filter_trichter", lambda head, tage: {"pruefungen": 0})
    _, tabellen = seite("lernen.py")
    kalender = tabellen[0]
    assert "urteilskalender" in kalender and kalender.count("<th ") == 7
    assert kalender.count("<tr>") == 3
    assert '<td class="text">Endspurt viele Trades</td>' in kalender
    assert '<td class="text einzeilig">4 / 200</td>' in kalender
    assert '<td class="num">1,3</td>' in kalender and '<td class="num">2 %</td>' in kalender
    assert "Tempo je Tag" in kalender and "voraussichtlich" in kalender
    assert r.zeit_text(r.urteils_kalender(konten, time.time())[0]["eta"]) in kalender
    css = a.stil._css()
    konto_regel = re.search(r'\.nx-tabellenrahmen\.urteilskalender \.nx-tabelle th:first-child\s*\{([^}]+)\}', css).group(1)
    assert "min-width: 12ch" in konto_regel
    assert "max-width: 18ch" in konto_regel
    assert ".nx-tabellenrahmen.urteilskalender th.num { white-space: nowrap; }" in css
    assert konten == vorher
