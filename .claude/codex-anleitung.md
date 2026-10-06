# Codex – Anleitung (Stand 06.10.2026)

Codex ist der Programmier-Assistent von OpenAI. Er läuft über dein ChatGPT-Pro-Abo und hilft Claude beim Prüfen und bei klar abgegrenzten Aufgaben. Regeln zur Zusammenarbeit: `CLAUDE.md`, Abschnitt „Team Claude + Codex“.

## 1. Was installiert ist

| Teil | Wo | Version |
|---|---|---|
| Codex CLI (Kommandozeile) | `npm install -g @openai/codex` | 0.160.1 |
| Offizielles Plugin `openai/codex-plugin-cc` (kein Fork) | Claude Code, Benutzer-Ebene, Marktplatz `openai-codex` | 1.0.6 |
| Konfiguration | `C:\Users\admin\.codex\config.toml` + Profile `astra`, `sol`, `terra`, `luna` (`*.config.toml`) | – |

**Review-Schranke (review gate) ist AUS** und bleibt aus. Sie würde Claude bei jedem Antwort-Ende zu einer Codex-Prüfung zwingen und kann das Kontingent schnell leeren. Prüfen: `/codex:setup` zeigt „review gate: disabled“.

**Windows:** läuft nativ (ohne WSL). Das Plugin startet Codex unter Windows über die Shell; harmlose Meldung „DeprecationWarning DEP0190“ ignorieren. Sandbox steht auf `unelevated` (geht ohne Admin). Stärker ist `elevated` – dafür einmal in einer **Admin-PowerShell**:

```
codex sandbox setup --elevated --user admin --codex-home C:\Users\admin\.codex
```

danach in `config.toml` `sandbox = "elevated"` setzen. Empfohlen vor dem ersten Nachtlauf.

## 2. Anmelden (einmalig)

Im Claude-Code-Fenster eintippen:

```
! codex login
```

Es öffnet sich der Browser → mit dem ChatGPT-Konto (Pro) anmelden → fertig. Klappt der Browser nicht: `! codex login --device-auth` (Code am Handy/PC eingeben). **Kein API-Key** verwenden – das würde extra kosten.
Danach `/codex:setup` → muss „Status: ready“ zeigen.

## 3. Modell wählen

Die vier Modelle (offizielle Namen laut developers.openai.com/codex/models; am 06.10. mit `codex debug models` für unser Konto bestätigt):

| Kurzname | Modell-ID | Wofür bei uns | Kontingent (grob) |
|---|---|---|---|
| Astra | `gpt-6-astra` | nur heikelste Prüfungen | am knappsten |
| Sol | `gpt-6.1-sol` | Standard: kritische Prüfung, Arbeitsaufgaben | mittel |
| Terra | `gpt-5.6-terra` | Ersatz, wenn Sol leer (ältere Reihe, „während der Umstellung verfügbar“) | mittel |
| Luna | `gpt-6-luna` | Einfaches, Wiederholbares | sehr groß (laut Doku ~20× Sol) |

**Standard ist Sol** (steht in `config.toml`).

So wählt man ein anderes Modell:

- **Im Plugin (aus Claude heraus):** `--model <Modell-ID>` anhängen. Profile kennt das Plugin nicht.
  - `/codex:adversarial-review --model gpt-6-astra --base HEAD~1`
  - `/codex:rescue --model gpt-6-luna --effort medium <Auftrag>`
- **Direkt in der Kommandozeile:** Profil mit `-p`:
  - `codex -p terra` (interaktiv) oder `codex exec -p luna "<Auftrag>"`
  - Ein Profil ist eine eigene Datei `~/.codex/<name>.config.toml` (seit Codex 0.134 nicht mehr `[profiles.x]` in `config.toml`).
- **Im laufenden Codex-Fenster:** `/model`.

## 4. Kontingent: Woran erkennt man „aufgebraucht“, wann geht es weiter?

- **Anzeigen:** im Codex-Fenster `/status` (Restkontingent und Rücksetzzeit) oder im Browser chatgpt.com/codex/settings/usage.
- **Aufgebraucht erkennt man** an einer Fehlermeldung zum Nutzungslimit („usage limit reached“ o. ä., meist mit „try again at …“-Uhrzeit), im Plugin als fehlgeschlagener Auftrag in `/codex:status` / `/codex:result`. Eine bereits laufende Runde darf laut Doku noch zu Ende arbeiten.
- **Rücksetzung:** Pro hat laut Doku derzeit **kein 5-Stunden-Limit**, es können aber **Wochenlimits** gelten. Die genaue Uhrzeit steht nur in `/status` bzw. im Usage-Dashboard – die Doku nennt keinen festen Wochentag. Rücksetzzeiten in UTC und deutscher Zeit in `.claude/codex-status.md` eintragen.
- Die Kontingente gelten **je Modell unterschiedlich schnell** (Astra am teuersten, Luna am billigsten). Darum die Modell-Leiter in `CLAUDE.md`.
- **Keine Zusatz-Credits kaufen** ohne Entscheidung des Betreibers.

## 5. Die wichtigsten Befehle (Plugin)

| Befehl | Was er tut |
|---|---|
| `/codex:review` | normale Prüfung, nur lesen |
| `/codex:adversarial-review [--model …] [--base <ref>] [Fokus]` | **kritische Prüfung**: stellt Ansatz und Annahmen in Frage, nur lesen |
| `/codex:rescue [--model …] <Auftrag>` | Aufgabe an Codex geben (bei uns nur im Worktree, siehe CLAUDE.md) |
| `/codex:status`, `/codex:result`, `/codex:cancel` | Hintergrund-Aufträge ansehen, Ergebnis holen, abbrechen |
| `/codex:setup` | Bereitschaft prüfen (Schranke NICHT einschalten) |

Für Prüfungen in einem anderen Ordner (Worktree) nimmt das Plugin intern `--cwd <Ordner>`.

### Wichtig: Aufruf durch Claude (Stand 06.10.)

`/codex:review` und `/codex:adversarial-review` sind im Plugin mit `disable-model-invocation: true` markiert. Das heißt: **Claude kann sie nicht über das Skill-Werkzeug starten** (das war der Grund für den Fehlschlag am 06.10.); sie funktionieren nur, wenn der Betreiber den Befehl selbst eintippt. Der Aufruf von Claude aus geht direkt über das Plugin-Skript (Bash, im Hauptordner oder mit `--cwd <Ordner>`):

```
node "C:/Users/admin/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/codex-companion.mjs" adversarial-review --wait --model gpt-6.1-sol --base HEAD~1 "Fokus: ..."
```

- `--wait` = im Vordergrund; für längere Läufe stattdessen `run_in_background` im Bash-Werkzeug nutzen und mit `... status` / `... result` abholen.
- Unterstützt: `--base <ref>`, `--scope auto|working-tree|branch`, `--model`, `--cwd`; Fokustext am Ende.
- Der Pfad enthält die Plugin-Version (1.0.6); nach einem Plugin-Update anpassen. Probe ohne Verbrauch: dasselbe Skript mit `setup` (zeigt „Status: ready“).
- Die Warnung „DEP0190“ ist harmlos.

