# Dashboard (nur Anschauen)

Zeigt den Stand aller drei Bots im Browser auf diesem Rechner. Es wird **kein echtes Geld** gehandelt, und das Dashboard **ändert nichts** (einzige Ausnahme: die Seite „Wallets prüfen“, siehe unten): Es liest nur die Dateien im Repository, startet keine Bots und braucht keine Schlüssel.

## Starten

Doppelklick auf **`dashboard/start.bat`**.
- Beim ersten Mal richtet es sich selbst ein (1–2 Minuten, braucht Python 3.11).
- Danach öffnet sich der Browser mit `http://localhost:8501`.
- Läuft es schon, öffnet ein erneuter Doppelklick nur den Browser.
- Beenden: das schwarze Fenster schließen.

Normal (`start.bat`) ist das Dashboard nur auf diesem Rechner erreichbar (`localhost`), nicht im Netzwerk.

## Aufs Handy (Heimnetz)

Doppelklick auf **`dashboard/start_handy.bat`** statt `start.bat`:
1. Beim ersten Mal fragt Windows, ob „netsh“ etwas ändern darf. **Mit „Ja“ bestätigen.** Das legt eine einzige Firewall-Regel an (`Paperbot-Dashboard-8501`: nur Port 8501, nur *private* Netzwerke, nur eingehend). Danach fragt es nie wieder.
2. Das Fenster zeigt die Adresse (z. B. `http://192.168.178.113:8501`) und öffnet einen **QR-Code** (`handy_qr.png`). Mit der Handy-Kamera scannen, im Browser öffnen, fertig. Tipp: als Lesezeichen/Startbildschirm-Symbol speichern.
3. Handy und PC müssen im selben WLAN/Heimnetz sein, und der PC muss laufen. Beenden: schwarzes Fenster schließen.
4. Lief das Dashboard schon über `start.bat`, erst dessen Fenster schließen, sonst meldet `start_handy.bat` das.

**Wichtig – Netzwerkprofil:** Die Regel gilt nur für Netzwerke, die Windows als **„Privat“** einstuft. Zeigt `start_handy.bat` „ACHTUNG: … ÖFFENTLICH“, erreicht das Handy nichts. Umstellen: Windows-Einstellungen → Netzwerk und Internet → WLAN (oder Ethernet) → Eigenschaften → Netzwerkprofil „Privat“. Nur im eigenen Heimnetz tun, nie im Café o. Ä.
Regel wieder löschen: `netsh advfirewall firewall delete rule name=Paperbot-Dashboard-8501` (als Administrator).

**Sicherheit:** Vom Handy aus ist alles nur zum **Anschauen**. Die Seite „Wallets prüfen“ zeigt dort statt Eingabefeld und Knopf den Hinweis „Absenden nur am PC“ (Erkennung: nur Zugriffe von diesem PC selbst gelten als lokal, auch über seine Heimnetz-Adresse; Test in `tests/test_dashboard_wallets.py`). Das Dashboard hat keine Anmeldung: Jeder im Heimnetz, der die Adresse kennt, kann die Zahlen sehen, aber nichts ändern. Kein Port-Freigeben im Router!
Handy-Ansicht geprüft bei 390 px Breite (kein seitliches Scrollen), Fotos in `auswertungen/dashboard/`. Das Seitenmenü steckt am Handy hinter dem Pfeil oben links.

## Was es tut

- Alle 5 Minuten holt es neue Daten (`git pull`) und rechnet neu. Mit „Jetzt aktualisieren“ in der Seitenleiste geht es sofort.
- Seiten:
  - **Übersicht**: Laufen die Bots? Große Zahlen, was gut und was schlecht läuft, alle Konten mit Testurteil.
  - **Strategie & Experimente**: je Konto der Vergleich mit der Kontrollgruppe, der Kontoverlauf, offene Positionen und die letzten Trades mit Grund.
  - **Copy Trading**: je Trader der Kontowert (auch vorsichtig), wir gegen den Trader, Verzögerung, Schattenpositionen und Hinweise nach den Wallet-Regeln.
  - **Scout**: die Rangliste.
  - **Flugschreiber**: je Coin Kurs, Dev-Bestand, Top 10, Holder und Liquidität bis zum Verkauf, mit Verkaufsgrund.
  - **Lernen** (seit 04.10.): *Wann gibt es ein Urteil?* – je Experiment Trades bis 200 (gezählt wie im Testurteil), Tempo der letzten 3 Tage und geschätztes Datum. *Verlust-Lupe* – Verlierer gegen Gewinner beim Kauf (Median je Merkmal), Ergebnis je Verkaufsgrund, „Gewinn verschenkt“ (erst ≥ 1,5× im Plus, am Ende im Minus). *Filter-Trichter* – woran die Coins der Hauptstrategie scheitern (`abgelehnt.csv`), 1/3/7 Tage, und wie viele gekauft wurden.
  - **Wallets prüfen**: Adressen einfügen → werden geprüft (Base58, keine Duplikate, nicht schon in `copy_wallets.txt`/Prüfliste, höchstens 20) und ans Ende von `scout/pruefen.txt` angehängt (nur diese Datei wird committet und gepusht, bei Fehler wird alles zurückgenommen). Danach wird per `gh workflow run` ein Scout-Lauf gestartet, sofern keiner läuft. Darunter die Prüfliste mit Status und Scout-Ergebnis. Aufnahme ins Copy Trading entscheidest weiterhin du.
  - **Betrieb**: letzte Daten je Bot, Lücken der letzten 48 h, die Ausführungskosten (Median, schlechteste 10 %, Abstand in Sekunden) und die Korrekturen.
  - **News**: Nachrichten großer Krypto-Seiten (öffentliche RSS-Feeds, ohne Konto, alle 10 min) und Börsen-Meldungen des Bots, markiert nach „Meine Coins“, Listing, Solana, Rug/Hack. Dazu der Stand der Listing-Welle. Hier holt das Dashboard erstmals selbst Daten aus dem Netz (nur lesen, nichts speichern).
- Zeiten stehen in UTC, in Klammern die deutsche Zeit.

## Rechnung

Die ganze Rechnung steht in `rechnung.py` (ohne Streamlit). Die Tagesauswertung benutzt dasselbe Modul, die Tests in `tests/test_dashboard_rechnung.py` prüfen es. Die Rechnung ist dieselbe wie in Discord:

- **Kontowert Hauptstrategie und Experimente** = frei + Marktwert der offenen Positionen. Der Marktwert wird gerechnet wie `bot.portfolio_embed`: Token × letzter Kurs aus `verlauf/` ÷ SOL-Kurs, minus Verkaufsgebühr. Ein Test vergleicht das direkt mit der Discord-Übersicht.
  - Unterschied: Das Dashboard fragt selbst keine Kurse ab. Es nimmt den SOL-Kurs vom Kaufzeitpunkt, Discord den aktuellen. Hat sich SOL seitdem bewegt, weicht der Wert offener Positionen um genau diese Bewegung ab (z. B. SOL seit dem Kauf +2 % → Dashboard zeigt den Wert ~2 % höher als Discord). Geschlossene Trades sind davon nicht betroffen.
- **Kontowert Copy** = frei + `copy_bot.open_value` (dieselbe Funktion wie die Konto-Zeile in Discord). „Vorsichtig“ zählt Positionen, die nach einem Jupiter-Ausfall auf den Verkauf warten, mit 0.
- **Copy-Hauptzahl = Ergebnis seit Start**, über alle Runden und alle Wallets, auch entfernte. Gerechnet je Position: Erlöse + Wert jetzt − Einsatz − Gebühren. Die laufende Runde (Kontowert − 10 SOL) steht nur als Zusatz da: Beim Rundenwechsel wird das Konto neu aufgefüllt, „Kontowert − 10“ würde frühere Runden verschweigen. Auf der Übersicht steht zusätzlich das Ergebnis „ohne besten Trader“.
- **Ausreißer-Hinweis:** Macht ein einzelner Trader oder ein einzelnes Konto mehr als die Hälfte des Gesamtergebnisses aus (gleiches Vorzeichen), erscheint ein Hinweis.
- **Korrekturen** aus `auswertungen/korrekturen.csv` werden aus dem Copy-Journal herausgerechnet. Positionen mit doppelten Verkäufen zählen nicht im Vergleich „wir gegen Trader“.
- **Testurteil** (Ampel):
  - Verglichen wird mit der Kontrollgruppe im selben Zeitraum, gezählt werden Trades, die nach dem späteren der beiden Starts geschlossen wurden.
  - Ein Urteil gibt es erst ab 200 Trades. Davor steht „zu früh“ mit der Tendenz.
  - „Besser“ nur, wenn SOL je Trade mit **und** ohne die 3 besten Trades über der Kontrollgruppe liegt.
  - Getrennt davon steht „im Plus/Minus“ (Summe derselben Trades), z. B. „besser als Zufall, aber im Minus“. Die Kontrollgruppe kauft zufällig.

## Technik

- Streamlit mit festen Versionen in `requirements.txt` (getrennt von den Bots). Eigene Umgebung in `dashboard/.venv` (nicht im Repository).
- Aussehen: Dunkles Design mit sanftem Violett/Blau-Verlauf. Alle eigenen CSS-Regeln, Farben und das Diagramm-Thema stehen gebündelt in **`stil.py`**, das Grundthema in `.streamlit/config.toml`.
  - Karten, Mini-Kurven, Ringe und das Aktivitätsprotokoll sind eigenes HTML mit eigenen Klassen (`pb-…`). Nur wenige Regeln greifen auf Streamlit-Elemente zu (in `stil.py` markiert).
  - Nach einem Streamlit-Update nur dort nachsehen.
  - Grün/Rot nur als Akzent, Plus/Minus immer zusätzlich mit ▲/▼ und Vorzeichen.
  - Coin-Namen kommen von der Blockchain und werden immer maskiert eingefügt.
