"""Daten laden fuer das Dashboard (mit Zwischenspeicher). Die Rechnung selbst steht in rechnung.py."""
import time

import streamlit as st

import rechnung


@st.cache_data(ttl=290, show_spinner=False)
def neueste_daten():
    """git pull hoechstens alle ~5 min (gemeinsam fuer alle offenen Browser-Tabs)."""
    ok, meldung, head = rechnung.git_pull()
    return {"ok": ok, "meldung": meldung, "head": head, "zeit": time.time()}


def stand():
    """Aktueller Datenstand (HEAD) - dient als Schluessel: neue Daten = neu rechnen."""
    return st.session_state.get("head", "")


@st.cache_data(ttl=600, max_entries=4, show_spinner="Konten werden berechnet …")
def strategie_konten(head):
    konten = rechnung.alle_strategie_konten()
    kontrolle = next(k for k in konten if k["key"] == rechnung.KONTROLLE)
    for k in konten:
        k["vergleich"] = rechnung.vergleich_mit_kontrolle(k, kontrolle)
        k["verlauf"] = rechnung.kontoverlauf(k)
    return konten


@st.cache_data(ttl=600, max_entries=4, show_spinner="Copy-Konten werden berechnet …")
def copy_konten(head):
    konten, gespeichert, rows = rechnung.copy_konten()
    letzte_zeile = rows[-1]["zeit"] if rows else None
    return konten, gespeichert, letzte_zeile


@st.cache_data(ttl=600, max_entries=4, show_spinner=False)
def copy_rohdaten(head):
    return rechnung.lade_json(rechnung.pfad(rechnung.cb.ACCOUNTS_FILE), {}) or {}


@st.cache_data(ttl=600, max_entries=4, show_spinner=False)
def scout(head):
    return rechnung.scout_rangliste(), rechnung.scout_letzter_lauf()


@st.cache_data(ttl=600, max_entries=4, show_spinner=False)
def betrieb(head):
    return rechnung.commit_zeiten(), rechnung.messung(), len(rechnung.korrekturen())


@st.cache_data(ttl=600, max_entries=4, show_spinner="Flugschreiber wird gelesen …")
def flugschreiber(head):
    rows = rechnung.flug_zeilen()
    return rows, rechnung.flug_coins(rows)


@st.cache_data(ttl=600, max_entries=4, show_spinner=False)
def messung_detail(head):
    return rechnung.messung_detail()


@st.cache_data(ttl=600, max_entries=6, show_spinner=False)
def neu_seit(head, stunden):
    """Was ist neu seit N Stunden? (gleicher Stand head = gleiche Antwort)"""
    jetzt = time.time()
    konten = strategie_konten(head)
    copy, _, _ = copy_konten(head)
    korr = rechnung.korrekturen()
    zeilen = rechnung.journal_bereinigen(rechnung.lade_csv(rechnung.pfad(rechnung.cb.JOURNAL_FILE)), korr)
    return rechnung.neu_seit(jetzt - stunden * 3600, konten, zeilen, copy, jetzt)
