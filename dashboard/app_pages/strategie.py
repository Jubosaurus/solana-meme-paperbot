import time

import pandas as pd
import streamlit as st

import ansicht
import daten
import rechnung

konten = daten.strategie_konten(daten.stand())
nach_key = {k["key"]: k for k in konten}
kontrolle = nach_key[rechnung.KONTROLLE]

st.title("Strategie & Experimente", anchor=False)
wahl = st.segmented_control("Konto", options=list(nach_key), default="hauptstrategie",
                            format_func=lambda key: nach_key[key]["label"], key="konto", required=True,
                            bind="query-params", label_visibility="collapsed")
k = nach_key[wahl or "hauptstrategie"]
v = k["vergleich"]

# ---------------------------------------------------------------- Kopf: Zahlen und Testurteil
with st.container(horizontal=True):
    ansicht.sol_metric("Kontowert", k["kontowert"], k["ergebnis"],
                       hilfe="Frei + offene Positionen zum letzten aufgezeichneten Kurs (wie in Discord). "
                             "Plus/Minus gegenüber 10 SOL.")
    st.metric("Trades", f"{k['trades']} von {rechnung.ZIEL_TRADES}", border=True,
              help="Urteil über ein Experiment frühestens nach 200 Trades.")
    st.metric("SOL je Trade", rechnung.zahl(k["pro_trade"], 4, vorzeichen=True) if k["trades"] else "–",
              border=True, help="Summe der geschlossenen Trades geteilt durch ihre Anzahl.")
    st.metric("ohne die 3 besten", rechnung.zahl(k["ohne_beste_pro_trade"], 4, vorzeichen=True)
              if k["ohne_beste_pro_trade"] is not None else "–", border=True,
              help="SOL je Trade, wenn man die 3 besten Trades weglässt – hält das Ergebnis auch ohne Glückstreffer?")
    st.metric("Gewinner", f"{k['gewinner']} von {k['trades']}" if k["trades"] else "–", border=True)

with st.container(border=True):
    st.markdown("**Testregel: gegen die Kontrollgruppe**")
    ansicht.ampel_badge(v)
    if v["ampel"] not in ("basis", "keine_daten"):
        a, b = v["eigen"], v["kontrolle"]
        st.caption(f"Gleicher Zeitraum ab {rechnung.zeit_text(v['beginn'])}: nur Trades, die danach geschlossen wurden.")
        st.dataframe(pd.DataFrame([
            {"": k["label"], "Trades": a["trades"], "SOL je Trade": a["pro_trade"],
             "ohne 3 beste": a["ohne_beste_pro_trade"], "Summe": a["summe"]},
            {"": "Kontrollgruppe", "Trades": b["trades"], "SOL je Trade": b["pro_trade"],
             "ohne 3 beste": b["ohne_beste_pro_trade"], "Summe": b["summe"]},
        ]), hide_index=True, alt="Vergleich mit der Kontrollgruppe", column_config={
            "SOL je Trade": st.column_config.NumberColumn(format="%+.4f"),
            "ohne 3 beste": st.column_config.NumberColumn(format="%+.4f"),
            "Summe": st.column_config.NumberColumn(format="%+.3f SOL"),
        })
    elif v["ampel"] == "basis":
        st.caption("Die Kontrollgruppe kauft zufällig ohne Filter. Sie ist der Maßstab für alle anderen Konten.")

# ---------------------------------------------------------------- Kontoverlauf
with st.container(border=True):
    st.markdown("**Kontostand nach jedem geschlossenen Trade** · Linie bei 10 SOL = Start")
    eigen = pd.DataFrame(k["verlauf"])
    vgl = pd.DataFrame(kontrolle["verlauf"]) if k["key"] != rechnung.KONTROLLE else None
    if len(eigen) > 1:
        st.altair_chart(ansicht.kontoverlauf(eigen, k["label"], vgl), alt=f"Kontostand {k['label']} über die Zeit")
        st.caption("Offene Positionen sind hier nicht enthalten, nur abgeschlossene Trades.")
    else:
        st.caption("Noch keine abgeschlossenen Trades.")

# ---------------------------------------------------------------- Offene Positionen
st.subheader(f"Offene Positionen ({len(k['offen'])})", anchor=False)
if k["offen"]:
    jetzt = time.time()
    st.dataframe(pd.DataFrame([{
        "Coin": o["symbol"], "seit": rechnung.dauer_text(jetzt - o["seit"]) if o["seit"] else "–",
        "Vielfaches": ansicht.txt(o["vielfaches"], 2, einheit="x"),
        "Wert jetzt": ansicht.txt(o["wert"], 3, einheit=" SOL"),
        "Plus/Minus": ansicht.plusminus(o["pnl"]), "Hälfte verkauft": o["haelfte_verkauft"],
        "Kurs von": rechnung.zeit_text(o["kurs_zeit"]) if o["kurs_zeit"] else "kein Kurs",
    } for o in k["offen"]]), hide_index=True, alt="Offene Positionen", column_config={
        "Vielfaches": st.column_config.TextColumn(help="Kurs jetzt / Kaufkurs"),
    })
else:
    st.caption("Keine offenen Positionen.")

# ---------------------------------------------------------------- Letzte Trades
st.subheader("Letzte Trades", anchor=False)
if k["closed"]:
    letzte = sorted(k["closed"], key=lambda c: c.get("closed_at") or "", reverse=True)[:30]
    st.dataframe(pd.DataFrame([{
        "geschlossen": rechnung.zeit_text(c.get("closed_at")),
        "Coin": c.get("symbol", "?"),
        "Ergebnis": ansicht.plusminus(rechnung.as_float(c.get("pnl_sol"))),
        "in %": rechnung.as_float(c.get("pnl_pct")),
        "Grund": c.get("exit_reason", ""),
        "gehalten": rechnung.dauer_text(rechnung.as_float(c.get("hold_h")) * 3600),
        "bestes Vielfaches": ansicht.txt(c.get("peak_multiple"), 2, einheit="x"),
    } for c in letzte]), hide_index=True, alt="Letzte 30 geschlossene Trades", column_config={
        "in %": st.column_config.NumberColumn(format="%+.1f %%"),
        "bestes Vielfaches": st.column_config.TextColumn(help="Höchster Kurs während der Haltezeit"),
        "Grund": st.column_config.TextColumn(width="large"),
    })
    st.caption("Die 30 neuesten. Zeiten in UTC, in Klammern deutsche Zeit.")
else:
    st.caption("Noch keine Trades.")
