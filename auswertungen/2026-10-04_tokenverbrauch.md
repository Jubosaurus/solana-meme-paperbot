# Token-Verbrauch und Sparvorschläge (04.10.2026)

Quelle: Plugin `session-report`, Zeitraum 02.10. 13:44 bis 04.10. 05:31 UTC (letzte 7 Tage, ältere Sitzungen gibt es nicht). Die Arbeit nach 05:31 UTC ist nicht enthalten. Den HTML-Bericht des Plugins habe ich nicht erzeugt: Er hätte selbst viele Token gekostet, und die Zahlen stehen hier.

## Gesamt

- **288 Mio. Token** in 40 Sitzungen.
  - 97,5 % davon kamen aus dem Zwischenspeicher (Cache). Die sind billiger, zählen aber trotzdem.
  - 99 % entfallen auf dieses Projekt.
- Nach Tagen: 02.10. 15,6 Mio., **03.10. 271,7 Mio.**, 04.10. bis 05:31 0,5 Mio.
- **Hauptursache:** Am 03.10. lief fast alles in **einer einzigen Sitzung**, vom Dashboard über die große Überprüfung bis zum Nachtlauf. Mit jeder Aufgabe wuchs der Gesprächsverlauf, zuletzt auf bis zu ~950.000 Token. Jeder einzelne Arbeitsschritt liest diesen ganzen Verlauf erneut. Teuer ist also nicht die einzelne Aufgabe, sondern die Länge der Sitzung.

## Die 5 teuersten Aufgaben

Anteil am Gesamtverbrauch; alle fünf liefen in derselben langen Sitzung.

| # | Aufgabe (Start, UTC) | Anteil | Arbeitsschritte | Grund |
|---|---|---|---|---|
| 1 | Nachtlauf (03.10. 22:29) | 18,7 % | 109, 6 Helfer | lange Arbeit **auf** einem schon riesigen Verlauf. Nach der Pause wegen des Nutzungslimits musste der Speicher einmal komplett neu aufgebaut werden (~930.000 Token auf einen Schlag) |
| 2 | Dashboard v1 (03.10. 13:04) | 14,9 % | 106, 1 Helfer | viele kleine Schritte mit Bildschirmfotos und Nachbessern, dazu der Verlauf aus den Reparaturen davor |
| 3 | Entscheidungen zur Überprüfung umsetzen (03.10. 22:13) | 14,6 % | 67, 4 Helfer | 8 Änderungen hintereinander, je Änderung Tests und Code-Prüfer, Verlauf schon sehr lang |
| 4 | Dashboard v2 (03.10. 15:17) | 13,7 % | 82, 3 Helfer | neues Aussehen, Handy-Ansicht, Prüfungen; nach einer längeren Pause Speicher neu aufgebaut (~490.000) |
| 5 | Große Überprüfung (03.10. 19:39) | 11,1 % | 66, 2 Helfer | breite Prüfung mit Helfern; Speicher neu aufgebaut (~620.000) |

Zusammen 73 % des gesamten Verbrauchs.

**Zum Vergleich:** Die Testsammlung am 02.10. war viel Arbeit, hat aber nur 2,5 % gekostet. Sie lief in einer eigenen, frischen Sitzung.

**Helfer (Subagenten):**
- 32 Aufrufe, zusammen 11,3 Mio. Token, das sind knapp 4 %.
- Im Schnitt ~350.000 je Aufruf. Am teuersten war der Code-Prüfer (103 Schritte in einer Prüfung).

## Spar-Regel (eingetragen 04.10.)

In `CLAUDE.md`, beim Daten-Prüfer, beim Strategie-Tester und im Skill Tagesauswertung steht jetzt:
> Große Dateien (`journal.csv`, `verlauf/`, `copy/`, `flugschreiber/`) nie direkt lesen, sondern per Python-Skript auswerten und nur das Ergebnis ausgeben. Subagenten bekommen nur die nötigen Zahlen, nicht ganze Dateien.

## Weitere Sparvorschläge (ohne Qualitätsverlust)

1. **`/clear` nach jeder Aufgabe.** Das ist der mit Abstand größte Hebel und steht schon in CLAUDE.md, wurde am 03.10. aber nicht eingehalten.
   - Eine frische Sitzung startet mit etwa 30.000–60.000 Token statt mit bis zu 950.000.
   - Das Wissen geht nicht verloren: CLAUDE.md, `STRATEGIE.md`, die Berichte in `auswertungen/` und meine Merkzettel bleiben.
   - Grobe Schätzung: Aufgaben wie Nr. 3–5 hätten in frischen Sitzungen etwa ein Drittel gekostet.
2. **Nach langen Pausen neu anfangen.** Nach mehr als einer Stunde Pause (Nutzungslimit, Nacht) verfällt der Zwischenspeicher. Dann wird der ganze Verlauf teuer neu eingelesen. Besser: `/clear` und mit einem kurzen Auftrag weitermachen.
3. **Nachtlauf mit Übergabezettel statt Riesensitzung.** Für lange, unbeaufsichtigte Arbeit eine eigene, frische Sitzung starten. Der Fortschritt steht ohnehin im Merkzettel. Wird der Verlauf zu lang, nach jedem Arbeitsblock neu beginnen.
4. **Strategie-Tester darf sein Ergebnis selbst in `auswertungen/` speichern.** Bisher darf er nichts schreiben. Seinen ganzen Bericht habe ich deshalb einmal gelesen und dann noch einmal als Datei geschrieben, das kostet doppelt. Änderung nur mit deinem OK. Er dürfte dann nur in `auswertungen/` schreiben, nie Code oder Daten.
5. **Code-Prüfer gezielt einsetzen.** Bei reinen Doku-Commits (Berichte, Zusammenfassungen) braucht es ihn nicht; das ist schon so geregelt. Bei Code bekommt er wie bisher den `git diff` und die Prüfpunkte. Er soll nur die betroffenen Stellen lesen, nicht ganze Dateien.
6. **Kurze Ausgaben.** Testläufe nur mit der Ergebniszeile, Logs und Listen gekürzt (z. B. `tail`). Das wird schon meist so gemacht, ich achte weiter darauf.

Vorschlag 1–3 kannst du selbst steuern: neue Aufgabe = `/clear`. Für Vorschlag 4 brauche ich dein OK.
