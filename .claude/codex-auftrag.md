# Vorlage: Auftragskarte für Codex

Claude füllt eine Karte pro Aufgabe aus und legt sie als `.claude/codex-karten/NN-kurzname.md` ab (Ordner wird nicht committet, siehe `.gitignore`). Codex arbeitet **nur im Worktree `../paperbot-codex`**, committet und pusht nie. Kopiervorlage ab der Linie.

---

# Karte NN: <kurzer Titel>

**Ziel:** <ein bis zwei Sätze: was am Ende anders ist und warum>

**Dateien:** <genau die Dateien, die Codex ändern oder neu anlegen darf>
- lesen erlaubt: <Dateien/Ordner zum Nachschlagen>

**Grenzen:**
- Nur im Worktree `../paperbot-codex` arbeiten, kein `git commit`, kein `git push`, kein `git checkout`/`reset` auf andere Stände.
- Keine Daten-Dateien ändern oder lesen, die groß sind (`portfolio.json`, `journal.csv`, `messung.csv`, `dexscreener.csv`, `flugschreiber/`, `verlauf/`, `experimente/`, `copy/`, `scout/*.csv`, `scout/status.json`), keine `copy_wallets.txt`, keine `scout/pruefen*.txt`.
- Nicht anfassen: `bot.py`, `copy_bot.py`, `scout_bot.py`, `.github/workflows/`, `.claude/settings.json`, `.claude/hooks/` – außer die Karte erlaubt es ausdrücklich.
- Keine Schlüssel, Token, Webhook-URLs lesen, ausgeben oder notieren. Kein Netzwerk außer Paketinstallation, wenn die Karte es erlaubt.
- Bestehende Regeln aus `CLAUDE.md` (Goldene Regeln 3 und 4) gelten.
- <weitere Grenzen dieser Aufgabe>

**Fertig wenn:**
- <prüfbares Kriterium 1>
- <prüfbares Kriterium 2>
- Am Ende eine kurze Zusammenfassung: geänderte Dateien, was getan, was offen, Unsicherheiten.

**Tests:** <z. B. `python -m pytest tests/test_dashboard_rechnung.py -q`; bei Dashboard zusätzlich `dashboard/.venv` + `tests/test_dashboard_wallets.py`> – alle grün, sonst nicht „fertig“ melden.

**Modell:** <Sol | Terra | Luna> (Leiter siehe `CLAUDE.md`; Ersatz, falls leer: <…>)

**Art:** <Arbeitsaufgabe | Einfaches | Prüfung>

---

Nach der Karte: Claude prüft das Ergebnis (`git -C ../paperbot-codex diff`), lässt Tests laufen, holt die Änderung ins Hauptverzeichnis und spielt sie selbst ein (Skill `einspielen`).
