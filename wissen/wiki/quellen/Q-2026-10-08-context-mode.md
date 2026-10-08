# Quelle: context-mode-Prüfung und Entscheidung (08.10.2026)

- Rohquelle: `auswertungen/2026-10-08_context_mode.md`.
- Datum der Quelle: 08.10.2026.
- Die installierte Plugin-Kopie Version 1.0.169 wurde statisch geprüft; ihre vollständige Gleichheit mit dem öffentlichen Commit ist nicht bewiesen. [[Q-2026-10-08-context-mode]]
- In der Prüfung wurde kein aktiver Datenupload und kein echter Schlüssel in den untersuchten context-mode-Daten gefunden. Das gilt nur für den untersuchten Stand und die dort beschriebenen Grenzen. [[Q-2026-10-08-context-mode]]
- Die Betreiberentscheidung vom 08.10. lautet: context-mode behalten und absichern; Marketplace-Auto-Update ist aus. [[Q-2026-10-08-context-mode]]
- `ctx_upgrade` und Plugin-Updates sollen erst nach einer neuen Prüfung erfolgen. [[Q-2026-10-08-context-mode]]
- `ctx_execute`, `ctx_execute_file` und `ctx_batch_execute` dürfen nicht verwendet werden, solange Schlüssel-Variablen gesetzt sind, weil gestarteter Code die Umgebung erbt und Netzwerkzugriff hat. [[Q-2026-10-08-context-mode]]
