# Lehren aus Fehlern

- Hochladen per GitHub-Weboberfläche schnitt Dateien ab (`scout_bot.py`) oder legte sie in den falschen Ordner (`pruefen.txt`); nach jedem Push prüfen, ob alles vollständig ankam. [[Q-CLAUDE]]
- WebSocket: Eine leere Nachricht heißt, der Server hat die Verbindung geschlossen → neu verbinden; am 01.10. stürzte der Copy-Bot um 14:34 UTC dadurch ab. [[Q-CLAUDE]] [[Q-STRATEGIE]]
- Hoch einer Position startet beim Kaufpreis, nicht beim Signalkurs (Rug [[cum]]). [[Q-CLAUDE]]
- Konto-Anzeige „Einsatz“ wurde als Guthaben missverstanden; Kontowert = frei + aktueller Wert. [[Q-CLAUDE]]
- Scout bewertete Trader mit Haltedauer in Tagen falsch (nur schnelle Fehlkäufe sichtbar) → 7-Tage-Fenster, gehaltene Coins zum Kurs, Reibung nach Haltedauer. [[Q-CLAUDE]]
- Abbruch einer Copy-Schicht von Hand ist seit 03.10. sicher; am 02.10. ging dadurch die Zrool-Position verloren und eine 922M-Position wurde doppelt geschlossen. [[Q-CLAUDE]] [[Q-Korrekturen]]
- `--probe` nur starten, wenn keine Schicht läuft: Der Kurztest verdrängt die wartende nächste Schicht, die Kette reißt bis zum Sicherheitsnetz ab (bis zu 6 h). [[Q-CLAUDE]]
- `copy/journal.csv` ist das Gedächtnis gegen doppeltes Nachholen und darf nicht gekürzt oder ausgelagert werden, ohne diesen Schutz anzupassen. [[Q-CLAUDE]]
- Ein neues Paket-Release hätte beim nächsten Schichtstart alle drei Bots stoppen können; deshalb feste Versionen in `requirements.txt` (03.10.). [[Q-STRATEGIE]]
- Ein Jupiter-Ausfall darf nie als „Coin wertlos“ gelten (03.10., siehe [[Jupiter]]). [[Q-STRATEGIE]]
- Die frühere Regressions-Angabe „+0,068 SOL auf 28 Verläufen“ war nicht nachvollziehbar (siehe [[Hauptstrategie-NARRATIV]]). [[Q-STRATEGIE]]
- Siehe auch [[Copy-Fehlbuchungen-bis-03-10]], [[Bot-Wallets]].
- 05./06.10.: Hauptbot-Lücke von 4,2 h, weil GitHub einem Lauf keinen Runner gab („not acquired by Runner“, 0 Schritte) und deshalb die nächste Schicht nicht startete; seit 06.10. stündliches Sicherheitsnetz bei Hauptbot und Copy-Bot statt alle 6 h. [[Q-2026-10-06-Entscheidungen]]
