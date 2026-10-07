"""Wissen: lokale Markdown-Dateien, fehlertolerantes Lesen, Suche und Anzeige."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))
import rechnung as r  # noqa: E402


def markdown(repo, name, text):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def wissen_repo(tmp_path):
    markdown(tmp_path, "wissen/index.md", "# Einstieg\n\nSiehe [[Rug]].")
    markdown(tmp_path, "wissen/wiki/muster/Rug.md", "# Rug erkennen\n\nGrößerer Verlust durch Verkäufe.")
    markdown(tmp_path, "wissen/wiki/regeln/Stop.md", "## Stop-Regel\n\nEin Ausstieg schützt Gewinne.")
    markdown(tmp_path, "wissen/wiki/regeln/detail/Tag.md", "# Detail\n\nKleine Regel.")
    markdown(tmp_path, "wissen/notizen/meine.md", "# Mein Gedanke\n\nEigene Beobachtung über Händler.")
    markdown(tmp_path, "wissen/log.md", "# Log\n\nEine frühere Entscheidung.")
    return tmp_path


def test_seiten_titel_unterordner_notizen_und_einstieg(wissen_repo):
    seiten = r.wissen_seiten(wissen_repo)
    assert len(seiten) == 6
    rug = next(s for s in seiten if s["titel"] == "Rug erkennen")
    assert rug["gruppe"] == "muster"
    assert rug["pfad"] == "wissen/wiki/muster/Rug.md"
    assert next(s for s in seiten if s["titel"] == "Detail")["gruppe"] == "regeln/detail"
    notiz = next(s for s in seiten if s["art"] == "notiz")
    assert notiz["eigene_notiz"] and notiz["gruppe"] == "Eigene Notizen"
    einstieg = next(s for s in seiten if s["art"] == "index")
    assert "[[" not in einstieg["markdown"]
    assert "Einstieg" not in r.wissen_gruppen(seiten)
    assert set(r.wissen_gruppen(seiten)) == {
        "muster", "regeln", "regeln/detail", "Eigene Notizen", "Weitere Dokumente"}


def test_fehlende_leere_binaere_und_unlesbare_dateien(tmp_path, monkeypatch):
    assert r.wissen_seiten(tmp_path) == []
    assert r.wissen_berichte(tmp_path) == []
    markdown(tmp_path, "wissen/wiki/leer.md", " \n\t")
    kaputt = markdown(tmp_path, "wissen/wiki/kaputt.md", "")
    kaputt.write_bytes(b"\xff\xfe")
    markdown(tmp_path, "wissen/wiki/binaer.md", "# Kaputt\x00")
    markdown(tmp_path, "wissen/wiki/gut.md", "\ufeff# Lesbar\nInhalt")
    gesperrt = markdown(tmp_path, "wissen/wiki/gesperrt.md", "# Gesperrt")
    original = Path.read_text

    def lesen(path, *args, **kwargs):
        if path == gesperrt:
            raise PermissionError("Nicht lesbar")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", lesen)
    assert [s["titel"] for s in r.wissen_seiten(tmp_path)] == ["Lesbar"]


def test_verweis_nach_ausserhalb_wird_nicht_gelesen(tmp_path, monkeypatch):
    path = markdown(tmp_path, "wissen/wiki/verweis.md", "# Verweis")
    original = Path.resolve

    def aufloesen(p, *args, **kwargs):
        if p == path:
            return tmp_path / "anderer_ordner" / "verweis.md"
        return original(p, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", aufloesen)
    assert r.wissen_seiten(tmp_path) == []


@pytest.mark.parametrize("suche", ["GRÖSSERER", "groesserer", "grosserer", "gro\u0308sserer"])
def test_suche_gross_klein_umlaute_und_umschreibungen(wissen_repo, suche):
    assert [s["titel"] for s in r.wissen_suche(r.wissen_seiten(wissen_repo), suche)] == ["Rug erkennen"]


def test_suche_volltext_mehrere_woerter_notizen_und_leere_eingabe(wissen_repo):
    seiten = r.wissen_seiten(wissen_repo)
    assert len(r.wissen_suche(seiten, "  \n ")) == len(seiten)
    assert r.wissen_suche(seiten, "groesserer VERLUST")[0]["titel"] == "Rug erkennen"
    assert not r.wissen_suche(seiten, "Verlust Gewinne")
    assert r.wissen_suche(seiten, "ueber haendler")[0]["eigene_notiz"]
    assert r.wissen_suche(seiten, "fruehere Entscheidung")[0]["pfad"] == "wissen/log.md"
    assert r.wissen_suche(seiten, "Stop-Regel")[0]["titel"] == "Stop-Regel"
    assert all("ausschnitt" not in s for s in seiten)
    assert r.wissen_suche([], "x") == []


def test_ausschnitt_um_treffer_auch_nach_vielen_umlauten():
    text = "Ä Ö Ü ß ae oe ue " * 100 + "Besonderer Händler verkauft alles. " + "Nachwort " * 80
    ausschnitt = r.wissen_ausschnitt(text, "HAENDLER", laenge=100)
    assert "Händler verkauft" in ausschnitt
    assert ausschnitt.startswith("… ") and ausschnitt.endswith(" …")
    assert len(ausschnitt) <= 104
    assert r.wissen_ausschnitt("Kurz\nund [[Seite|lesbar]].") == "Kurz und lesbar."
    assert r.wissen_ausschnitt("") == ""


def test_obsidian_alias_abschnitt_und_titel_ohne_code():
    text = "[[Seite]] / [[wiki/Seite.md|Mein Titel]] / [[Seite#Abschnitt]] / [[#Abschnitt]] / ![[Bild]]"
    assert r.wissen_links(text) == "Seite / Mein Titel / Seite – Abschnitt / Abschnitt / Bild"
    assert r.wissen_titel("```md\n# Code\n```\n## [[Seite|Echter Titel]] ##") == "Echter Titel"
    assert r.wissen_titel("Ohne Überschrift", "Dateiname") == "Dateiname"


def test_berichte_neueste_zuerst_suche_und_nur_direkter_ordner(tmp_path):
    alt = markdown(tmp_path, "auswertungen/2026-10-01.md", "# Alter Bericht\nVerkäufe")
    neu = markdown(tmp_path, "auswertungen/2026-10-07.md", "# Neuer Bericht\nVerkäufe")
    markdown(tmp_path, "auswertungen/2026-10-07_zusatz.md", "# Zusatz\nVerkäufe")
    markdown(tmp_path, "auswertungen/leer.md", "")
    markdown(tmp_path, "auswertungen/unterordner/2026-10-08.md", "# Nicht direkt")
    # Dateidatum hat Vorrang vor der Aenderungszeit.
    import os
    os.utime(alt, (2_000_000_000, 2_000_000_000))
    os.utime(neu, (1_000_000_000, 1_000_000_000))
    berichte = r.wissen_berichte(tmp_path)
    assert [s["titel"] for s in berichte] == ["Zusatz", "Neuer Bericht", "Alter Bericht"]
    assert [s["titel"] for s in r.wissen_suche(berichte, "VERKAEUFE")] == [s["titel"] for s in berichte]
    assert all(s["art"] == "bericht" for s in berichte)


def test_bericht_ohne_datum_nutzt_dateiaenderung(tmp_path):
    import os
    alt = markdown(tmp_path, "auswertungen/alt.md", "# Alt")
    neu = markdown(tmp_path, "auswertungen/neu.md", "# Neu")
    os.utime(alt, (100, 100))
    os.utime(neu, (200, 200))
    assert [s["titel"] for s in r.wissen_berichte(tmp_path)] == ["Neu", "Alt"]


@pytest.fixture
def streamlit_module(monkeypatch):
    import threading
    import time
    # conftest setzt sleep ausser Kraft; AppTest muss seinen Thread laufen lassen.
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    return pytest.importorskip("streamlit")


def test_daten_cache_laesst_suche_ausserhalb_des_caches(wissen_repo, monkeypatch, streamlit_module):
    import daten
    monkeypatch.setattr(r, "REPO", wissen_repo)
    daten.wissen.clear()
    daten.berichte.clear()
    try:
        assert len(daten.wissen("stand-a")) == 6
        markdown(wissen_repo, "wissen/wiki/neu.md", "# Neu")
        assert len(daten.wissen("stand-a")) == 6
        assert len(daten.wissen("stand-b")) == 7
        assert daten.berichte("stand-a") == []
    finally:
        daten.wissen.clear()
        daten.berichte.clear()


def seiten_test():
    # Eigener Test-Einstieg, die produktive Navigation bleibt unveraendert.
    import streamlit as st
    from pathlib import Path
    import rechnung
    st.navigation([st.Page(str(rechnung.REPO / "dashboard/app_pages/wissen.py"), title="Wissen")]).run()


def test_seite_reiter_suche_notiz_und_berichte(wissen_repo, monkeypatch, streamlit_module):
    from streamlit.testing.v1 import AppTest
    import daten
    monkeypatch.setattr(daten, "wissen", lambda head: r.wissen_seiten(wissen_repo))
    markdown(wissen_repo, "auswertungen/2026-10-07.md", "# Bericht\nEine große Erkenntnis.")
    monkeypatch.setattr(daten, "berichte", lambda head: r.wissen_berichte(wissen_repo))
    at = AppTest.from_function(seiten_test).run(timeout=15)
    assert not at.exception
    assert [tab.label for tab in at.tabs] == ["Wiki", "Berichte"]
    assert any(e.label == "Einstieg: Einstieg" for e in at.expander)
    at.text_input(key="wissen_suche").set_value("HAENDLER").run()
    assert not at.exception
    assert any("eigene Notiz" in c.value for c in at.caption)
    assert any(e.label == "Ganze Seite: Mein Gedanke" for e in at.expander)
    at.text_input(key="berichte_suche").set_value("GROSSE").run()
    assert not at.exception
    assert any(e.label == "Bericht" for e in at.expander)
    at.text_input(key="wissen_suche").set_value("unauffindbar").run()
    assert not at.exception
    assert not any(e.label.startswith("Ganze Seite:") for e in at.expander)


@pytest.mark.parametrize("ausfall", [False, True])
def test_seite_fehlende_daten_und_ladefehler(monkeypatch, streamlit_module, ausfall):
    from streamlit.testing.v1 import AppTest
    import daten

    def laden(head):
        if ausfall:
            raise OSError("Datei nicht lesbar")
        return []

    monkeypatch.setattr(daten, "wissen", laden)
    monkeypatch.setattr(daten, "berichte", laden)
    at = AppTest.from_function(seiten_test).run(timeout=15)
    assert not at.exception
    assert len(at.text_input) == 2
