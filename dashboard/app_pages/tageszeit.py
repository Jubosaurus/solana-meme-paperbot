"""Tageszeit geschlossener Trades: reine Anzeige, keine Strategieentscheidung."""
import altair as alt
import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung
import stil


def waermekarte(raster):
    """Sieben schmale Wochentage, Stunden untereinander: passt auch aufs Handy."""
    df = pd.DataFrame(raster)
    df["wert_text"] = df.apply(
        lambda row: a.plusminus(row["pro_trade"]) if row["ausreichend"] else "zu wenig Daten", axis=1)
    basis = alt.Chart(df).encode(
        x=alt.X("wochentag:N", sort=list(rechnung.TAGESZEIT_WOCHENTAGE), title=None,
                axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("stunde:O", sort=list(range(24)), title="Kaufstunde UTC",
                axis=alt.Axis(labelAngle=0)),
        tooltip=[alt.Tooltip("wochentag:N", title="Wochentag (UTC)"),
                 alt.Tooltip("zeit_text:N", title="Stunde (deutsche Zeit in Klammern)"),
                 alt.Tooltip("trades:Q", title="Trades"),
                 alt.Tooltip("wert_text:N", title="SOL je Trade")])
    felder = basis.mark_rect(stroke=stil.KARTE, strokeWidth=1).encode(
        color=alt.condition(alt.datum.ausreichend,
                            alt.Color("pro_trade:Q", title="SOL je Trade",
                                      scale=alt.Scale(domainMid=0, range=[stil.MINUS, stil.KARTE, stil.PLUS]),
                                      legend=alt.Legend(orient="bottom", gradientLength=140)),
                            alt.value(stil.LINIE)))
    anzahl = basis.mark_text(font="JetBrains Mono", fontSize=10, color=stil.TEXT).encode(
        text=alt.Text("trades:Q", format="d"),
        opacity=alt.condition(alt.datum.ausreichend, alt.value(1), alt.value(0.4)))
    return alt.layer(felder, anzahl).properties(height=576)


def gruppen_anzeigen(gruppen, mit_zeiten=True):
    """Je Gruppe eine Karte und aufklappbare Details statt einer breiten Tabelle."""
    for gruppe in gruppen:
        genug = gruppe["ausreichend"]
        unter = f"{gruppe['trades']} Trades · " + ("SOL je Trade" if genug else "zu wenig Daten")
        a.raster([a.karte(gruppe["name"], a.plusminus(gruppe["pro_trade"]) if genug else "–",
                          unter=a.e(unter), klein=True)])
        if mit_zeiten:
            st.caption(gruppe["zeit_text"])
        with st.expander(f"{gruppe['name']} · Ergebnis und Ausreißer"):
            if not genug:
                st.caption("zu wenig Daten: mindestens 10 abgeschlossene Trades nötig.")
            else:
                details = [
                    f"Ergebnis: {a.plusminus(gruppe['summe'])}",
                    f"SOL je Trade: {a.plusminus(gruppe['pro_trade'])} · {gruppe['trades']} Trades",
                    f"Ohne die 3 besten: {a.plusminus(gruppe['ohne_beste_summe'])}",
                    f"SOL je Trade ohne die 3 besten: {a.plusminus(gruppe['ohne_beste_pro_trade'])}",
                    f"Verbleibend: {gruppe['ohne_beste_trades']} Trades",
                ]
                a.tabelle(pd.DataFrame({"Angaben": details}))


a.seitenkopf("Tageszeit", "Wann waren Einstiege erfolgreich? Geschlossene Trades nach Kaufzeit in UTC.")
st.caption("Beobachtung, kein Urteil. Die Testregeln verlangen 200 Trades und einen Vergleich mit der "
           "Kontrollgruppe im selben Zeitraum, auch ohne die 3 besten Trades.")
try:
    quelle = daten.tageszeit(daten.stand())
except Exception:
    a.fehler("Trades konnten nicht geladen werden", "Die lokalen Kontodaten sind zurzeit nicht lesbar.")
    st.stop()

konten = {k["key"]: k for k in quelle["konten"]}
if not konten:
    a.leer("Noch keine Konten", "Für diese Seite werden lokale Kontodateien benötigt.")
    for hinweis in quelle["hinweise"]:
        st.caption(hinweis)
    st.stop()

keys = list(konten)
key = st.selectbox("Konto", keys, index=keys.index("hauptstrategie") if "hauptstrategie" in keys else 0,
                   format_func=lambda wert: konten[wert]["label"], key="tageszeit_konto")
mit_kosten = st.segmented_control("Ergebnisse", ["roh", "mit Kosten"], default="roh", required=True,
                                 key="tageszeit_kosten", wrap=True) == "mit Kosten"
kosten = rechnung.kosten_pct(key)
auswertung = rechnung.tageszeit_auswertung(konten[key]["closed"], kosten if mit_kosten else 0,
                                          marktphasen=quelle["marktphasen"])
gesamt = auswertung["gesamt"]
st.caption(f"{'Mit Kosten' if mit_kosten else 'Roh'} · Kostenaufschlag: {kosten:g} % vom Einsatz je Rundlauf. "
           "Nur abgeschlossene Trades über alle Runden; offene Positionen zählen noch nicht.")
if not gesamt["trades"]:
    a.leer("Noch keine auswertbaren Trades", "Es fehlen abgeschlossene Trades mit Ergebnis und Kaufzeit oder Haltedauer.")
else:
    a.raster([
        a.karte("SOL je Trade", a.plusminus(gesamt["pro_trade"]) if gesamt["ausreichend"] else "–",
                unter=a.e(gesamt["status"]), klein=True),
        a.karte("Geschlossene Trades", str(gesamt["trades"]), unter="mit auswertbarer Kaufzeit", klein=True),
    ], gross=True)
    st.subheader("Wochentag und Stunde", anchor=False)
    stil.zeigen(waermekarte(auswertung["raster"]), "SOL je Trade nach UTC-Kaufstunde und Wochentag, Zahlen sind Trade-Anzahlen")
    st.caption("Zahl im Feld = Trades. Grau und blass = zu wenig Daten (unter 10 Trades). "
               "Tippe auf ein Feld für SOL je Trade und die deutsche Uhrzeit in Klammern. "
               "MESZ = Sommerzeit (UTC+2), MEZ = Winterzeit (UTC+1); Wochentage bleiben UTC.")
    st.subheader("Vier Tageszeiten", anchor=False)
    st.caption("Zeiträume schließen die Endzeit aus: Nacht 0–7, Vormittag 8–13, Nachmittag 14–19, Abend 20–23 Uhr UTC.")
    gruppen_anzeigen(auswertung["gruppen"])
    if auswertung["phasen"]:
        st.subheader("Gespeicherte Marktphase beim Kauf", anchor=False)
        gruppen_anzeigen(auswertung["phasen"], mit_zeiten=False)

with st.expander("Rechnung und Datenlücken"):
    st.caption("Kaufzeit = gespeicherte Kaufzeit, sonst Verkaufszeit minus Haltedauer. "
               "Die Haltedauer kann gerundet sein. Dadurch sind Zuordnungen an Stunden- und Tagesgrenzen unsicher. "
               "Ohne die 3 besten wird innerhalb jeder Gruppe neu gerechnet, nach dem gewählten Kostenmodus.")
    st.caption("Die Zeitgruppen sind Beobachtungen und ändern keine Kauf- oder Verkaufsregel. "
               "Kleine Gruppen und einzelne Gewinntrades können ein scheinbares Muster erzeugen.")
    for hinweis in quelle["hinweise"] + auswertung["hinweise"]:
        st.caption(hinweis)
