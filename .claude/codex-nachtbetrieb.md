# Codex-Nachtbetrieb – Vorschlag (vorbereitet 06.10.2026, NICHT gestartet)

Ziel: Codex arbeitet nachts allein eine Reihe Auftragskarten ab. Morgens prüft Claude die Ergebnisse und spielt Gutes ein. Codex selbst ändert nichts auf GitHub.

## Ablauf

1. **Abends (Claude):** Karten nach `.claude/codex-auftrag.md` schreiben, als `.claude/codex-karten/01-….md`, `02-….md` ablegen. Nur Aufgaben der Codex-Rolle (Tests, Dashboard, Auswertungsskripte, Doku, Wiki) – keine Bot-Logik, keine Wallet-Liste, keine Scout-Automatik.
2. **Nachts (Skript `.claude/codex-nachtlauf.ps1 -Los`):** je Karte nacheinander
   - Worktree `../paperbot-codex` auf den neuesten `origin/main` setzen, alte Reste löschen (jede Karte startet sauber, Karten stören sich nicht),
   - `codex exec -p <Modell> -C ../paperbot-codex --sandbox workspace-write --json -o <ergebnis>` mit der Karte als Auftrag,
   - danach alle Änderungen als **Patch** sichern, Urteil ins Protokoll: OK / LEER / ABGELEHNT (hat committet oder verbotene Dateien berührt),
   - Kontingent-Meldung im Protokoll → ganze Nacht beenden, Rest bleibt für die nächste Nacht liegen.
3. **Morgens (Claude):** Protokoll `.claude/codex-protokolle/<Zeit>/nachtlauf.log` lesen, jeden OK-Patch im Hauptordner mit `git apply --check` prüfen, Tests laufen lassen, code-pruefer, dann Zustimmung des Betreibers wie gewohnt und Skill `einspielen`.

Protokoll pro Karte: `NN.auftrag.md` (was Codex bekam), `NN.jsonl` (alle Schritte), `NN.stderr.txt`, `NN.ergebnis.md` (Schlussbericht von Codex), `NN.patch` (Änderungen), dazu `nachtlauf.log` (Urteile).

## Leitplanken

| Leitplanke | Wie umgesetzt |
|---|---|
| Kein Push, kein Commit | Codex-Sandbox `workspace-write` darf nur im Worktree schreiben; die Git-Datenbank liegt außerhalb (im Hauptordner `.git/`), Commits sollten also schon technisch scheitern (noch nicht erprobt – beim ersten Testlauf prüfen). Netz in der Sandbox ist laut `codex doctor` gesperrt. Skript prüft zusätzlich, ob HEAD sich bewegt hat → ABGELEHNT. |
| Keine Daten-Dateien | Skript prüft jede geänderte Datei gegen eine Verbotsliste (Daten, `copy_wallets.txt`, `scout/`, Workflows, Hooks, Settings) → ABGELEHNT. |
| Keine Schlüssel | Keine Projekt-Schlüssel liegen lokal (nur GitHub-Secrets, geprüft 06.10.). `config.toml` filtert Umgebungsvariablen mit KEY/TOKEN/SECRET/WEBHOOK/PASS heraus. **Restrisiko:** Die Sandbox darf lesen, auch außerhalb des Worktrees (z. B. den Discord-Token in `~/.claude/channels/`). AGENTS.md verbietet das; technisch ganz dicht wäre erst ein Berechtigungsprofil nur für den Worktree (später prüfen). |
| Begrenzte Menge | höchstens 5 Karten pro Nacht (`-MaxKarten`), höchstens 45 min je Karte (`-MaxMinutenProKarte`), danach Abbruch. |
| Kein Astra nachts | Karten mit Astra überspringt das Skript. |
| Bots laufen weiter ungestört | Worktree ist getrennt; nichts geht nach GitHub. Nur `git fetch` (lesend). |
| Nichts automatisch übernehmen | Patches spielt nur Claude nach Prüfung und Zustimmung ein. |

## Start (erst nach Freigabe durch den Betreiber)

Einmal von Hand testen: eine kleine Karte (z. B. Doku), `powershell -File .claude\codex-nachtlauf.ps1 -Los`, Protokoll ansehen. Danach bei Bedarf über die Windows-Aufgabenplanung um z. B. 00:30 UTC (02:30 deutscher Zeit) starten; der PC muss an sein. **Vorher empfohlen:** starke Sandbox einrichten (`.claude/codex-anleitung.md`, Abschnitt 1).

## Kosten

- **Geld:** keine Zusatzkosten, solange nur das Pro-Kontingent verbraucht wird (keine Credits kaufen, kein API-Key).
- **Kontingent:** Pro hat derzeit kein 5-Stunden-Limit, aber Wochenlimits. Ein Nachtlauf mit 5 Sol-Karten kann einen spürbaren Teil des Wochenkontingents kosten – genaue Zahl unbekannt, erst nach dem ersten Lauf in `/status` ablesen und in `codex-status.md` eintragen. Einfache Karten mit Luna (sehr großes Kontingent).
- **Risiko für Prüfungen am Tag:** Leert die Nacht Sol, fehlt Sol für die Pflicht-Prüfungen am nächsten Tag (dann Terra). Vorschlag: Nachtlauf nur, wenn `/status` vorher noch über die Hälfte zeigt.
- **Claude-Seite:** Morgens kostet das Durchsehen der Patches Claude-Token (Patches lesen statt ganze Dateien).

## Risiken

1. **Schlechte Patches** – Codex kann Tests „grün machen“, indem er Tests ändert. Gegenmittel: in der Karte festlegen, welche Tests unverändert bleiben müssen; Claude prüft den Patch.
2. **Patch passt morgens nicht mehr** – `main` hat sich über Nacht geändert (Bots pushen nur Daten, also selten ein Problem). `git apply --check` zeigt es.
3. **Hängender Lauf** – Zeitlimit je Karte.
4. **Kontingent leer** – Lauf bricht ab, Rest bleibt liegen.
5. **Sandbox-Lücke beim Lesen** – siehe Leitplanke „Keine Schlüssel“.
6. **Windows-Eigenheiten** – Defender kann Codex bremsen (`codex doctor` meldet fehlende Ausnahmen); erster Lauf deshalb unter Aufsicht.
