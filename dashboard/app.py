"""Dashboard Solana-Paperbot - nur zum Anschauen.

Liest die Daten im Repository, holt alle 5 min neue Daten (git pull) und rechnet mit rechnung.py.
Schreibt nie Daten, startet keine Bots, braucht keine Schluessel. EINZIGE Ausnahme: die Seite "Wallets pruefen"
(wallets.py) haengt Adressen an scout/pruefen.txt an und stoesst den Scout an. Start: dashboard/start.bat
"""
import time

import streamlit as st

import daten
import rechnung
import stil

st.set_page_config(page_title="Paperbot", page_icon=":material/monitoring:", layout="wide")
stil.anwenden()


@st.fragment(run_every="5m")
def aktualisierung():
    """Alle 5 min neue Daten holen; bei neuem Stand die ganze Seite neu rechnen."""
    info = daten.neueste_daten()
    erster_lauf = "head" not in st.session_state
    if info["head"] and info["head"] != st.session_state.get("head"):
        st.session_state["head"] = info["head"]
        if not erster_lauf:
            st.rerun(scope="app")
    st.session_state.setdefault("head", info["head"])
    if info["ok"]:
        st.caption(f":material/sync: Daten geholt {rechnung.zeit_text(info['zeit'], mit_datum=False)}  \n"
                   "Neue Daten alle 5 min automatisch.")
    else:
        st.caption(f":material/sync_problem: Aktualisieren fehlgeschlagen, zeige letzten Stand.  \n"
                   f"{info['meldung'][:120]}")
    if st.button("Jetzt aktualisieren", icon=":material/refresh:", type="tertiary"):
        daten.neueste_daten.clear()
        st.rerun(scope="app")


seiten = st.navigation([
    st.Page("app_pages/uebersicht.py", title="Übersicht", icon=":material/dashboard:", default=True),
    st.Page("app_pages/strategie.py", title="Strategie & Experimente", icon=":material/science:"),
    st.Page("app_pages/copy_trading.py", title="Copy Trading", icon=":material/group:"),
    st.Page("app_pages/scout.py", title="Scout", icon=":material/travel_explore:"),
    st.Page("app_pages/flugschreiber.py", title="Flugschreiber", icon=":material/flight:"),
    st.Page("app_pages/wallets_pruefen.py", title="Wallets prüfen", icon=":material/playlist_add_check:"),
    st.Page("app_pages/betrieb.py", title="Betrieb", icon=":material/build:"),
], position="top")

with st.sidebar:
    st.markdown("**Paperbot** · nur Anschauen, kein echtes Geld")
    aktualisierung()
    st.caption(f"Jetzt: {rechnung.zeit_text(time.time())}")

seiten.run()
