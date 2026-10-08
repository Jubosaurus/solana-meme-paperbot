# Plugin context-mode: Prüfung (08.10.2026)

Nur berichtet, nichts geändert. Entscheidung beim Betreiber (Stand: „vorerst behalten“).

## Kurzfassung

- Bei uns ist **kein Datenupload aktiv**. Die dafür nötige Datei `platform.json` gibt es nicht (geprüft: `%APPDATA%\context-mode\`, `~\.context-mode\`, `XDG_CONFIG_HOME` nicht gesetzt). Ohne sie bleibt der Ereignis-Upload aus.
- Das Plugin kontaktiert **von sich aus nur die npm-Registry** (Versionsabfrage beim Start und stündlich). Das ist der einzige gefundene automatische Außenkontakt.
- **Lokal gespeichert** werden vollständige Prompts, `CLAUDE.md`-Inhalt, Befehle, Ausgaben und MCP-Antworten, ohne allgemeine Schwärzung. In den Daten fanden wir **keine echten Schlüssel** (siehe unten).
- Ein Offline-Schalter für die Versionsabfrage existiert nicht. Automatische Updates des Plugins selbst sind bei Drittanbieter-Marketplaces nach Doku standardmäßig aus.

## 1. Quellcode-Prüfung durch Codex (Sol), Karte 20

Geprüft wurde eine Kopie der installierten Version 1.0.169 (aus dem Plugin-Cache, nicht frisch von GitHub). Ob sie genau dem öffentlichen Commit `b706902` entspricht, ließ sich aus der Kopie nicht beweisen. Codex hat nichts ausgeführt und kein Netzwerk benutzt. Die Aussagen sind statisch aus dem Code gelesen. **Das heißt nicht, dass jeder Zweig bei uns läuft.**

**Adressen im Code (Frage 2):**

| Adresse | Zweck |
|---|---|
| `169.254.169.254` | Nur Beispiel für den Cloud-Metadatendienst. Der Bereich `169.254.*.*` wird beim Abrufen von Webseiten **gesperrt**. Es ist kein Ziel von Anfragen. |
| `context-mode.com` | Seite „Insight“, die nur im Browser geöffnet wird (`ctx_insight`). Es werden keine Sitzungsdaten an die Adresse gehängt. Verhalten der Seite selbst: nicht geprüft. |
| `registry.npmjs.org` | Automatische Versionsabfrage (Start, dann stündlich), reiner GET ohne Daten. |
| `raw.githubusercontent.com` | Nur Herkunftsangabe der Modellpreise und Kennung eines eingebetteten Schemas, kein Aufruf. |
| `github.com` | Quelle für das Upgrade und Verweise. |

**Außenkontakte (Frage 1):**
- Automatisch: npm-Versionsabfrage (s. o.).
- Nur bei Bedarf: `npm install` fehlender Pakete (`better-sqlite3`, `turndown`) und Reparatur der nativen Datei, ausgelöst auch durch Hooks. Dabei laufen Befehle, die nicht von uns getippt wurden.
- Nur auf Aufruf: `ctx_fetch_and_index` (Webseiten holen), `ctx_execute` (beliebiger Code, **ohne Netzsperre**, mit unserer ganzen Umgebung), Upgrade, `ctx_insight`.
- Keine eigenen Netzwerk-Server/Ports; die MCP-Verbindung läuft über Standard-Ein-/Ausgabe.

**Telemetrie (Frage 3):** Es gibt einen **bedingten** Upload von Sitzungsdaten an eine konfigurierbare „Plattform-Adresse“ (`platform.json`). Übertragbar wären: Sitzungskennung, Projektpfad, Werkzeugnamen, Zähler, Prompts, Entscheidungen, Fehlertexte, Befehlsausschnitte, `CLAUDE.md`-Inhalt, MCP-Antworten, jeweils auf 200 Zeichen gekürzt, mit teilweiser Schwärzung bekannter Schlüsselformate. Die Adresse wird nicht auf einen festen Host oder HTTPS eingeschränkt. **Bei uns inaktiv, solange keine `platform.json` existiert.** Ein eigener Absturzmelder wurde nicht gefunden.

**Speicherung (Frage 4):**
- `~/.claude/context-mode/sessions/*.db` (Ereignisse, Prompts, Snapshots) und `content/*.db` (Suchindex mit Ausgaben und Dateiinhalten), dazu kleine Protokolle.
- Prompts, Regeltexte und MCP-Antworten werden **ungekürzt und ohne allgemeine Schwärzung** gespeichert. Schwärzung gibt es nur an einzelnen Stellen (`export`-Befehle, bestimmte MCP-Feldnamen, vor einem Upload).
- Aufbewahrung: Sitzungen 7 Tage, Suchindex 14 Tage, höchstens 1000 Ereignisse je Sitzung. Fehlerprotokolle und Statistikdateien: keine Frist gefunden. Löschen lokal mit `ctx_purge`.

**Hooks (Frage 5):** `pretooluse` kann Bash-Befehle **vor der Ausführung ersetzen** (z. B. `curl`/`wget` durch einen Hinweis) und WebFetch sperren. `posttooluse` liest Ein- und Ausgabe und speichert sie. Dazu `sessionstart` (liest `CLAUDE.md`), `userpromptsubmit` (speichert deine Prompts), `precompact`, `stop` (speichert bis 2000 Zeichen der letzten Antwort).

**Selbst-Update (Frage 6):** Kein automatisches Upgrade im Startweg gefunden. `ctx_upgrade` liefert nur einen Befehl, den der Assistent ausführen soll. Dieser Befehl lädt **den aktuellen GitHub-Stand** (nicht den geprüften Commit) und führt dessen Installations- und Buildcode aus. Daher: `ctx_upgrade` nur nach eigener Prüfung ausführen. Kein gemeinsamer Offline-Schalter gefunden.

**Umgebung (Frage 7):** Von `ctx_execute` gestarteter Code erbt unsere **gesamte Umgebung** (auch Schlüssel-Variablen) mit echtem Benutzerverzeichnis und Netzwerk. Eine „Sandbox“ ist das nicht. Ein eigener Sammelzugriff auf `.env`, `.ssh`, `.aws` wurde nicht gefunden. Lesende Zugriffe auf Claude-Einstellungen, Plugin-Register, `CLAUDE.md`, Gesprächsprotokolle, Memory-Dateien.

**Bundle gegen Quelltext (Frage 8):** Vier Netzwerkstellen wurden verglichen und stimmen überein. Eine vollständige Gleichheit ist **nicht bewiesen** (Bundle ist minimiert, kein Neubau durchgeführt).

**Auffälliges (Frage 9):**
- Schreibzugriffe außerhalb der eigenen Ordner: Claude-Einstellungen (`settings.json`), Plugin-Register, der globale Hook `~/.claude/hooks/context-mode-cache-heal.mjs`, Shell-Snapshots, beim Upgrade `~/.claude.json`.
- Vermutet, nicht ausgeführt: Bei der Build-Umleitung wird der Befehl in ein `echo` in Anführungszeichen gesetzt, `$` und Backticks werden nicht maskiert (`hooks/core/routing.mjs:811–815`).
- Ein bekannter Befund der automatischen Prüfung (security-guidance, mittel): `hooks/session-helpers.mjs` liest eine Marker-Datei im gemeinsamen Temp-Ordner, ohne den Inhalt zu prüfen. Auf einem Ein-Benutzer-PC kaum ausnutzbar; nicht weiter untersucht.
- Kein verschleierter Schadcode und keine absichtliche Datensammlung belegt. **Eine pauschale Unbedenklichkeit lässt sich aus einer statischen Prüfung nicht ableiten.**

## 2. Suche nach Schlüsseln in `~/.claude/context-mode/` (Claude)

44 Dateien, 20 MB, nur Treffer gezählt, keine Werte ausgegeben.

| Muster | Ergebnis |
|---|---|
| Discord-Webhook-URL | 1 Treffer in `sessions\d1ea…db`. Es ist die **Test-Platzhalter-Adresse aus `tests/test_sicherheit.py`** (Vergleich bestätigt, Token hat keine echte Länge). Kein echter Webhook. |
| Helius `api-key=<UUID>` | keiner |
| Schlüsselnamen mit Wert (`GMGN_API_KEY=`, `JUPITER_…`, `HELIUS_…`, `BIRDEYE_…`, `DISCORD_WEBHOOK…`, `GITHUB_TOKEN` …) | keiner |
| `api_key=…` allgemein | 20 Treffer, alle derselbe 17-stellige Name (Platzhalter/Text aus Dokumentation, kein Schlüssel) |
| `BEGIN … PRIVATE KEY` | keiner |
| GitHub-Token, `sk-…`, Discord-Bot-Token, `Bearer …` | keiner |
| Base58-Zeichenketten mit 64–88 Zeichen | 336 Treffer; 105 davon decodieren zu 64 Byte, **keine ist ein gültiges Solana-Keypair** (geprüft: zweite Hälfte = öffentlicher Schlüssel zur ersten). Es sind Transaktions-Signaturen. |

Grenzen: Unbekannte Schlüsselformate (z. B. GMGN-Key ohne festes Präfix) sind nicht sicher erkennbar. Da der Key nie in einer Ausgabe oder Eingabe stand und die Windows-Variable inzwischen gelöscht ist, kann das nicht mehr gegengeprüft werden. Auch Dateien außerhalb von `context-mode/` (z. B. `~/.claude/projects/` mit Gesprächsprotokollen) wurden nicht durchsucht.

## 3. Automatische Updates abschalten (Recherche des Hilfe-Agenten, nicht selbst nachgeprüft)

- Laut Claude-Code-Doku (`code.claude.com/docs/en/plugins/install`, Abschnitt „Keep plugins updated“) gilt: **Marketplaces von Drittanbietern haben Auto-Update standardmäßig aus**, nur der offizielle Marketplace und Anthropic-Namen standardmäßig an.
- Abschalten: in `~/.claude/settings.json` bei `extraKnownMarketplaces.context-mode` das Feld `"autoUpdate": false` ergänzen, oder in `/plugin` → Marketplaces → context-mode → „Disable auto-update“. Aktuell steht dort **kein** `autoUpdate`-Feld, es gilt also der Standard.
- Es gibt einen gemeldeten Fehler, bei dem die Einstellung nicht in `known_marketplaces.json` landet.
- Zusätzlich: Eigene Wege des Plugins (stündliche npm-Abfrage, `cache-heal`, Nachinstallation fehlender Pakete) werden dadurch **nicht** abgeschaltet. Das wäre nur durch Plugin-Deaktivierung oder eine Netzsperre möglich.
- Version pinnen: nicht geklärt.

## Optionen für die Entscheidung

1. **Behalten wie jetzt:** Risiko gering, solange keine `platform.json` entsteht. `ctx_upgrade` nicht ohne Prüfung ausführen.
2. **Behalten, absichern:** `"autoUpdate": false` setzen; regelmäßig prüfen, ob `%APPDATA%\context-mode\platform.json` existiert; `ctx_purge` gelegentlich.
3. **Entfernen:** Plugin und Hook `context-mode-cache-heal.mjs` zusammen entfernen (der Hook wurde vom Plugin selbst angelegt), `~/.claude/context-mode/` löschen.

Nicht entschieden. Es wurde nichts verändert.
