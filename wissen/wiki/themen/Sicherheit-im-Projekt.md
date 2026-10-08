# Sicherheit im Projekt

- Die Sicherheitsprüfung vom 07.10.2026 fand keinen Schlüssel im Git-Verlauf; Daten-Dateien waren ausdrücklich nicht Teil dieses Scans. [[Q-2026-10-07-Sicherheit]]
- Danach werden bekannte Schlüssel und Webhook-Muster vor Ausgaben und Discord-Meldungen gefiltert; fällt der Filter aus, wird laut Bericht nur `***` ausgegeben. [[Q-2026-10-07-Sicherheit]]
- Das Dashboard prüft für schreibende Funktionen zulässige Host-Namen und lehnt fremde Hosts ab; der Bericht nennt beim Test für `evil.example` den Status 403. [[Q-2026-10-07-Sicherheit]]
- Die GitHub-Actions wurden auf feste Commit-Stände gesetzt; die Nachtlauf-Sperrliste enthält die drei Bot-Dateien und das Nachtlauf-Skript. [[Q-2026-10-07-Sicherheit]]
