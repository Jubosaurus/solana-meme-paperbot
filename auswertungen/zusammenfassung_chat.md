# Zusammenfassung fürs Chat-Projekt (Stand 04.10.2026, ca. 05:30 UTC = 07:30 deutsche Zeit)

## 1. Projekt

- **Paper-Trading** mit Solana-Memecoins: Es wird **kein echtes Geld** gehandelt, alles ist simuliert.
- Ziel: herausfinden, ob es Regeln gibt, die auf Dauer Gewinn bringen. Erst auf Papier beweisen, dann weitersehen.
- Läuft rund um die Uhr kostenlos auf GitHub (öffentliches Repository). Die Bots speichern ihren Stand etwa jede Minute.
- **Leitlinie seit 04.10.: „Mutig starten, streng urteilen, nichts ohne Aufzeichnung.“**
  - **Mutig starten:** Experimente dürfen auf Papier riskant sein, auch bewusst mit Rugs (Betrugs-Coins) oder Bündel-Coins.
  - **Nichts ohne Aufzeichnung:** Jeder Verlust soll Daten liefern, aus denen wir lernen.
  - **Streng urteilen:** Ein Urteil gibt es erst nach 200 Trades, gegen die Kontrollgruppe (Zufallskäufe) aus derselben Zeit. Das Ergebnis muss auch ohne die 3 besten Trades halten.

## 2. Arbeitsteilung

- **Ich (Betreiber):**
  - entscheide über Strategie, Regeln und Wallets;
  - programmiere kaum und lese oft am Handy.
- **Claude Code** (auf meinem PC):
  - setzt um, testet und spielt ein;
  - wertet aus und erklärt in einfachem Deutsch.
  - Regeländerungen nur mit meinem OK. Technische Reparaturen schlägt Claude vor.
- **Ablauf bei jeder Änderung:**
  1. Tests grün (zurzeit rund 230 Tests).
  2. Helfer „Code-Prüfer“ sagt „einspielbar“.
  3. Eintrag im Änderungsprotokoll (`STRATEGIE.md`).
  4. Einzeln einspielen, kein Neustart von Hand: Die Bots übernehmen neuen Code bei der nächsten Schicht.
- **Helfer (Subagenten):**
  - Daten-Prüfer rechnet Zahlen nach;
  - Strategie-Tester prüft neue Regeln an alten Daten;
  - Code-Prüfer prüft jede Änderung.
- **Skills (feste Abläufe):** Tagesauswertung, Wallet prüfen, Einspielen. Dazu fremde Nachschlagewerke: Helius, pytest, Streamlit, Task Observer (nur auf Ansage).
- **Dashboard** (seit 03.10.): Doppelklick auf `dashboard/start.bat`. Läuft nur auf meinem PC, liest nur. Zeigt Konten, Urteile, Copy-Trader (inkl. Exit-Liquidität) und den Betriebszustand.

## 3. Bots

Drei Bots, jeder in Schichten von knapp 6 Stunden, die sich selbst weiterstarten (Kettenstart).

**a) Hauptbot (`bot.py`)**
- Hauptstrategie **NARRATIV**: Regeln Tag 1–17 aus den Videos, zuletzt Tag 17 „kein Kauf nach mehr als 30 % Anstieg in 5 min“.
- Dazu Experimente mit je eigenem 10-SOL-Konto:

| Experiment | Idee |
|---|---|
| Kontrollgruppe | zufällige junge Coins = Vergleichsbasis |
| Zweite Welle | Wiedereinstieg nach der Notbremse |
| Heiße Coins | kauft, wenn der Bündel-Check nicht möglich ist |
| Endspurt viele Trades | kurz vor der Graduation (Wechsel von Pump.fun an die große Börse) |
| Notbremse 25 (neu 04.10.) | wie die Hauptstrategie, Notbremse schon bei −25 % statt −40 % |
| Offene Tür (neu 04.10.) | Story-Filter ohne Sicherheitsprüfungen, kauft bewusst auch Rugs |
| Serien-Devs (neu 04.10.) | Coins von Erstellern, deren früherer Coin ≥ 300.000 $ wert war; Verkauf auch, wenn der Ersteller verkauft |
| Große Coins (neu 04.10.) | wie die Hauptstrategie, aber nur Coins **über** 3 Mio. $ (prüft Tag 7) |
| *Beendet 04.10.:* Ohne Limit, Endspurt ohne Filter | Daten bleiben |

- **Neu: Aufzeichnung (nur Beobachtung, keine Regel)**
  - **Flugschreiber:** je offene Position etwa jede Minute Liquidität, Holder, Top-10-Anteil, Bestand des Erstellers, Käufe/Verkäufe und Bestand der Bündel-Käufer. Damit lassen sich später Muster vor Rugs finden.
  - **DexScreener:** Wurde für Werbung oder ein Profil bezahlt, und wann?
  - **Messung:** Kurs 2 Sekunden nach dem Kauf, also wie viel Verzögerung kostet.
  - **Gebühren-Feld von Jupiter:** gezahlte Gebühren je Coin, falls Jupiter es liefert.

**b) Copy-Bot (`copy_bot.py`)**
- Kopiert 22 Wallets (Obergrenze), jede mit eigenem 10-SOL-Konto.
- Jeder Kauf des Traders ab 0,1 SOL wird bei uns ein Kauf von 0,2 SOL.
- Am 03./04.10. entfernt:
  - 922M: nicht kopierbar, sehr teuer bei Helius;
  - Zrool, Putrick, Cooker: Wallet-Regel, also mindestens 30 Positionen und mehr als 1 SOL Verlust.
- Neu 04.10.: G7b2, GeFg, 499R, 2Nxj.

**c) Wallet-Scout (`scout_bot.py`)**
- Läuft alle 6 h und liefert nur Ranglisten von Wallet-Kandidaten.
- Ändert nie selbst etwas an der Wallet-Liste.
- Neu: Bewertung 3 (Kleinstkäufer werden nicht mehr bewertet) und ein Prüf-Modus für einzelne Transaktionen.

## 4. Stand der Ergebnisse (04.10. ca. 05:45 UTC, vom Daten-Prüfer nachgerechnet)

Alle Konten starten mit 10 SOL. Kontowert = freies Geld + Wert der offenen Positionen.

| Konto | Kontowert | Trades | Urteil |
|---|---|---|---|
| Hauptstrategie | 9,71 SOL (−0,29) | 114 | zu früh (67 von 200 im Vergleichszeitraum), gemischt |
| Kontrollgruppe (Zufall) | 4,56 SOL (−5,44) | 229 | Vergleichsbasis |
| Zweite Welle | 10,21 (+0,21) | 13 | zu früh |
| Heiße Coins | 7,90 (−2,10) | 94 | zu früh, Tendenz schlechter als Zufall |
| Endspurt viele Trades | 8,28 (−1,72) | 134 | zu früh, Tendenz besser als Zufall |
| Endspurt ohne Filter (beendet) | 6,58 (−3,42) | 280 | besser als Zufall, aber im Minus |
| Ohne Limit (beendet) | 8,68 (−1,32) | 63 | hat seine Frage nicht gemessen |
| Notbremse 25 / Offene Tür / Serien-Devs / Große Coins | 9,96 / 9,54 / 9,48 / 10,00 | 3 / 17 / 5 / 0 | erst seit heute Nacht, viel zu früh |

**Copy Trading seit Start**
- Insgesamt **−44,0 SOL** über alle Wallets, auch die entfernten. Der Großteil des Verlusts kommt von entfernten Wallets wie 922M.
- Die 22 aktiven zusammen: **+21,8 SOL**. Fast alles kommt von **HEBO (+23,1)**, danach 4DOV (+2,9). Ohne HEBO wären die aktiven etwa −1,3.
- Die meisten neuen Wallets haben erst 0–3 Positionen, ein Urteil ist noch nicht möglich.
- **Erkenntnis Exit-Liquidität:**
  - Verlierer-Trader verkaufen oft binnen 60 s nach ihrem Kauf, manchmal schon vor unserem Kauf. Wir kaufen dann ihre Verkaufsware.
  - Gewinner (HEBO, 4DOV) halten Minuten bis eine halbe Stunde.

**Videos**
- 14 Videos von OrangieWEB3 ausgewertet; weitere Kanäle hat YouTube gesperrt.
- Viel Werbung mit Empfehlungslinks, und er widerspricht sich selbst.
- Daraus entstanden: Experiment Große Coins, das Gebühren-Feld und zwei Nachrechnungen (`auswertungen/2026-10-04_video_nachrechnung.md`):
  - Wallet-Signal (2 Copy-Wallets kaufen denselben Coin): hilft nicht.
  - Verkauf in Drittel-Stücken bei 1,5x/2x/3x: etwas besser als „Hälfte bei 2x“, aber auch im Minus. Möglich wäre ein Experiment „Drittel-Leiter“, das wartet auf meine Entscheidung.

## 5. Budgets

- **Helius** (Gratis: 1 Mio. Credits/Monat):
  - Vorher ~520.000/Monat, davon ~70 % durch 922M, der jetzt weg ist.
  - Neue Funktionen der Nacht: höchstens ~80.000, Große Coins < 15.000.
  - Die aktuelle Zahl aus dem Helius-Dashboard fehlt noch.
- **Birdeye** (Gratis: 30.000 CUs/Monat): nur für den Scout, Zähler stoppt bei 28.000.
- **Jupiter:** ein Schlüssel für alle Bots.
- **Solana Tracker:** höchstens 70 Abfragen am Tag, nur Beobachtung.
- **GitHub Actions:** kostenlos, weil das Repository öffentlich ist.
- **Claude:** Das Nutzungslimit wurde im Nachtlauf erreicht (etwa 3,5 h Pause).

## 6. Offene Punkte

1. **Helius-Zahl** aus dem Dashboard melden. Erst dann wird über mehr als 22 Wallets entschieden.
2. **05.10. ab 12:12 UTC (14:12 deutsche Zeit): stille Wallets entfernen** und mit den besten Scout-Kandidaten auf 22 auffüllen.
   - Achtung: haru, Eshi und koko haben inzwischen gehandelt.
   - Wirklich still sind nur noch **43Nu und 42wu**.
3. **C7bF** beobachten bis 20 Käufe. Bleibt das Muster (verkauft binnen Sekunden), wird die Wallet ersetzt.
4. **Videos:** ruhiger zweiter Versuch heute Nacht ab 22:00 UTC (24:00 deutsche Zeit), etwa 4 Videos pro Stunde.
   - Bei erneuter Sperre wird aufgegeben, nichts umgangen.
   - Läuft auf meinem PC, der muss also an bleiben.
5. **Experiment „Drittel-Leiter“?** Kauft wie die Hauptstrategie, verkauft je ⅓ bei 1,5x / 2x / 3x. Wartet auf meine Entscheidung.
6. **Gebühren-Feld:** nach einem Tag prüfen, ob Jupiter es überhaupt liefert.
7. Tag 17 beobachten: Wie liefen die abgelehnten „FOMO-Sprung“-Coins?
8. Auswertung der DexScreener-Daten ab 100 Käufen, des Flugschreibers nach den ersten Rugs.

## 7. Entscheidungen und Vorlieben

- **Sprache:** Deutsch, einfach, kurz, handytauglich. Zahlen zeigen statt behaupten, Unsicherheit und eigene Fehler offen sagen.
- **Zeiten:** immer UTC und deutsche Zeit (UTC+2).
- **Urteile:** nur nach den Testregeln (200 Trades, Kontrollgruppe, ohne die 3 besten). Hauptstrategie, Kontrollgruppe und Testregeln nicht ohne mein OK ändern.
- **Copy-Regeln:**
  - 0,2 SOL je Kauf; Käufe älter als 60 s nie nachkaufen.
  - Kein Kauf bei mehr als ±15 % Preisabstand zum Trader; Verkäufe nie blockiert.
  - Kein Take-Profit, kein Stop-Loss.
  - Wallet-Regeln:
    - Bot → ersetzen.
    - 72 h ohne Trade → ersetzen.
    - 30 Positionen und mehr als 1 SOL Verlust → prüfen.
  - Verlierer dürfen für Erkenntnisse bleiben.
- **Sicherheit:**
  - keine neuen Schlüssel, Konten, Wallet-Verbindungen, Browser-Erweiterungen oder Trading-Terminals;
  - keine Schlüssel in Code oder Notizen, denn das Repository ist öffentlich;
  - Daten der Bots nie löschen, „Zurücksetzen“ nur per `git revert`.
- **Abgelehnt** (nicht wieder vorschlagen): OmniRoute, Ruflo, Trading-/Sniper-Skills mit Wallet.
- **Sparsam:** eine Aufgabe pro Sitzung, Helfer nur mit klarem Zweck.
