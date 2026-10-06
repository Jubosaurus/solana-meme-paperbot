# Ausführungskosten und Verzögerung (Messung)

- Seit 03.10. wird bei jedem Kauf/Verkauf dieselbe Jupiter-Quote 2 s später noch einmal abgefragt (`messung.csv`, `copy/messung.csv`); + = später schlechter für uns. [[Q-STRATEGIE]]
- Stand 03.10. (wenige Daten): Hauptbot-Käufe 18 Messungen, Mittel −4,7 %, Median −0,8 %, jeder zehnte schlechter als +15,5 %; Copy-Käufe 50 Messungen, Mittel +1,8 %, Median +0,6 %. [[Q-2026-10-03-Ueberpruefung]]
- Der tatsächliche Abstand der zweiten Quote ist wegen des Jupiter-Takts meist 3–6 s statt 2 s. [[Q-2026-10-03-Ueberpruefung]]
- Geschätzt (nicht gemessen): 1–3 % je Seite, also etwa 0,004–0,012 SOL je Trade zusätzlich; kein Konto käme damit ins Plus. [[Q-2026-10-03-Ueberpruefung]]
- Neue Prüfung mit echten Kosten ab etwa 10.10. geplant. [[Q-2026-10-03-Ueberpruefung]]
- In der Nachrechnung zum gestaffelten Verkauf: „mit Kosten“ = 3 % auf 0,2 SOL plus 0,0015 SOL je Transaktion; mit Kosten bleiben alle Varianten im Minus. [[Q-2026-10-04-Video-Nachrechnung]]
- Aus den Videos: Trading-Terminals nehmen etwa 1 % Gebühr je Kauf und Verkauf. [[Q-Videos-Regeln]]
- Stand 06.10. (Messung seit 03.10.): Median Abweichung 0 bei Kauf und Verkauf (Hauptbot und Copy); 90 %-Wert Hauptbot Kauf 3,8 %, Verkauf 5,6 %, Copy Kauf 6,2 %, Verkauf 4,4 %. [[Q-2026-10-06-Tagesauswertung]]
- NOTBREMSE-Verkäufe (451): Median 0, 90 %-Wert 4,4 %, gewichtet −0,12 SOL (kein Aufschlag im Mittel); Endspurt-Verkäufe Mittel +0,97 %, 90 %-Wert 11,3 %. Vorschlag (offen): 2 % je Rundlauf, Endspurt 4 %. [[Q-2026-10-06-Tagesauswertung]]
- Entscheidung 07.10.: Kostenaufschlag in alle Bewertungen (Tagesauswertung, Dashboard, Testregeln): 2 % vom Einsatz je Rundlauf, Endspurt-Experimente 4 %; immer beide Zahlen zeigen, roh und mit Kosten (`dashboard/rechnung.py`, `KOSTEN_PCT`). Bots und Verkaufsregeln unverändert. Sandwich-Angriffe und gescheiterte Transaktionen sind nicht enthalten. [[Q-2026-10-07-Entscheidungen]]
