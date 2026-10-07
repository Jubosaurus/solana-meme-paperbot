"""Nexus Core (Dashboard Solana-Paperbot) - nur zum Anschauen.

Liest die Daten im Repository, holt alle 5 min neue Daten (git pull) und rechnet mit rechnung.py.
Schreibt nie Daten, startet keine Bots, braucht keine Schluessel. Seit 04.10. holt es fuer die Seite News
oeffentliche RSS-Feeds (nur lesen, nichts speichern). EINZIGE Schreib-Ausnahme: die Seite "Wallets pruefen"
(wallets.py) haengt Adressen an scout/pruefen.txt an und stoesst den Scout an. Start: dashboard/start.bat
Aussehen: stil.py (Vorgaben in DESIGN.md). Menue links mit aufklappbaren Gruppen, Datenstand in der Fusszeile.
"""
import html
import time

import streamlit as st

import daten
import rechnung
import stil

stil.seite_einrichten()
stil.logo_einbinden()
stil.anwenden()

# Datenstand VOR den Seiten setzen (gemeinsam zwischengespeichert, git pull hoechstens alle ~5 min)
_info = daten.neueste_daten()
st.session_state.setdefault("head", _info["head"])

SEITEN = {
    "uebersicht": st.Page("app_pages/uebersicht.py", title="Übersicht", icon=":material/dashboard:", default=True),
    "strategie": st.Page("app_pages/strategie.py", title="Strategie & Experimente", icon=":material/science:"),
    "copy": st.Page("app_pages/copy_trading.py", title="Copy Trading", icon=":material/group:"),
    "scout": st.Page("app_pages/scout.py", title="Scout", icon=":material/travel_explore:"),
    "flugschreiber": st.Page("app_pages/flugschreiber.py", title="Flugschreiber", icon=":material/flight:"),
    "lernen": st.Page("app_pages/lernen.py", title="Lernen", icon=":material/school:"),
    "news": st.Page("app_pages/news.py", title="News", icon=":material/newspaper:"),
    "wallets": st.Page("app_pages/wallets_pruefen.py", title="Wallets prüfen", icon=":material/playlist_add_check:"),
    "betrieb": st.Page("app_pages/betrieb.py", title="Betrieb", icon=":material/build:"),
    "rennbahn": st.Page("app_pages/rennbahn.py", title="Rennbahn", icon=":material/show_chart:"),
    "waechter": st.Page("app_pages/waechter.py", title="Wallet-Wächter", icon=":material/shield:"),
    "verpasst": st.Page("app_pages/verpasste_chancen.py", title="Verpasste Chancen", icon=":material/undo:"),
    "tageszeit": st.Page("app_pages/tageszeit.py", title="Tageszeit", icon=":material/schedule:"),
    "wissen": st.Page("app_pages/wissen.py", title="Wissen", icon=":material/menu_book:"),
}
# Menue: Gruppe -> Seiten (Gruppen mit mehreren Seiten klappen auf; die aktive Gruppe ist offen)
MENUE = {
    "Handel": ["strategie", "rennbahn", "copy", "waechter", "scout"],
    "Analyse": ["flugschreiber", "lernen", "verpasst", "tageszeit", "news", "wissen"],
    "System": ["wallets", "betrieb"],
}

aktuell = st.navigation(list(SEITEN.values()), position="hidden")

with st.sidebar:
    st.html('<div class="nx-sidebar-leitsatz">Centralized Intelligence · Algorithmic Precision</div>')
    st.page_link(SEITEN["uebersicht"])
    for gruppe, schluessel in MENUE.items():
        offen = any(SEITEN[s].title == aktuell.title for s in schluessel)
        with st.expander(gruppe, expanded=offen):
            for s in schluessel:
                st.page_link(SEITEN[s])

@st.fragment(run_every="5m")
def fusszeile():
    """Fusszeile am Ende jeder Seite: Datenstand, Aktualisieren, Hinweis. Alle 5 min neue Daten; bei neuem Stand
    wird die ganze Seite neu gerechnet."""
    info = daten.neueste_daten()
    if info["head"] and info["head"] != st.session_state.get("head"):
        st.session_state["head"] = info["head"]
        st.rerun(scope="app")
    if info["ok"]:
        stand = f"Daten geholt <b>{html.escape(rechnung.zeit_text(info['zeit'], mit_datum=False))}</b> · neue Daten alle 5 min"
    else:
        stand = f"<b>Aktualisieren fehlgeschlagen</b>, zeige letzten Stand ({html.escape(info['meldung'][:100])})"
    st.html(f'<div class="nx-fuss"><span class="nx-fuss-marke"><img src="{stil.marke_uri()}" alt=""/>'
            f'<span class="nx-leitsatz"><span class="nx-leitsatz-name">Nexus Core – </span>'
            f'Centralized Intelligence · Algorithmic Precision</span></span>'
            f'<span>nur Anschauen, kein echtes Geld</span><span>{stand}</span>'
            f'<span>Jetzt: {html.escape(rechnung.zeit_text(time.time()))}</span></div>')
    if st.button("Jetzt aktualisieren", icon=":material/refresh:", type="tertiary"):
        daten.neueste_daten.clear()
        st.rerun(scope="app")


try:
    aktuell.run()
finally:
    fusszeile()    # auch wenn eine Seite st.stop() ruft: Timer und Aktualisieren-Knopf bleiben
