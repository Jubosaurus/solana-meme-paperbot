import time

import pandas as pd
import streamlit as st

import ansicht
import daten
import rechnung

jetzt = time.time()
head = daten.stand()
konten = daten.strategie_konten(head)
copy, copy_gespeichert, _ = daten.copy_konten(head)
commits, _, _ = daten.betrieb(head)
_, scout_lauf = daten.scout(head)

st.title("Übersicht", anchor=False)

# ---------------------------------------------------------------- Laeuft alles?
letzte = {bot: (t[-1] if t else None) for bot, t in commits.items()}
status = {bot: rechnung.bot_status(ts, jetzt) for bot, ts in letzte.items()}
scout_status = "kaputt" if scout_lauf is None else "ok" if jetzt - scout_lauf <= 7 * 3600 else \
    "achtung" if jetzt - scout_lauf <= 13 * 3600 else "kaputt"
kaputt = [b for b, s in status.items() if s == "kaputt"] + (["Scout"] if scout_status == "kaputt" else [])
if kaputt:
    st.error(f"**{', '.join(kaputt)}: keine neuen Daten.** Details unter Betrieb.", icon=":material/error:")
with st.container(horizontal=True, gap="small"):
    for bot, s in status.items():
        ansicht.status_badge(s, f"· {bot} · Daten {ansicht.vor(letzte[bot])}")
    ansicht.status_badge(scout_status, f"· Scout · letzter Lauf {ansicht.vor(scout_lauf)}")

# ---------------------------------------------------------------- Grosse Zahlen
haupt = next(k for k in konten if k["key"] == "hauptstrategie")
kontrolle = next(k for k in konten if k["key"] == rechnung.KONTROLLE)
aktiv = [c for c in copy if c["aktiv"]]
copy_summe = sum(c["ergebnis_runde"] for c in aktiv)
im_plus = sum(1 for c in aktiv if c["ergebnis_runde"] > 0)

with st.container(horizontal=True):
    ansicht.sol_metric("Hauptstrategie", haupt["kontowert"], haupt["ergebnis"],
                       hilfe="Kontowert = frei + offene Positionen zum letzten Kurs (SOL-Kurs vom Kauf). "
                             "Plus/Minus gegenüber 10 SOL.")
    ansicht.sol_metric("Kontrollgruppe", kontrolle["kontowert"], kontrolle["ergebnis"],
                       hilfe="Zufällige Käufe ohne Filter – der Maßstab für alle Experimente.")
    ansicht.sol_metric(f"Copy: {len(aktiv)} Trader zusammen", len(aktiv) * rechnung.START_SOL + copy_summe,
                       copy_summe, hilfe=f"Summe der Kontowerte der laufenden Runden. Start: {len(aktiv)} × 10 SOL "
                                         f"= {len(aktiv) * 10} SOL.")
    st.metric("Copy-Trader im Plus", f"{im_plus} von {len(aktiv)}", border=True,
              help="Kontowert der laufenden Runde über 10 SOL.")

# ---------------------------------------------------------------- Gut / schlecht
alle = [(k["label"], k["ergebnis"], "Strategie") for k in konten] + \
       [(f"Copy {c['name']}", c["ergebnis_runde"], "Copy") for c in aktiv]
alle.sort(key=lambda x: -x[1])
gut, schlecht = st.columns(2)
with gut.container(border=True):
    st.markdown("**:material/trending_up: Läuft gut**")
    for name, erg, _ in [a for a in alle if a[1] > 0][:4] or [("Noch nichts im Plus", None, "")]:
        st.markdown(f"{name} · {ansicht.plusminus(erg)}" if erg is not None else name)
with schlecht.container(border=True):
    st.markdown("**:material/trending_down: Läuft schlecht**")
    for name, erg, _ in [a for a in reversed(alle) if a[1] < 0][:4] or [("Nichts im Minus", None, "")]:
        st.markdown(f"{name} · {ansicht.plusminus(erg)}" if erg is not None else name)

# ---------------------------------------------------------------- Konten und Testregeln
st.subheader("Hauptstrategie und Experimente", anchor=False)
st.caption("Testregel: Urteil frühestens nach 200 Trades, gegen die Kontrollgruppe aus demselben Zeitraum, "
           "und nur, wenn es auch ohne die 3 besten Trades hält.")
tabelle = pd.DataFrame([{
    "Konto": k["label"],
    "Plus/Minus": ansicht.plusminus(k["ergebnis"]),
    "Testurteil": ansicht.ampel_text(k["vergleich"]),
    "Kontowert": k["kontowert"],
    "Trades": k["trades"],
    "SOL je Trade": k["pro_trade"],
    "ohne 3 beste": k["ohne_beste_pro_trade"],
    "bis 200 Trades": k["fortschritt"],
    "offen": len(k["offen"]),
} for k in konten])
st.dataframe(tabelle, hide_index=True, alt="Alle Konten mit Testurteil", column_config={
    "Kontowert": st.column_config.NumberColumn(format="%.2f SOL"),
    "SOL je Trade": st.column_config.NumberColumn(format="%+.4f", help="Summe der Ergebnisse / Trades"),
    "ohne 3 beste": st.column_config.NumberColumn(format="%+.4f", help="SOL je Trade ohne die 3 besten Trades"),
    "bis 200 Trades": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
    "Plus/Minus": st.column_config.TextColumn(help="Kontowert minus 10 SOL Start (▲ Plus, ▼ Minus)"),
})

with st.container(border=True):
    st.markdown("**SOL je Trade** · graue Linie = Kontrollgruppe")
    df = pd.DataFrame([{"Konto": k["label"], "pro_trade": k["pro_trade"] or 0.0} for k in konten if k["trades"]])
    if len(df):
        st.altair_chart(ansicht.balken(df, "pro_trade", "Konto", "SOL je Trade", stellen=4,
                                       referenz=kontrolle["pro_trade"], referenz_text="Kontrollgruppe"),
                        alt="SOL je Trade je Konto, Kontrollgruppe als Linie")
    else:
        st.caption("Noch keine geschlossenen Trades.")
    st.caption("Einzelne Konten, Kontoverlauf, offene Positionen und letzte Trades: Seite "
               "„Strategie & Experimente“.")

st.page_link("app_pages/copy_trading.py", label="Copy Trading im Detail", icon=":material/arrow_forward:")
