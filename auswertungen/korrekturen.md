# Korrekturen Copy-Bot (Stand 03.10.2026)

Alte Daten werden **nicht** umgeschrieben. Die Tagesauswertung rechnet die Zeilen aus
`auswertungen/korrekturen.csv` heraus (Abgleich über `trader` + `trader_signatur` + `aktion` + `zeit`).
Gefunden im Prüfbericht vom 03.10. Ursachen: Nachholen ohne dauerhaftes Gedächtnis (behoben 03.10.,
Copy-Bot merkt sich verarbeitete Signaturen aus dem Journal) und Abbruch einer Schicht ohne Speichern
(Fehler C, Behebung folgt).

Alle Zeiten UTC (Deutschland: +2 h).

## Übersicht

| Art | Anzahl | Zeitraum | Geld betroffen? |
|---|---|---|---|
| Doppelt ausgeführter Verkauf | 15 | 01.10. 19:15 – 02.10. 19:16 | ja, in `konten.json` gebucht |
| Doppelt geschlossene Position (922M, MODEL) | 1 | 02.10. 19:14 / 19:16 | nein, nur Journal |
| Verlorene Position (Zrool, DUGECOIN) | 1 | 02.10. 19:14 | nein, nur Journal |
| Falscher `VERPASST_KAUF` | 279 | 01.10. 19:13 – 03.10. 01:00 | nein, nur Statistik |
| Doppelt vorgemerkter Teilverkauf (`VERKAUF_GEMERKT`) | 22 | gleiche Zeit | nein |

## 1. Doppelt ausgeführte Verkäufe (15)

**Ursache:** Der stündliche Abgleich einer neuen Schicht holte die Trades des Traders bis zur Eröffnung der Position nach. Gemerkt waren nur die letzten 60 Signaturen je Position. Ältere Verkäufe liefen deshalb ein zweites Mal durch. Bei HEBO (BUCK) schloss der alte Verkauf sogar eine **neue** Position im selben Coin.

**Wirkung:**
- Gebucht wurden zusätzlich 1,014 SOL Erlös und 0,071 SOL Gebühren.
- Das Konto ist dadurch **nicht** um 1,01 SOL zu hoch: Verkauft wurden Token der noch offenen Position, die sonst später zu einem anderen Kurs verkauft worden wären.
- Sicher falsch sind die zusätzlichen Gebühren, der Zeitpunkt der Verkäufe und der Vergleich „wir gegen Trader“ der betroffenen Positionen.

| Zeit (2. Ausführung) | Trader | Coin | Mint | 1. Ausführung | Erlös 2. | Gebühr 2. |
|---|---|---|---|---|---|---|
| 01.10. 19:15:27 | HEBO | BUCK | AfqLJuo9 | 01.10. 14:07:53 | 0,127268 | 0,001005 |
| 01.10. 19:17:41 | 4DOV | Saw | 9twiuSdT | 01.10. 14:51:41 | 0,004343 | 0,000100 |
| 02.10. 12:13:26 | 922M | Agency | 7VertkgF | 02.10. 12:03:56 | 0,007642 | 0,000139 |
| 02.10. 12:13:34 | 922M | Agency | 7VertkgF | 02.10. 12:05:35 | 0,006234 | 0,002739 |
| 02.10. 12:13:36 | 922M | Agency | 7VertkgF | 02.10. 12:05:36 | 0,006965 | 0,001128 |
| 02.10. 12:13:37 | 922M | Agency | 7VertkgF | 02.10. 12:05:38 | 0,001594 | 0,002913 |
| 02.10. 19:15:28 | 922M | CATGPT | CNohWHNT | 02.10. 18:49:28 | 0,262417 | 0,018301 |
| 02.10. 19:15:30 | 922M | CATGPT | CNohWHNT | 02.10. 18:50:11 | 0,156270 | 0,002417 |
| 02.10. 19:15:32 | 922M | CATGPT | CNohWHNT | 02.10. 18:50:16 | 0,127182 | 0,001101 |
| 02.10. 19:15:35 | 922M | SGI | 68RUKJSk | 02.10. 18:51:02 | 0,124701 | 0,010486 |
| 02.10. 19:15:38 | 922M | CATGPT | CNohWHNT | 02.10. 18:51:42 | 0,119154 | 0,026988 |
| 02.10. 19:15:39 | 922M | CATGPT | CNohWHNT | 02.10. 18:51:44 | 0,021856 | 0,001276 |
| 02.10. 19:15:56 | 922M | SGI | 68RUKJSk | 02.10. 18:56:21 | 0,007893 | 0,001081 |
| 02.10. 19:16:11 | 922M | SGI | 68RUKJSk | 02.10. 19:01:53 | 0,004632 | 0,001088 |
| 02.10. 19:16:44 | 922M | SI | 9aqmJjCn | 02.10. 19:13:46 | 0,035652 | 0,000019 |

**Behandlung in der Auswertung:** Die Zeilen bei Rechnungen aus dem Journal ignorieren. Die betroffenen Positionen (Trader + Mint + Runde) aus dem Vergleich „wir gegen Trader“ nehmen. Beim Kontowert aus `konten.json` mit dem Hinweis „enthält 15 doppelte Verkäufe“ ausweisen (922M, HEBO, 4DOV).

## 2. 922M, MODEL (`DyrjPqqq…`): doppelt geschlossen

- 02.10. 19:09:17: Teilverkauf. 19:14:11: Position geschlossen (Erlös 0,094200, Ergebnis −0,109861).
- 19:14 wurde die Copy-Schicht von Hand abgebrochen (Neustart). Die Schließung kam nicht mehr in `konten.json`.
- Die neue Schicht holte den Verkauf um 19:16:46 nach (Erlös 0,103979, Ergebnis −0,100083). **Gültig ist diese zweite Schließung.**
- **Behandlung:** Die Journalzeile von 19:14:11 ignorieren.

## 3. Zrool, DUGECOIN (`Ay63NThh…`): verlorene Position

- 02.10. 19:14:32: Kauf 0,2 SOL (Runde 1) im Journal, kurz vor dem Abbruch der Schicht.
- Die Position fehlt in `konten.json` (offen und geschlossen). Das Geld wurde dort nie abgezogen.
- **Behandlung:** Die Journalzeile ignorieren. Der Kontowert aus `konten.json` ist richtig.

## 4. Falsche `VERPASST_KAUF` (279 von 632)

**Ursache:** Wie bei 1. Beim Nachholen wurden Käufe erneut gelesen, die schon verarbeitet waren. Davon:
- 188 waren gekauft (`KAUF`).
- 32 waren als Schattenposition verfolgt (`SCHATTEN_KAUF`).
- 59 waren bewusst ausgelassen (`AUSGELASSEN`, z. B. unter 0,1 SOL).

Im Prüfbericht standen 220. Die 59 ausgelassenen kamen hier dazu, denn auch sie waren nicht verpasst.

Je Trader: Cooker 58, HEBO 45, 4DOV 43, 922M 39, 6ANG 30, 9LXM 25, GYYR 10, Pikalosi 10, ENKM 6, Putrick 4, Troupe 4, 3zsr 3, AFYP 1, Dior 1.

**Behandlung:** Die Zeilen bei „verpasste Käufe“ nicht mitzählen. Echte verpasste Käufe: 632 − 279 = 353.

## 5. Doppelt vorgemerkte Teilverkäufe (22)

Gleiche Ursache, kein Geldfluss. Diese Zeilen nicht als eigene Verkaufssignale zählen.
