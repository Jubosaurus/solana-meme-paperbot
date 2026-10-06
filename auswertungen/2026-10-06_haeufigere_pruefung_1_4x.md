# Häufigere Prüfung für Positionen mit Hoch >= 1,4x

Stand 06.10.2026. Nur gerechnet, nichts am Code geändert. Vorarbeit: `2026-10-06_gewinnschutz_1_5x.md`. Hypothese kam aus den Daten (hinterher gefunden), also nur Hinweis.

## 1. Ergebnis in einem Satz

Technisch machbar und billig, aber der Nutzen ist klein und unsicher: Höchstens +0,35 SOL/Tag über alle Konten (Obergrenze), realistisch etwa +0,1 bis 0,2 SOL/Tag. Ob der Kurs bei Jupiter überhaupt schneller als alle 12-16 s aktualisiert wird, ist unbekannt. Die Verläufe sind zu grob, um die Regel direkt zu testen.

## 2. Was der Code heute macht (bot.py)

- Hauptschleife `run()`: pro Durchlauf `manage_positions`, `manage_experiments`, alle 6 Durchläufe `scan`, danach `sleep_with_rechecks(12)`. Gemessen (verlauf, Phase `offen`, Hauptbot): Abstand der Prüfungen Median 16 s (10 % 14 s, 90 % 24 s). 12 s ist nur die Pause, Scan und Abfragen kommen obendrauf.
- Kurs: **eine** Jupiter-Abfrage `/tokens/v2/search` für alle offenen Positionen aller Konten zusammen (bis 100 Coins pro Anfrage). Ein Mini-Takt nur für heiße Positionen kostet also auch nur 1 Anfrage je Prüfung, egal wie viele heiß sind.
- Hindernisse: `TOK_CACHE_SECONDS = 6` (Antworten werden 6 s wiederverwendet, ein 3-5-s-Takt würde ohne Anpassung oft den alten Wert sehen) und Drossel `jup_get` 1,1 s pro Anfrage (mit Key). Beides müsste für heiße Positionen umgangen werden. Der Lauf ist ein Thread: während Scan/Experimente/Messungen kann kein Mini-Takt laufen, es sei denn, er wird in `sleep_with_rechecks` eingebaut.
- GEWINN_GESCHUETZT (Z. 1563): Hoch >= 1,5x und Kurs <= 1,0x. Auslöser für die häufigere Prüfung wäre "Hoch >= 1,4x, kein Teilverkauf, Kurs <= ca. 1,2x".

## 3. Ist die Auflösung der Verläufe fein genug?

**Nein.** Haupt-Konto: Aufzeichnung ca. alle 12-16 s (genau der Prüftakt). Alle Experimente: ca. alle 48-50 s (`EXP_LOG_OPEN_EVERY_LOOPS = 3`). Nach Verkauf ca. 55 s. Ein 3-5-s-Takt lässt sich daher nicht direkt nachrechnen. Außerdem ändert sich der Preis in der Aufzeichnung bei 30 % der 15-s-Zeilen nicht: Jupiter liefert offenbar nicht jede Sekunde einen neuen Preis. Zwischen Preisänderungen liegen im Median 16 s (Untergrenze durch unseren Takt, also unklar). **Ob häufigeres Fragen neue Preise bringt, weiß ich nicht**; das müsste ein kurzer Live-Test zeigen (ein Coin, alle 2 s, 2 min).

Was ich stattdessen genutzt habe:
- Verteilung der Verkaufspreise der 149 GEWINN_GESCHUETZT-Verkäufe (alle Konten, `closed`, Verkaufspreis / Einstiegspreis).
- Bei den 15 Haupt-Trades (16-s-Raster) den letzten Schritt von über 1,0x auf den Verkaufspreis linear interpoliert und gerechnet, wo ein 3-, 5- oder 8-s-Takt ausgelöst hätte.

## 4. Wie viel rutscht durch

149 Verkäufe, alle Konten (28.09. bis 06.10.), Einsatz je 0,2 SOL:

| Kennzahl | Wert |
|---|---|
| Verkaufspreis Median | 0,962x (Ø 0,933x, schlechtester 0,639x) |
| Unter 1,0x im Mittel (Durchrutschen) | Ø 6,7 %, Median 3,8 % |
| Mehr als 5 % unter 1,0x | 39 % der Fälle |
| Mehr als 15 % unter 1,0x | 13 % |
| Summe des Durchrutschens | 2,00 SOL (ohne die 3 größten: 1,79) |
| Summe Ergebnis dieser 149 Trades | -2,59 SOL |

Pro Tag (Anzahl, Durchrutschen in SOL): 04.10. 34 / 0,70; 05.10. 26 / 0,20; 06.10. 25 / 0,41; 03.10. 16 / 0,23; 02.10. 15 / 0,13; 01.10. 11 / 0,13; 30.09. 13 / 0,12; 29.09. 7 / 0,09. Erste Hälfte (74 Trades) Ø 0,0108 SOL, zweite Hälfte (75) Ø 0,0160 SOL, ohne Top 3 je Hälfte 0,0094 und 0,0138. Kein Ein-Tages-Effekt, das Durchrutschen ist stetig da; die Obergrenze hält also auch ohne Ausreißer.

Haupt-Konto (15 Trades) Schritt vor dem Verkauf, Beispiele: ALON 1,09 -> 0,95, JUF 1,09 -> 0,90, OATH 1,27 -> 0,66, ZIPBOOK 1,07 -> 0,84, CHAMBER 1,01 -> 0,90 (je in einem 12-16-s-Schritt). Ob das echte Sprünge (nicht abfangbar) oder schnelle Rutsche (abfangbar) waren, sehen wir nicht.

## 5. Schätzung der Ersparnis

Modell: Fällt der Kurs gleichmäßig zwischen zwei Prüfungen, löst ein 3-s-Takt statt 12-16 s das Durchrutschen auf (Haupt-Stichprobe, 15 Trades, nur Tendenz):

| Takt für heiße Positionen | Durchrutschen bleibt (von Ø 7,2 % auf) | Anteil gespart |
|---|---|---|
| heute (12-16 s) | 7,2 % | 0 |
| 8 s | 3,3 % | 54 % |
| 5 s | 2,6 % | 64 % |
| 3 s | 1,2 % | 83 % |

Das ist die **optimistische** Annahme (gleichmäßiger Fall). Bei Sprüngen (ein einziger Preisschritt von 1,09 auf 0,90) spart der schnellere Takt nichts. Realistischer Anteil: 20-50 %.

Hochgerechnet auf alle Konten (Ø 0,0135 SOL Durchrutschen je Trade, ca. 25-34 solche Trades pro Tag zuletzt):

| Anteil gespart | je Trade | gesamt über 9 Tage | pro Tag (ca. 28 Trades) | je Trade ohne Top 3 |
|---|---|---|---|---|
| 20 % (Sprünge überwiegen) | 0,0027 | 0,4 SOL | 0,08 | 0,0025 |
| 50 % (Mischung) | 0,0067 | 1,0 SOL | 0,19 | 0,0061 |
| 83 % (Obergrenze, 3-s-Takt) | 0,0112 | 1,7 SOL | 0,31 | 0,0102 |

Nur im Haupt-Konto (ca. 2 Trades/Tag): etwa 0,005-0,02 SOL/Tag. Das sind wenige Cent bei 10-SOL-Konten; über alle Experimente verteilt etwa +1-2 % pro Woche bei den Konten mit vielen Trades. Die Zahl ist ein Vielfaches der Rundlaufkosten nicht und ändert kein Urteil über eine Strategie.

## 6. Was die Regel kosten würde

- **Mehr Jupiter-Anfragen:** Heiße Zeit (Hoch >= 1,4x, kein Teilverkauf, Kurs <= 1,2x) gab es an 04./05./06.10. in 47 %, 27 % und 28 % der Minuten (mit Obergrenze 1,3x: 55 %, 35 %, 37 %). Mit einer Anfrage alle 4 s in dieser Zeit: ca. 6.000-10.000 Zusatzanfragen/Tag (ca. 0,07-0,12 pro Sekunde im Schnitt, in heißen Phasen 0,25/s). Heute: ca. 5.400 Positionsprüfungen/Tag plus Scan. Unter dem Limit von ~1 Anfrage/s des Hauptbots (Copy-Bot und Scout nutzen denselben Key, deshalb nicht ausreizen). Bei 3 s: +30 %.
- **Zusatz-Auslöser (nicht messbar):** Bei dichterem Takt löst die Regel auch bei kurzen Rücksetzern auf 1,0x aus, die sich vorher wieder erholt hätten (solche Coins hat die Vorarbeit schon als größte verpasste Gewinner gefunden: CHAMBER +0,40, CHONK +0,27). Diese Seite können die 12-s-Daten nicht zeigen; sie kann den Nutzen auffressen.
- **Verlierer, die ein schnellerer Takt gefangen hätte (im Haupt-Konto, linear gerechnet):** OATH (1,27x -> 0,66x, bei 5 s ca. -0,13 statt -0,34 Durchrutschen), STONK6900, ZIPBOOK, JUF, CHAMBER-Schritt, PROMPT. Verpasste Gewinner lassen sich aus den Daten nicht bestimmen (siehe oben).
- Entwicklungsaufwand: Mini-Takt in `sleep_with_rechecks`, Cache-Umgehung, neue Tests; Gegenprobe in `test_regression.py` bleibt unberührt, weil sie auf 12-s-Daten läuft.

## 7. Unsicherheit

- Auflösung der Daten reicht nicht (siehe 3). Die Ersparnis ist ein Modell mit 15 Haupt-Trades, nicht gemessen.
- Unbekannt, ob Jupiter schnellere Preise liefert; 30 % der 15-s-Preise sind unverändert.
- Die 149 Trades überlappen (gleiche Coins in mehreren Konten), keine unabhängigen Stichproben.
- Hypothese hinterher aus den Daten gefunden: nur Hinweis.

## 8. Empfehlung

- **Jetzt nichts einbauen.** Sicherheit: gering (Nutzen +0,1 bis 0,3 SOL/Tag über alle Konten, Spanne 0 bis 0,35).
- Als Nächstes: kleiner, billiger **Messtest** statt Regel: 2-5 Minuten lang (nur wenn eine Position mit Hoch >= 1,4x offen ist, aber ohne Handel) alle 2-3 s den Kurs abfragen und aufzeichnen (neue Phase, nur anhängen). Dann zeigt sich (a) ob Jupiter überhaupt schneller aktualisiert und (b) ob der Fall Sprung oder Rutsche ist. Erst dann lässt sich die Regel an echten 3-s-Daten testen (erste Hälfte finden, zweite bestätigen, ohne Top 3).
- Falls man gleich als Experiment testen will: nur im Haupt-Konto, kein neues Konto nötig, Vergleich gegen die eigene Vorperiode ist schwach; ein eigenes Experiment-Konto ist wegen der 200-Trades-Regel erst bei etwa 8 Tagen aussagekräftig (ca. 25 GG-Trades/Tag nur über alle Konten).
