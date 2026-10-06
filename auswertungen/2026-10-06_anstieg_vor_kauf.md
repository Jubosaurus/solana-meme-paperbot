# Anstieg vor dem Kauf: Filter "kein Kauf wenn Anstieg < X %" (06.10.2026)

## Ergebnis in einem Satz
Die Spur "Verlierer vorher weniger gestiegen (16 % vs. 25 %)" lässt sich nicht bestätigen: Sie ließ sich nicht nachbauen, und der Unterschied zeigt in Hauptstrategie plus Kontrollgruppe in die falsche Richtung. Ein Filter nach dem Anstieg ist nicht belegt.

## Woher die Spur kommt
In `2026-10-05_verlustserie_kleiner_setzen.md` steht die Zahl nicht. Ich habe beide möglichen Merkmale geprüft: `entry_view.price_change_5m` (Anstieg 5 min) und `price_change_1h` (Anstieg 1 h). Beide Merkmale zu prüfen heißt: zwei Tests, zusätzlich viele Schwellen. Die Zahlen sind also schon mehrfach getestet.
Das ist eine Hypothese aus den Daten (hinterher gefunden), nicht vorher formuliert.

## Methode
- Alle abgeschlossenen Trades, 1.792 Trades in 11 Konten, 26.09.-06.10.
- Gleicher Coin in mehreren Konten innerhalb von 30 min = ein Ereignis (Mittel der Konten). Das ergibt 1.222 Ereignisse (Merkmal 5 min).
- Zeitlich in zwei gleich große Hälften geteilt (ältere Hälfte H1, neuere H2).
- SOL-Werte sind `pnl_sol` aus dem Portfolio. Darin stecken Kosten (ca. 3 % Hin- und Rückweg) und Gebühren bereits.
- Alle Konten kaufen 0,2 SOL je Trade.

## 1) Gewinner gegen Verlierer: Anstieg 5 min (Mittel / Median in %)
| Gruppe | Hälfte | Ereignisse | Gewinner | Verlierer |
|---|---|---|---|---|
| Haupt + Kontrolle | H1 | 230 | 10 / 7 | 14 / 4 |
| Haupt + Kontrolle | H2 | 230 | 4 / 3 | 10 / 6 |
| Alle Konten | H1 | 611 | 55 / 28 | 59 / 17 |
| Alle Konten | H2 | 611 | 30 / 15 | 21 / 12 |

- Haupt + Kontrolle: Gewinner sind in beiden Hälften vor dem Kauf weniger gestiegen (Mittel). Das ist das Gegenteil der Spur. Rang-Korrelation Anstieg zu Gewinn: -0,02 und +0,01, also null.
- Alle Konten: Mittel mal höher, mal niedriger, Median bei Gewinnern höher. Korrelation +0,10 und +0,08, schwach.
- Anstieg 1 h: Gewinner liegen im Median bei Haupt + Kontrolle in beiden Hälften unter oder etwa gleich den Verlierern. Korrelation -0,13 und -0,09. Auch hier kein Hinweis für "mehr Anstieg ist besser".
- Die genannten 16 % vs. 25 % tauchen in keiner Kombination auf.

## 2) Filterregel "kein Kauf wenn Anstieg 5 min < X %" (Summe SOL der behaltenen / ausgefilterten Trades, Ereignisse)

### Haupt + Kontrolle (je 230 Ereignisse pro Hälfte)
| X | H1 behalten | H1 ausgef. | H2 behalten | H2 ausgef. | H2 ausgefiltert: Gew/Verl | H2 behalten ohne Top 3 |
|---|---|---|---|---|---|---|
| 0 | 142: -2,17 | 88: -2,86 | 140: -2,81 | 90: -2,47 | 20/70 | -4,03 |
| 10 | 86: -2,17 | 144: -2,86 | 94: -2,56 | 136: -2,72 | 34/102 | -3,68 |
| 15 | 68: -2,02 | 162: -3,00 | 67: -1,49 | 163: -3,79 | 39/124 | -2,61 |
| 30 | 40: -1,80 | 190: -3,22 | 26: -1,57 | 204: -3,71 | 49/155 | -2,03 |

Ohne Filter H2: 230 Trades, -5,28 SOL (ohne Top 3: -6,50).
Der Filter "spart" nur, weil er weniger Trades macht. Pro Trade ist das Ergebnis der behaltenen Trades nicht besser, sondern bei X = 30 sogar klar schlechter:
- X = 30, H1: Ø -0,045 SOL behalten gegen -0,017 ausgefiltert.
- X = 30, H2: Ø -0,060 SOL behalten gegen -0,018 ausgefiltert.
- X = 15, H2: -0,022 gegen -0,023, praktisch gleich.
- Die Unterschiede liegen in keinem Fall außerhalb der Zufallsspanne (Bootstrap-Intervall schließt 0 ein, bei X = 30 knapp negativ).
- Die Kontrollgruppe allein hat bei Anstieg >= 30 % die schlechtesten Trades (+Verlust je Trade höher als bei den Hauptstrategie-Käufen).

### Alle Konten (je 611 Ereignisse pro Hälfte)
| X | H1 Ø behalten | H1 Ø ausgef. | H2 Ø behalten | H2 Ø ausgef. |
|---|---|---|---|---|
| 10 | -0,0159 | -0,0172 | -0,0300 | -0,0320 |
| 15 | -0,0134 | -0,0200 | -0,0285 | -0,0330 |
| 30 | -0,0156 | -0,0169 | -0,0186 | -0,0346 |

- Nur bei X = 30 in H2 sieht es besser aus (141 Trades, -2,62 SOL gegen -16,27 SOL der ausgefilterten 470). In H1 gibt es denselben Effekt nicht (Ø -0,0156 gegen -0,0169, gleich). In H1 findet sich also keine Schwelle, die in H2 bestätigt werden könnte. Der Test "in H1 finden, in H2 bestätigen" scheitert.
- Erklärung für H2: Zusammensetzung der Konten, kein echter Filtereffekt. Anstieg >= 30 % haben fast nur `endspurt` (66 %), `endspurt_ohne_filter` (94 %), `serien_devs` (45 %), `zweite_welle`. `offene_tuer` (353 Trades, Ø -0,040) hat nie einen Anstieg >= 30 %. Der Filter wirft also vor allem das schlechteste Konto raus, nicht schlechte Coins.
- Ohne die Top 3 H2: Ohne Filter -20,39 SOL, mit Filter X = 30 -3,69 SOL. Der Ausfall bleibt, aber das Ergebnis bleibt negativ und beruht auf Konto-Mix.

## 3) Was die Regel gekostet und gespart hätte
(Haupt + Kontrolle, X = 15, H2, 163 ausgefilterte Trades) 39 Gewinner verpasst, 124 Verlierer vermieden. Verlust vermieden -3,79 SOL, aber auch Gewinne verpasst: Netto +3,79 weniger Verlust nur durch Weglassen, pro Trade kein Vorteil. Konkrete Coins: nicht einzeln aufgelistet, weil kein belegter Effekt.
Anstieg 1 h: Filter "mindestens +200 %" wirft viele Verlierer raus, aber auch bis zu 35 Gewinner; in H1 bei Haupt + Kontrolle ebenfalls kein Pro-Trade-Vorteil, die Summen schwanken nur wegen weniger Trades.

## 4) Warnungen
- Mehrfachtests: 2 Merkmale x 2 Gruppen x 2 Hälften x 6-8 Schwellen = rund 50 Vergleiche. Einzelne "gute" Zeilen sind bei so vielen Tests zu erwarten.
- Gesamtergebnis ist negativ (H+K: -10,3 SOL über 460 Ereignisse). Jeder Filter, der Trades weglässt, sieht deshalb "besser" aus. Maßstab ist der Durchschnitt je Trade, nicht die Summe.
- Hohe Anstiege sind Ausreißer (1-h-Anstieg bis in die Tausende Prozent): Mittelwerte sind unzuverlässig, Medians zählen.
- Stichprobe H+K: nur 26-94 Trades hinter den Schwellen, unter 200: nur Tendenz.
- Tage nicht einzeln getrennt (Hälften = ca. 5 Tage je); in H2 wirkt nur die Kontomischung.

## Empfehlung
Verwerfen (Sicherheit: mittel). Keine Regel "kein Kauf bei Anstieg < X %" einführen: nicht in beiden Hälften bestätigt, Richtung bei Haupt + Kontrolle sogar umgekehrt, Effekt bei allen Konten ist Konto-Mischung. Nächstes: nichts bauen. Wenn der Betreiber es trotzdem will, als eigenes Experiment mit zufälliger Hälfte (Kontrollgruppen-Prinzip) laufen lassen, frühestens Urteil bei 200 Trades.

Skripte: Scratchpad (nicht im Repository). Keine Dateien geändert außer diesem Bericht.
