import statistics
import time

import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung
import stil

head = daten.stand()
konten, gespeichert, _ = daten.copy_konten(head)
roh = daten.copy_rohdaten(head)
jetzt = time.time()

st.title("Copy Trading", anchor=False)
st.caption(f"Stand der Konten: {rechnung.zeit_text(gespeichert)}. Jede Wallet hat ein eigenes Konto mit 10 SOL je "
           "Runde. Fehlbuchungen bis 03.10. sind herausgerechnet (auswertungen/korrekturen.csv).")

nur_aktiv = st.toggle("Nur aktive Trader", value=False,
                      help="Aus: alle Wallets seit Start, auch entfernte (ehrliches Gesamtergebnis). "
                           "An: nur Wallets aus copy_wallets.txt.")
liste = [k for k in konten if k["aktiv"] or not nur_aktiv]


def hinweise(k):
    h = []
    if k["wartend"]:
        h.append(f"{k['wartend']} wartet auf Verkauf")
    if k["aktiv"] and k["letzter_trade"] and jetzt - k["letzter_trade"] > 72 * 3600:
        h.append("72 h ohne Trade → ersetzen")
    if k["geschlossen"] >= 30 and k["pnl_geschlossen"] < -1:
        h.append("prüfen: ≥ 30 Positionen, > 1 SOL Verlust")
    if k["runde"] > 1:
        h.append(f"{k['runde'] - 1}× Konto aufgebraucht")
    if k["korrigiert"]:
        h.append("enthält Korrekturen")
    if not k["aktiv"]:
        h.append("entfernt")
    return ", ".join(h)


# ---------------------------------------------------------------- Kopf
gesamt = sum(k["ergebnis_seit_start"] for k in liste)
vorsichtig = sum(k["ergebnis_seit_start_vorsichtig"] for k in liste)
bester = max(liste, key=lambda k: k["ergebnis_seit_start"]) if liste else None
runde = sum(k["ergebnis_runde"] for k in liste if k["aktiv"])
verz = [k["verzoegerung_median_s"] for k in liste if k["verzoegerung_median_s"] is not None]
a.raster([
    a.karte("Ergebnis seit Start (alle Runden)", rechnung.sol_text(gesamt, 2),
            f"{len(liste)} Wallets" + (f" · vorsichtig {a.pm_html(vorsichtig, 2)}" if abs(vorsichtig - gesamt) > 0.005
                                      else ""), leuchten=True),
    a.karte("Ohne besten Trader", rechnung.sol_text(gesamt - bester["ergebnis_seit_start"], 2) if bester else "–",
            f"ohne {a.e(bester['name'])}" if bester else ""),
    a.karte("Laufende Runden (aktive)", rechnung.sol_text(runde, 2),
            f"{sum(1 for k in liste if k['aktiv'] and k['ergebnis_runde'] > 0)} von "
            f"{sum(1 for k in liste if k['aktiv'])} im Plus"),
    a.karte("Verzögerung beim Kauf", f"{rechnung.zahl(statistics.median(verz), 1)} s" if verz else "–",
            "Median nach dem Trader"),
], gross=True)

for name, wert, anteil in rechnung.ausreisser([(k["name"], k["ergebnis_seit_start"]) for k in liste]):
    a.hinweis(a.ausreisser_text(name, wert, anteil, gesamt, "im Copy Trading"))

# ---------------------------------------------------------------- Balken
with st.container(border=True):
    st.markdown("**Ergebnis seit Start je Trader** (alle Runden)")
    mit = [k for k in liste if abs(k["ergebnis_seit_start"]) >= 0.005]
    df = pd.DataFrame([{"Trader": k["name"], "ergebnis": k["ergebnis_seit_start"]} for k in mit])
    if len(df):
        stil.zeigen(a.balken(df, "ergebnis", "Trader", "SOL", stellen=2), "Ergebnis seit Start je Trader")
    if len(liste) > len(mit):
        st.caption(f"{len(liste) - len(mit)} Wallets ohne Ergebnis (noch kein Trade) ausgeblendet; sie stehen in der Tabelle.")

# ---------------------------------------------------------------- Tabelle
st.subheader("Alle Trader", anchor=False)
st.dataframe(pd.DataFrame([{
    "Trader": k["name"], "seit Start": a.plusminus(k["ergebnis_seit_start"], 2),
    "laufende Runde": a.plusminus(k["ergebnis_runde"], 2), "Runde": k["runde"], "Kontowert": k["kontowert"],
    "vorsichtig": k["vorsichtig"], "offen": k["offen"], "geschlossen": k["geschlossen"],
    "wir %": a.txt(k["wir_median_pct"], 1, True), "Trader %": a.txt(k["trader_median_pct"], 1, True),
    "Verzögerung s": a.txt(k["verzoegerung_median_s"], 1), "Preisabstand %": a.txt(k["preisabstand_median_pct"], 1, True),
    "Schatten": k["schatten"], "Schatten SOL": a.plusminus(k["schatten_pnl"]),
    "Trader raus ≤ 60 s": a.txt(k["exit_liq"]["raus_60s"] / k["exit_liq"]["kaeufe"] * 100, 0, einheit=" %")
    if k.get("exit_liq") and k["exit_liq"]["kaeufe"] else "–",
    "raus vor uns": a.txt(k["exit_liq"]["raus_vor_uns"] / k["exit_liq"]["kaeufe"] * 100, 0, einheit=" %")
    if k.get("exit_liq") and k["exit_liq"]["kaeufe"] else "–",
    "letzter Trade": a.vor(k["letzter_trade"]), "Hinweise": hinweise(k),
} for k in liste]), hide_index=True, alt="Alle Copy-Trader", column_config={
    "seit Start": st.column_config.TextColumn(help="Alle Runden: geschlossene Positionen + offene zum letzten Kurs"),
    "laufende Runde": st.column_config.TextColumn(help="Kontowert minus 10 SOL der laufenden Runde"),
    "Kontowert": st.column_config.NumberColumn(format="%.2f SOL", help="Frei + offene Positionen (wie in Discord)"),
    "vorsichtig": st.column_config.NumberColumn(format="%.2f SOL",
                                                help="Wie Kontowert, aber Positionen, die auf den Verkauf warten, mit 0"),
    "wir %": st.column_config.TextColumn(help="Median unseres Ergebnisses je geschlossener Position "
                                              "(nur gültige Vergleiche)"),
    "Trader %": st.column_config.TextColumn(help="Median des Traders auf denselben Positionen"),
    "Verzögerung s": st.column_config.TextColumn(help="Median beim Kauf, Sekunden nach dem Trader"),
    "Preisabstand %": st.column_config.TextColumn(help="Unser Kaufkurs gegenüber dem des Traders (Median, + = teurer)"),
    "Schatten SOL": st.column_config.TextColumn(help="Wegen Preisgrenze nicht gekauft, nur verfolgt"),
    "Trader raus ≤ 60 s": st.column_config.TextColumn(help="Anteil unserer Kaeufe, bei denen der Trader innerhalb von "
                                                           "60 s nach seinem Kauf schon wieder verkauft (Exit-Liquiditaet)"),
    "raus vor uns": st.column_config.TextColumn(help="Anteil, bei dem der Trader schon verkauft hatte, bevor unser "
                                                     "Kauf ausgefuehrt war – dann kaufen wir seine Ware"),
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
    a.raster([
        a.karte("Seit Start", rechnung.sol_text(k["ergebnis_seit_start"], 2), f"Runde {k['runde']}", klein=True),
        a.karte("Kontowert jetzt", rechnung.sol_text(k["kontowert"], 2, False),
                f"frei {rechnung.sol_text(k['frei'], 2, False)}", klein=True),
        a.karte("Wir gegen Trader", f"{a.txt(k['wir_median_pct'], 1, True)} % / {a.txt(k['trader_median_pct'], 1, True)} %",
                f"Median je Position, {k['vergleiche']} Vergleiche", klein=True),
    ])
    st.caption(f"Adresse {k['adresse']}")
    links, rechts = st.columns(2)
    with links:
        st.markdown(f"**Offen ({len(acct['positionen'])})**")
        if acct["positionen"]:
            eintraege = []
            for p in acct["positionen"].values():
                w = p["tokens_raw"] / 10 ** p["decimals"] * p["letzter_preis_sol"] \
                    if p.get("letzter_preis_sol") is not None else None
                eintraege.append({"name": p.get("symbol", "?"),
                                  "detail": f"Einsatz {rechnung.sol_text(p['invested_sol'], 2, False)} · seit "
                                            f"{rechnung.dauer_text(jetzt - p['opened'])}"
                                            + (" · Verkauf wartet" if p.get("verkauf_offen") else ""),
                                  "wert": (w + p["proceeds_sol"] - p["invested_sol"] - p.get("fees_sol", 0))
                                  if w is not None else None,
                                  "rechts_unten": f"Wert {a.txt(w, 3, einheit=' SOL')}"})
            a.protokoll(eintraege)
        else:
            st.caption("Keine.")
    with rechts:
        geschlossen = sorted(acct.get("geschlossen") or [], key=lambda g: g.get("geschlossen") or "", reverse=True)
        st.markdown(f"**Geschlossen ({len(geschlossen)})** · die 40 neuesten")
        if geschlossen:
            a.protokoll([{
                "name": f"{g.get('symbol', '?')} · wir {a.txt(g.get('pnl_pct'), 1, True, ' %')}",
                "detail": f"Trader {a.txt(g.get('trader_pnl_pct'), 1, True, ' %')} · {g.get('grund', '')}",
                "wert": rechnung.as_float(g.get("pnl_sol")),
                "rechts_unten": rechnung.zeit_text(g.get("geschlossen")),
            } for g in geschlossen[:40]])
        else:
            st.caption("Keine.")
