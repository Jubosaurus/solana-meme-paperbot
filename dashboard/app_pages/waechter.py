"""Wallet-Waechter: ausschliesslich lokale Daten anzeigen, keine Aktionen."""
import re

import streamlit as st

import ansicht as a
import daten
import rechnung


def automatische_entfernung(ereignis):
    """Nur der ausdrueckliche Scout-Vermerk belegt die Herkunft einer Entfernung.

    Das Feld 'automatisch' der Rechnung dient der Tageslimit-Zaehlung, nicht dieser Plakette.
    """
    return (ereignis.get("art") == "Entfernung"
            and re.match(r"^\s*entfernt\s+\d{2}\.\d{2}\.\s+automatisch\s*:",
                         str(ereignis.get("grund", "")), re.IGNORECASE) is not None)


def details(paare, automatisch=False):
    """Nexus-Zeilen umbrechen auch bei langen Adressen auf 390 px."""
    a.ereignisse([(a.e(angabe), a.e(wert) + (" " + a.chip("automatisch")
                                          if automatisch and angabe == "Änderung" else ""))
                 for angabe, wert in paare])


a.seitenkopf("Wallet-Wächter", "Scout-Automatik im Blick · nur Vorschau, keine Änderungen.")
try:
    u = daten.waechter(daten.stand())
except Exception:
    a.fehler("Wallet-Vorschau konnte nicht geladen werden", "Lokale Daten fehlen oder sind nicht lesbar.")
    st.stop()

heute = u["heute"]
a.raster([
    a.karte("Aktive Copy-Wallets", f"{u['aktiv'] if u['aktiv'] is not None else '–'} / {u['maximum']}"),
    a.karte("Automatik heute", f"{heute['anzahl'] if heute['anzahl'] is not None else '–'} / {heute['limit']}",
            unter=a.e("Aufnahme / Ersetzen · UTC-Tag")),
    a.karte("Warteliste", str(len(u["warteliste"]))),
])
st.caption(f"Vorschau: {rechnung.zeit_text(u['jetzt'])} · Copy-Daten: {rechnung.zeit_text(u['gespeichert'])}")

st.subheader("Nächster Kandidat zum Ersetzen", anchor=False)
if u["naechster"]:
    z = u["naechster"]
    a.raster([a.karte(z["name"], {"bot": "Bot-Hinweis", "still": "72 Stunden still", "verlust": "Größter Verlust"}[z["kandidat"]],
                      unter=a.e(" · ".join(z["gruende"])), klein=True)])
    a.hinweis("Nur Vorschau nach den gespeicherten Daten. Bot und Verlust werden nur gegen einen geeigneten Kandidaten getauscht.")
    if heute["rest"] == 0:
        a.hinweis("Das Tageslimit ist erreicht. Aufnahme und Ersetzen müssen bis zum nächsten UTC-Tag warten.")
    elif heute["rest"] is None:
        a.hinweis("Das Tageslimit ist unbekannt; ein Tausch kann hier nicht bestätigt werden.")
else:
    a.leer("Kein belegter Kandidat zum Ersetzen", "Fehlende Daten können eine vollständige Prüfung verhindern.")
st.caption("Reihenfolge: Bot-Hinweis, längste Pause ab 72 Stunden, größter Verlust. Stille Entfernungen ohne Ersatz "
           "zählen nicht zum Tageslimit; nur bei höchstens 2 Stunden alten Copy-Daten, höchstens zwei pro Scout-Lauf.")

with st.expander("Datenlücken und Grenzen der Vorschau", icon=":material/info:"):
    for h in u["hinweise"]:
        a.hinweis(h)
    st.caption("Grün: keine Regel greift in den vorhandenen Daten. Gelb: Schonfrist, Datenlücke oder gesperrte Stille. "
               "Rot: belegter Vorschau-Kandidat. Das Dashboard nimmt keine Wallet auf und entfernt keine.")

st.subheader("Aktive Wallets", anchor=False)
if not u["wallets"]:
    a.leer("Keine aktiven Wallets gefunden")
else:
    a.wallet_liste(u["wallets"])
    with st.expander("Wallet-Details", icon=":material/info:"):
        wallets = sorted(u["wallets"], key=lambda z: {"rot": 0, "gelb": 1, "gruen": 2}[z["ampel"]])
        name = st.selectbox("Wallet", [z["name"] for z in wallets], key="waechter_wallet")
        z = next(z for z in wallets if z["name"] == name)
        details([
            ("Adresse", z["wallet"]),
            ("Start", rechnung.zeit_text(z["gestartet"])),
            ("Letzter eigener Trade", rechnung.zeit_text(z["letzter_trade"])),
            ("Pause (ohne Trade seit Start)", a.txt(z["pause_h"], 1, einheit=" h")),
            ("Geschlossene Positionen", a.txt(z["geschlossen"], 0)),
            ("Ergebnis geschlossen roh, alle Runden (Wallet-Regel)", a.plusminus(z["ergebnis"])),
            ("Ergebnis roh einschließlich offener Positionen", a.plusminus(z["ergebnis_seit_start"])),
            ("Schonfrist für Ergebnis", "Ja · unter 7 Tagen und 30 Positionen" if z["schonfrist"] else "Nein / nicht belegt"),
            ("Scout-Bewertung", rechnung.zeit_text(z["scout_zeit"])),
            ("Flutschutz-Abmeldung", rechnung.zeit_text(z["flutschutz_zeit"])),
        ])
        for h in z["luecken"]:
            if h != a.SCOUT_LUECKE:
                a.hinweis(h)
    st.caption("Verlustregel: mindestens 30 geschlossene Positionen und mehr als 1 SOL Verlust roh über alle Runden, "
               "aus geschlossenen Positionen. Die Vorschau nutzt die gemeinsame Copy-Rechnung.")

st.subheader("Warteliste", anchor=False)
if not u["warteliste"]:
    a.leer("Keine lesbaren Einträge in der Warteliste")
for w in u["warteliste"]:
    with st.expander(w["name"] or w["wallet"][:4]):
        details([
            ("Adresse", w["wallet"]),
            ("Wartet seit", rechnung.zeit_text(w["seit"])),
            ("Bewertet", rechnung.zeit_text(w["bewertet"])),
            ("Quelle", w["quelle"]),
            ("Punkte", a.txt(w["punkte"])),
            ("Rendite ohne besten Coin", a.txt(w["rendite_ohne_besten_pct"], 1, einheit=" %")),
            ("Coins", a.txt(w["coins"], 0)),
            ("Kauf-Median", a.txt(w["kauf_median_sol"], 3, einheit=" SOL")),
            ("Trades je Tag", a.txt(w["trades_pro_tag"])),
            ("Inaktiv bei Bewertung", a.txt(w["inaktiv_h"], 1, einheit=" h")),
        ])
        if w["abgelaufen"]:
            a.hinweis("Wartet länger als 7 Tage; laut Regel abgelaufen.")
        if w["neu_pruefen"]:
            a.hinweis("Bewertung älter als 6 Stunden oder unbekannt; vor Aufnahme neu prüfen.")

with st.expander("Heutige Änderungen aus der lokalen Git-Historie", icon=":material/history:"):
    if not heute["ereignisse"]:
        a.leer("Keine Änderungen belegt" if heute["anzahl"] is not None else "Git-Historie nicht lesbar")
    for e in heute["ereignisse"]:
        details([
            ("Wallet", e["name"]),
            ("Zeit", rechnung.zeit_text(e["zeit"])),
            ("Änderung", e["art"]),
            ("Grund", e["grund"]),
        ], automatisch=automatische_entfernung(e))
