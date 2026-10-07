# Sicherheitsprüfung des ganzen Repos – 07.10.2026

**Kurzfassung:** Kein Fund mit hoher Schwere. **Kein Schlüssel stand je im Git-Verlauf** (Code, Doku, Wiki, `auswertungen/`, `.claude/`). Es gibt ein paar kleine Schwächen, die ich nur auflisten, aber nicht ohne dein Okay ändern will.

## Wie geprüft wurde

- Das Plugin „Claude Security“ ist installiert, lief hier aber nicht: Es braucht das Workflow-Werkzeug, das in dieser Sitzung fehlt. Es wurde nichts angelegt.
- Deshalb habe ich selbst nach denselben Schwerpunkten geprüft:
  - Alle Dateien im Git-Verlauf außer den Daten-Dateien nach Schlüsseln durchsucht (Discord-Webhooks, GitHub-Tokens, Helius-`api-key=`, private Schlüssel, lange Geheimtexte). Es waren 64.254 Dateiversionen.
  - Workflows, Dashboard, Scout-Automatik und Codex-Konfiguration von Hand gelesen.
- **Nicht durchsucht:** Daten-Dateien wie `journal.csv`, `verlauf/`, `flugschreiber/`, `copy/`, `experimente/`. Sie schreiben die Bots selbst, und Schlüssel kommen dort nicht vor. Das Repo ist 3,7 GB groß, ein Volltreffer-Scan wäre sehr langsam.
- Die sechs Treffer des Suchmusters sind harmlos. Es sind Beispielwerte in Fremd-Doku (Streamlit, Helius), Transaktions-Signaturen und Coin-Adressen. Ich habe nur den Aufbau der Zeilen angesehen, nie die Werte ausgegeben.
- Codex (Sol) hat die Funde unabhängig gegengeprüft. Seine Ergebnisse stehen unten getrennt als „Codex fand“.

## Funde

### 1. Discord-Webhook-Adresse kann in Fehlertexten im öffentlichen Log landen
- **Schwere:** niedrig bis mittel
- **Was könnte passieren:** Schlägt das Senden an Discord fehl, schreibt `bot.py` (`discord()`) den Fehlertext ins Log. Der enthält die Webadresse mit der Webhook-Nummer. GitHub versteckt nur den *ganzen* geheimen Wert, nicht Teile davon, und die Logs sind bei einem öffentlichen Repo öffentlich. Der Text wird auf 120 Zeichen gekürzt. Es könnten also nur die Nummer und die ersten Zeichen des Schlüsselteils sichtbar werden, nicht der volle Schlüssel. Ob und wie viel wirklich sichtbar wird, habe ich nicht an einem echten Fehlerlog überprüft.
- **Codex fand das als zusätzlichen Punkt** und stufte es als „hoch, abhängig vom Fehlertext“ ein. Meine Einstufung ist wegen der Kürzung niedriger.
- **Getan:** nichts. `bot.py` ist Bot-Logik. Die Änderung braucht code-pruefer und kritische Prüfung durch Codex.
- **Vorschlag:** Fehlertexte vor dem Ausgeben von `/api/webhooks/...` befreien (eine Zeile in `_hide_key`).

### 2. Helius-Schlüssel steckt in der WebSocket-Adresse des Copy-Bots
- **Schwere:** niedrig
- **Was könnte passieren:** `copy_bot.py` gibt Fehlertexte beim Verbindungsaufbau ohne den Filter `_hide_key` aus. Auch die Endmeldung in Discord übernimmt `last_error` ungefiltert. Im Actions-Log versteckt GitHub den vollen Schlüssel automatisch, in Discord nicht. Einen echten Leck-Fall habe ich nicht gefunden. Die Meldungen der Bibliothek enthalten die Adresse normalerweise nicht.
- **Codex bestätigt** das. Auch er hat kein tatsächliches Leck nachgewiesen.
- **Getan:** nichts.
- **Vorschlag:** Die Ausgaben und `last_error` im Copy-Bot ebenfalls durch `_hide_key` schicken.

### 3. Dashboard im Heimnetz: Lesen für alle im WLAN, Schreiben nur am PC
- **Schwere:** niedrig
- **Stand:** `start_handy.bat` startet das Dashboard auf allen Netzadressen, ohne Anmeldung. Die Firewall-Regel gilt nur für private Netze. Jeder im Heim-WLAN kann also alles *ansehen*. Das sind dieselben Daten, die ohnehin im öffentlichen Repo stehen. Schreiben (Wallets prüfen) geht nur, wenn die Verbindung vom PC selbst kommt oder Streamlit keine Adresse meldet. Ein WLAN-Nachbar hat eine fremde Adresse und ist gesperrt, Proxy-Köpfe sperren ebenfalls. Der Standard in `config.toml` ist nur localhost.
- **Offener Punkt (Codex fand):** Es gibt keine Prüfung des Host-Namens. Über „DNS-Rebinding“ könnte eine fremde Webseite im PC-Browser theoretisch das lokale Dashboard ansprechen. Ob Streamlit das abfängt, habe ich nicht getestet. Schlimmster Fall: eine Wallet-Adresse in der Prüfliste, keine Handelsregel und keine Schlüssel.
- **Getan:** nichts.
- **Vorschlag:** Beim Schreiben zusätzlich den `Host`-Kopf auf `localhost`/`127.0.0.1` prüfen. Das ist eine schreibende Dashboard-Funktion und braucht die kritische Prüfung durch Codex.

### 4. Scout-Automatik: fremder Text kann nicht in `copy_wallets.txt`
- **Schwere:** niedrig (kein Fund, nur Rest-Risiko)
- **Stand:** Wallet-Namen werden auf Buchstaben, Ziffern und `_.-` beschränkt. Der Begründungstext besteht aus festen Wörtern und berechneten Zahlen. Coin-Symbole stehen nur in Discord und in `kandidaten.csv`, nie in `copy_wallets.txt`. Adressen kommen aus eigenen Daten und müssen dem Adress-Muster entsprechen.
- **Codex:** bestätigt für den normalen Ablauf. Eine Garantie gebe es nicht, falls Antworten oder gespeicherte CSV-Dateien manipuliert würden (z. B. ein Zeilenumbruch im Begründungstext).
- **Getan:** nichts.
- **Vorschlag:** Zeilenumbrüche aus dem Begründungstext entfernen und Adressen beim Schreiben noch einmal prüfen. Das ist eine Absicherung, kein akutes Loch.

### 5. GitHub-Workflows
- **Schwere:** niedrig
- Gestartet werden sie nur per Zeitplan oder von Hand, nie durch Pull-Requests von Fremden. Schlüssel kommen nur aus Secrets, keine fremden Actions außer den offiziellen `actions/checkout@v5` und `actions/setup-python@v6`.
- **Schwäche:** Die Actions sind auf Versions-Tags festgelegt, nicht auf feste Commits. Werden die Tags bei GitHub verschoben, läuft neuer Code mit Schreibrechten. Zusätzlich haben Haupt- und Copy-Workflow `actions: write`. Das braucht der Kettenstart, es ist also gewollt.
- **Getan:** nichts. **Vorschlag:** Die zwei Actions auf Commit-Nummern festsetzen.

### 6. Codex-Konfiguration
- **Schwere:** niedrig
- **Stand:** Codex läuft in `workspace-write`, `approval_policy = on-request`, nur im Worktree `../paperbot-codex`. Das Nachtlauf-Skript prüft das Ergebnis nachträglich und lehnt Commits oder verbotene Dateien ab. Die Windows-Sandbox steht auf „unelevated“, der schwächeren Stufe. Die stärkere Stufe ist in `.claude/codex-anleitung.md` beschrieben.
- **Codex fand:** Die Sperrliste des Nachtlaufs enthält `bot.py`, `copy_bot.py` und `scout_bot.py` nicht. Das ist unkritisch, weil nur ein Patch gespeichert wird und Claude ihn vor dem Einspielen prüft. Der Nachtlauf ist außerdem nur vorbereitet, nicht aktiv.
- **Getan:** nichts. **Vorschlag:** Die Sandbox vor dem ersten Nachtlauf auf „elevated“ stellen (steht schon in der Anleitung) und die drei Bot-Dateien in die Sperrliste aufnehmen.

### 7. Discord (nur lesen)
- **Schwere:** keine Beanstandung. Schreib-Werkzeuge sind in `.claude/settings.json` gesperrt. Meldungen der Bots gehen als „Embeds“, in denen `@everyone` aus Coin-Namen niemanden anpingt.

### 8. Dashboard-Darstellung fremder Texte (News, Coin-Namen)
- **Schwere:** keine Beanstandung. Fremder Text wird maskiert (`html.escape`). Links aus RSS-Feeds müssen mit `http://` oder `https://` beginnen. Der einzige Ort mit `unsafe_allow_html` (`strategie.py`) zeigt nur selbst berechnete Zahlen.

## Was ich nicht geprüft habe

- Die GitHub-Einstellungen im Browser (Branch-Schutz, Secret-Scanning, wer Schreibrechte hat). Das kannst nur du dort ansehen.
- Ob frühere Logs der Bots (nicht im Repo) etwas enthalten. Der GitHub-Verbindungsfehler beim Start (`plugin:github`, „Authorization header is badly formatted“) hat mit der Prüfung nichts zu tun.
- Die Schlüssel selbst (`~/.codex/`, `~/.claude/channels/discord/.env`): bewusst nicht angesehen.

## Nächste Schritte (nur mit deinem Okay)

Die Punkte 1 und 2 (Fehlertexte filtern) sind klein und betreffen Bot-Dateien. Dafür müssten zuerst Tests laufen, `code-pruefer` und die kritische Prüfung durch Codex, dann würde ich einspielen. Punkt 3 (Host-Prüfung) ginge im selben Zug.

---

## Nachtrag (07.10., nach deinem Okay): was umgesetzt wurde

| Nr. | Punkt | Ergebnis |
|---|---|---|
| 1 | Webhook nie im Log | `_hide_key` ersetzt jetzt alle bekannten Schlüssel aus der Umgebung und die Muster `/api/webhooks/…` und `api-key=…`, auch abgeschnittene Reste. Es gilt für `stdout`/`stderr` aller drei Bots (Filter beim Start) und für Titel, Text und Fehler jeder Discord-Meldung. Fällt der Filter selbst aus, wird `***` ausgegeben, nie der Rohtext. |
| 1b | Actions-Logs prüfen | Letzte 90 Tage, alle drei Workflows, 308 Läufe (Hauptbot 209, Copy 62, Scout 37), 2 Läufe nicht lesbar (vermutlich noch laufend). **Kein Treffer für „webhooks/“. Dein Webhook muss nicht erneuert werden.** Schlüssel kamen in keinem Fall vor; GitHub versteckt volle Werte ohnehin. |
| 2 | Copy-Bot | `last_error` und alle Ausgaben laufen durch den Filter. |
| 3 | Dashboard | Streamlit prüft die Host-Namen nun selbst (`allowedHosts`: localhost, 127.0.0.1, ::1; CORS und XSRF ausdrücklich an). `start_handy.bat` fügt die Heimnetz-Adresse des PCs hinzu. Zusätzlich lehnt `wallets.ist_lokal` jeden fremden Host-Kopf ab. Am echten Server getestet: Host „evil.example“ bekommt 403, localhost und die Heimnetz-Adresse verbinden. **Dashboard einmal neu starten**, damit es gilt. |
| 4 | Scout | Begründungstexte werden einzeilig (Zeilenumbrüche, Steuer- und Unicode-Trennzeichen entfernt). Adressen müssen exakt dem Muster entsprechen. |
| 5 | Workflows | `actions/checkout` und `actions/setup-python` auf feste Commit-Nummern gesetzt (Version v5/v6 im Kommentar). Codex hat die Änderung gemacht (Auftragskarte), ich habe die Nummern selbst bei GitHub abgefragt. Neuere Versionen (v7) habe ich bewusst nicht eingeführt. |
| 6 | Nachtlauf | Sperrliste enthält jetzt `bot.py`, `copy_bot.py`, `scout_bot.py` und das Nachtlauf-Skript selbst. |

**Prüfungen:** alle Tests grün (neue Tests: `tests/test_sicherheit.py`, Ergänzungen in `tests/test_dashboard_wallets.py`); `code-pruefer`: freigegeben mit Hinweisen (Absturzschutz des Filters ist daraufhin eingebaut); kritische Prüfung durch Codex (Sol): fand fünf Schwächen im neuen Filter, alle behoben (siehe unten).

**Codex fand (kritische Prüfung) – alle behoben und mit Tests abgesichert:**
- Der Log-Filter umging `writelines()` → jetzt ebenfalls gefiltert.
- Zusätzliche Discord-Embeds wurden nicht gefiltert → jetzt alle Texte in der ganzen Meldung.
- Versionierte Pfade wie `/api/v10/webhooks/…` wurden nicht erkannt → Muster auf `/webhooks/…` erweitert.
- Kurze Helius-Schlüssel (unter 8 Zeichen) bleiben wie bisher in jeder Länge geschützt.
- Die Maske verschluckte Nachbartext (`api-key=abc,HTTP=500`) → Fehlerstatus bleibt lesbar.

**`code-pruefer` fand:** Der Filter hatte keinen Absturzschutz → eingebaut (bei Fehler wird `***` ausgegeben, nie der Rohtext). Zur Endfassung lief eine zweite Prüfung.

