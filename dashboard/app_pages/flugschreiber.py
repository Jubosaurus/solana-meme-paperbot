import altair as alt
import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung
import stil

rows, coins = daten.flugschreiber(daten.stand())

st.title("Flugschreiber", anchor=False)
st.caption("Für jeden Coin, den ein Konto hält, schreiben die Bots etwa einmal pro Minute auf: Kurs, Dev-Bestand, "
           "Top-10-Anteil, Holder und Liquidität. Hier siehst du den Verlauf bis zum Verkauf – die rote Linie "
           "zeigt, wann und warum verkauft wurde. Ziel: Rug-Muster erkennen.")
if not coins:
    st.info("Noch keine Aufzeichnungen in flugschreiber/.", icon=":material/info:")
    st.stop()


def verkauf_kurz(grund):
    return (grund or "").split(" (")[0].strip() or "Verkauf"


def ist_rug_verdacht(c):
    return (c.get("verkauf_grund") or "").startswith(("NOTBREMSE", "LIQUIDITAET"))


konten = sorted({c["konto"] for c in coins})
with st.container(horizontal=True, vertical_alignment="bottom"):
    konto_wahl = st.selectbox("Konto", ["alle"] + konten, key="flug_konto")
    nur_rug = st.checkbox("Nur Rug-Verdacht (Notbremse oder Liquidität abgezogen)", key="flug_rug")
auswahl = [c for c in coins if konto_wahl in ("alle", c["konto"]) and (not nur_rug or ist_rug_verdacht(c))]
if not auswahl:
    st.caption("Keine Coins für diese Auswahl.")
    st.stop()


def beschriftung(c):
    ende = "offen" if "verkauf_grund" not in c else verkauf_kurz(c["verkauf_grund"])
    return f"{c['symbol']} · {c['konto']} · {c['von'][5:16]} UTC · {c['punkte']} Punkte · {ende}"


c = st.selectbox("Coin", auswahl, format_func=beschriftung, key="flug_coin")
verlauf = pd.DataFrame(rechnung.flug_verlauf(rows, c["konto"], c["mint"]))
verkaeufe = pd.DataFrame(rechnung.flug_verkaeufe(c["konto"], c["mint"]), columns=["minuten", "grund", "pnl_pct"])
verkaeufe["kurz"] = verkaeufe["grund"].map(verkauf_kurz)
verkaeufe["pnl_text"] = verkaeufe["pnl_pct"].map(lambda v: "" if pd.isna(v) else rechnung.zahl(v, 1, True) + " %")


def start_ende(feld):
    s = verlauf[feld].dropna()
    return (s.iloc[0], s.iloc[-1]) if len(s) else (None, None)


# ---------------------------------------------------------------- Kopf
dev0, dev1 = start_ende("dev_pct")
liq0, liq1 = start_ende("liquiditaet")
hol0, hol1 = start_ende("holder")
top0, top1 = start_ende("top10_pct")


def von_bis(v0, v1, stellen=1, einheit=""):
    if v0 is None:
        return "–"
    return f"{rechnung.zahl(v0, stellen)} → {rechnung.zahl(v1, stellen)}{einheit}"


def aenderung(v0, v1):
    return None if not v0 or v1 is None else (v1 / v0 - 1) * 100


liq_aend = aenderung(liq0, liq1)
grund = c.get("verkauf_grund")
a.raster([
    a.karte("Verkauf", a.e(verkauf_kurz(grund)) if grund else "noch offen",
            a.pm_html(c["pnl_sol"]) if "pnl_sol" in c else "",
            oben_rechts=a.chip("Rug-Verdacht", "schlecht") if ist_rug_verdacht(c) else "", klein=True),
    a.karte("Dev-Bestand", von_bis(dev0, dev1, 1, " %"), "Start → letzter Messpunkt", klein=True),
    a.karte("Liquidität", von_bis(liq0, liq1, 0, " $"),
            a.pm_html(liq_aend, 0, " %") if liq_aend is not None else "", klein=True),
    a.karte("Holder · Top 10", f"{von_bis(hol0, hol1, 0)}", f"Top-10-Anteil {von_bis(top0, top1, 1, ' %')}", klein=True),
])

# ---------------------------------------------------------------- Diagramme
PANELS = [("vielfaches", "Kurs (Vielfaches vom Kaufpreis)", 1.0), ("dev_pct", "Dev-Bestand %", None),
          ("top10_pct", "Top-10-Anteil %", None), ("holder", "Holder", None), ("liquiditaet", "Liquidität $", None),
          ("block0_gehalten_pct", "Block-0-Käufer halten %", None), ("netto_kaeufer_5m", "Netto-Käufer 5 min", 0.0)]
lagen = []
vorhanden = [p for p in PANELS if verlauf[p[0]].notna().any()]
for i, (feld, titel, referenz) in enumerate(vorhanden):
    d = verlauf.dropna(subset=[feld])
    letzte = i == len(vorhanden) - 1
    x = alt.X("minuten_seit_kauf:Q", title="Minuten seit Kauf" if letzte else None, axis=alt.Axis(tickCount=8))
    linie = alt.Chart(d).mark_line(color=stil.VIOLETT, strokeWidth=2, interpolate="step-after").encode(
        x=x, y=alt.Y(f"{feld}:Q", title=titel, scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("minuten_seit_kauf:Q", title="Minute", format=".1f"),
                 alt.Tooltip(f"{feld}:Q", title=titel, format=",.2f")])
    teile = [linie]
    if referenz is not None:
        teile.append(alt.Chart(pd.DataFrame({"y": [referenz]})).mark_rule(
            color=stil.TEXT_LEISE, strokeDash=[4, 4]).encode(y="y:Q"))
    if len(verkaeufe):
        teile.append(alt.Chart(verkaeufe).mark_rule(color=stil.MINUS, strokeWidth=2, strokeDash=[6, 3]).encode(
            x="minuten:Q", tooltip=[alt.Tooltip("grund:N", title="Verkaufsgrund"),
                                    alt.Tooltip("pnl_text:N", title="Ergebnis")]))
        if i == 0:
            teile.append(alt.Chart(verkaeufe).mark_text(align="right", dx=-5, baseline="top", color=stil.MINUS,
                                                        fontSize=12).encode(
                x="minuten:Q", y=alt.value(4), text="kurz:N"))
    lagen.append(alt.layer(*teile).properties(height=110, width="container"))
stil.zeigen(alt.vconcat(*lagen).resolve_scale(x="shared"), f"Flugschreiber von {c['symbol']}")
st.caption("Rote gestrichelte Linie = Verkauf (Grund oben, Details beim Darüberfahren). Teilverkäufe haben je eine Linie. "
           "Fehlende Linien: Der Wert wurde für diesen Coin nicht aufgezeichnet.")
if not len(verkaeufe):
    st.caption("Der Coin wurde noch nicht verkauft oder das Journal kennt keinen Verkauf.")
