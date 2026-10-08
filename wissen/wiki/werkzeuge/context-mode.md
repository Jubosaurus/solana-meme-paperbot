# context-mode

- Die installierte Plugin-Kopie Version 1.0.169 wurde am 08.10. statisch geprüft; kein aktiver Datenupload und kein echter Schlüssel in den untersuchten Daten gefunden. Die Prüfung beweist weder vollständige Gleichheit mit dem öffentlichen Stand noch allgemeine Unbedenklichkeit. [[Q-2026-10-08-context-mode]]
- Betreiberentscheidung am 08.10.: behalten und absichern; Marketplace-Auto-Update aus. [[Q-2026-10-08-context-mode]]
- Kein `ctx_upgrade` und kein Plugin-Update ohne neue Prüfung. [[Q-2026-10-08-context-mode]]
- `ctx_execute`, `ctx_execute_file` und `ctx_batch_execute` nie verwenden, solange Schlüssel-Variablen gesetzt sind: gestarteter Code erbt die Umgebung und hat Netzwerkzugriff. [[Q-2026-10-08-context-mode]]
