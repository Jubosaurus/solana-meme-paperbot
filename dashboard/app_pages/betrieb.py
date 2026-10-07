import time

import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung

head = daten.stand()
commits, messung, n_korrekturen = daten.betrieb(head)
konten = daten.strategie_konten(head)
_, copy_gespeichert, copy_letzte_zeile = daten.copy_konten(head)
_, scout_lauf = daten.scout(head)
jetzt = time.time()
GRENZE_MIN = 20

a.seitenkopf("Betrieb", "Datenstand, Lücken der Bots und gemessene Ausführungskosten im Überblick.")
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
    return a.pille(status, "Datenstand")


karten = []
for z in zeilen:
    dauer = sum((b or jetzt) - a for a, b in z["luecken"])
    n = len(z["luecken"])
    karten.append(a.karte(
        z["bot"], f"Daten {a.vor(z['letzte'])}",
        f"{a.e(rechnung.zeit_text(z['letzte']))}<br>{n} {'Lücke' if n == 1 else 'Lücken'} über {GRENZE_MIN} min "
        f"in 48 h" + (f", zusammen {rechnung.dauer_text(dauer)}" if n else ""),
        oben_rechts=status_chip(z["status"]), klein=True))
# Fehlende Historie sichtbar machen, ohne Dateizeiten als Bot-Lauf zu deuten.
for bot in rechnung.BOT_COMMITS:
    if bot not in commits:
        karten.append(a.karte(bot, "Datenstand fehlt", "Die Git-Historie ist nicht verfügbar.",
                              oben_rechts=a.chip("nicht prüfbar"), klein=True))
karten.append(a.karte("Scout", f"Lauf {a.vor(scout_lauf)}",
                            f"{a.e(rechnung.zeit_text(scout_lauf))}<br>läuft alle 6 Stunden",
                            oben_rechts=status_chip(scout_status), klein=True))
a.raster(karten)

# ---------------------------------------------------------------- Luecken
st.subheader("Lücken in den letzten 48 Stunden", anchor=False)
luecken = [{"Bot": z["bot"], "von": rechnung.zeit_text(a), "bis": rechnung.zeit_text(b) if b else "läuft noch",
            "Dauer": rechnung.dauer_text((b or jetzt) - a), "_start": a}
           for z in zeilen for a, b in z["luecken"]]
if luecken:
    df = pd.DataFrame(sorted(luecken, key=lambda x: -x["_start"])).drop(columns="_start")
    a.datentabelle(df, alt_text="Lücken je Bot")
elif not all(commits.get(bot) for bot in rechnung.BOT_COMMITS):
    a.leer("Lücken nicht prüfbar", "Für mindestens einen Bot fehlen Zeitpunkte aus der Git-Historie.")
else:
    a.leer("Keine Lücken über 20 min", "In den letzten 48 Stunden kamen die Bot-Daten ohne größere Unterbrechung an.")

# ---------------------------------------------------------------- Dateien
st.subheader("Datenstand der Dateien", anchor=False)
a.tabelle(pd.DataFrame([
    {"Datei": "portfolio.json (Hauptbot)", "zuletzt gespeichert": rechnung.zeit_text(haupt["gespeichert"])},
    {"Datei": "copy/konten.json", "zuletzt gespeichert": rechnung.zeit_text(copy_gespeichert)},
    {"Datei": "copy/journal.csv (letzte Zeile)", "zuletzt gespeichert": rechnung.zeit_text(copy_letzte_zeile)},
    {"Datei": "scout/kandidaten.csv (letzte Bewertung)", "zuletzt gespeichert": rechnung.zeit_text(scout_lauf)},
]))

# ---------------------------------------------------------------- Messung und Korrekturen
st.subheader("Messung: Was würde Verzögerung kosten?", anchor=False)
st.caption("Seit 03.10.: Bei jedem Kauf und Verkauf fragt der Bot dieselbe Quote 2 s später noch einmal ab. "
           "Plus = 2 s später hätten wir weniger bekommen. Nur Aufzeichnung, keine Regel.")
karten = []
for name in ("Hauptbot und Experimente", "Copy-Bot"):
    m = messung[name]
    karten.append(a.karte(
        name, f"{rechnung.zahl(m['median'], 2, vorzeichen=True)} %" if m["median"] is not None else "–",
        f"Median aus {m['anzahl']} Messungen; jede zehnte über {rechnung.zahl(m['p90'], 2, vorzeichen=True)} %"
        if m["anzahl"] else "Noch keine Messung.", klein=True))
karten.extend([
    a.karte("0,95-Notlösung beim Verkauf", f"{messung['notloesung']}×",
            "Verkauf ohne Jupiter-Quote: Kurs × 0,95 angenommen (Hauptbot und Experimente).", klein=True),
    a.karte("Korrekturen herausgerechnet", str(n_korrekturen),
            "Zeilen aus auswertungen/korrekturen.csv (Fehlbuchungen im Copy-Journal bis 03.10.)", klein=True),
])
a.raster(karten)

detail = daten.messung_detail(head)
st.subheader("Ausführungskosten genauer: typisch und im schlechten Fall", anchor=False)
a.datentabelle(pd.DataFrame([{
    "Bot": m["quelle"], "Aktion": "Kauf" if m["aktion"] == "KAUF" else "Verkauf", "Messungen": m["anzahl"],
    "Median": m["median"], "schlechteste 10 % im Mittel": m["schlechteste_10"],
    "jede zehnte schlechter als": m["schwelle_10"],
    "über 5 % schlechter": m["schlechter_5"] * 100 if m["schlechter_5"] is not None else None,
    "Abstand der 2. Quote, Median": m["median_s"], "Abstand, längster": m["max_s"],
} for m in detail if m["anzahl"]]), zahlen={
    "Messungen": (0, False, ""), "Median": (2, True, " %"),
    "schlechteste 10 % im Mittel": (1, True, " %"), "jede zehnte schlechter als": (1, True, " %"),
    "über 5 % schlechter": (0, False, " %"), "Abstand der 2. Quote, Median": (1, False, " s"),
    "Abstand, längster": (1, False, " s"),
}, alt_text="Ausführungskosten genauer", hauptspalten=[
    "Bot", "Aktion", "Messungen", "Median", "schlechteste 10 % im Mittel",
    "jede zehnte schlechter als", "über 5 % schlechter",
], detail_gruppen={
    "Abstand der beiden Quotes": ["Bot", "Aktion", "Abstand der 2. Quote, Median", "Abstand, längster"],
})
st.caption("Plus = 2 Sekunden später hätten wir weniger bekommen (Kauf: weniger Token, Verkauf: weniger SOL). "
           "Der Median liegt meist bei 0; die Kosten stecken im schlechten Zehntel, vor allem bei schnellen "
           "Coins. „Abstand“ = tatsächliche Zeit zwischen den beiden Quoten: "
           "Gewollt sind 2 s, gemessen wird aber erst in der Pause zwischen zwei Durchläufen, daher später.")
