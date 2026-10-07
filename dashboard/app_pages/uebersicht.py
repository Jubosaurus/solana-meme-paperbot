import time

import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung
import stil

jetzt = time.time()
head = daten.stand()
konten = daten.strategie_konten(head)
copy, _, _ = daten.copy_konten(head)
commits, _, _ = daten.betrieb(head)
_, scout_lauf = daten.scout(head)

a.seitenkopf("Übersicht", "Läuft alles, wie stehen die Konten, was ist neu? Zahlen roh und mit Kostenaufschlag (2 %, Endspurt 4 %).")

# ---------------------------------------------------------------- 1. Laeuft alles? (Pillen stehen im Seitenkopf)
letzte = {bot: (t[-1] if t else None) for bot, t in commits.items()}
status = {bot: rechnung.bot_status(ts, jetzt) for bot, ts in letzte.items()}
scout_status = "kaputt" if scout_lauf is None else "ok" if jetzt - scout_lauf <= 7 * 3600 else \
    "achtung" if jetzt - scout_lauf <= 13 * 3600 else "kaputt"
kaputt = [b for b, s in status.items() if s == "kaputt"] + (["Scout"] if scout_status == "kaputt" else [])
if kaputt:
    a.fehler(f"{', '.join(kaputt)}: keine neuen Daten.", "Details unter System → Betrieb.")

# ---------------------------------------------------------------- 1a. Fuer dich wichtig (News)
with st.container():
    st.subheader("Für dich wichtig", anchor=False)
    try:
        news = daten.news(head)
        wichtig = [i for i in news["liste"] if set(i["marken"]) & {"position", "listing", "rug"}
                   and jetzt - i["zeit"] <= 48 * 3600][:5]
    except Exception:
        news, wichtig = None, []
    if wichtig:
        a.news_liste(wichtig, scroll=False)
    elif news is None or len(news["fehler"]) >= news["feeds"]:
        st.caption("Nachrichten gerade nicht erreichbar.")
    else:
        st.caption("Nichts Wichtiges zu deinen Coins, Listings oder Hacks in den letzten 48 Stunden.")
    st.page_link("app_pages/news.py", label="Alle News", icon=":material/newspaper:")

# ---------------------------------------------------------------- 1b. Was ist neu
ZEITRAEUME = {"24 Stunden": 24, "48 Stunden": 48, "7 Tage": 168}
with st.container():
    st.subheader("Was ist neu?", anchor=False)
    wahl_zeit = st.segmented_control("Zeitraum", list(ZEITRAEUME), default="24 Stunden", key="neu_zeitraum",
                                     required=True, label_visibility="collapsed")
    neu = daten.neu_seit(head, ZEITRAEUME[wahl_zeit or "24 Stunden"])
    zeilen = []
    if neu["trades"]:
        gesamt = sum(t["trades"] for t in neu["trades"])
        zeilen.append(("Trades", f"{gesamt} neue Trades der Strategien: " + ", ".join(
            f"{a.e(t['konto'])} {t['trades']} ({a.pm_html(t['summe'], 2)})" for t in neu["trades"])))
    if neu["copy"]:
        k = sum(v["KAUF"] for v in neu["copy"].values())
        vk = sum(v["VERKAUF"] for v in neu["copy"].values())
        top = sorted(neu["copy"].items(), key=lambda x: -(x[1]["KAUF"] + x[1]["VERKAUF"]))[:3]
        zeilen.append(("Copy", f"{k} Käufe und {vk} Verkäufe bei {len(neu['copy'])} Tradern; am aktivsten: "
                       + ", ".join(f"{a.e(n)} ({v['KAUF']}/{v['VERKAUF']})" for n, v in top)))
    w = neu["wallets"]
    if w["aufgenommen"]:
        zeilen.append(("Wallets", "Neu im Copy Trading: " + a.e(", ".join(w["aufgenommen"]))))
    for text in w["entfernt"]:
        zeilen.append(("Wallets", "Entfernt: " + a.e(text)))
    if w["geprueft_neu"]:
        zeilen.append(("Prüfliste", f"{w['geprueft_neu']} neue Adresse(n) zur Prüfung"))
    heute = neu["beendete_experimente"]
    if heute:
        zeilen.append(("Experimente beendet", ", ".join(f"{a.e(n)} ({a.e(d)})" for n, d in heute)))
    for text in neu["auffaellig"]:
        zeilen.append(("Auffällig", a.e(text)))
    for ts, text in neu["commits"][:8]:
        zeilen.append((rechnung.zeit_text(ts, mit_datum=True).split(" UTC")[0] + " UTC", a.e(text)))
    if zeilen:
        a.ereignisse(zeilen)
    else:
        st.caption("Nichts Neues in diesem Zeitraum.")
    st.caption("Die Zeilen mit Uhrzeit sind Änderungen am Projekt (Code, Regeln, Doku), nicht die Daten-Updates "
               "der Bots.")

# ---------------------------------------------------------------- 2. Grosse Zahlen
haupt = next(k for k in konten if k["key"] == "hauptstrategie")
kontrolle = next(k for k in konten if k["key"] == rechnung.KONTROLLE)
copy_gesamt = sum(c["ergebnis_seit_start"] for c in copy)
bester = max(copy, key=lambda c: c["ergebnis_seit_start"]) if copy else None
ohne_besten = copy_gesamt - (bester["ergebnis_seit_start"] if bester else 0.0)
aktiv = [c for c in copy if c["aktiv"]]
runde_summe = sum(c["ergebnis_runde"] for c in aktiv)


def verlauf_werte(k):
    return [p["kontostand"] for p in k["verlauf"]][-60:]


a.raster([
    a.konto_karte(haupt, fuss=a.sparkline(verlauf_werte(haupt)), leuchten=True),
    a.konto_karte(kontrolle, fuss=a.sparkline(verlauf_werte(kontrolle))),
], breit=True)
st.write("")
a.raster([
    a.karte("Copy seit Start", rechnung.sol_text(copy_gesamt, 2),
            f"alle Runden, {len(copy)} Wallets inkl. entfernte<br>laufende Runden: {a.pm_html(runde_summe, 2)}",
            oben_rechts=a.chip(f"{sum(1 for c in aktiv if c['ergebnis_runde'] > 0)}/{len(aktiv)} im Plus")),
    a.karte("Copy ohne besten Trader", rechnung.sol_text(ohne_besten, 2),
            f"ohne {a.e(bester['name'])} ({a.pm_html(bester['ergebnis_seit_start'], 2)})" if bester else ""),
], gross=True)

# ---------------------------------------------------------------- 3. Ausreisser
for name, wert, anteil in rechnung.ausreisser([(c["name"], c["ergebnis_seit_start"]) for c in copy]):
    a.hinweis(a.ausreisser_text(name, wert, anteil, copy_gesamt, "im Copy Trading"))
strategie_gesamt = sum(k["ergebnis"] for k in konten)
for name, wert, anteil in rechnung.ausreisser([(k["label"], k["ergebnis"]) for k in konten]):
    a.hinweis(a.ausreisser_text(name, wert, anteil, strategie_gesamt, "bei den Strategien"))

# ---------------------------------------------------------------- 4. Gut / schlecht
alle = [(k["label"], k["ergebnis"], "Strategie") for k in konten] + \
       [(f"Copy {c['name']}", c["ergebnis_seit_start"], "Copy, seit Start") for c in copy if c["aktiv"]]
alle.sort(key=lambda x: -x[1])
gut, schlecht = st.columns(2)
with gut:
    st.markdown("**Läuft gut**")
    a.protokoll([{"name": n, "detail": art, "wert": w} for n, w, art in alle if w > 0][:4] or
                [{"name": "noch nichts im Plus", "detail": "", "wert": None}], scroll=False)
with schlecht:
    st.markdown("**Läuft schlecht**")
    a.protokoll([{"name": n, "detail": art, "wert": w} for n, w, art in reversed(alle) if w < 0][:4] or
                [{"name": "nichts im Minus", "detail": "", "wert": None}], scroll=False)

# ---------------------------------------------------------------- 5. Konten mit Testurteil
st.subheader("Hauptstrategie und Experimente", anchor=False)
st.caption("Urteil: verglichen mit der Kontrollgruppe (kauft zufällig) aus demselben Zeitraum, frühestens nach "
           "200 Trades und nur, wenn es auch ohne die 3 besten Trades hält. „Im Plus/Minus“ getrennt davon.")
a.raster([a.roh_kosten_karte(
    k["label"], rechnung.sol_text(k["kontowert"], 2, False), rechnung.sol_text(rechnung.kontowert_mit_kosten(k), 2, False),
    a.pm_html(k["ergebnis"]), a.pm_html(rechnung.ergebnis_mit_kosten(k)), kosten_pct=k["kosten_pct"],
    fuss='<div class="pb-zeile"><div>' + a.urteil_chip(k["vergleich"]) + f'<div class="pb-unter">{k["trades"]}/200 Trades</div></div>'
         + a.ring(k["fortschritt"], f"{k['fortschritt']:.0%}", f"{k['trades']}/200") + "</div>" + a.sparkline([p["kontostand"] for p in k["verlauf"]][-60:]))
          for k in konten], breit=True)

st.write("")
with st.expander("Alle Kennzahlen als Tabelle", icon=":material/table_chart:", expanded=True):
    tab = pd.DataFrame([{
        "Konto": k["label"],
        "Plus/Minus roh": k["ergebnis"], "Plus/Minus mit Kosten": rechnung.ergebnis_mit_kosten(k),
        "Kontowert roh": k["kontowert"], "Kontowert mit Kosten": rechnung.kontowert_mit_kosten(k),
        "Trades": k["trades"], "offen": len(k["offen"]),
        "SOL je Trade roh": k["pro_trade"], "SOL je Trade mit Kosten": k["pro_trade_kosten"],
        "ohne 3 beste roh": k["ohne_beste_pro_trade"], "ohne 3 beste mit Kosten": k["ohne_beste_pro_trade_kosten"],
        "Urteil roh": a.urteil_roh(k["vergleich"]),
        "Urteil mit Kosten": a.urteil_mit_kosten(k["vergleich"]),
    } for k in konten])
    a.tabelle(tab, zahlen={"Kontowert roh": (2, False, " SOL"), "Kontowert mit Kosten": (2, False, " SOL"),
                           "Trades": (0, False, ""), "offen": (0, False, ""),
                           "SOL je Trade roh": (4, True, ""), "SOL je Trade mit Kosten": (4, True, ""),
                           "ohne 3 beste roh": (4, True, ""), "ohne 3 beste mit Kosten": (4, True, "")},
              pm_spalten={"Plus/Minus roh": (3, " SOL"), "Plus/Minus mit Kosten": (3, " SOL")}, hoehe=520)

with st.container(border=True):
    st.markdown("**SOL je Trade** · graue Linie = Kontrollgruppe")
    df = pd.DataFrame([{"Konto": k["label"].split(" (beendet")[0], "pro_trade": k["pro_trade"] or 0.0} for k in konten if k["trades"]])
    if len(df):
        stil.zeigen(a.balken(df, "pro_trade", "Konto", "SOL je Trade", stellen=4, referenz=kontrolle["pro_trade"],
                             referenz_text="Kontrollgruppe"), "SOL je Trade je Konto, Kontrollgruppe als Linie")
    else:
        a.leer("Noch keine geschlossenen Trades", "Sobald die ersten Trades geschlossen sind, erscheint hier der Vergleich.")
