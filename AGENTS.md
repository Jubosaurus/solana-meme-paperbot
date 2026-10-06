# AGENTS.md – Regeln für Codex in diesem Projekt

Paper-Trading-Projekt für Solana-Memecoins (kein echtes Geld). Die vollständigen Projektregeln stehen in `CLAUDE.md` (Abschnitte „Goldene Regeln“ und „Team Claude + Codex“), die Strategie in `STRATEGIE.md`. Claude (Anthropic) leitet das Projekt und spielt als Einziger ein.

## Für Codex verbindlich

- Arbeite nur im Worktree `../paperbot-codex` bzw. im Ordner, in dem du gestartet wurdest. Lies und schreibe nichts außerhalb.
- **Nie `git commit`, nie `git push`**, kein Wechsel auf andere Branches oder Stände.
- **Nie Daten-Dateien ändern:** `portfolio.json`, `journal.csv`, `messung.csv`, `dexscreener.csv`, `abgelehnt.csv`, `knapp_abgelehnt.csv`, `marktphase.json`, `flugschreiber/`, `verlauf/`, `experimente/`, `copy/`, `scout/`, `copy_wallets.txt`. Große Dateien nicht ganz lesen, sondern per Skript auswerten.
- Nicht ändern ohne ausdrückliche Erlaubnis in der Auftragskarte: `bot.py`, `copy_bot.py`, `scout_bot.py`, `.github/workflows/`, `.claude/settings.json`, `.claude/hooks/`.
- **Keine Schlüssel, Token oder Webhook-URLs** suchen, lesen, ausgeben oder notieren (auch nicht unter `~/.claude/` oder `~/.codex/`). Das Repository ist öffentlich.
- Neue Felder in gespeicherten Daten nur mit `setdefault`/`.get`, neue CSV-Spalten nur hinten anhängen. Kein einzelner Fehler darf einen Bot stoppen.
- Tests: `python -m pytest` (alle grün). Dashboard-Tests mit `dashboard/.venv`.
- Sprache: Berichte, Doku und Kommentare auf Deutsch; Code-Kommentare ohne Umlaute.
- Bei Prüfungen: nur Funde berichten, nichts ändern.
