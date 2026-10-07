"""Wissens-Wiki und Berichte ansehen, nur lokale Daten lesen."""
import streamlit as st

import ansicht as a
import daten
import rechnung


a.seitenkopf("Wissen", "Wissen nachschlagen, eigene Notizen finden und frühere Berichte lesen.", status=False)
st.caption("Das Wiki sammelt Wissen. Verbindlich bleiben die Strategie und die Projektregeln.")
head = daten.stand()
wiki_tab, berichte_tab = st.tabs(["Wiki", "Berichte"])

with wiki_tab:
    suche = st.text_input("Im Wissen suchen", placeholder="Begriff oder mehrere Wörter", key="wissen_suche")
    try:
        seiten = daten.wissen(head)
    except Exception:
        seiten = []
        a.fehler("Wissen konnte nicht geladen werden", "Bitte später erneut versuchen.")
    if not seiten:
        a.leer("Noch keine Wissensseiten", "Leere oder unlesbare Dateien werden übersprungen.")
    elif suche.strip():
        treffer = rechnung.wissen_suche(seiten, suche)
        st.caption(f"{len(treffer)} Treffer · alle Suchwörter müssen vorkommen")
        if not treffer:
            a.leer("Keine passenden Wissensseiten", "Versuche einen anderen oder kürzeren Suchbegriff.")
        for seite in treffer:
            with st.container(border=True):
                st.markdown("**" + seite["titel"] + "**")
                st.caption(seite["pfad"] + (" · eigene Notiz" if seite["eigene_notiz"] else ""))
                st.caption(seite["ausschnitt"])
                with st.expander("Ganze Seite: " + seite["titel"]):
                    st.markdown(seite["markdown"], unsafe_allow_html=False)
    else:
        einstieg = next((s for s in seiten if s["art"] == "index"), None)
        if einstieg:
            with st.expander("Einstieg: " + einstieg["titel"]):
                st.markdown(einstieg["markdown"], unsafe_allow_html=False)
        else:
            a.leer("Der Wiki-Einstieg fehlt", "Die übrigen lesbaren Seiten stehen unten.")
        for gruppe, liste in rechnung.wissen_gruppen(seiten).items():
            st.subheader(gruppe.capitalize(), anchor=False)
            for seite in liste:
                label = seite["titel"] + (" · eigene Notiz" if seite["eigene_notiz"] else "")
                with st.expander(label):
                    st.caption(seite["pfad"])
                    st.markdown(seite["markdown"], unsafe_allow_html=False)

with berichte_tab:
    suche = st.text_input("In Berichten suchen", placeholder="Begriff oder mehrere Wörter", key="berichte_suche")
    st.caption("Neueste zuerst · Datum im Dateinamen, sonst letzte Dateiänderung")
    try:
        berichte = daten.berichte(head)
    except Exception:
        berichte = []
        a.fehler("Berichte konnten nicht geladen werden", "Bitte später erneut versuchen.")
    treffer = rechnung.wissen_suche(berichte, suche)
    if not berichte:
        a.leer("Noch keine Berichte", "Leere oder unlesbare Dateien werden übersprungen.")
    elif not treffer:
        a.leer("Keine passenden Berichte", "Versuche einen anderen oder kürzeren Suchbegriff.")
    else:
        st.caption(f"{len(treffer)} " + ("Treffer" if suche.strip() else "Berichte"))
    for seite in treffer:
        if suche.strip():
            st.caption(seite["ausschnitt"])
        with st.expander(seite["titel"]):
            st.caption(seite["pfad"])
            st.markdown(seite["markdown"], unsafe_allow_html=False)
