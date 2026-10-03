# Dashboard (nur Anschauen)

Zeigt den Stand aller drei Bots im Browser auf diesem Rechner. Es wird **kein echtes Geld** gehandelt, und das Dashboard **ändert nichts**: Es liest nur die Dateien im Repository, startet keine Bots und braucht keine Schlüssel.

## Starten

Doppelklick auf **`dashboard/start.bat`**.
- Beim ersten Mal richtet es sich selbst ein (1–2 Minuten, braucht Python 3.11).
- Danach öffnet sich der Browser mit `http://localhost:8501`.
- Läuft es schon, öffnet ein erneuter Doppelklick nur den Browser.
- Beenden: das schwarze Fenster schließen.

Das Dashboard ist nur auf diesem Rechner erreichbar (`localhost`), nicht im Netzwerk.

## Was es tut

- Alle 5 Minuten holt es neue Daten (`git pull`) und rechnet neu. Mit „Jetzt aktualisieren“ in der Seitenleiste geht es sofort.
- Seiten:
  - **Übersicht**: Laufen die Bots? Große Zahlen, was gut und was schlecht läuft, alle Konten mit Testurteil.
  - **Strategie & Experimente**: je Konto der Vergleich mit der Kontrollgruppe, der Kontoverlauf, offene Positionen und die letzten Trades mit Grund.
  - **Copy Trading**: je Trader der Kontowert (auch vorsichtig), wir gegen den Trader, Verzögerung, Schattenpositionen und Hinweise nach den Wallet-Regeln.
  - **Scout**: die Rangliste.
  - **Betrieb**: letzte Daten je Bot, Lücken der letzten 48 h, die Messung der Ausführungskosten und die Korrekturen.
- Zeiten stehen in UTC, in Klammern die deutsche Zeit.

## Rechnung

Die ganze Rechnung steht in `rechnung.py` (ohne Streamlit). Die Tagesauswertung benutzt dasselbe Modul, die Tests in `tests/test_dashboard_rechnung.py` prüfen es. Die Rechnung ist dieselbe wie in Discord:

- **Kontowert Hauptstrategie und Experimente** = frei + Marktwert der offenen Positionen. Der Marktwert wird gerechnet wie `bot.portfolio_embed`: Token × letzter Kurs aus `verlauf/` ÷ SOL-Kurs, minus Verkaufsgebühr. Ein Test vergleicht das direkt mit der Discord-Übersicht.
  - Unterschied: Das Dashboard fragt selbst keine Kurse ab. Es nimmt den SOL-Kurs vom Kaufzeitpunkt, Discord den aktuellen. Hat sich SOL seitdem bewegt, weicht der Wert offener Positionen um genau diese Bewegung ab (z. B. SOL seit dem Kauf +2 % → Dashboard zeigt den Wert ~2 % höher als Discord). Geschlossene Trades sind davon nicht betroffen.
- **Kontowert Copy** = frei + `copy_bot.open_value` (dieselbe Funktion wie die Konto-Zeile in Discord). „Vorsichtig“ zählt Positionen, die nach einem Jupiter-Ausfall auf den Verkauf warten, mit 0.
- **Korrekturen** aus `auswertungen/korrekturen.csv` werden aus dem Copy-Journal herausgerechnet. Positionen mit doppelten Verkäufen zählen nicht im Vergleich „wir gegen Trader“.
- **Testurteil** (Ampel):
  - Verglichen wird mit der Kontrollgruppe im selben Zeitraum, gezählt werden Trades, die nach dem späteren der beiden Starts geschlossen wurden.
  - Ein Urteil gibt es erst ab 200 Trades. Davor steht „zu früh“ mit der Tendenz.
  - „Besser“ nur, wenn SOL je Trade mit **und** ohne die 3 besten Trades über der Kontrollgruppe liegt.

## Technik

- Streamlit mit festen Versionen in `requirements.txt` (getrennt von den Bots). Eigene Umgebung in `dashboard/.venv` (nicht im Repository).
- Erscheinungsbild in `.streamlit/config.toml`: ruhig und hell. Blau = Plus, Rot = Minus, immer mit ▲/▼ und Vorzeichen.
