import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung

rangliste, letzter_lauf = daten.scout(daten.stand())
in_copy = {addr for _, addr in rechnung.aktive_wallets()}

a.seitenkopf("Scout", "Bewertete und aussortierte Wallets mit ihren Kennzahlen und dem aktuellen Prüfstand.")
st.caption(f"Letzter Lauf: {rechnung.zeit_text(letzter_lauf)}. Der Scout liefert nur eine Rangliste; "
           "Wallets werden erst nach Prüfung und deiner Zustimmung aufgenommen.")

bewertet = [r for r in rangliste if r["ergebnis"] == "bewertet"]
raus = [r for r in rangliste if r["ergebnis"] != "bewertet"]

a.raster([
    a.karte("Bewertete Wallets", str(len(bewertet))),
    a.karte("Davon schon im Copy Trading", str(sum(1 for r in bewertet if r["wallet"] in in_copy))),
    a.karte("Aussortiert", str(len(raus))),
])


def zahl(x):
    return rechnung.as_float(x, None)


def pct(x):
    v = zahl(x)
    return None if v is None else v * 100


st.subheader("Rangliste", anchor=False)
a.datentabelle(pd.DataFrame([{
    "Rang": i + 1, "Wallet": r["wallet"][:4] + "…" + r["wallet"][-4:], "Quelle": r["quelle"],
    "Punkte": zahl(r["punkte"]), "abgeschl. Coins": zahl(r["coins_abgeschlossen"]),
    "Trades je Tag": zahl(r["trades_pro_tag"]),
    "Trefferquote": pct(r["trefferquote"]),
    "Rendite ohne besten %": zahl(r["rendite_ohne_besten_pct"]),
    "Reibung pp": zahl(r["reibung_pp"]),
    "Haltedauer min": zahl(r["haltedauer_median_min"]),
    "Verkäufe < 60 s": pct(r.get("schnelle_verkaeufe_anteil")),
    "Kauf median SOL": zahl(r["kauf_median_sol"]),
    "Bot-Gebühr-Anteil": pct(r["bot_gebuehr_anteil"]),
    "im Copy": "ja" if r["wallet"] in in_copy else "", "bewertet": rechnung.zeit_text(r["zeit"]),
    "Adresse": r["wallet"],
} for i, r in enumerate(bewertet)]), alt_text="Rangliste des Scouts", zahlen={
    "Rang": (0, False, ""), "Punkte": (1, False, ""), "abgeschl. Coins": (0, False, ""),
    "Trades je Tag": (1, False, ""), "Trefferquote": (0, False, " %"),
    "Reibung pp": (1, False, ""), "Haltedauer min": (1, False, ""),
    "Verkäufe < 60 s": (0, False, " %"), "Kauf median SOL": (3, False, ""),
    "Bot-Gebühr-Anteil": (0, False, " %"),
}, pm_spalten={"Rendite ohne besten %": (1, "")}, hilfen={
    "Punkte": "Bewertung des Scouts (höher = besser)",
    "abgeschl. Coins": "Abgeschlossene Coins im 7-Tage-Fenster. Wenige = unsichere Punktzahl",
    "Reibung pp": "Geschätzte Kosten fürs Kopieren (Prozentpunkte)",
}, leer_text="Noch keine bewerteten Wallets.")
st.caption("Vorsicht bei sehr hohen Punkten mit wenigen abgeschlossenen Coins: Dann bläht oft ein einzelner "
           "Treffer die Rendite stark auf.")

with st.expander(f"Aussortiert ({len(raus)})", icon=":material/filter_alt_off:"):
    a.datentabelle(pd.DataFrame([{
        "Wallet": r["wallet"][:4] + "…" + r["wallet"][-4:], "Quelle": r["quelle"], "Ergebnis": r["ergebnis"],
        "Grund": r["grund"], "geprüft": rechnung.zeit_text(r["zeit"]), "Adresse": r["wallet"],
    } for r in raus]), alt_text="Vom Scout aussortierte Wallets", leer_text="Keine aussortierten Wallets.")
