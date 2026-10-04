import time

import pandas as pd
import streamlit as st

import ansicht
import daten
import rechnung

head = daten.stand()
commits, messung, n_korrekturen = daten.betrieb(head)
konten = daten.strategie_konten(head)
_, copy_gespeichert, copy_letzte_zeile = daten.copy_konten(head)
_, scout_lauf = daten.scout(head)
jetzt = time.time()
GRENZE_MIN = 20

st.title("Betrieb", anchor=False)
st.caption("Die Bots speichern etwa jede Minute. Eine Lücke über 20 min heißt: In der Zeit kamen keine neuen Daten "
           "(Schichtwechsel, Absturz oder GitHub hat einen Lauf verzögert).")

# ---------------------------------------------------------------- Zustand je Bot
haupt = next(k for k in konten if k["key"] == "hauptstrategie")
zeilen = []
for bot, zeiten in commits.items():
    letzte = zeiten[-1] if zeiten else None
    l = rechnung.luecken(zeiten, GRENZE_MIN, jetzt)
    zeilen.append({"bot": bot, "status": rechnung.bot_status(letzte, jetzt), "letzte": letzte, "luecken": l})
scout_status = "kaputt" if scout_lauf is None else "ok" if jetzt - scout_lauf <= 7 * 3600 else \
    "achtung" if jetzt - scout_lauf <= 13 * 3600 else "kaputt"

def status_chip(status):
    klasse, zeichen, wort = ansicht.STATUS[status]
    return ansicht.chip(f"{zeichen} {wort}", klasse)


karten = []
for z in zeilen:
    dauer = sum((b or jetzt) - a for a, b in z["luecken"])
    n = len(z["luecken"])
    karten.append(ansicht.karte(
        z["bot"], f"Daten {ansicht.vor(z['letzte'])}",
        f"{ansicht.e(rechnung.zeit_text(z['letzte']))}<br>{n} {'Lücke' if n == 1 else 'Lücken'} über {GRENZE_MIN} min "
        f"in 48 h" + (f", zusammen {rechnung.dauer_text(dauer)}" if n else ""),
        oben_rechts=status_chip(z["status"]), klein=True))
karten.append(ansicht.karte("Scout", f"Lauf {ansicht.vor(scout_lauf)}",
                            f"{ansicht.e(rechnung.zeit_text(scout_lauf))}<br>läuft alle 6 Stunden",
                            oben_rechts=status_chip(scout_status), klein=True))
ansicht.raster(karten)

# ---------------------------------------------------------------- Luecken
st.subheader("Lücken in den letzten 48 Stunden", anchor=False)
luecken = [{"Bot": z["bot"], "von": rechnung.zeit_text(a), "bis": rechnung.zeit_text(b) if b else "läuft noch",
            "Dauer": rechnung.dauer_text((b or jetzt) - a), "_start": a}
           for z in zeilen for a, b in z["luecken"]]
if luecken:
    df = pd.DataFrame(sorted(luecken, key=lambda x: -x["_start"])).drop(columns="_start")
    st.dataframe(df, hide_index=True, alt="Lücken je Bot")
else:
    st.caption("Keine Lücken über 20 min.")

# ---------------------------------------------------------------- Dateien
st.subheader("Datenstand der Dateien", anchor=False)
st.dataframe(pd.DataFrame([
    {"Datei": "portfolio.json (Hauptbot)", "zuletzt gespeichert": rechnung.zeit_text(haupt["gespeichert"])},
    {"Datei": "copy/konten.json", "zuletzt gespeichert": rechnung.zeit_text(copy_gespeichert)},
    {"Datei": "copy/journal.csv (letzte Zeile)", "zuletzt gespeichert": rechnung.zeit_text(copy_letzte_zeile)},
    {"Datei": "scout/kandidaten.csv (letzte Bewertung)", "zuletzt gespeichert": rechnung.zeit_text(scout_lauf)},
]), hide_index=True, alt="Wann die Dateien zuletzt gespeichert wurden")

# ---------------------------------------------------------------- Messung und Korrekturen
st.subheader("Messung: Was würde Verzögerung kosten?", anchor=False)
st.caption("Seit 03.10.: Bei jedem Kauf und Verkauf fragt der Bot dieselbe Quote 2 s später noch einmal ab. "
           "Plus = 2 s später hätten wir weniger bekommen. Nur Aufzeichnung, keine Regel.")
with st.container(horizontal=True):
    for name in ("Hauptbot und Experimente", "Copy-Bot"):
        m = messung[name]
        st.metric(name, f"{rechnung.zahl(m['median'], 2, vorzeichen=True)} %" if m["median"] is not None
                  else "–", border=True,
                  help=f"Median aus {m['anzahl']} Messungen; jede zehnte über "
                       f"{rechnung.zahl(m['p90'], 2, vorzeichen=True)} %" if m["anzahl"] else "Noch keine Messung.")
    st.metric("0,95-Notlösung beim Verkauf", f"{messung['notloesung']}×", border=True,
              help="Verkauf ohne Jupiter-Quote: Kurs × 0,95 angenommen (Hauptbot und Experimente).")
    st.metric("Korrekturen herausgerechnet", n_korrekturen, border=True,
              help="Zeilen aus auswertungen/korrekturen.csv (Fehlbuchungen im Copy-Journal bis 03.10.)")

detail = daten.messung_detail(head)
st.markdown("**Ausführungskosten genauer: typisch und im schlechten Fall**")
st.dataframe(pd.DataFrame([{
    "Bot": m["quelle"], "Aktion": "Kauf" if m["aktion"] == "KAUF" else "Verkauf", "Messungen": m["anzahl"],
    "Median": ansicht.txt(m["median"], 2, True, " %"),
    "schlechteste 10 % im Mittel": ansicht.txt(m["schlechteste_10"], 1, True, " %"),
    "jede zehnte schlechter als": ansicht.txt(m["schwelle_10"], 1, True, " %"),
    "über 5 % schlechter": ansicht.txt(m["schlechter_5"] * 100 if m["schlechter_5"] is not None else None, 0,
                                       einheit=" %"),
    "Abstand der 2. Quote, Median": ansicht.txt(m["median_s"], 1, einheit=" s"),
    "Abstand, längster": ansicht.txt(m["max_s"], 1, einheit=" s"),
} for m in detail if m["anzahl"]]), hide_index=True, alt="Ausführungskosten je Bot und Aktion")
st.caption("Plus = 2 Sekunden später hätten wir weniger bekommen (Kauf: weniger Token, Verkauf: weniger SOL). "
           "Der Median liegt meist bei 0; die Kosten stecken im schlechten Zehntel, vor allem bei schnellen "
           "Coins. „Abstand“ = tatsächliche Zeit zwischen den beiden Quoten: "
           "Gewollt sind 2 s, gemessen wird aber erst in der Pause zwischen zwei Durchläufen, daher später.")
