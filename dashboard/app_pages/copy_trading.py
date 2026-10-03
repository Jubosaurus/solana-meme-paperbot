import statistics
import time

import pandas as pd
import streamlit as st

import ansicht
import daten
import rechnung

head = daten.stand()
konten, gespeichert, letzte_zeile = daten.copy_konten(head)
roh = daten.copy_rohdaten(head)
jetzt = time.time()

st.title("Copy Trading", anchor=False)
st.caption(f"Stand der Konten: {rechnung.zeit_text(gespeichert)}. Jede Wallet hat ein eigenes Konto mit 10 SOL je "
           "Runde. Fehlbuchungen bis 03.10. sind herausgerechnet (auswertungen/korrekturen.csv).")

nur_aktiv = st.toggle("Nur aktive Trader", value=True, help="Aktiv = steht in copy_wallets.txt")
liste = [k for k in konten if k["aktiv"] or not nur_aktiv]


def hinweise(k):
    h = []
    if k["wartend"]:
        h.append(f"{k['wartend']} wartet auf Verkauf")
    if k["letzter_trade"] and jetzt - k["letzter_trade"] > 72 * 3600:
        h.append("72 h ohne Trade → ersetzen")
    if k["geschlossen"] >= 30 and k["pnl_geschlossen"] < -1:
        h.append("prüfen: ≥ 30 Positionen, > 1 SOL Verlust")
    if k["korrigiert"]:
        h.append("enthält Korrekturen")
    if not k["aktiv"]:
        h.append("entfernt")
    return ", ".join(h)


# ---------------------------------------------------------------- Kopf
summe = sum(k["ergebnis_runde"] for k in liste)
verz = [k["verzoegerung_median_s"] for k in liste if k["verzoegerung_median_s"] is not None]
wartend = sum(k["wartend"] for k in liste)
with st.container(horizontal=True):
    ansicht.sol_metric("Plus/Minus laufende Runden", len(liste) * rechnung.START_SOL + summe, summe,
                       hilfe="Summe der Kontowerte aller gezeigten Trader; Plus/Minus gegenüber je 10 SOL.")
    st.metric("Trader im Plus", f"{sum(1 for k in liste if k['ergebnis_runde'] > 0)} von {len(liste)}", border=True)
    st.metric("Verzögerung beim Kauf", f"{rechnung.zahl(statistics.median(verz), 1)} s" if verz else "–",
              border=True, help="Median über alle Trader: Sekunden zwischen Trader-Kauf und unserem Kauf.")
    st.metric("Warten auf Verkauf", wartend, border=True,
              help="Positionen, bei denen Jupiter beim Verkaufssignal nicht antwortete. Im vorsichtigen "
                   "Kontowert zählen sie mit 0.")

# ---------------------------------------------------------------- Balken
with st.container(border=True):
    st.markdown("**Plus/Minus der laufenden Runde je Trader** (Kontowert − 10 SOL)")
    df = pd.DataFrame([{"Trader": k["name"], "ergebnis": k["ergebnis_runde"]} for k in liste])
    if len(df):
        st.altair_chart(ansicht.balken(df, "ergebnis", "Trader", "SOL", stellen=2),
                        alt="Plus und Minus je Trader in der laufenden Runde")

# ---------------------------------------------------------------- Tabelle
st.subheader("Alle Trader", anchor=False)
tabelle = pd.DataFrame([{
    "Trader": k["name"], "Runde": k["runde"], "Kontowert": k["kontowert"],
    "vorsichtig": k["vorsichtig"], "Plus/Minus": ansicht.plusminus(k["ergebnis_runde"], 2),
    "offen": k["offen"], "geschlossen": k["geschlossen"],
    "wir %": ansicht.txt(k["wir_median_pct"], 1, True), "Trader %": ansicht.txt(k["trader_median_pct"], 1, True),
    "Vergleiche": k["vergleiche"], "Verzögerung s": ansicht.txt(k["verzoegerung_median_s"], 1),
    "Preisabstand %": ansicht.txt(k["preisabstand_median_pct"], 1, True),
    "Schatten": k["schatten"], "Schatten SOL": k["schatten_pnl"],
    "letzter Trade": ansicht.vor(k["letzter_trade"]), "Hinweise": hinweise(k),
} for k in liste])
st.dataframe(tabelle, hide_index=True, alt="Alle Copy-Trader", column_config={
    "Kontowert": st.column_config.NumberColumn(format="%.2f SOL", help="Frei + offene Positionen (wie in Discord)"),
    "vorsichtig": st.column_config.NumberColumn(format="%.2f SOL",
                                                help="Wie Kontowert, aber Positionen, die auf den Verkauf warten, mit 0"),
    "wir %": st.column_config.TextColumn(help="Median unseres Ergebnisses je geschlossener Position "
                                              "(nur Positionen mit gültigem Vergleich)"),
    "Trader %": st.column_config.TextColumn(help="Median des Traders auf denselben Positionen"),
    "Verzögerung s": st.column_config.TextColumn(help="Median beim Kauf, Sekunden nach dem Trader"),
    "Preisabstand %": st.column_config.TextColumn(help="Unser Kaufkurs gegenüber dem des Traders (Median, + = teurer)"),
    "Schatten SOL": st.column_config.NumberColumn(format="%+.3f", help="Wegen Preisgrenze nicht gekauft, nur "
                                                                      "verfolgt: Summe der Ergebnisse"),
    "Hinweise": st.column_config.TextColumn(width="large"),
})
st.caption("Wallet-Regeln: 72 h ohne Trade → ersetzen; nach 30 Positionen und mehr als 1 SOL Verlust → prüfen. "
           "Der Bot entscheidet nichts selbst, die Entscheidung triffst du.")

# ---------------------------------------------------------------- Einzelner Trader
st.subheader("Einzelner Trader", anchor=False)
name = st.selectbox("Trader", [k["name"] for k in liste], key="trader", bind="query-params")
acct = (roh.get("wallets") or {}).get(name)
if acct:
    k = next(x for x in liste if x["name"] == name)
    st.caption(f"Adresse {k['adresse']} · Runde {k['runde']} · frei {rechnung.sol_text(k['frei'], 3, False)}")
    offen, zu = st.columns(2)
    with offen.container(border=True):
        st.markdown(f"**Offene Positionen ({len(acct['positionen'])})**")
        if acct["positionen"]:
            st.dataframe(pd.DataFrame([{
                "Coin": p.get("symbol", "?"), "seit": rechnung.dauer_text(jetzt - p["opened"]),
                "Einsatz": p["invested_sol"],
                "Wert jetzt": ansicht.txt(p["tokens_raw"] / 10 ** p["decimals"] * p["letzter_preis_sol"]
                                          if p.get("letzter_preis_sol") is not None else None, 3, einheit=" SOL"),
                "Verkauf wartet": bool(p.get("verkauf_offen")),
            } for p in acct["positionen"].values()]), hide_index=True, alt="Offene Positionen des Traders",
                column_config={"Einsatz": st.column_config.NumberColumn(format="%.2f SOL")})
        else:
            st.caption("Keine.")
    with zu.container(border=True):
        geschlossen = sorted(acct.get("geschlossen") or [], key=lambda g: g.get("geschlossen") or "", reverse=True)
        st.markdown(f"**Geschlossene Positionen ({len(geschlossen)})** · die 20 neuesten")
        if geschlossen:
            st.dataframe(pd.DataFrame([{
                "geschlossen": rechnung.zeit_text(g.get("geschlossen")), "Coin": g.get("symbol", "?"),
                "wir": ansicht.plusminus(g.get("pnl_sol")), "wir %": ansicht.txt(g.get("pnl_pct"), 1, True),
                "Trader %": ansicht.txt(g.get("trader_pnl_pct"), 1, True), "Grund": g.get("grund", ""),
            } for g in geschlossen[:20]]), hide_index=True, alt="Geschlossene Positionen des Traders")
        else:
            st.caption("Keine.")
