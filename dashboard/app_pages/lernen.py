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

st.title("Lernen", anchor=False)
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
    st.dataframe(pd.DataFrame([{
        "Konto": z["label"], "Fortschritt": z["anteil"], "Trades": f"{z['trades']} / {rechnung.ZIEL_TRADES}",
        "Tempo je Tag": round(z["tempo_pro_tag"], 1), "Urteil": wann(z),
        "voraussichtlich": rechnung.zeit_text(z["eta"]) if z["eta"] and z["rest"] else "",
        "Stand heute": z["urteil"],
    } for z in kalender]), hide_index=True, alt="Fortschritt aller Experimente bis zum Urteil", column_config={
        "Fortschritt": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
        "Tempo je Tag": st.column_config.NumberColumn(help="Abgeschlossene Trades je Tag, Schnitt der letzten 3 Tage"),
    })
    st.caption("Gezählt wie im Testurteil: nur Trades, die im selben Zeitraum wie die Kontrollgruppe geschlossen "
               "wurden. Das Datum ist eine Schätzung aus dem Tempo der letzten 3 Tage.")

# ---------------------------------------------------------------- 2. Verlust-Lupe
st.subheader("Verlust-Lupe", anchor=False)
alle = rechnung.lupe_trades(konten)
nach_key = {k["key"]: k["label"] for k in konten}
wahl = st.multiselect("Konten", options=list(nach_key), default=["hauptstrategie"],
                      format_func=lambda key: nach_key[key], key="lupe_konten",
                      placeholder="Alle Konten", help="Leer = alle Konten zusammen")
trades = [t for t in alle if not wahl or t["key"] in wahl]

if not trades:
    st.info("Noch keine abgeschlossenen Trades in dieser Auswahl.", icon=":material/info:")
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
        st.dataframe(pd.DataFrame([{
            "Merkmal": m["merkmal"],
            "Verlierer": a.txt(m["verlierer"], 1, einheit=m["einheit"]),
            "Gewinner": a.txt(m["gewinner"], 1, einheit=m["einheit"]),
            "Unterschied": m["abstand_pct"] / 100 if m["abstand_pct"] is not None else None,
            "Werte (V/G)": f"{m['n_verlierer']} / {m['n_gewinner']}",
        } for m in vergleich["merkmale"]]), hide_index=True, alt="Merkmale beim Kauf: Verlierer gegen Gewinner",
            column_config={"Unterschied": st.column_config.NumberColumn(
                format="percent", help="Verlierer im Vergleich zu Gewinnern (+ = bei Verlierern höher)")})
        st.caption("Vorsicht: Ein Unterschied ist nur eine Spur, kein Beweis. Bei wenigen Werten (rechte Spalte) "
                   "kann er Zufall sein. Eine neue Regel daraus erst mit dem Strategie-Tester prüfen.")

    with tab_gruende:
        df_g = pd.DataFrame([{"Grund": g["grund"], "Summe": g["summe"]} for g in gruende])
        stil.zeigen(a.balken(df_g, "Summe", "Grund", "Ergebnis SOL"), "Ergebnis je Verkaufsgrund")
        st.dataframe(pd.DataFrame([{
            "Verkaufsgrund": g["grund"], "Trades": g["trades"], "Summe": a.plusminus(g["summe"]),
            "Anteil Verlierer": g["anteil_verlierer"], "schlechtester": a.plusminus(g["schlechtester"]),
        } for g in gruende]), hide_index=True, alt="Verkaufsgründe mit Anzahl und Ergebnis", column_config={
            "Anteil Verlierer": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})

    with tab_verschenkt:
        if not verschenkt:
            st.info("Keine Trades, die erst im Plus waren und im Minus endeten.", icon=":material/check_circle:")
        else:
            st.dataframe(pd.DataFrame([{
                "Konto": t["konto"], "Coin": t["symbol"], "Hoch": t["hoch"], "Ergebnis": t["pnl_sol"],
                "Verkaufsgrund": t["grund_lang"], "Haltedauer h": t["halte_h"],
                "geschlossen": rechnung.zeit_text(t["zeit"]),
            } for t in sorted(verschenkt, key=lambda t: t["pnl_sol"])]), hide_index=True,
                alt="Trades, die erst im Plus waren und im Minus endeten", column_config={
                    "Hoch": st.column_config.NumberColumn(format="%.2f×", help="Höchster Stand als Vielfaches"),
                    "Ergebnis": st.column_config.NumberColumn(format="%+.4f SOL"),
                    "Haltedauer h": st.column_config.NumberColumn(format="%.2f"),
                })
            st.caption("Diese Trades zeigen, wo eine Gewinnsicherung früher hätte greifen können. "
                       "Den Verlauf eines Coins siehst du auf der Seite Flugschreiber.")

# ---------------------------------------------------------------- 3. Filter-Trichter
st.subheader("Filter-Trichter", anchor=False)
tage = st.segmented_control("Zeitraum", options=[1, 3, 7], default=7, format_func=lambda t: "heute" if t == 1 else f"{t} Tage",
                            key="trichter_tage", required=True, label_visibility="collapsed")
trichter = daten.filter_trichter(daten.stand(), tage or 7)
if not trichter["pruefungen"]:
    st.info("Keine abgelehnten Coins in diesem Zeitraum.", icon=":material/info:")
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
        st.dataframe(pd.DataFrame([{"Tag (UTC)": d["tag"], "Ablehnungen": d["abgelehnt"], "Käufe": d["kaeufe"]}
                                   for d in reversed(trichter["je_tag"])]), hide_index=True,
                     alt="Ablehnungen und Käufe je Tag")
