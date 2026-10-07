"""Alle Strategie-Konten vergleichen, ausschliesslich mit lokalen Daten."""
import altair as alt
import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung
import stil


def diagramm(punkte, mit_kosten):
    """Anzeige der vorberechneten Werte; Kontrollgruppe dick, beendete Konten blass."""
    df = pd.DataFrame(punkte)
    wert = "mit_kosten" if mit_kosten else "roh"
    df["zeit_text"] = df["zeit"].map(rechnung.zeit_text)
    df["wert_text"] = df[wert].map(rechnung.sol_text)
    farben = [stil.INDIGO, stil.INDIGO_HELL, stil.BLAU, "#818CF8", "#C4B5FD", "#67E8F9"]
    namen = list(dict.fromkeys(df["konto"]))
    skala = []
    for i, name in enumerate(namen):
        gruppe = df[df["konto"] == name].iloc[0]
        skala.append(stil.KONTROLLE if gruppe["kontrolle"] else
                     stil.NEUTRAL if gruppe["beendet"] else farben[i % len(farben)])
    basis = alt.Chart(df).encode(
        x=alt.X("zeit:T", title="Zeit (UTC)", scale=alt.Scale(type="utc"),
                axis=alt.Axis(format="%d.%m.", tickCount=4, labelAngle=0, grid=False)),
        y=alt.Y(f"{wert}:Q", title="Gewinn / Verlust (SOL)", scale=alt.Scale(zero=True)),
        color=alt.Color("konto:N", scale=alt.Scale(domain=namen, range=skala), legend=None),
        detail="key:N", order="folge:Q",
        tooltip=[alt.Tooltip("konto:N", title="Konto"), alt.Tooltip("zeit_text:N", title="Zeit"),
                 alt.Tooltip("wert_text:N", title="Mit Kosten" if mit_kosten else "Roh")])
    linien = basis.mark_line(interpolate="step-after", point=True).encode(
        strokeWidth=alt.condition(alt.datum.kontrolle, alt.value(3.5), alt.value(1.6)),
        opacity=alt.condition(alt.datum.beendet, alt.value(0.35), alt.value(0.85)),
        strokeDash=alt.condition(alt.datum.kontrolle, alt.value([6, 3]), alt.value([1, 0])))
    null = alt.Chart(pd.DataFrame({"start": [0]})).mark_rule(
        color=stil.TEXT_LEISE, strokeDash=[3, 3]).encode(y="start:Q")
    return alt.layer(null, linien).properties(height=350)


def rangtabelle(zeilen):
    """Schmale Rangtabelle; alle Zahlen und Urteile darunter pro Konto aufklappbar."""
    if not zeilen:
        a.leer("Keine Konten in dieser Auswahl")
        return
    a.tabelle(pd.DataFrame([{
        "Konto": f"{k['rang']}. {k['label']}",
        "Roh / mit Kosten": a.plusminus(k["ergebnis"]) + " / " + a.plusminus(k["ergebnis_kosten"]),
    } for k in zeilen]))
    for k in zeilen:
        with st.expander(f"{k['rang']}. {k['label']} · {k['trades']} Trades"):
            details = [
                {"Angabe": "Ergebnis roh", "Wert": a.plusminus(k["ergebnis"])},
                {"Angabe": "Ergebnis mit Kosten", "Wert": a.plusminus(k["ergebnis_kosten"])},
                {"Angabe": "Runde", "Wert": str(k["runde"])},
                {"Angabe": "Trades insgesamt", "Wert": str(k["trades"])},
                {"Angabe": "Trades bis 200", "Wert": str(k["trades_bis_200"])},
                {"Angabe": "Trades im Vergleichszeitraum", "Wert": str(k["vergleich_trades"])},
                {"Angabe": "Testurteil roh", "Wert": k["urteil"]},
                {"Angabe": "Testurteil mit Kosten", "Wert": k["urteil_kosten"]},
            ]
            a.tabelle(pd.DataFrame({"Angaben": [f"{d['Angabe']}: {d['Wert']}" for d in details]}))
            st.caption(f"Kostenaufschlag: {rechnung.zahl(k['kosten_pct'], 0)} % vom Einsatz je Rundlauf.")
            beginn = k["vergleich"].get("beginn")
            if beginn:
                st.caption("Vergleich ab " + rechnung.zeit_text(beginn))


a.seitenkopf("Rennbahn", "Hauptstrategie und Experimente im Vergleich. Start im Diagramm = 0 SOL.")
try:
    rennen = daten.rennbahn(daten.stand())
except Exception:
    a.fehler("Konten konnten nicht geladen werden", "Die lokalen Kontodaten sind zurzeit nicht lesbar.")
    st.stop()

alle = rennen["rangliste"] + rennen["beendet"]
if not alle:
    a.leer("Noch keine Konten", "Sobald lokale Kontodaten vorliegen, erscheint der Vergleich.")
    st.stop()

nach_key = {k["key"]: k for k in alle}
mit = st.segmented_control("Diagrammwerte", ["roh", "mit Kosten"], default="roh", required=True,
                           key="rennbahn_kosten", wrap=True) == "mit Kosten"
with st.expander("Sichtbare Konten", expanded=False):
    auswahl = st.multiselect("Konten im Diagramm und in der Rangtabelle", list(nach_key),
                             default=rennen["standard"], format_func=lambda key: nach_key[key]["label"],
                             key="rennbahn_konten", wrap=True)

aktiv = [k for k in rennen["rangliste"] if k["key"] in auswahl]
alte = [k for k in rennen["beendet"] if k["key"] in auswahl]
kopf = []
if aktiv:
    k = aktiv[0]
    kopf.append(a.roh_kosten_karte("Vorne nach Ergebnis roh · " + k["label"],
                                 a.plusminus(k["ergebnis"]), a.plusminus(k["ergebnis_kosten"]),
                                 "laufende Runde, inklusive offener Positionen", leuchten=True))
kontrolle = nach_key.get(rechnung.KONTROLLE)
if kontrolle and rechnung.KONTROLLE in auswahl:
    kopf.append(a.roh_kosten_karte("Kontrollgruppe · Maßstab", a.plusminus(kontrolle["ergebnis"]),
                                 a.plusminus(kontrolle["ergebnis_kosten"]),
                                 "zufällige Käufe im selben Zeitraum"))
if kopf:
    a.raster(kopf, gross=True)

st.subheader("Gewinn und Verlust aus abgeschlossenen Trades", anchor=False)
punkte = [p for p in rennen["verlauf"] if p["key"] in auswahl]
if punkte:
    stil.zeigen(diagramm(punkte, mit), "Gewinn und Verlust aller ausgewählten Konten seit Start bei 0 SOL")
    st.caption("Kontrollgruppe: dicke, gestrichelte graue Linie. Beendete Konten: blass. "
               "Tippe auf einen Punkt für Konto, Wert und Zeit in UTC (deutsche Zeit in Klammern).")
else:
    a.leer("Noch kein Verlauf für diese Auswahl", "Wähle Konten mit gespeicherter Start- oder Trade-Zeit.")
st.caption("Diagramm: geschlossene Trades über alle Runden, ohne offene Positionen. "
           "Rangtabelle: laufende Runde inklusive offener Positionen, wie bei Strategie & Experimente. "
           "Deshalb können Kurvenende und Rangwert voneinander abweichen.")

st.subheader("Rangtabelle · aktive Konten", anchor=False)
st.caption("Nach Ergebnis roh geordnet. Beide Ergebnisse und Testurteile bleiben beim Umschalten sichtbar.")
rangtabelle(aktiv)
if rennen["beendet"]:
    with st.expander("Beendete Experimente"):
        st.caption("Keine neuen Käufe. Für den Vergleich oben unter „Sichtbare Konten“ auswählen.")
        rangtabelle(alte)
with st.expander("So wird verglichen"):
    st.caption("Ergebnis = Kontowert minus 10 SOL Start. Urteil frühestens nach 200 Trades im "
               "Vergleichszeitraum mit der Kontrollgruppe; es muss auch ohne die 3 besten Trades halten. "
               "Die Zahl „Trades bis 200“ zählt alle abgeschlossenen Trades. Der Vergleichszeitraum "
               "kann weniger Trades enthalten. Endspurt viele Trades hat zusätzlich den Prüfpunkt bei 400 Trades.")
    st.caption(f"Kosten sind ein Aufschlag von {rechnung.KOSTEN_PCT:g} %, bei Endspurt-Konten "
               f"{rechnung.KOSTEN_ENDSPURT_PCT:g} % vom Einsatz je Rundlauf. "
               "Sandwich-Angriffe und gescheiterte Transaktionen sind darin nicht gemessen.")
if rennen["hinweise"]:
    with st.expander("Datenlücken und Hinweise"):
        for hinweis in rennen["hinweise"]:
            st.caption(hinweis)
