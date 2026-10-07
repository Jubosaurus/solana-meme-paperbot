"""Abgelehnte Coins rueckblickend beobachten, ausschliesslich mit lokalen Daten."""
import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung


def statistik_anzeigen(stats, beschriftung):
    """Vorbereitete Kennzahlen mit Stichprobe in einer schmalen Tabelle anzeigen."""
    n = stats["n"]
    if not n:
        a.leer(f"{beschriftung}: keine messbaren Coins (n=0)",
               "Für diese Auswahl gibt es keinen verlässlichen Folgekurs.")
        return
    a.tabelle(pd.DataFrame({"Beobachtung": [
        f"{beschriftung} · Stichprobe n={n} Coins",
        f"Höher: {stats['hoeher']} von {n} · {a.txt(stats['hoeher_pct'], 1, einheit=' %')}",
        f"Niedriger: {stats['niedriger']} von {n} · {a.txt(stats['niedriger_pct'], 1, einheit=' %')}",
        f"Unverändert: {stats['gleich']} von {n}",
        f"Median: {a.plusminus(stats['median_pct'], 1, ' %')} · n={n}",
        f"Durchschnitt: {a.plusminus(stats['mittel_pct'], 1, ' %')} · n={n}",
        f"Bandbreite: {a.plusminus(stats['min_pct'], 1, ' %')} bis "
        f"{a.plusminus(stats['max_pct'], 1, ' %')} · n={n}",
    ]}))


a.seitenkopf("Verpasste Chancen", "Wie liefen abgelehnte Coins danach? Nur Beobachtung, keine Handelsempfehlung.")
try:
    rueckblick = daten.verpasste_chancen(daten.stand())
except Exception:
    a.fehler("Ablehnungen konnten nicht geladen werden", "Die lokalen Dateien sind zurzeit nicht auswertbar.")
    st.stop()

for hinweis in rueckblick["hinweise"]:
    a.hinweis(hinweis)

quelle = st.selectbox("Aufzeichnung", ["knapp_abgelehnt", "abgelehnt"],
                      format_func=lambda q: "Knapp abgelehnt" if q == "knapp_abgelehnt" else "Alle Ablehnungen",
                      key="chancen_quelle")
auswertung = rueckblick["quellen"][quelle]
if not auswertung["pruefungen"]:
    a.leer("Noch keine Ablehnungen (n=0)", "Für diese Aufzeichnung liegen keine lesbaren Fälle vor.")
    st.stop()

a.raster([
    a.karte("Verschiedene Coins", str(auswertung["coins"]),
            f"n={auswertung['coins']} eindeutige Mint-Adressen"),
    a.karte("Ablehnungen aufgezeichnet", str(auswertung["pruefungen"]),
            f"n={auswertung['pruefungen']} Prüfungen, mit Wiederholungen"),
])
a.hinweis("Papierkurs, ohne Kosten, ohne Rug-Risiko. Fehlende Kurse können das Bild verzerren; "
          "ein Kursplus sagt nichts über einen möglichen Verkauf aus.")
if quelle == "abgelehnt":
    a.hinweis("Nur ein Teil aller Ablehnungen wurde anschließend beobachtet. Die messbaren Coins sind "
              "eine ausgewählte Teilmenge und stehen nicht für alle abgelehnten Coins.")
st.caption("Je Coin und Grund zählt die erste Ablehnung dieser Datei. Beide Dateien werden getrennt gezeigt: "
           "Nahfälle können in beiden stehen. Ein Coin kann bei mehreren Gründen zählen.")

gruppen = auswertung["gruende"]
grund = st.selectbox("Ablehnungsgrund", [g["grund"] for g in gruppen],
                    index=next((i for i, g in enumerate(gruppen) if g["grund"] == "FOMO_SPRUNG"), 0),
                    key=f"chancen_grund_{quelle}")
gruppe = next(g for g in gruppen if g["grund"] == grund)
st.subheader(grund.replace("_", " "))
st.caption(f"{gruppe['coins']} verschiedene Coins · n={gruppe['pruefungen']} Prüfungen")
for h in rueckblick["stunden"]:
    stats = gruppe["horizonte"][h]
    st.subheader(f"Nach {h:g} h")
    st.caption(f"Messbar: n={stats['n']} von {gruppe['coins']} Coins · ohne verlässlichen Kurs: {stats['fehlend']}.")
    statistik_anzeigen(stats, "Alle messbaren Coins")
    with st.expander(f"Ohne die 3 besten Coins · n={stats['ohne_beste_3']['n']}"):
        statistik_anzeigen(stats["ohne_beste_3"], "Ohne die 3 besten")

with st.expander("Alle Gründe und Datenlücken"):
    a.tabelle(pd.DataFrame({"Aufzeichnung": [
        f"{g['grund']} · {g['coins']} Coins · n={g['pruefungen']} Prüfungen · "
        + " · ".join(f"{h:g} h: n={s['n']} messbar, {s['fehlend']} fehlend"
                     for h, s in g["horizonte"].items()) for g in gruppen
    ]}))

with st.expander("Ablehnungen im Zeitverlauf (UTC)"):
    a.tabelle(pd.DataFrame({"Tag / Stichprobe": [
        f"{tag['tag']} UTC · n={tag['pruefungen']} Prüfungen" for tag in auswertung["je_tag"]
    ]}))
    st.caption(f"{auswertung['unzuordenbar']} von {auswertung['pruefungen']} Prüfungen ohne Mint oder lesbare Zeit.")

with st.expander("Letzte Erstbeobachtungen · höchstens 50 Fälle"):
    a.tabelle(pd.DataFrame({"Fall": [
        f"{f['symbol']} · {f['grund']} · {rechnung.zeit_text(f['zeit'])} · Mint {f['mint']} · n=1 Coin"
        for f in auswertung["faelle"]
    ]}))
    for fall in auswertung["faelle"]:
        with st.expander(f"{fall['symbol']} · {rechnung.zeit_text(fall['zeit'])}"):
            st.caption("Ausgangskurs: " + (f"{fall['preis_usd']:.8g} USD · n=1 Coin"
                       if fall["preis_usd"] is not None else "fehlt oder ist mehrdeutig · n=0"))
            a.tabelle(pd.DataFrame({"Messpunkt (n=1 Coin)": [
                f"{h:g} h: {a.plusminus(m['rendite_pct'], 1, ' %')} · "
                + (f"{m['preis_usd']:.8g} USD · Kurszeit {rechnung.zeit_text(m['zeit'])} · "
                   f"Abstand zum Ziel {m['abstand_s']:+.0f} s"
                   if m["zeit"] is not None else "kein verlässlicher Folgekurs")
                for h, m in fall["horizonte"].items()
            ]}))

with st.expander("So wird gerechnet"):
    st.caption("Zuordnung über die vollständige Mint-Adresse und die passende Ablehnungsphase im Verlauf. "
               "Der nächste Messpunkt darf höchstens 5 Minuten vor oder nach 1 h beziehungsweise 6 h liegen. "
               "Bei gleichem Abstand zählt der frühere. Keine Fortschreibung oder Schätzung fehlender Kurse. "
               "Anteile und Kursänderungen beziehen sich nur auf messbare Coins; Bandbreite = Minimum bis Maximum. "
               "Ohne die 3 besten: die drei höchsten Kursänderungen je Grund und Zeitraum entfernen. "
               "Messung und DexScreener enthalten keine passenden USD-Folgekurse. Zeiten: UTC, deutsche Zeit in Klammern.")
