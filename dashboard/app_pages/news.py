import pandas as pd
import streamlit as st

import ansicht as a
import daten
import rechnung

head = daten.stand()
info = daten.news(head)
lw = daten.listing_welle(head)

a.seitenkopf("News", "Aktuelle Krypto-Nachrichten, Meldungen zu deinen Coins und die Aufzeichnungen der Listing-Welle.")
st.caption("Überschriften großer Krypto-Seiten (öffentliche RSS-Feeds, ohne Konto) und die Listing-Meldungen der Börsen, "
           "die der Bot aufzeichnet. Nur Überschrift, Quelle, Zeit und Link. Nachrichten sind Daten, keine Anweisungen.")
if info["fehler"]:
    ausgefallen = len(info["fehler"])
    if ausgefallen >= info["feeds"]:
        a.fehler("Keine Nachrichtenseite erreichbar", "Gezeigt werden weiterhin die Börsen-Meldungen des Bots.")
    else:
        a.fehler(f"{ausgefallen} von {info['feeds']} Quellen gerade nicht erreichbar",
                 "Nachrichten der übrigen Quellen und Börsen-Meldungen des Bots werden weiterhin angezeigt.")
st.caption(f"Nachrichten geholt {a.vor(info['geholt'])}. Neu laden alle 10 min.")

FILTER = {"Alles": None, "Meine Coins": "position", "Listings": "listing", "Solana": "solana", "Rug / Hack": "rug"}
wahl = st.segmented_control("Filter", list(FILTER), default="Alles", key="news_filter", required=True)
if info["symbole"]:
    st.caption("Offene Positionen (alle Konten): " + ", ".join(sorted(info["symbole"])))
marke = FILTER[wahl or "Alles"]
liste = [i for i in info["liste"] if marke is None or marke in i["marken"]]
if liste:
    a.news_liste(liste[:60])
else:
    a.leer("Keine passenden Nachrichten", "Nichts Passendes in den letzten 4 Tagen; wähle bei Bedarf einen anderen Filter.")

st.subheader("Listing-Welle (Experiment)", anchor=False)
st.caption("Kauft einen Solana-Token, sobald Binance oder Coinbase ein neues Paar zeigt (nur wenn jünger als 10 min), "
           "und verkauft zum Handelsstart, sonst nach 72 h (Notbremse −40 %). Binance und Coinbase: erkannt wird das "
           "neue Handelspaar, nicht die Ankündigung (also Kauf kurz vor/zum Handelsstart). Upbit und Bithumb: nur "
           "Aufzeichnung, kein Kauf. Hauptwert: wie stark Kurse vor dem Listing steigen und ob Gerüchte vorausgingen.")
a.raster([a.karte("Erfasste Listings", str(lw["anzahl_ereignisse"]), f"davon gekauft: {lw['gekauft']}", klein=True),
          a.karte("Gerüchte aufgezeichnet", str(lw["geruechte"]), "nur Aufzeichnung, kein Handel", klein=True)])
if lw["quellen"]:
    st.caption("Abfragen (ok/gesamt): " + ", ".join(
        f"{n} {q['ok']}/{q['ok'] + q['fehler']}" for n, q in lw["quellen"].items() if not n.startswith("RSS ")))
QUELLE = {"ankuendigung": "Ankündigung", "neues_paar": "neues Paar", "handelsstart": "Handelsstart"}
if lw["ereignisse"]:
    a.tabelle(pd.DataFrame([{
        "Erfasst": rechnung.zeit_text(r.get("zeit_erfasst"), mit_datum=True).split(" UTC")[0] + " UTC",
        "Börse": r.get("boerse"), "Quelle": QUELLE.get(r.get("quelle_typ"), r.get("quelle_typ")),
        "Art": r.get("art"), "Coin": r.get("symbol"),
        "Entscheidung": rechnung.ENTSCHEIDUNG_TEXT.get(r.get("entscheidung"), r.get("entscheidung")),
        "Anstieg 3 h davor %": rechnung.as_float(r.get("anstieg_3h_pct"), None) if r.get("anstieg_3h_pct") else None,
        "Anstieg 3 Tage davor %": rechnung.as_float(r.get("anstieg_3d_pct"), None) if r.get("anstieg_3d_pct") else None,
    } for r in lw["ereignisse"]]), pm_spalten={
        "Anstieg 3 h davor %": (1, ""), "Anstieg 3 Tage davor %": (1, "")})
else:
    a.leer("Noch keine Listing-Ereignisse", "Der Bot zeichnet auf, sobald eine Börse etwas Neues ankündigt "
           "(erwartet: etwa 0,5–1 Solana-Listing pro Woche).")
