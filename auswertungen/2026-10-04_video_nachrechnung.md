# Video-Ideen nachgerechnet (04.10.2026)

Auftrag des Betreibers vom 04.10.: zwei Ideen aus den Videos (OrangieWEB3) an unseren aufgezeichneten Daten nachrechnen. Beide Ideen standen vorher fest. Gerechnet wurde nur mit vorhandenen Daten; Code und Daten wurden nicht geändert. Gerechnet hat der Helfer Strategie-Tester, nachgeprüft der Daten-Prüfer.

> **Ergebnis der Nachprüfung (Daten-Prüfer, ca. 05:45 UTC)**
> - **Wallet-Signal:** Die Zahl von 22 Signal-Coins und die Zeile „21 Trades, Ø −13,1 %“ ließen sich **nicht nachbauen**. Wie genau der Strategie-Tester „Signal“ abgegrenzt hat, ist unklar.
>   - Unabhängig gezählt ergeben sich je nach Abgrenzung 18 Signal-Coins (17 Trades, Ø −34,8 %, ohne Top 3 −43,2 %) oder 32 Signal-Coins (29 Trades, Ø −21,4 %).
>   - **Das Fazit „Signal hilft nicht“ hält also, eher noch deutlicher.** Die Einzelzahlen in Teil 1 sind aber unsicher.
>   - Bestätigt sind „nur 1 Wallet“ (576 Trades, Ø −9,8 %) und die Überschneidung mit der Hauptstrategie (14 Coins insgesamt).
> - **Verkauf in Stücken:**
>   - Bestätigt: Die Basis reproduziert die Regressionsprobe, es sind 96 Verläufe, 27 Gewinner, 53 enden bei der Notbremse.
>   - Die Summe der Basis lag bei der Nachprüfung bei −0,290 statt −0,275, vermutlich weil neue Kurszeilen dazukamen.
>   - Die Varianten selbst wurden **nicht** unabhängig nachgerechnet.

## 1. Wallet-Signal: Mindestens 2 unserer Copy-Wallets kaufen denselben Coin binnen 10 min

**Ergebnis: Das Signal hilft nicht.** Wer erst beim zweiten Kauf einsteigt, kommt zu spät. Die erste Wallet hat verdient, die Nachzügler haben verloren.

**Methode**
- Grundlage: `copy/journal.csv`, Aktion KAUF, nach Trader-Zeit; entfernte Wallets zählen mit.
- Zeitraum: 30.09. 10:06 bis 04.10. 05:00 UTC.
- 680 Coins insgesamt:
  - 22 mit Signal;
  - 608 nur von einer Wallet gekauft;
  - 50 mit mehreren Wallets, die aber mehr als 10 min auseinanderlagen.
- Fairer Vergleich mit **genau einem Trade je Coin:**
  - Bei Signal-Coins zählt unsere erste Copy-Position ab dem zweiten Kauf.
  - Bei Coins mit nur einer Wallet zählt die erste Position.
- Die Ergebnisse in % stammen aus `copy/konten.json` (geschlossene Positionen, echte Gebühren und Kurse enthalten).

| Variante | Trades | Gewinner | Summe SOL | Ø je Trade | Median | Ø ohne Top 3 |
|---|---|---|---|---|---|---|
| Signal, Einstieg beim 2. Kauf | 21 | 6 (29 %) | −0,49 | −13,1 % | −13,6 % | −20,7 % |
| Signal, Position der 1. Wallet (nur Vergleich, nicht umsetzbar) | 22 | 9 (41 %) | +0,20 | +12,8 % | −8,2 % | −7,9 % |
| Nur 1 Wallet | 575 | 105 (18 %) | −9,51 | −9,8 % | −21,9 % | −17,3 % |
| Kontrollgruppe ab 30.09. | 193 | 38 (20 %) | – | −12,1 % | −36,0 % | −16,0 % |

**Je Tag** (Ø je Trade, Signal gegen nur 1 Wallet):

| Tag | Signal | nur 1 Wallet |
|---|---|---|
| 30.09. | −24,6 % (n=5) | −18,6 % |
| 01.10. | −10,6 % (n=2) | −8,0 % |
| 02.10. | −9,3 % (n=8) | −2,8 % |
| 03.10. | −9,3 % (n=6) | −16,1 % |

Das Signal war nur am 03.10. besser.

**Breitere Zählung**
- Hier zählen auch verpasste, wegen Preisgrenze blockierte oder aus Geldmangel ausgelassene Wallet-Käufe (nicht aber Kleinstkäufe unter 0,1 SOL).
- Dann gibt es 40 Signal-Coins.
- Ergebnis: 32 Trades, Ø −4,8 %, Median −15,4 %, ohne Top 3 −23,7 %.
- Der Durchschnitt hängt an zwei Ausreißern: test +272 % und MAJOR +206 %.

**Kurs nach dem 2. Kauf**
- Gemessen als Vielfaches zum Kurs beim 2. Kauf, aus `copy/verlauf/`.
- Kursdaten gibt es nur für 14 von 22 Coins.

| Zeitpunkt | Signal (Median) | nur 1 Wallet (Median) |
|---|---|---|
| nach 10 min | 1,15x (n=8) | 1,00x |
| nach 30 min | 0,88x (n=7) | 0,91x |
| nach 60 min | 0,85x (n=6) | 0,93x |

- Signal-Coins: Hoch im Median 1,18x, Tief 0,61x.
- 3 von 14 erreichten 2x; 7 von 14 fielen auf 0,6x oder tiefer.
- Vorbehalt: Kurse gibt es nur, solange wir eine Position halten. Das verzerrt den Vergleich.

**Einzelne Trades**
- Beste: Agency (4DOV) +54 %, PUMPCHAN (Putrick) +23 %, www +22 %, STARS +15 %.
- Schlechteste: DOPPLER (Cooker) −81 %, Saw −48 %, FIX6900 −44 %, PRLS −44 %, LUCY −36 %.
- Die Signale gehen vor allem auf wenige Vieltrader zurück: 922M 5×, Zrool 5×, 4DOV 4×. 922M und Zrool sind inzwischen entfernt.

**Überschneidung mit unseren anderen Strategien**
- Hauptstrategie: 1 Signal-Coin (MINEPAD). Insgesamt teilt sie nur 14 von 680 Copy-Coins, das sind fast getrennte Welten.
- Kontrollgruppe: 6 Signal-Coins.
- Heiße Coins 6, Endspurt 2, Offene Tür 1.

**Häufigkeit**
- Etwa 5 Signale pro Tag (5 / 2 / 9 / 6), mit der breiten Zählung etwa 10.
- Für 200 Trades bräuchte man 3–6 Wochen.
- Eher werden es weniger, weil Vieltrader entfernt wurden.

**Fazit 1: Ein eigenes Experiment lohnt nicht.** Sicherheit mittel bis gering, weil es nur 21 Trades sind.
- Im Schnitt ist das Signal schlechter als die Coins mit nur einer Wallet.
- Gegen die Kontrollgruppe ist es kaum anders, ohne die Top 3 sogar schlechter.
- Vorschlag: etwa einmal pro Woche mit demselben Skript aus dem Journal nachrechnen. Dafür ist kein neuer Code nötig.

## 2. Verkauf in Stücken statt „Hälfte bei 2x“

**Ergebnis: Je ein Drittel bei 1,5x, 2x und 3x schneidet etwas besser ab als die heutige Regel.** Das gilt auch ohne die Top 3 und für alte wie neue Tage. Mit Kosten bleiben aber alle Varianten im Minus.

**Methode**
- Jede Zeile eines Verlaufs läuft durch das unveränderte `bot.manage_positions`, genau wie in der Regressionsprobe.
- Der eingebaute Teilverkauf ist abgeschaltet. Die Stufen verkauft ein vorgeschalteter Schritt über `bot.sell`: höchstens eine Stufe je Durchlauf, wie im Bot.
- Alle anderen Ausstiege bleiben unverändert: Notbremse, These, Liquidität, Gewinnschutz, Abstand zum Hoch und Haltedauer.
- Die Basis reproduziert die Regressionsprobe exakt: 33 Verläufe, −0,0204 SOL, jeder Coin mit gleichem Verkaufsgrund.
- Neu dazu: 63 Verläufe der Hauptstrategie vom 30.09. bis 04.10. Zusammen sind es 96.
- „Roh“ heißt ohne Gebühren. „Mit Kosten“ heißt: 3 % auf 0,2 SOL plus 0,0015 SOL je Transaktion, einschließlich jedes Teilverkaufs.

| Variante (96 Verläufe) | Gewinner | Summe roh | Median | Ohne Top 3 | Summe mit Kosten | Verkäufe |
|---|---|---|---|---|---|---|
| **Heute:** ½ bei 2x | 27 | −0,275 | −0,081 | −1,460 | −1,171 | 117 |
| ⅓ bei 1,5x / 2x / 3x | 39 | +0,009 | −0,081 | −1,031 | −0,942 | 154 |
| ⅓ bei 1,5x / 2x / 3x, Abstand zum Hoch ab 1,5x | 39 | **+0,123** | −0,081 | **−0,916** | **−0,825** | 152 |
| ¼ bei 1,5x / 2x / 3x / 5x | 39 | −0,168 | −0,081 | −1,275 | −1,130 | 161 |
| ¼ bei 1,5x / 2x / 3x / 5x, Abstand zum Hoch ab 1,5x | 39 | −0,005 | −0,081 | −1,112 | −0,964 | 159 |
| ⅓ bei 2x / 3x, Rest mit Abstand zum Hoch | 27 | −0,239 | −0,081 | −1,438 | −1,145 | 124 |

- **Je Trade mit Kosten:** heute −0,0122 SOL, beste Variante −0,0086 SOL.
- **Alt und neu getrennt** (roh, beste Variante gegen heute):
  - 27.–29.09.: +0,113 gegen −0,020
  - 30.09.–04.10.: +0,010 gegen −0,255

**Je Tag** (roh, beste Variante gegen heute):

| Tag | Heute | Beste Variante |
|---|---|---|
| 27.09. | +0,39 | +0,51 |
| 28.09. | −0,27 | −0,18 |
| 29.09. | −0,14 | −0,22 |
| 30.09. | −0,54 | −0,44 |
| 01.10. | +0,27 | +0,21 |
| 02.10. | −0,48 | −0,31 |
| 03.10. | +0,59 | +0,56 |
| 04.10. | −0,10 | −0,01 |

An 5 von 8 Tagen ist die Variante besser.

**Was das bedeutet**
- Der Median ist überall gleich: Der typische Coin erreicht nie 1,5x und endet bei der Notbremse (53 von 96).
- **Gekostet** hat die Variante bei Läufern, die früh teilweise verkauft wurden: SPEC −0,207, Liza −0,125, BORN −0,090.
- **Gespart** hat sie viele kleine Beträge bei Coins, die kurz 1,5x erreichten und dann zurückfielen (z. B. SOCIALBAGS +0,113, CHAMBER +0,096, PROMPT +0,093). Der Vorteil hängt also nicht an einem einzelnen Trade.
- **Gebühren:** 35 Verkäufe mehr, rund 0,05 SOL; das ist in „mit Kosten“ schon enthalten. Die Simulation verkauft genau zum Stufenkurs, echte Kurse wären etwas schlechter.
- **48 h statt 24 h halten ist nicht messbar:** Der längste Verlauf reicht nur 9,7 h ab Kauf. Keine Position erreichte die 24-h-Grenze.

**Fazit 2: Ein Experiment lohnt sich.** Sicherheit gering bis mittel.
- **Dafür:** Der Vorteil hält ohne die Top 3, an alten und neuen Tagen und an 5 von 8 Tagen.
- **Dagegen:**
  - Es sind nur 96 Verläufe.
  - 6 Varianten wurden getestet, die beste also hinterher ausgewählt.
  - „Abstand zum Hoch ab 1,5x“ ist eine Zusatzvariante des Helfers.
  - Der Vorteil ist klein (etwa +0,004 SOL je Trade) und dreht das Ergebnis nicht ins Plus.
- **Vorschlag (nur mit Zustimmung):** Experiment „Drittel-Leiter“. Es kauft genau wie die Hauptstrategie (aufgebaut wie Notbremse 25) und verkauft je ⅓ bei 1,5x / 2x / 3x, sonst mit gleichen Ausstiegen. Urteil nach 200 Trades, gegen die Hauptstrategie mit denselben Käufen und gegen die Kontrollgruppe, auch ohne die Top 3. Die Hauptstrategie bleibt unverändert.

Skripte (nur lokal im Scratchpad, nicht im Repository): `leiter.py`, `lauf2.py` und `wsignal.py`.
