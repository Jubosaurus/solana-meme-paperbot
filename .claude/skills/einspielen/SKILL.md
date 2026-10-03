---
name: einspielen
description: Fertige Änderungen sicher auf GitHub einspielen und die betroffenen Bots neu starten. Verwenden, wenn der Betreiber einer Änderung zustimmt („ja, einspielen“, „lade hoch“, „mach live“) oder wenn nach einer Änderung geprüft werden soll, ob alles angekommen ist und läuft.
---

# Einspielen

Die Bots nehmen jede Änderung beim nächsten Start. Deshalb immer in dieser Reihenfolge, ohne Schritte auszulassen.

## 1. Vorher

1. Zustimmung des Betreibers liegt vor (bei Regeländerungen ausdrücklich).
2. `git pull` – die Bots haben inzwischen Daten gepusht.
3. Testsammlung ausführen: `python -m pytest` (alle grün, etwa 15 s). Bei Fehlern: nicht einspielen, Ursache erklären. Bei Verkaufsregeln muss `tests/test_regression.py` unverändert grün sein.
4. Subagent **code-pruefer** prüfen lassen. Bei ❌ nicht einspielen.

## 2. Einspielen

1. Nur die gewollten Dateien einzeln hinzufügen (`git add <datei>`), **nie** `git add .` oder `git add -A`. Daten-Dateien bleiben draußen.
2. Commit-Nachricht auf Deutsch, ein Satz: was und warum.
3. `git push`. Wird der Push abgelehnt, weil die Bots inzwischen gepusht haben: `git pull --rebase` und erneut pushen.

## 3. Prüfen, ob alles angekommen ist

1. `git fetch` und für jede eingespielte Datei vergleichen: `git diff origin/main -- <datei>` muss leer sein.
2. Bei Python-Dateien zusätzlich die letzte Zeile auf GitHub prüfen (`git show origin/main:<datei> | tail -1`), um abgeschnittene Dateien auszuschließen.

## 4. Betroffene Bots neu starten

Welche Datei welchen Bot betrifft:

| Geänderte Datei | Neu starten |
|---|---|
| `bot.py` | Hauptbot **und** Copy-Bot (der Copy-Bot nutzt `bot.py`); der Scout übernimmt es beim nächsten Lauf |
| `copy_bot.py`, `copy_wallets.txt` | Copy-Bot; der Scout übernimmt es beim nächsten Lauf |
| `scout_bot.py`, `scout/pruefen.txt` | nichts; auf Wunsch Scout einmal starten |
| Workflow-Dateien | wirken beim nächsten Start des jeweiligen Bots; laufende Schicht nur nach Rückfrage abbrechen |
| nur Doku, Tests, `.claude/`, `auswertungen/`, `skill-observations/`, `skill-updates/` | nichts |

Neustart eines Bots:
1. Laufenden Lauf finden: `gh run list --workflow <workflow>.yml --status in_progress`
2. Abbrechen: `gh run cancel <id>`
3. Neu starten: `gh workflow run <workflow>.yml -f modus=normal`
4. Nach etwa 2 Minuten `gh run view <neue id> --log` und prüfen: keine Fehlermeldung, Startmeldung vorhanden (Copy-Bot: „verbunden, X von X Wallets angemeldet“).

## 5. Abschluss

Dem Betreiber in zwei bis drei Sätzen berichten: was eingespielt wurde, dass es vollständig angekommen ist, welche Bots neu gestartet wurden und ob sie sauber laufen. Falls nötig, Eintrag im Änderungsprotokoll von `STRATEGIE.md` nachholen.
