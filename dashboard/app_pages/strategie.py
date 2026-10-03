import time

import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung
import stil

konten = daten.strategie_konten(daten.stand())
nach_key = {k["key"]: k for k in konten}
kontrolle = nach_key[rechnung.KONTROLLE]
jetzt = time.time()

st.title("Strategie & Experimente", anchor=False)
wahl = st.segmented_control("Konto", options=list(nach_key), default="hauptstrategie",
                            format_func=lambda key: nach_key[key]["label"], key="konto", required=True,
                            bind="query-params", label_visibility="collapsed")
k = nach_key[wahl or "hauptstrategie"]
v = k["vergleich"]

# ---------------------------------------------------------------- Kopf: grosse Zahlen
a.raster([
    a.karte("Kontowert", rechnung.sol_text(k["kontowert"], 2, False), a.pm_html(k["ergebnis"]) + " seit Start",
            fuss=a.sparkline([p["kontostand"] for p in k["verlauf"]][-80:]), leuchten=True),
    a.karte("Fortschritt bis zum Urteil", f"{k['trades']}", f"von {rechnung.ZIEL_TRADES} Trades",
            a.ring(k["fortschritt"], f"{k['fortschritt']:.0%}")),
    a.karte("SOL je Trade", rechnung.zahl(k["pro_trade"], 4, vorzeichen=True) if k["trades"] else "–",
            "ohne die 3 besten: " + (rechnung.zahl(k["ohne_beste_pro_trade"], 4, vorzeichen=True)
                                     if k["ohne_beste_pro_trade"] is not None else "–")),
    a.karte("Gewinner", f"{k['gewinner']} von {k['trades']}" if k["trades"] else "–",
            f"Trefferquote {k['gewinner'] / k['trades']:.0%}" if k["trades"] else ""),
], gross=True)

# ---------------------------------------------------------------- Testurteil
with st.container(border=True):
    st.markdown("**Testurteil** " + ("" if v["ampel"] in ("basis", "keine_daten") else
                                     f"· gleicher Zeitraum wie die Kontrollgruppe, ab {rechnung.zeit_text(v['beginn'])}"))
    st.html(a.urteil_chip(v))
    if v["ampel"] not in ("basis", "keine_daten"):
        e, kg = v["eigen"], v["kontrolle"]
        st.dataframe(pd.DataFrame([
            {"": k["label"], "Trades": e["trades"], "SOL je Trade": e["pro_trade"],
             "ohne 3 beste": e["ohne_beste_pro_trade"], "Summe": a.plusminus(e["summe"])},
            {"": "Kontrollgruppe (Zufall)", "Trades": kg["trades"], "SOL je Trade": kg["pro_trade"],
             "ohne 3 beste": kg["ohne_beste_pro_trade"], "Summe": a.plusminus(kg["summe"])},
        ]), hide_index=True, alt="Vergleich mit der Kontrollgruppe", column_config={
            "SOL je Trade": st.column_config.NumberColumn(format="%+.4f"),
            "ohne 3 beste": st.column_config.NumberColumn(format="%+.4f"),
        })
        st.caption("„Besser als Zufall“ heißt: mehr SOL je Trade als die Kontrollgruppe im selben Zeitraum, mit und "
                   "ohne die 3 besten Trades. „Im Plus/Minus“ ist die Summe dieser Trades – beides kann auseinanderfallen.")
    elif v["ampel"] == "basis":
        st.caption("Die Kontrollgruppe kauft zufällig ohne Filter. Sie ist der Maßstab für alle anderen Konten.")

# ---------------------------------------------------------------- Kontoverlauf (gross)
with st.container(border=True):
    st.markdown(f"**Kontoverlauf** · {k['label']} violett"
                + ("" if k["key"] == rechnung.KONTROLLE else ", Kontrollgruppe grau") + " · gestrichelt = 10 SOL Start")
    eigen = pd.DataFrame(k["verlauf"])
    vgl = pd.DataFrame(kontrolle["verlauf"]) if k["key"] != rechnung.KONTROLLE else None
    if len(eigen) > 1:
        stil.zeigen(a.kontoverlauf(eigen, k["label"], vgl), f"Kontostand {k['label']} über die Zeit")
        st.caption("Stand nach jedem geschlossenen Trade; offene Positionen sind nicht enthalten.")
    else:
        st.caption("Noch keine abgeschlossenen Trades.")

# ---------------------------------------------------------------- Offene Positionen und letzte Trades
links, rechts = st.columns([2, 3])
with links:
    st.subheader(f"Offen ({len(k['offen'])})", anchor=False)
    if k["offen"]:
        a.protokoll([{
            "name": o["symbol"],
            "detail": (f"{a.txt(o['vielfaches'], 2, einheit='x')} · seit "
                       f"{rechnung.dauer_text(jetzt - o['seit']) if o['seit'] else '–'}"
                       + (" · Hälfte verkauft" if o["haelfte_verkauft"] else "")),
            "wert": o["pnl"],
            "rechts_unten": f"Wert {a.txt(o['wert'], 3, einheit=' SOL')}" if o["wert"] is not None else "kein Kurs",
        } for o in k["offen"]], scroll=False)
    else:
        st.caption("Keine offenen Positionen.")
with rechts:
    st.subheader("Letzte Trades", anchor=False)
    if k["closed"]:
        letzte = sorted(k["closed"], key=lambda c: c.get("closed_at") or "", reverse=True)[:40]
        a.protokoll([{
            "name": f"{c.get('symbol', '?')} · {a.txt(rechnung.as_float(c.get('pnl_pct')), 1, True, ' %')}",
            "detail": c.get("exit_reason", ""),
            "wert": rechnung.as_float(c.get("pnl_sol")),
            "rechts_unten": rechnung.zeit_text(c.get("closed_at")),
        } for c in letzte])
        st.caption("Die 40 neuesten. Zeiten in UTC, in Klammern deutsche Zeit.")
    else:
        st.caption("Noch keine Trades.")
