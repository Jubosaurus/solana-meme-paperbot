# Prüfung Backtest-Plan (07.10.2026, Stand Daten ca. 22:10 UTC)

Alles per DuckDB/Python an den Rohdateien im Hauptordner nachgerechnet.

| Nr | Behauptung | Nachgerechnet | Urteil |
|---|---|---|---|
| 1a | Coins/Tag 01.-06.10. ca. 2.330-2.610 | 2.575 / 2.510 / 2.533 / 2.536 / 2.329 / 2.613 | bestätigt |
| 1b | Coins nicht nur STORY_ZU_ALT 430-580 | 582 / 560 / 523 / 578 / 491 / 582 (Spanne 491-582) | korrigiert: 490-580 |
| 1c | Zeilen/Tag ca. 13.000-15.800 | 15.143 / 15.533 / 15.391 / 15.803 / 12.816 / 15.615 | bestätigt (05.10. mit 12.816 knapp darunter) |
| 1d | 23 MB, ca. 144 Byte/Zeile | 23.495.195 Byte, 159.972 Zeilen = 146,9 Byte/Zeile | bestätigt (147 statt 144) |
| 2 | Seit 05.10. STORY_ZU_ALT 37.000 von 41.900 (89 %) | 37.162 von 41.844 = 88,8 % | bestätigt |
| 3a | copy/journal KAUF 4.090; SCHATTEN_KAUF 573; VERPASST_KAUF 1.017 | 4.090 / 573 / 1.017 | bestätigt |
| 3b | Verzögerung KAUF Median 1,6 s, p90 10,7 s | 1,6 s / 10,7 s (n=4.090) | bestätigt |
| 3c | Preisabstand KAUF bei Verzögerung < 2 s: Median +1,5 (p10 -1,3, p90 +8,4) | +1,5 / -1,34 / +8,43 (n=2.807) | bestätigt |
| 3d | VERKAUF < 2 s Median -0,49 % | -0,49 % (n=3.394; p10 -5,6, p90 +1,16) | bestätigt |
| 4 | messung.csv: Median fast überall 0,0; Mittel Kauf meist -1..0 %; Ausreißer serien_devs -4,25 % | Median 0,0 (Ausnahmen: ohne_limit KAUF -5,39 bei n=4; grosse_coins n=1; heisse_coins VERKAUF -0,36). Mittel KAUF zwischen -0,95 und 0, serien_devs -4,25 (n=99), ohne_limit -5,58 (n=4, beendet) | bestätigt (ohne_limit-Kauf ist ein weiterer Ausreißer, nur 4 Fälle) |
| 5a | Git 06.10. neue Objekte roh ca. 57.700 MB | 57.668 MB (43.528 Objekte) | bestätigt |
| 5b | copy/verlauf ~17.400, abgelehnt.csv ~16.300, copy/* ~12.100, verlauf/* ~7.000 MB | 17.398 / 16.261 / 12.122 (copy/ ohne verlauf: journal 7.180, konten.json 4.861, messung 81) / 7.049 | bestätigt |
| 5c | ca. 2.312 Commits am 06.10. | 2.389 (gleicher Zeitfilter, Stand jetzt) | korrigiert: 2.389 (Abweichung +77, evtl. andere Zählweise oder Zeitfilter) |
| 6 | 2.500 Coins x 6 h => ~625 gleichzeitig; 100 Mints/Abruf alle 60 s => 7/min = 10.080/Tag; 120 s => 5.040/Tag; 900.000 Zeilen/Tag, ~90 MB bei 100 Byte; 550 junge Coins = 198.000 Zeilen = ~20 MB (60 s) bzw. ~10 MB (120 s) | Rechnung stimmt: 2.500*6/24=625; 625/100 aufgerundet 7; 7*1440=10.080; 2.500*360=900.000; 550*360=198.000. Annahmen (gleichmäßige Verteilung, 6 h Verfolgung, 100 Byte/Zeile) sind nicht gemessen. | bestätigt (reine Rechnung, Annahmen grob) |
| 7 | abgelehnt.csv: 50 MB in ~12 Tagen, 100 MB in ~35 Tagen bei ~2,2 MB/Tag | 15.600 Zeilen x 147 Byte = 2,3 MB/Tag; (50-23,5)/2,2 = 12,0; (100-23,5)/2,2 = 34,8 Tage. Mittel seit 26.09. nur ca. 2,0 MB/Tag (Anfang weniger Zeilen) => 13 bzw. 38 Tage | bestätigt (grob, +-10 %) |

Hinweise: Datei wächst laufend, Zahlen für 07.10. sind Teiltag. Spalte `zeit` in UTC. Git-Größen sind Rohgrößen (unkomprimiert), Speicher im Repository ist wegen Kompression/Deltas kleiner.
