import time

import altair as alt
import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung
import stil

konten = daten.strategie_konten(daten.stand())
jetzt = time.time()

a.seitenkopf("Lernen", "Zeit bis zum Testurteil, Merkmale von Verlusten und der Filter-Trichter als Spuren für weitere Prüfungen.")
st.caption("Streng urteilen, aus Verlusten lernen. Alles hier sind Hinweise für neue Regeln oder Experimente – "
           "ob eine Regel wirklich hilft, prüft danach der Strategie-Tester an den aufgezeichneten Daten.")

# ---------------------------------------------------------------- 1. Urteils-Kalender
st.subheader("Wann gibt es ein Urteil?", anchor=False)
kalender = rechnung.urteils_kalender(konten, jetzt)


def wann(z):
    if z["rest"] == 0:
        return "jetzt"
    if z["eta"] is None:
        return "nicht absehbar"
    tage = z["tage_bis_urteil"]
    return f"in {tage:.0f} Tagen" if tage >= 1.5 else f"in {tage * 24:.0f} h"


if kalender:
    naechstes = kalender[0]
    a.raster([
        a.karte("Nächstes Urteil", naechstes["label"], wann(naechstes)
                + (f" · {rechnung.zeit_text(naechstes['eta'])}" if naechstes["eta"] and naechstes["rest"] else ""),
                a.ring(naechstes["anteil"], f"{naechstes['trades']}", f"von {rechnung.ZIEL_TRADES}"), leuchten=True,
                klein=True),
        a.karte("Experimente mit Urteil in 7 Tagen",
                str(sum(1 for z in kalender if z["eta"] is not None and z["tage_bis_urteil"] <= 7)),
                f"von {len(kalender)} laufenden Konten"),
        a.karte("Ohne absehbares Urteil", str(sum(1 for z in kalender if z["eta"] is None or z["tage_bis_urteil"] > 30)),
                "kein Trade in 3 Tagen oder länger als 30 Tage"),
    ])
    a.tabelle(pd.DataFrame([{
        "Konto": z["label"], "Fortschritt": z["anteil"] * 100, "Trades": f"{z['trades']} / {rechnung.ZIEL_TRADES}",
        "Tempo je Tag": round(z["tempo_pro_tag"], 1), "Urteil": wann(z),
        "voraussichtlich": rechnung.zeit_text(z["eta"]) if z["eta"] and z["rest"] else "",
        "Stand heute": z["urteil"],
    } for z in kalender]), zahlen={"Fortschritt": (0, False, " %"), "Tempo je Tag": (1, False, "")})
    st.caption("Tempo je Tag: abgeschlossene Trades je Tag, Schnitt der letzten 3 Tage.")
    st.caption("Gezählt wie im Testurteil: nur Trades, die im selben Zeitraum wie die Kontrollgruppe geschlossen "
               "wurden. Das Datum ist eine Schätzung aus dem Tempo der letzten 3 Tage.")
else:
    a.leer("Keine laufenden Konten im Urteils-Kalender", "Beendete Experimente und die Kontrollgruppe werden hier nicht angezeigt.")

# ---------------------------------------------------------------- 2. Verlust-Lupe
st.subheader("Verlust-Lupe", anchor=False)
alle = rechnung.lupe_trades(konten)
nach_key = {k["key"]: k["label"] for k in konten}
wahl = st.multiselect("Konten", options=list(nach_key), default=["hauptstrategie"],
                      format_func=lambda key: nach_key[key], key="lupe_konten",
                      placeholder="Alle Konten", help="Leer = alle Konten zusammen")
trades = [t for t in alle if not wahl or t["key"] in wahl]

if not trades:
    a.leer("Noch keine abgeschlossenen Trades", "Wähle andere Konten oder warte auf die ersten Verkäufe in dieser Auswahl.")
else:
    vergleich = rechnung.lupe_vergleich(trades)
    gruende = rechnung.lupe_gruende(trades)
    verschenkt = [t for t in trades if t["verschenkt"]]
    verlust_summe = sum(t["pnl_sol"] for t in trades if t["pnl_sol"] < 0)
    schlimmster = gruende[0] if gruende else None
    a.raster([
        a.karte("Verlierer", f"{vergleich['verlierer']} von {len(trades)}",
                a.pm_html(verlust_summe) + " zusammen"),
        a.karte("Teuerster Verkaufsgrund", schlimmster["grund"] if schlimmster else "–",
                (a.pm_html(schlimmster["summe"]) + f" bei {schlimmster['trades']} Trades") if schlimmster else "",
                klein=True),
        a.karte("Gewinn verschenkt", str(len(verschenkt)),
                f"schon {rechnung.zahl(rechnung.GEWINN_VERSCHENKT_AB, 1)}× im Plus, am Ende im Minus · "
                + a.pm_html(sum(t["pnl_sol"] for t in verschenkt))),
    ])

    tab_merkmale, tab_gruende, tab_verschenkt = st.tabs(
        [":material/compare_arrows: Beim Kauf", ":material/logout: Verkaufsgründe", ":material/trending_down: Verschenkt"])

    with tab_merkmale:
        st.markdown("Wie sahen die Coins **beim Kauf** aus? Mittlerer Wert (Median) bei Verlierern und Gewinnern.")
        a.tabelle(pd.DataFrame([{
            "Merkmal": m["merkmal"],
            "Verlierer": m["verlierer"], "Gewinner": m["gewinner"], "Einheit (V/G)": m["einheit"],
            "Unterschied": m["abstand_pct"],
            "Werte (V/G)": f"{m['n_verlierer']} / {m['n_gewinner']}",
        } for m in vergleich["merkmale"]]), zahlen={
            "Verlierer": (1, False, ""), "Gewinner": (1, False, ""), "Unterschied": (0, True, " %")})
        st.caption("Unterschied: Verlierer im Vergleich zu Gewinnern (+ = bei Verlierern höher). "
                   "Einheit (V/G) gilt für beide Medianwerte.")
        st.caption("Vorsicht: Ein Unterschied ist nur eine Spur, kein Beweis. Bei wenigen Werten (rechte Spalte) "
                   "kann er Zufall sein. Eine neue Regel daraus erst mit dem Strategie-Tester prüfen.")

    with tab_gruende:
        df_g = pd.DataFrame([{"Grund": g["grund"], "Summe": g["summe"]} for g in gruende])
        stil.zeigen(a.balken(df_g, "Summe", "Grund", "Ergebnis SOL"), "Ergebnis je Verkaufsgrund")
        a.tabelle(pd.DataFrame([{
            "Verkaufsgrund": g["grund"], "Trades": g["trades"], "Summe": g["summe"],
            "Anteil Verlierer": g["anteil_verlierer"] * 100, "schlechtester": g["schlechtester"],
        } for g in gruende]), zahlen={"Trades": (0, False, ""), "Anteil Verlierer": (0, False, " %")},
            pm_spalten={"Summe": (3, " SOL"), "schlechtester": (3, " SOL")})

    with tab_verschenkt:
        if not verschenkt:
            a.leer("Keine verschenkten Gewinne", "Keine Trades in dieser Auswahl, die erst im Plus waren und im Minus endeten.")
        else:
            a.datentabelle(pd.DataFrame([{
                "Konto": t["konto"], "Coin": t["symbol"], "Hoch": t["hoch"], "Ergebnis": t["pnl_sol"],
                "Verkaufsgrund": t["grund_lang"], "Haltedauer h": t["halte_h"],
                "geschlossen": rechnung.zeit_text(t["zeit"]),
            } for t in sorted(verschenkt, key=lambda t: t["pnl_sol"])]),
                alt_text="Trades, die erst im Plus waren und im Minus endeten", zahlen={
                    "Hoch": (2, False, "×"), "Haltedauer h": (2, False, "")},
                pm_spalten={"Ergebnis": (4, " SOL")}, hilfen={"Hoch": "Höchster Stand als Vielfaches"})
            st.caption("Diese Trades zeigen, wo eine Gewinnsicherung früher hätte greifen können. "
                       "Den Verlauf eines Coins siehst du auf der Seite Flugschreiber.")

# ---------------------------------------------------------------- 3. Filter-Trichter
st.subheader("Filter-Trichter", anchor=False)
tage = st.segmented_control("Zeitraum", options=[1, 3, 7], default=7, format_func=lambda t: "heute" if t == 1 else f"{t} Tage",
                            key="trichter_tage", required=True, label_visibility="collapsed")
trichter = daten.filter_trichter(daten.stand(), tage or 7)
if not trichter["pruefungen"]:
    a.leer("Keine abgelehnten Coins", "Für diesen Zeitraum liegen keine Ablehnungen vor; wähle bei Bedarf einen anderen Zeitraum.")
else:
    oben = trichter["gruende"][0]
    a.raster([
        a.karte("Geprüfte Coins (verschieden)", f"{trichter['coins']:,}".replace(",", "."),
                f"{trichter['pruefungen']:,} Ablehnungen".replace(",", ".")),
        a.karte("Gekauft (Hauptstrategie)", str(trichter["kaeufe"]),
                f"etwa 1 Kauf auf {trichter['coins'] / max(1, trichter['kaeufe']):.0f} geprüfte Coins"),
        a.karte("Häufigster Grund", oben["grund"], f"{oben['anteil']:.0%} aller Ablehnungen", klein=True),
    ])
    df = pd.DataFrame([{"Grund": g["grund"], "Coins": g["coins"], "Ablehnungen": g["pruefungen"]}
                       for g in trichter["gruende"]])
    chart = alt.Chart(df).mark_bar(cornerRadiusEnd=4, color=stil.VIOLETT, opacity=0.85).encode(
        x=alt.X("Coins:Q", title="verschiedene Coins", axis=alt.Axis(grid=True, tickCount=5)),
        y=alt.Y("Grund:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, ticks=False, domain=False)),
        tooltip=["Grund", "Coins", "Ablehnungen"]).properties(height=max(160, 24 * len(df) + 40))
    stil.zeigen(chart, "Abgelehnte Coins je Filter")
    st.caption("Ein Coin wird oft mehrfach geprüft und abgelehnt; der Balken zählt jeden Coin je Grund einmal. "
               "Nur die Hauptstrategie schreibt abgelehnte Coins auf.")
    with st.expander("Je Tag", icon=":material/calendar_month:"):
        a.tabelle(pd.DataFrame([{"Tag (UTC)": d["tag"], "Ablehnungen": d["abgelehnt"], "Käufe": d["kaeufe"]}
                               for d in reversed(trichter["je_tag"])]),
                  zahlen={"Ablehnungen": (0, False, ""), "Käufe": (0, False, "")})
