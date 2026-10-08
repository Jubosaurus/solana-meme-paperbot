# Nachrechnung Notbremse 25 und Drittel-Leiter auf allen aufgezeichneten Verläufen (08.10.2026)

Hypothese: Notbremse 25 war die Idee aus den Daten (hinterher), Drittel-Leiter eine Video-Idee (vorher). Hier wird nachgerechnet, nicht neu entschieden.

## Methode
- Wie `tests/test_regression.py`: jeder Verlauf (Phasen `offen` und `nach_verkauf`) läuft ab dem Kauf durch `manage_positions`. Kaufpreis = 1, 0,2 SOL Einsatz, ohne Gebühren und Slippage.
- Drei Läufe je Coin, gleiche Käufe: Hauptstrategie, Notbremse 25 (`stop_pct = -25`), Drittel-Leiter (`leiter = [1.5, 2, 3]`), jeweils mit dem echten Code aus `bot.py`.
- Quellen: `verlauf.csv` (27.09.) und `verlauf/2026-09-28` bis `2026-10-08`. Ergebnis: 166 Käufe. Die Rechnung für die Hauptstrategie trifft alle 33 festgeschriebenen Werte aus `EXPECTED` auf 0,0001 SOL genau (Methode passt). 1 Coin war am Ende der Aufzeichnung noch offen (zum letzten Kurs gerechnet).
- Kostenaufschlag: 2 % vom Einsatz je Rundlauf = 0,004 SOL je Trade, für beide Seiten gleich. Der Unterschied je Paar ändert sich dadurch nicht, nur die Gesamtsummen. Nicht mitgerechnet: zusätzliche Transaktionsgebühren der Drittel-Leiter (mehr Teilverkäufe); sie würde damit eher noch etwas schlechter dastehen.
- Skript (nicht im Repository): Ordner Scratchpad der Sitzung, `sim.py` und `an.py`.

## Ergebnis (alle 166 Käufe seit 27.09.)

| Variante | Paare | Summe roh | Summe mit Kosten | Unterschied zu Haupt (roh) | Unterschied ohne 3 beste | besser / schlechter / gleich |
|---|---|---|---|---|---|---|
| Hauptstrategie | 166 | -0,340 | -1,004 | - | - | - |
| Notbremse 25 | 166 | +0,048 | -0,616 | +0,388 | +0,171 | 85 / 14 / 67 |
| Drittel-Leiter | 166 | -0,091 | -0,755 | +0,249 | +0,017 | 33 / 30 / 103 |

Aufgeteilt nach Zeitraum (Kauf vor / nach dem Start der Live-Experimente am 04.10. ca. 01:00 UTC):

| Variante | Zeitraum | Paare | Unterschied roh | ohne 3 beste | Summe Haupt | Summe Variante |
|---|---|---|---|---|---|---|
| Notbremse 25 | vor 04.10. | 93 | +0,621 | +0,403 | -0,026 | +0,595 |
| Notbremse 25 | ab 04.10. | 73 | -0,233 | -0,385 | -0,314 | -0,547 |
| Drittel-Leiter | vor 04.10. | 93 | +0,232 | +0,027 | -0,026 | +0,205 |
| Drittel-Leiter | ab 04.10. | 73 | +0,018 | -0,182 | -0,314 | -0,296 |

Tage getrennt (Unterschied zur Hauptstrategie in SOL, Käufe pro Tag):

| Tag | Käufe | Notbremse 25 | Drittel-Leiter |
|---|---|---|---|
| 27.09. | 11 | -0,190 | +0,065 |
| 28.09. | 13 | +0,143 | +0,070 |
| 29.09. | 9 | -0,074 | -0,004 |
| 30.09. | 10 | +0,328 | +0,048 |
| 01.10. | 16 | +0,266 | -0,005 |
| 02.10. | 18 | -0,006 | +0,155 |
| 03.10. | 15 | +0,154 | -0,084 |
| 04.10. | 20 | +0,381 | +0,129 |
| 05.10. | 19 | -0,663 | -0,131 |
| 06.10. | 19 | +0,102 | -0,072 |
| 07.10. | 14 | -0,072 | +0,079 |
| 08.10. | 2 | +0,020 | 0,000 |

Notbremse 25 gewinnt an 7 von 12 Tagen, verliert aber am 05.10. allein 0,663 SOL. Der Gesamtvorsprung hängt damit von einzelnen Tagen ab.

## Was die Regeln kosten und sparen

Notbremse 25 (frühere Notbremse):
- Spart bei Rugs, die sonst bis -50 bis -70 % fielen: SHIT +0,081 (statt -0,138 jetzt -0,057), RF +0,069, LAB +0,068, ANSEMWEEN +0,068, mINE +0,060, Agentws +0,056.
- Kostet bei Gewinnern, die zuerst tief fielen und dann 3x und mehr erreichten: PUNCH -0,379 (Haupt +0,329 über STORY_ABGEKUEHLT, Variante -0,050), NEURALS -0,280, CASHED -0,272, MAXIM -0,267, SPAWN -0,257, SIERRA -0,229. Diese Coins hatten vor dem Anstieg einen Rückgang von 25 bis 31 %.
- Der Nutzen sind viele kleine Ersparnisse (85 Fälle), der Preis wenige große verpasste Gewinner (14 Fälle schlechter).

Drittel-Leiter:
- Verliert bei den großen Gewinnern, weil bei 3x alles verkauft wird: SPEC (13,85x) -0,207 (statt +0,486 nur +0,279), BACKERS (6,76x) -0,101, Respawn -0,084, THAW -0,066, DAO -0,033, CASHED -0,032.
- Gewinnt kleine Beträge bei Coins, die zwischen 1,5x und 2x umkehren: PUNCH +0,091, OATH +0,072, WIKIPAD +0,069, SOCIALBAGS +0,061, ZIPBOOK +0,054.
- 103 von 166 Fällen sind gleich (kein Coin erreichte 1,5x). Ohne die 3 besten Fälle bleibt praktisch nichts (+0,017). Mit Kosten für zusätzliche Gebühren eher ein Nullergebnis.

## Vergleich mit den live aufgezeichneten Paaren (Methodenprüfung)

Alle live Paare sind auch in der Nachrechnung vorhanden (Coin und Kaufzeit auf 10 min genau, Nachrechnung hat 73 statt 74 Käufe im Zeitraum, deshalb für die Gegenüberstellung nur die gepaarten Coins).

| Experiment | Paare | Unterschied live | Unterschied Nachrechnung (gleiche Coins) | Je Coin gleich (±0,02) | gleiche Richtung | gleicher Verkaufsgrund Experiment / Haupt |
|---|---|---|---|---|---|---|
| Notbremse 25 | 74 | -0,412 | -0,233 | 63 von 74 | 57 von 74 | 73 / 67 |
| Drittel-Leiter | 68 | -0,375 | -0,095 | 58 von 68 | 46 von 68 | 59 / 63 |

Die Gesamtsummen liegen live tiefer, weil live Slippage, Gebühren und 3 % Rundlaufkosten drin sind (Notbremse-Paare live Experiment -0,946 gegen Nachrechnung -0,398; Haupt live -0,534 gegen -0,165). Der Unterschied zwischen den Varianten stimmt in der Richtung überein, die Größe nicht ganz. Größte Abweichungen je Coin:
- Respawn (Drittel-Leiter): live -0,382 (Experiment schied über GEWINN_GESCHUETZT aus), Nachrechnung -0,084. Live war der Kurs zwischen den Messpunkten anders; die Nachrechnung nimmt nur die Minutenwerte.
- Respawn (Notbremse 25): live -0,123, Nachrechnung 0,000. Memedraft live -0,039, Nachrechnung 0,000.
- Bei Notbremse 25 liegen live mehrfach Fälle, wo das Experiment bei -25 bis -28 % stieg aus, während die Haupt-Seite schon wegen LIQUIDITAET_ABGEZOGEN raus war; die Nachrechnung hat dort andere Verkaufszeitpunkte (Volition, AGENCYBOOK, AD).
- Grund: Die Verlaufszeilen kommen etwa jede Minute, live prüft der Bot öfter (Takt etwa 36 s bei der These, Kurs öfter), außerdem kann die Haupt-Position live früher oder später ausgestiegen sein.

Fazit zur Methode: Die Nachrechnung ist brauchbar (Hauptstrategie trifft die festgeschriebenen Werte exakt, Richtung und Verkaufsgrund meist gleich), aber Zeitpunkte unter einer Minute und Slippage fehlen. Einzelwerte darf man nicht überbewerten; die Summenaussage für Drittel-Leiter live (-0,375) gegen Nachrechnung (-0,095) zeigt eine deutliche Unschärfe.

## Einordnung
- Notbremse 25: Vor dem Live-Start war die Regel in der Nachrechnung klar besser (+0,621, ohne 3 beste +0,403, 93 Käufe), im Live-Zeitraum klar schlechter (-0,233, ohne 3 beste -0,385). Nachgerechnet ist die Regel damit nur im ersten Zeitraum belegt, im neuen nicht. Die frühere Beobachtung war hinterher aus den Daten gefunden (Hinweis, kein Beleg); die neuen Daten bestätigen sie nicht. Ob der Unterschied Zufall oder Marktwechsel ist (05.10. allein -0,663), lässt sich mit 166 Fällen nicht entscheiden.
- Drittel-Leiter: Im Gesamtbild praktisch gleich wie die Hauptstrategie (+0,249 roh, ohne 3 beste +0,017, 103 gleiche Fälle). Kein belegter Vorteil.
- Unter 200 Käufe (166) und beide Zeiträume gegensätzlich: nur Tendenz, kein Urteil.

## Empfehlung
- Sicherheit: gering bis mittel.
- Notbremse 25: weiter laufen lassen (sie ist ein Paar-Experiment mit gleichen Käufen und deshalb sauber), Urteil frühestens bei 200 Paaren; nicht auf die Hauptstrategie übernehmen. Im Gesamtbild sprach die Nachrechnung dafür, die Live-Zahlen dagegen. Prüfen, ob live nur Slippage und Messpunkte den Unterschied erzeugen.
- Drittel-Leiter: Kein Vorteil in der Nachrechnung, live schlechter. Bei Platzbedarf eher beenden (Daten bleiben); Entscheidung beim Betreiber.
- Nächster Schritt: Nachrechnung mit zusätzlichen Gebühren je Teilverkauf wiederholen und mit den neuen Verläufen alle paar Tage fortschreiben. Wenn gewünscht, kann man Notbremse -30 und -35 mit denselben Daten nachrechnen (Hinweis: dann wäre es wieder Suche in den Daten, nur mit neuen Verläufen prüfen).
