import pandas as pd
import streamlit as st

import ansicht
import daten
import rechnung

rangliste, letzter_lauf = daten.scout(daten.stand())
in_copy = {addr for _, addr in rechnung.aktive_wallets()}

st.title("Scout", anchor=False)
st.caption(f"Letzter Lauf: {rechnung.zeit_text(letzter_lauf)}. Der Scout liefert nur eine Rangliste; "
           "Wallets werden erst nach Prüfung und deiner Zustimmung aufgenommen.")

bewertet = [r for r in rangliste if r["ergebnis"] == "bewertet"]
raus = [r for r in rangliste if r["ergebnis"] != "bewertet"]

with st.container(horizontal=True):
    st.metric("Bewertete Wallets", len(bewertet), border=True)
    st.metric("Davon schon im Copy Trading", sum(1 for r in bewertet if r["wallet"] in in_copy), border=True)
    st.metric("Aussortiert", len(raus), border=True)


def zahl(x):
    return rechnung.as_float(x, None)


def pct(x):
    v = zahl(x)
    return None if v is None else v * 100


st.subheader("Rangliste", anchor=False)
st.dataframe(pd.DataFrame([{
    "Rang": i + 1, "Wallet": r["wallet"][:4] + "…" + r["wallet"][-4:], "Quelle": r["quelle"],
    "Punkte": zahl(r["punkte"]), "abgeschl. Coins": zahl(r["coins_abgeschlossen"]),
    "Trades je Tag": ansicht.txt(zahl(r["trades_pro_tag"]), 1),
    "Trefferquote": ansicht.txt(pct(r["trefferquote"]), 0, einheit=" %"),
    "Rendite ohne besten %": ansicht.txt(zahl(r["rendite_ohne_besten_pct"]), 1, True),
    "Reibung pp": ansicht.txt(zahl(r["reibung_pp"]), 1),
    "Haltedauer min": ansicht.txt(zahl(r["haltedauer_median_min"]), 1),
    "Verkäufe < 60 s": ansicht.txt(pct(r.get("schnelle_verkaeufe_anteil")), 0, einheit=" %"),
    "Kauf median SOL": ansicht.txt(zahl(r["kauf_median_sol"]), 3),
    "Bot-Gebühr-Anteil": ansicht.txt(pct(r["bot_gebuehr_anteil"]), 0, einheit=" %"),
    "im Copy": "ja" if r["wallet"] in in_copy else "", "bewertet": rechnung.zeit_text(r["zeit"]),
    "Adresse": r["wallet"],
} for i, r in enumerate(bewertet)]), hide_index=True, alt="Rangliste des Scouts", column_config={
    "Punkte": st.column_config.NumberColumn(format="%.1f", help="Bewertung des Scouts (höher = besser)"),
    "abgeschl. Coins": st.column_config.NumberColumn(format="%d", help="Abgeschlossene Coins im 7-Tage-Fenster. "
                                                                       "Wenige = unsichere Punktzahl"),
    "Reibung pp": st.column_config.TextColumn(help="Geschätzte Kosten fürs Kopieren (Prozentpunkte)"),
})
st.caption("Vorsicht bei sehr hohen Punkten mit wenigen abgeschlossenen Coins: Dann bläht oft ein einzelner "
           "Treffer die Rendite stark auf.")

with st.expander(f"Aussortiert ({len(raus)})", icon=":material/filter_alt_off:"):
    st.dataframe(pd.DataFrame([{
        "Wallet": r["wallet"][:4] + "…" + r["wallet"][-4:], "Quelle": r["quelle"], "Ergebnis": r["ergebnis"],
        "Grund": r["grund"], "geprüft": rechnung.zeit_text(r["zeit"]), "Adresse": r["wallet"],
    } for r in raus]), hide_index=True, alt="Vom Scout aussortierte Wallets")
