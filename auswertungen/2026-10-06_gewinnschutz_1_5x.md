# Gewinnschutz ab 1,5x: Wirkung und "87 Verlierer"

Stand 06.10.2026 (Strategie-Tester, nur gerechnet, nichts am Code geändert). Skripte liegen im Temp-Ordner, nicht im Repo.

## 1. Ergebnis in einem Satz

Die Regel "Gewinn geschützt" ist in **allen** Konten schon aktiv, auch in den Experimenten. Es gibt also keine Konten ohne die Regel, in denen man sie nachrüsten könnte. Die Rückrechnung zeigt außerdem: Die Regel hilft (ca. +1,8 SOL gegenüber "ohne Regel" bei 687 Trades), und die getesteten Varianten (früher, später, höherer Boden) sind nicht besser.

## 2. Die Zählung (Trades mit Hoch >= 1,5x und Ende im Minus)

Ich komme auf **151**, nicht auf 87 (alle Konten, `closed`, `peak_multiple>=1.5` und `pnl_sol<0`). Seit 04.10. sind es 84, ohne die beendeten Konten (ohne_limit, endspurt_ohne_filter) 143. Die 87 passen am ehesten zu "seit ca. 04.10.". Summe Verlust: **-4,18 SOL** (Ø -0,028 je Trade, Einsatz immer 0,2 SOL).

Je Konto (Anzahl, Verlust SOL):

| Konto | Trades | Verlust |
|---|---|---|
| offene_tuer | 46 | -1,26 |
| kontrollgruppe | 43 | -1,11 |
| haupt | 19 | -0,69 |
| heisse_coins | 19 | -0,59 |
| serien_devs | 10 | -0,26 |
| ohne_limit (beendet) | 8 | -0,13 |
| notbremse_25 | 5 | -0,13 |
| drittel_leiter | 1 | -0,02 |
| endspurt, zweite_welle | 0 | 0 |

Je Verkaufsgrund:

| Grund | Trades | Verlust |
|---|---|---|
| GEWINN_GESCHUETZT | 138 | -2,77 |
| NOTBREMSE | 11 | -1,28 |
| LIQUIDITAET_ABGEZOGEN | 1 | -0,08 |
| THESE_GEBROCHEN | 1 | -0,06 |

Wichtig: 138 von 151 sind **schon durch die Regel verkauft worden**. Ihr "Verlust" ist der Rest nach Kosten und Schlupf: Ø -10 % (Median -7 %, schlimmster -45 %). Die Regel verkauft nicht genau bei 1,0x, weil der Kurs zwischen zwei Prüfungen (ca. 12 s) durchrutscht und die Rundlaufkosten (ca. 3 %) dazukommen. Die 11 Notbremse-Fälle (Hoch 1,5-2,0x, dann Absturz bis -40 % in einem Sprung) hat die Regel nicht fangen können.

Wo steht die Regel? `bot.py` Z.141/142 (`PROTECT_AT_MULTIPLE = 1.5`, `PROTECT_FLOOR_MULTIPLE = 1.0`) und Z.1563 in `manage_positions`. Das ist die gemeinsame Verkaufsfunktion; keine Experiment-Weiche schaltet sie ab. Ausnahmen:
- **Endspurt-Konten** haben eigene Ausstiege (`exit_mode endspurt`: KURVE_ZURUECK, GRADUIERT, ZEIT_STOP). Dort 0 Trades der Gruppe.
- **drittel_leiter** setzt `tp1_done` schon beim Aufstieg der Leiter (Z.1533); die Regel greift dort nur vor der ersten Stufe (1 Fall).
- Vor dem 28.09. gab es die Regel nicht (2 Verlierer vom 26./27.09.).

## 3. Würde Gewinnschutz in Konten ohne die Regel helfen?

Die Frage stellt sich nicht, weil alle Konten sie haben. Stattdessen habe ich über die aufgezeichneten Verläufe (`verlauf/*.csv`, Phasen offen und nach_verkauf, 6 h nach Verkauf) die echte `manage_positions` nochmal laufen lassen, mit verschiedenen Einstellungen, in einer Kopie ohne Netz (wie `tests/test_regression.py`). Kosten für alle Varianten gleich: 3 % Rundlauf, 1 % Schlupf je Verkauf, 0,0015 SOL je Transaktion.

Konten mit Nachverkauf-Verlauf (haupt, offene_tuer, serien_devs, notbremse_25, ohne_limit): **687 Trades**, nur hier ist "ohne Regel" gültig. Erste Hälfte = zeitlich frühere 344, zweite Hälfte 343.

| Variante (Auslöser / Boden) | Trades | Gewinner | Summe SOL | Ø je Trade | ohne Top 3 | 1. Hälfte | 2. Hälfte |
|---|---|---|---|---|---|---|---|
| A aktuell (1,5x / 1,0) | 687 | 143 | -19,99 | -0,0291 | -21,74 | -8,38 | -11,61 |
| B ohne Gewinnschutz | 687 | 156 | -21,84 | -0,0318 | -23,58 | -8,74 | -13,09 |
| C früher (1,3x / 1,0) | 687 | 118 | -22,69 | -0,0330 | -24,33 | -9,88 | -12,80 |
| D Boden 1,2 (1,5x / 1,2) | 687 | 202 | -20,00 | -0,0291 | -21,75 | -8,35 | -11,65 |
| E Boden 1,1 (1,5x / 1,1) | 687 | 170 | -21,43 | -0,0312 | -23,18 | -9,00 | -12,43 |
| F (1,3x / 1,1) | 687 | 179 | -23,19 | -0,0338 | -24,83 | -9,88 | -13,31 |
| G später (1,7x / 1,0) | 687 | 149 | -21,54 | -0,0313 | -23,28 | -9,06 | -12,47 |

(Die absoluten Summen sind stark negativ, weil der Nachbau grob ist und die Kosten voll abgezogen werden; maßgeblich ist der **Unterschied** zwischen den Zeilen. Die Summen weichen von den echten Kontoständen ab.)

Gewinnschutz (A) gegen ohne (B): **+1,84 SOL**, in beiden Hälften besser (+0,36 und +1,48). Das hält auch ohne die 3 besten Trades (+1,84 bleibt, da Top 3 in beiden Läufen fast gleich).

Konten ohne Nachverkauf-Pfad (kontrollgruppe, heisse_coins; 492 Trades): hier gibt es keine Kurse nach dem Verkauf, "ohne Regel" lässt sich nicht rechnen, nur frühere Ausstiege. A: -4,64; C: -5,37; D: -5,14; E: -4,80; F: -5,90. Auch hier ist A am besten.

### Pro Tag (Unterschied B minus A; positiv = ohne Regel besser)

| Tag | Trades | B-A |
|---|---|---|
| 27.09. | 11 | -0,18 |
| 28.09. | 13 | -0,16 |
| 29.09. | 13 | -0,13 |
| 30.09. | 19 | **+0,89** |
| 01.10. | 32 | +0,39 |
| 02.10. | 36 | -0,33 |
| 03.10. | 30 | -0,07 |
| 04.10. | 208 | -0,77 |
| 05.10. | 168 | -0,89 |
| 06.10. | 157 | -0,59 |

Die Regel ist an 8 von 10 Tagen besser; am 30.09. und 01.10. wäre ohne sie besser gewesen (Coins wie CHAMBER, CHONK).

### Was die Regel kostet und was sie spart (Nachbau, 73 Trades, bei denen sie griff)

- **Vermiedene Verluste:** In 57 von 73 Fällen wäre es ohne Regel schlechter gewesen, meist Notbremse (46 Mal). Größte: SHARKTANK (-0,20 statt -0,01), AZZ (-0,18 statt -0,01), Stompy, GENESIS, STABLES, CLANKER, OFF, ARCADE (je -0,12 bis -0,18 statt ca. -0,01 bis -0,03).
- **Verpasste Gewinner:** In 14 von 73 Fällen wäre ohne Regel mehr drin gewesen, Coins, die nach dem Rücksetzer auf Einstand weiter stiegen (STORY_ABGEKUEHLT als Ausgang): CHAMBER (+0,40 in haupt und ohne_limit), CHONK (+0,27), SC, ACTIII, XFUNPAD (je ca. +0,15), CHONKS (+0,13). Das sind wenige, aber große Ausreißer.
- Kleine Kante: Variante D (Boden 1,2) gewinnt viele kleine Plus-Trades (202 Gewinner), die Summe bleibt aber gleich (-20,00 gegen -19,99), also kein Nutzen.

## 4. Unsicherheit

- Der Nachbau stimmt beim Verkaufsgrund nur zu 63 % mit der Wirklichkeit überein (Aufzeichnung ca. alle 12-60 s, echte Prüfung etwas anders getaktet). Er ist eine Näherung.
- "Ohne Regel" endet bei 2-3 % der Fälle offen (nur 6 h nach Verkauf aufgezeichnet).
- Die Experimente teilen sich oft dieselben Coins (offene_tuer ist mit 351 Trades prägend); die Trades sind nicht unabhängig.
- drittel_leiter, Endspurt-Konten und zweite_welle sind im Nachbau nicht enthalten.

## 5. Empfehlung

- Urteil: **Regel behalten, nichts ändern.** Sie ist überall schon da und der Test zeigt kleinen, stabilen Nutzen (+1,8 SOL auf 687 Trades, besser in beiden Hälften und an 8 von 10 Tagen). Sicherheit: **mittel** (Näherung, aber klare Richtung).
- Die "87 Verlierer" sind kein Beleg gegen die Regel: 138 der 151 wurden von ihr verkauft; der Verlust (Ø -10 %) kommt aus Durchrutschen und Kosten. Eine Verschiebung auf 1,2 oder einen früheren/späteren Auslöser bringt nichts. Verwerfen.
- Möglich zum weiter Beobachten: Wie oft rutscht der Kurs bei GEWINN_GESCHUETZT deutlich unter 1,0x (Median -7 %)? Wenn die Prüfung für Positionen mit Hoch >= 1,4x häufiger liefe, könnte das den Schlupf drücken. Das ist nur ein Ideenhinweis, noch nicht gerechnet.
- Offen: Wenn der Betreiber "87" aus einer anderen Zählung hat (z. B. Dashboard-Filter), bitte das Datum nennen, dann prüfe ich dieselbe Auswahl.
