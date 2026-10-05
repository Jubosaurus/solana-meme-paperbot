# Idee "nach Verlustserie kleiner setzen" – Rückrechnung (05.10.2026)

Herkunft der Idee: Video rasmr (vorher formuliert, nichts beschlossen). Nur gerechnet, kein Code geändert. Skripte liegen im Temp-Ordner (nicht im Repository).

## Ergebnis in einem Satz
Auf den Papier-Konten spart die Regel Geld, aber fast nur, weil die Strategien im Schnitt verlieren und man dann mit weniger Einsatz weniger verliert. Gegenüber einer zufällig umgemischten Reihenfolge ist der Mehrwert klein und nicht belegt (Hauptstrategie plus Experimente: +0,7 SOL, p = 0,25). Beim Copy-Trading schadet sie.

## Definitionen
- Quelle Hauptstrategie und Experimente: `closed` in `portfolio.json` und `experimente/*/portfolio.json` (pro Konto, nach Schließzeit sortiert). Dort ist das Ergebnis `pnl_sol` (Roundtrip-Kosten ca. 3 % stecken schon in den Preisen). Dazu 0,003 SOL Gebühr (2 x 0,0015) je Trade, fest, also nicht mitskaliert.
- Copy: `copy/konten.json` -> `geschlossen` je Wallet. `pnl_sol` enthält schon die Gebühren (`fees_sol`), die ebenfalls fest bleiben.
- Verlust = Ergebnis nach Gebühren bei voller Größe < 0. Die Serie zählt immer nach diesem Vollgrößen-Ergebnis. Nach einem Gewinn (oder 0) geht der Zähler auf 0 zurück, sofort wieder volle Größe.
- Regel: Nach N Verlusten in Folge wird der nächste Trade mit Faktor F skaliert (Gewinn und Verlust x F, Gebühr bleibt).
- Vereinfachungen: Kontostand und Kapitalmangel (z. B. Kontrollgruppe fast leer) bleiben unberücksichtigt, Teilverkäufe werden als ein Trade gezählt. Die Konten laufen parallel und kaufen teils dieselben Coins, die Summen sind also nicht unabhängig.
- Zufallsvergleich: Reihenfolge je Konto 300 bis 2000 Mal gemischt, jedes Mal Regel gegen ohne Regel. Zeigt, was die Regel "einfach durch weniger Einsatz" bringt.

## Hauptstrategie + 10 Experimente (N=3, F=0,5), je Konto
| Konto | Trades | ohne Regel | mit Regel | Differenz | Regel griff | Max-DD vorher -> nachher | Zufall: p* |
|---|---|---|---|---|---|---|---|
| Haupt | 143 | -0,631 | -0,587 | +0,044 | 53 | 2,58 -> 2,03 | 0,44 |
| kontrollgruppe | 288 | -8,587 | -6,508 | +2,079 | 146 | 8,59 -> 6,51 | 0,43 |
| offene_tuer | 199 | -9,092 | -5,735 | +3,357 | 128 | 9,40 -> 5,76 | 0,02 |
| endspurt_ohne_filter | 280 | -4,257 | -3,419 | +0,838 | 74 | 4,39 -> 3,56 | 0,07 |
| endspurt | 188 | -1,831 | -1,916 | -0,084 | 39 | 2,57 -> 2,47 | 0,81 |
| heisse_coins | 130 | -3,043 | -2,982 | +0,061 | 68 | 3,30 -> 3,11 | 0,86 |
| ohne_limit | 63 | -1,505 | -0,902 | +0,603 | 29 | 2,13 -> 1,53 | 0,12 |
| serien_devs | 40 | -0,616 | -0,438 | +0,178 | 22 | 1,58 -> 1,09 | 0,33 |
| notbremse_25 | 32 | -0,460 | -0,639 | -0,178 | 16 | 0,74 -> 0,64 | 0,91 |
| drittel_leiter | 28 | -0,041 | -0,202 | -0,161 | 7 | 0,86 -> 0,72 | 0,84 |
| zweite_welle | 17 | +0,438 | +0,309 | -0,128 | 5 | 0,48 -> 0,39 | 0,66 |
| **Summe** | **1408** | **-29,625** | **-23,018** | **+6,607** | **587** | **36,6 -> 27,8** | |

*p = Anteil zufällig umgemischter Reihenfolgen, in denen die Regel mindestens so gut abschneidet. Niedrig (< 0,05) hieße "Serien wirken wirklich". grosse_coins und listing_welle haben noch keine Trades. Konten unter 30 Trades (drittel_leiter, zweite_welle, notbremse_25 knapp) nur als Tendenz.

Ohne die 3 besten Trades je Konto: ohne Regel -42,095, mit Regel -32,115 (Vorteil bleibt, +10,0). Das sagt aber nur, dass die Strategien ohne ihre Ausreißer noch schlechter sind; die Regel wirkt wie ein Rabatt auf Verluste.

## Varianten (Summe aller 11 Konten, Differenz zu "ohne Regel" -29,625)
| Schwelle N | Faktor | Regel griff | Mit Regel | Differenz | Max-DD (vorher 36,6) | ohne Top 3 (vorher -42,1) | Konten besser |
|---|---|---|---|---|---|---|---|
| 2 | 0,5 | 771 | -21,09 | +8,54 | 25,8 | -29,69 | 8/11 |
| 3 | 0,5 | 587 | -23,02 | +6,61 | 27,8 | -32,12 | 7/11 |
| 4 | 0,5 | 448 | -24,69 | +4,93 | 29,8 | -34,64 | 6/11 |
| 5 | 0,5 | 346 | -25,47 | +4,15 | 31,1 | -35,83 | 6/11 |
| 2 | 0,25 | 771 | -16,82 | +12,81 | 20,6 | -23,49 | 8/11 |
| 3 | 0,25 | 587 | -19,72 | +9,91 | 23,8 | -27,12 | 7/11 |
| 4 | 0,25 | 448 | -22,23 | +7,40 | 26,8 | -30,92 | 6/11 |
| 5 | 0,25 | 346 | -23,40 | +6,23 | 28,8 | -32,69 | 6/11 |

Je kleiner der Einsatz und je früher die Regel greift, desto besser: das ist das Muster von "weniger Einsatz in einer verlierenden Strategie", nicht von Serien-Wissen.

## Ist es mehr als Zufall? (Kernfrage)
Pooled über alle Konten, gegen umgemischte Reihenfolge:
| Variante | echt | Zufalls-Mittel | Mehrwert | p |
|---|---|---|---|---|
| N=3 F=0,5 | +6,61 | +5,92 | +0,69 | 0,25 |
| N=3 F=0,25 | +9,91 | +8,87 | +1,04 | 0,26 |
| N=2 F=0,5 | +8,54 | +7,63 | +0,91 | 0,17 |
| N=4 F=0,5 | +4,93 | +4,75 | +0,18 | 0,45 |

Fast der ganze Gewinn (ca. 90 %) kommt auch bei zufälliger Reihenfolge. Der echte "Serien-Effekt" ist klein: Nach 3+ Verlusten ist die Verlustquote 76,8 % (587 Trades), sonst 71,4 % (821 Trades). Leichte Häufung, aber nicht belastbar, und die Konten sind nicht unabhängig (gleiche Coins zur gleichen Zeit).

## Tage getrennt (Hauptstrategie + Experimente, N=3, F=0,5; Differenz SOL)
| Tag | Trades | ohne | mit | Diff |
|---|---|---|---|---|
| 26.09. | 19 | +0,81 | +0,61 | -0,20 |
| 27.09. | 10 | -0,11 | -0,19 | -0,08 |
| 28.09. | 13 | -0,18 | -0,20 | -0,03 |
| 29.09. | 55 | -1,92 | -1,70 | +0,22 |
| 30.09. | 134 | -3,25 | -2,04 | +1,21 |
| 01.10. | 203 | -4,55 | -3,99 | +0,56 |
| 02.10. | 233 | -3,62 | -3,17 | +0,44 |
| 03.10. | 227 | -4,05 | -2,94 | +1,11 |
| 04.10. | 345 | -8,89 | -6,65 | +2,24 |
| 05.10. | 169 | -3,87 | -2,74 | +1,13 |

Die Regel hilft an Tagen mit Verlust und kostet an Tagen mit Gewinn (26.09., einziger Plustag: -0,20). Sie wirkt also nur als Bremse, nicht als Treffer-Verbesserung. 04.10. hat zusätzlich viele Trades durch neue Experimente.

## Was die Regel gekostet und gespart hätte (N=3, F=0,5)
- Hauptstrategie + Experimente: 587 Trades mit halber Größe. Davon 136 Gewinner (zusammen +20,9 SOL, halbiert = 10,5 SOL verschenkt) und 451 Verlierer (zusammen -35,9 SOL, halbiert = 18,0 SOL gespart). Netto +7,5 vor Gebühren-Effekt (Gebühren wirken gleich).
- Größte verpasste Gewinner (Anteil, der durch Halbierung fehlt): www (heisse_coins) 0,65; LIFE (serien_devs) 0,29; CLAUDIA (heisse_coins) 0,25; LIFE (heisse_coins) 0,25; BACKERS (offene_tuer) 0,22.
- Vermiedene Verlierer sind überwiegend viele gleich kleine (je ca. 0,1 SOL, z. B. Pumpkinu, SUPERIOR, WISP, SCAT, JOEkin); kein Einzel-Rettungsfall.
- Die Regel kostet also nichts Spektakuläres, aber sie nimmt auch bei Gewinn-Phasen etwas weg.

## Zusatz: Copy-Trading (klar getrennt, nur als Hinweis)
Die Wallets haben sehr unterschiedliche Größe (922M 678 Trades, Zrool 134, HEBO 98, Putrick 229, 6ANG 67; viele Wallets unter 30 Trades). Ergebnis N=3, F=0,5: ohne Regel -38,72, mit Regel -46,41 (Differenz -7,69), Regel griff 635 Mal, Max-DD (Summe der Einzel-DDs) 83,4 -> 71,0.
- Warum schlecht: Der große Gewinner PIGEON bei HEBO (+32 SOL, mit halber Größe 16 SOL verpasst) kam nach einer Verlustserie. HEBO allein: +26,47 -> +12,47. Ohne HEBO-Ausreißer wäre das Bild anders, aber dann ist es ein Einzelfall.
- Gegen Zufall: echt -7,69, Zufalls-Mittel -0,19, Streuung 8,4 (p = 0,76). Ohne 922M (entfernt): -9,48 vs. -0,56.
- Besser mit Regel: Zrool +6,1 (p 0,11), 922M +1,8; schlechter: HEBO -14,0, 6ANG -1,7, Putrick -1,0. Nur 11 von 27 Wallets verbessert. Schwellen 4 und 5 sind schlechter (-11,9 bzw. -13,8).
- Ohne die 3 besten Trades je Wallet: -94,1 -> -77,9 (Regel "besser", da dann nur Verlierer übrig). Auch hier: kein Beleg.
- Copy folgt dem Trader; dessen Gewinne kommen oft aus wenigen großen Treffern. Einsatz nach Serien zu senken nimmt diese Treffer mit.

## Fazit und Sicherheit
- Hauptstrategie/Experimente: Differenz positiv (+6,6 SOL), Mehrwert gegenüber Zufall nur +0,7 SOL (p = 0,25). Nicht belegt. Nur offene_tuer (p = 0,02) und knapp endspurt_ohne_filter (p = 0,07) sehen auffällig aus, bei 11 Konten ist ein p = 0,02 aber zu erwarten und die Konten sind nicht unabhängig; es sind Funde im Nachhinein.
- Die Regel verkleinert Verluste, solange die Strategie verliert. Sie macht keine verlierende Strategie gewinnend und senkt den Gewinn einer gewinnenden (zweite_welle, 26.09.: leicht negativ). Wer weniger riskieren will, erreicht dasselbe mit einer festen kleineren Größe.
- Copy: Regel schadet (HEBO-Ausreißer).
- Sicherheit: gering bis mittel für "kein echter Mehrwert über kleinere Größe hinaus".

Empfehlung (ohne Umsetzung, Entscheidung beim Betreiber): nicht übernehmen. Sinnvoll wäre höchstens ein Test als Experiment später, wenn eine Strategie nachweislich positiv ist (dann könnte man den Gewinnverlust messen), und frühestens bei 200 Trades je Konto, gleichzeitig gegen eine feste halbe Größe vergleichen. Alle Zahlen ohne Kapitalgrenzen gerechnet; Stand 05.10.2026.
