import pandas as pd
import streamlit as st

import ansicht
import daten
import rechnung
import wallets

st.title("Wallets prüfen", anchor=False)
st.caption("Hier schickst du neue Wallet-Adressen zur Prüfung an den Scout. Diese Seite speichert nur ans Ende "
           "von scout/pruefen.txt und startet einen kurzen Scout-Lauf, der nur die Prüfliste bewertet (ohne "
           "Coin-Suche und Birdeye). Erfüllt eine Wallet alle Aufnahme-Kriterien, nimmt der Scout sie automatisch "
           "ins Copy Trading auf oder ersetzt eine schwache Wallet (höchstens 3 Änderungen pro Tag); sonst kommt sie "
           "auf die Warteliste. Abschalten: Schalter AUTO_AUFNAHME oben in scout_bot.py.")

# ---------------------------------------------------------------- Eingabe
# Schreiben nur am PC selbst (localhost). Vom Handy im Heimnetz: nur anschauen.
am_pc = wallets.ist_lokal(st.context.ip_address, dict(st.context.headers))
if not am_pc:
    st.info("Absenden nur am PC. Auf dem Handy kannst du die Prüfliste nur anschauen.",
            icon=":material/lock:")
if am_pc:
    with st.container(border=True):
        st.markdown("**Neue Adressen**")
        text = st.text_area("Adressen", height=150, label_visibility="collapsed",
                            placeholder="Eine Adresse pro Zeile, optional mit Namen:\nMeinName: 9yYya3F5EJoLnBNKW6z4bZvyQytMXzDcpU5D6yYr4jqL",
                            key="wallet_text")
        vorschau, abgelehnt = wallets.eingabe_pruefen(text)
        if text.strip():
            if vorschau:
                st.caption(f":material/check_circle: {len(vorschau)} gültige Adresse(n) bereit "
                           f"(höchstens {wallets.MAX_ADRESSEN} pro Absenden).")
            for zeile, grund in abgelehnt:
                st.warning(f"**{zeile}**  \n{grund}", icon=":material/block:")
        if st.button("Zur Prüfung schicken", type="primary", icon=":material/send:", disabled=not vorschau):
            with st.spinner("Wird gespeichert und hochgeladen …"):
                ok, meldung = wallets.zur_pruefung_schicken(vorschau)
            if ok:
                st.success(meldung, icon=":material/check_circle:")
                with st.spinner("Scout wird angestoßen …"):
                    _, scout_meldung = wallets.scout_anstossen()
                st.info(scout_meldung, icon=":material/travel_explore:")
                daten.neueste_daten.clear()
                st.session_state.pop("head", None)
            else:
                st.error(meldung, icon=":material/error:")

# ---------------------------------------------------------------- Liste mit Ergebnissen
zeilen = wallets.pruefliste_status()
wartet = sum(1 for z in zeilen if z["status"] == "wartet")
st.subheader("Prüfliste", anchor=False)
with st.container(horizontal=True):
    st.metric("Adressen in der Prüfliste", len(zeilen), border=True)
    st.metric("Geprüft", len(zeilen) - wartet, border=True)
    st.metric("Warten auf den Scout", wartet, border=True)


def ergebnis_text(z):
    if z["status"] == "wartet":
        return "wartet auf den nächsten Scout-Lauf"
    if z["ergebnis"] == "bewertet":
        return "bewertet"
    return f"abgelehnt: {z['grund'] or z['ergebnis']}"


if zeilen:
    st.dataframe(pd.DataFrame([{
        "Name": z["name"], "Status": z["status"], "Ergebnis": ergebnis_text(z),
        "Punkte": z["punkte"], "Haltedauer min": ansicht.txt(z["haltedauer_min"], 1),
        "Rendite ohne besten Coin %": ansicht.txt(z["rendite_ohne_besten"], 1, True),
        "abgeschl. Coins": z["coins"],
        "Copy": z["copy"], "geprüft": rechnung.zeit_text(z["zeit"]) if z["zeit"] else "",
        "Adresse": z["wallet"],
    } for z in zeilen]), hide_index=True, alt="Prüfliste mit Scout-Ergebnis", column_config={
        "Punkte": st.column_config.NumberColumn(format="%.1f", help="Bewertung des Scouts (höher = besser)"),
        "abgeschl. Coins": st.column_config.NumberColumn(format="%d"),
    })
    st.caption("Die Punkte kommen vom Scout und sind nur eine Hilfe. Vorsicht bei wenigen abgeschlossenen Coins. "
               "Jede Adresse wird nur einmal bewertet; neu erst, wenn sich die Bewertungsmethode ändert.")
else:
    st.caption("Die Prüfliste ist leer.")
