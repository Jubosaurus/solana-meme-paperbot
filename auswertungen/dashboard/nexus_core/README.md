# Nexus Core, Teil 3 von 3 – Logo und Qualitätsschleife (07.10.2026)

Fotos: `nachher/` = alle 14 Seiten, je Desktop (1280 px) und Handy (390 px), Stand Runde 4. `vorher/` = vier Hauptseiten aus Runde 1 (da war das neue Logo schon eingebaut; ein Foto mit dem allerersten Logo gibt es nicht). Alle Fotos mit `tools/foto.py` (nur localhost, keine Netzabfragen). „Datenstand fehlt“ bei Hauptbot und Copy-Bot im Betrieb ist ein Effekt des Fotomodus (keine Git-Historie), kein Fehler.

## A. Logo
- Vorlage: `dashboard/static/neu/Gemini_Generated_Image_xo8v14xo8v14xo8v.jpg` (Original bleibt).
- Hintergrund freigestellt (weicher Rand, Farbe am Rand zurückgerechnet = keine dunklen Säume). **PNG mit Transparenz, kein SVG**: Die Farbverläufe und Glanzkanten ließen sich als Vektor nicht treu nachbauen.
- Zwei Fassungen: `nexus-core-bildzeichen.png` (quadratisch, 1024 px) und `nexus-core-logo-text.png` (Zeichen + „Nexus Core“). Dazu Favicon, `icon-192/512.png`, `apple-touch-icon.png`, `nexus-core-bildzeichen-klein.png` (96 px für die Fußzeile).
- Erzeugt von `tools/logo_aus_vorlage.py` (ersetzt das alte Vektor-Logo-Skript; dieses und die beiden alten SVG-Dateien sind gelöscht).
- Leitsatz: unter dem Logo in der Seitenleiste und in der Fußzeile (am Handy ohne „Nexus Core –“, umbrechend).
- Farbwelt: Das Logo verläuft von Indigo über Cyan zu Grün, die Dashboard-Farben (Indigo als Akzent, Grün/Rot für Gewinn/Verlust) passen dazu. **Keine Änderung nötig, kein Vorschlag.**

## B. Wächter
Entfernungen stiller Wallets durch die Scout-Automatik tragen die Plakette „automatisch“ (nur wenn der Vermerk in `copy_wallets.txt` die Automatik belegt, sonst keine). Zählung gegen das Tageslimit unverändert.

## C. Qualitätsschleife – Verbesserungen je Runde
Frage jeder Runde: „Würde ein Mensch dieses Dashboard kaufen?“ Runde 1–3: nein, Runde 4: fast, Runde 5: ja (mit den Restpunkten unten).

**Runde 1 (Fotos aller Seiten):** Nein. Logo winzig; Kontostände standen unter den News; Tabellen abgeschnitten; Wächter = 26 gleiche Karten; Schrift am Handy zu klein; eine Kennzahl-Karte allein in der Zeile.
→ Karte 20: Logo 44–56 px, Leitsatz in der Leiste, Fußzeilenbild klein (vorher 730 KB als Base64 in jeder Seite), Übersicht mit Konten zuerst, kompaktere Tabellen mit Wisch-Hinweis, Wächter als Liste mit Zählerzeile („23 Gelb · 3 Rot“), Vierer-Raster, größere Handy-Schrift, obere Leiste 48 px.

**Runde 2:** Nein. Scout-Tabelle am Handy 90+ Zeilen lang; Tabellen am Desktop noch abgeschnitten (Testurteil, Betrieb); einzelne Karten allein in der letzten Zeile; Handy-Übersicht mit 13 hohen Karten; „…“ vor den Urteilen wirkt wie ein Fehler; Marke am Handy klein; Rennbahn ohne Legende; „Aktuelle Scout-Prüfung fehlt“ 24-mal im Wächter; Flugschreiber-Achsen nicht bündig.
→ Karten 22–24 (Karte 21 hing über eine Stunde ohne Ausgabe, wurde abgebrochen und in drei kleinere geteilt): Tabellen mit innerem Scrollen, Raster nach Kartenanzahl, kompakte Handy-Karten, Uhr-Symbol statt „…“, Handy-Logo 48 px, Legende und eigene Spalten „roh“/„mit Kosten“ in der Rennbahn, ein Hinweis statt 24, feste Achsenbreite im Flugschreiber, Betrieb zeigt Hauptbot/Copy-Bot-Karten auch ohne Git-Historie.

**Runde 3:** Nein, und zwar durch zwei **Rückschritte** aus Runde 2: (1) Tabellen am Handy brachen Buchstabe für Buchstabe um (Scout, Lernen, Kennzahl-Tabelle der Übersicht, Köpfe im Betrieb), nur 3 Zeilen sichtbar; (2) drei bis vier Spalten machten reiche Karten am Desktop zu schmal.
→ Karte 25: kein Umbruch mitten im Wort, Mindestbreiten, waagerechtes Scrollen, mindestens ~8 Zeilen sichtbar; reiche Karten höchstens zwei Spalten, Strategie-Kopf als 2×2; Tageszeiten in 4, Marktphasen in 3 Spalten.

**Runde 4:** Ja. Keine abgeschnittenen Tabellenspalten bei 1280 px auf den gesehenen Seiten, Tabellen am Handy lesbar. Seitliches Scrollen der ganzen Seite am Handy (Messung von `foto.py`): in Runde 3 bei allen 14 Seiten „nein“, in Runde 4 nur bei Scout und Lernen ausgewertet (die Meldung der übrigen zwölf habe ich nicht mitgeschrieben). Foto-Durchsicht Runde 4: Übersicht, Strategie, Betrieb, Tageszeit, Copy Trading, Scout und Lernen angesehen; Wächter, Rennbahn, Flugschreiber, News, Wallets prüfen, Verpasste Chancen und Wissen nur in Runde 3 angesehen (Änderungen aus Karte 25 betreffen dort nur Tabellen-CSS).
**Runde 5 (Karte 26, nur noch vier Restpunkte):** „Wallets prüfen“ (Desktop) zeigt alle Spalten ohne Abschneiden (sieben Hauptspalten, Rest im Aufklapper; nur Darstellung, Schreiblogik und `wallets.py` unverändert, Diff von mir gelesen), Scout-Adressen am Handy einzeilig, Tageszeit-Zahlen einzeilig, Lernen-Tabelle am Handy etwas gleichmäßiger. Danach neu fotografiert: Wallets prüfen, Scout, Tageszeit, Lernen (diese vier Fotos in `nachher/` sind Stand Runde 5, die übrigen Stand Runde 4).
Restpunkte (klein, ehrlich): Die Zeilenhöhen in der Lernen-Tabelle am Handy sind noch nicht ganz gleich (einzelne Zeilen ca. doppelt so hoch); Menü-Gruppen und Seitenleiste am Handy (ausgeklappt) wurden nicht fotografiert (Streamlit-Menü, nicht von uns gebaut).

Außerdem vom Code-Prüfer gefunden und behoben: die Zeile „92 von 92 bewerteten Wallets“ im Scout (beide Zahlen immer gleich) heißt jetzt „92 bewertete Wallets, alle Zeilen enthalten.“

## D. Zahlen unverändert
`tools/kontowerte_pruefen.py` vor und nach allen Änderungen auf denselben Daten: **identisch** (13 Strategie-Konten roh und mit Kosten, 47 Copy-Konten Kontowert, vorsichtiger Wert und Ergebnis seit Start). `dashboard/rechnung.py` und `dashboard/daten.py` unverändert.

## E. Dashboard am Android-Handy auf den Startbildschirm (nur Heimnetz)
1. Am PC `dashboard/start_handy.bat` starten (Port 8501, Firewall nur für private Netze). Handy im selben WLAN.
2. Adresse oder QR-Code aus dem Fenster nutzen, in Chrome öffnen (z. B. `http://192.168.x.x:8501`).
3. Chrome-Menü (drei Punkte) → „Zum Startbildschirm hinzufügen“ → Name „Nexus Core“ → „Hinzufügen“.
Ehrlich: Das ist eine Verknüpfung zur Seite, **keine echte App**. Streamlit liefert im Seitenkopf keinen Manifest-Verweis, deshalb bleibt oben die Chrome-Adressleiste sichtbar, das Symbol kann je nach Chrome-Version das Favicon statt unseres großen Symbols sein, und es gibt keine eigene Startfarbe. Läuft der PC oder das Heimnetz nicht, lädt die Seite nicht. Außerhalb des Heimnetzes geht es bewusst nicht (keine Freigabe nach außen).
