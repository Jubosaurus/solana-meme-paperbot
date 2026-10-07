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

a.seitenkopf("Strategie & Experimente", "Konten, Testurteile und Trades der Hauptstrategie und Experimente, roh und mit Kosten.")
wahl = st.segmented_control("Konto", options=list(nach_key), default="hauptstrategie",
                            format_func=lambda key: nach_key[key]["label"], key="konto", required=True,
                            bind="query-params", label_visibility="collapsed")
k = nach_key[wahl or "hauptstrategie"]
v = k["vergleich"]

# ---------------------------------------------------------------- Kopf: grosse Zahlen
a.raster([
    a.konto_karte(k, fuss=a.sparkline([p["kontostand"] for p in k["verlauf"]][-80:]), leuchten=True),
    a.karte("Fortschritt bis zum Urteil", f"{k['trades']}", f"von {rechnung.ZIEL_TRADES} Trades",
            a.ring(k["fortschritt"], f"{k['fortschritt']:.0%}")),
    a.roh_kosten_karte("SOL je Trade",
                      a.plusminus(k["pro_trade"], 4, "") if k["trades"] else "–",
                      a.plusminus(k["pro_trade_kosten"], 4, "") if k["trades"] else "–",
                      "ohne die 3 besten: " + a.pm_html(k["ohne_beste_pro_trade"], 4, ""),
                      "ohne die 3 besten: " + a.pm_html(k["ohne_beste_pro_trade_kosten"], 4, ""),
                      kosten_pct=k["kosten_pct"]),
    a.karte("Gewinner", f"{k['gewinner']} von {k['trades']}" if k["trades"] else "–",
            f"Trefferquote {k['gewinner'] / k['trades']:.0%}" if k["trades"] else ""),
], gross=True)

# ---------------------------------------------------------------- Testurteil
with st.container():
    st.subheader("Testurteil", anchor=False)
    if v["ampel"] not in ("basis", "keine_daten"):
        st.caption(f"Gleicher Zeitraum wie die Kontrollgruppe, ab {rechnung.zeit_text(v['beginn'])}")
    st.html(a.urteil_chip(v))
    if v["ampel"] not in ("basis", "keine_daten"):
        e, kg = v["eigen"], v["kontrolle"]
        a.tabelle(pd.DataFrame([
            {"": k["label"], "Trades": e["trades"], "SOL je Trade": e["pro_trade"],
             "je Trade mit Kosten": e["pro_trade_kosten"],
             "ohne 3 beste": e["ohne_beste_pro_trade"], "ohne 3 beste mit Kosten": e["ohne_beste_pro_trade_kosten"],
             "Summe": e["summe"], "Summe mit Kosten": e["summe_kosten"]},
            {"": "Kontrollgruppe (Zufall)", "Trades": kg["trades"], "SOL je Trade": kg["pro_trade"],
             "je Trade mit Kosten": kg["pro_trade_kosten"],
             "ohne 3 beste": kg["ohne_beste_pro_trade"], "ohne 3 beste mit Kosten": kg["ohne_beste_pro_trade_kosten"],
             "Summe": kg["summe"], "Summe mit Kosten": kg["summe_kosten"]},
        ]), zahlen={"Trades": (0, False, "")}, pm_spalten={
            **{c: (4, "") for c in ("SOL je Trade", "je Trade mit Kosten", "ohne 3 beste", "ohne 3 beste mit Kosten")},
            "Summe": (3, " SOL"), "Summe mit Kosten": (3, " SOL"),
        })
        st.caption(f"Kostenaufschlag: {rechnung.KOSTEN_PCT:.0f} % vom Einsatz je Rundlauf, Endspurt-Konten "
                   f"{rechnung.KOSTEN_ENDSPURT_PCT:.0f} % (Schätzung aus der Messung, nicht gemessen: Sandwich-Angriffe, "
                   "gescheiterte Transaktionen).")
        st.caption("„Besser als Zufall“ heißt: mehr SOL je Trade als die Kontrollgruppe im selben Zeitraum, mit und "
                   "ohne die 3 besten Trades. „Im Plus/Minus“ ist die Summe dieser Trades – beides kann auseinanderfallen.")
    elif v["ampel"] == "basis":
        st.caption("Die Kontrollgruppe kauft zufällig ohne Filter. Sie ist der Maßstab für alle anderen Konten.")
    else:
        a.leer("Noch kein Vergleich möglich", "Beide Konten brauchen abgeschlossene Trades im selben Zeitraum.")

# ---------------------------------------------------------------- Paar-Experimente: Coin fuer Coin
if k["key"] in rechnung.PAAR_EXPERIMENTE:
    pv = rechnung.paarvergleich(k["closed"], nach_key["hauptstrategie"]["closed"])
    with st.container():
        st.subheader("Coin für Coin gegen die Hauptstrategie", anchor=False)
        st.caption(f"Gleiche Käufe, {pv['anzahl']} Paare abgeschlossen")
        if pv["anzahl"]:
            st.markdown(f"Unterschied gesamt {a.pm_html(pv['differenz'])} · ohne die 3 besten "
                        f"{a.pm_html(pv['differenz_ohne_beste'])} · besser {pv['besser']}, schlechter "
                        f"{pv['schlechter']}, gleich {pv['gleich']}", unsafe_allow_html=True)
            a.datentabelle(pd.DataFrame([{
                "Coin": x["symbol"], "Experiment": x["experiment"], "Hauptstrategie": x["haupt"],
                "Unterschied": x["differenz"], "Grund Experiment": x["grund_experiment"],
                "Grund Hauptstrategie": x["grund_haupt"]} for x in pv["paare"]]),
                alt_text="Coin für Coin gegen die Hauptstrategie", pm_spalten={
                    c: (4, "") for c in ("Experiment", "Hauptstrategie", "Unterschied")})
            st.caption("Nur Coins, die beide Konten gekauft und schon verkauft haben (Kauf höchstens 10 min "
                       "auseinander). Positiv = Experiment besser.")
        else:
            a.leer("Noch keine abgeschlossenen Paare", "Beide Konten müssen denselben Coin gekauft und verkauft haben.")

# ---------------------------------------------------------------- Kontoverlauf (gross)
with st.container():
    st.subheader("Kontoverlauf", anchor=False)
    st.caption(f"{k['label']} violett"
               + ("" if k["key"] == rechnung.KONTROLLE else ", Kontrollgruppe grau") + " · gestrichelt = 10 SOL Start")
    eigen = pd.DataFrame(k["verlauf"])
    vgl = pd.DataFrame(kontrolle["verlauf"]) if k["key"] != rechnung.KONTROLLE else None
    if len(eigen) > 1:
        stil.zeigen(a.kontoverlauf(eigen, k["label"], vgl), f"Kontostand {k['label']} über die Zeit")
        st.caption("Stand nach jedem geschlossenen Trade; offene Positionen sind nicht enthalten.")
    else:
        a.leer("Noch kein Kontoverlauf", "Nach den ersten abgeschlossenen Trades erscheint der Verlauf.")

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
        a.leer("Keine offenen Positionen", "Neue Käufe erscheinen hier, solange die Position offen ist.")
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
        a.leer("Noch keine Trades", "Hier erscheinen die 40 neuesten abgeschlossenen Trades.")
