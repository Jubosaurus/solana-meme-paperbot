---
title: "Nexus Core – Dashboard-Entscheidung"
datum: "2026-10-07"
typ: werkzeug
status: "Teil 1 gebaut; Teil 2 in Arbeit"
quellen:
  - Q-2026-10-07-Nexus-Core
  - Q-CLAUDE
  - Q-STRATEGIE
---

# Nexus Core – Dashboard-Entscheidung

Stand: 07.10.2026; gehört zu [[Dashboard]]. [[Q-2026-10-07-Nexus-Core]]

Das Wiki sammelt Wissen und beschließt nichts; verbindlich bleiben `STRATEGIE.md` und `CLAUDE.md`. [[Q-CLAUDE]]

## Teil 1: Aussehen und Marke – gebaut

- Seit 07.10.2026 heißt das neue Dashboard-Aussehen „Nexus Core“, mit verbindlichen Vorgaben in `dashboard/DESIGN.md`. [[Q-CLAUDE]] [[Q-STRATEGIE]]
- Die Marke soll Bots, Listings, Strategietests und Kennzahlen an einem Ort zeigen und klare Zustände sowie gut lesbare Zahlen vermitteln. [[Q-2026-10-07-Nexus-Core]]
- Die Farben sind dunkles Schieferblau für den Hintergrund (`#080B11`), dunkle Karten (`#0F172A`), Indigo für Marke und Navigation (`#6366F1`), Grün für Gewinn/OK (`#10B981`), Rot für Verlust (`#F43F5E`) und Gelb für Hinweise (`#F59E0B`). [[Q-2026-10-07-Nexus-Core]]
- Die Schriftvorgaben sind Space Grotesk oder Inter Tight für Überschriften und Logo, Inter für Texte und JetBrains Mono für Zahlen und Wallet-Adressen. [[Q-2026-10-07-Nexus-Core]]
- Seit 07.10.2026 liegen die optischen Regeln in `dashboard/stil.py`, gemeinsame Bausteine in `dashboard/ansicht.py` und Logo, Schriften und Symbole in `dashboard/static/`. [[Q-CLAUDE]]
- Seit 07.10.2026 hat das Menü aufklappbare Gruppen und die Fußzeile zeigt den Datenstand. [[Q-CLAUDE]]
- Seit 07.10.2026 zeigt die Übersicht den Kontowert roh und mit Kosten nebeneinander; die Kennzahlen wurden vor und nach dem Umbau auf Gleichheit geprüft. [[Q-STRATEGIE]]
- Am 07.10.2026 blieb die Rechnung unverändert; hinzu kamen die Hilfsfunktionen `kosten_abzug`, `kontowert_mit_kosten` und `ergebnis_mit_kosten` in `dashboard/rechnung.py`. [[Q-STRATEGIE]]
- Stand 07.10.2026 sind für die Handy-Web-App Name, Favicon und Farben vorgesehen, während ein eigenes Startbildschirm-Symbol und eine eigene Startfarbe mit Streamlit nicht sauber umsetzbar sind. [[Q-CLAUDE]]

## Teil 2: Neue Funktionen und Seiten – in Arbeit

Am 07.10.2026 wurden die Ideen 1–5 zum Bau ausgewählt; Wissen, Rennbahn, Verpasste Chancen, Wallet-Wächter und Tageszeit sind laut Auftragskarte noch in Arbeit, und Claude trägt das Ergebnis nach. [[Q-2026-10-07-Nexus-Core]]

„Vorgemerkt – in Arbeit“ kennzeichnet hier die ausgewählten Seiten im Bau; Stand 07.10.2026 wird keine der zehn neuen Ideen als gebaut geführt. [[Q-2026-10-07-Nexus-Core]]

| Nr. | Idee | Aussage zum Stand 07.10.2026 | Status | Quelle |
|---|---|---|---|---|
| 1 | Wissen | Wiki und Tagesberichte sollen im Dashboard lesbar und durchsuchbar werden. | Vorgemerkt – in Arbeit | [[Q-2026-10-07-Nexus-Core]] |
| 2 | Rennbahn | Alle Konten sollen zusammen mit der Kontrollgruppe als Linien in einem Diagramm erscheinen, wahlweise roh oder mit Kosten. | Vorgemerkt – in Arbeit | [[Q-2026-10-07-Nexus-Core]] |
| 3 | Verpasste Chancen | Die Seite soll zeigen, wie knapp abgelehnte Coins weiterliefen, und bei fehlenden Folgekursen ehrlich „keine Daten“ anzeigen. | Vorgemerkt – in Arbeit | [[Q-2026-10-07-Nexus-Core]] |
| 4 | Wallet-Wächter | Die Seite soll die Belegung der Wallet-Liste bis 30, die heutigen Änderungen und den nächsten möglichen Ersatz nur als Vorschau zeigen. | Vorgemerkt – in Arbeit | [[Q-2026-10-07-Nexus-Core]] |
| 5 | Tageszeit | Ergebnisse nach UTC-Stunde und Wochentag sollen nur zur Beobachtung dienen, mit einem Hinweis bei kleinen Fallzahlen. | Vorgemerkt – in Arbeit | [[Q-2026-10-07-Nexus-Core]] |
| 6 | Kosten-Regler | Der Regler soll Ergebnisse bei anderen Kostenaufschlägen, etwa 1, 2 oder 4 Prozent, durchspielen. | Vorgemerkt – als Nächstes | [[Q-2026-10-07-Nexus-Core]] |
| 7 | Regel-Zeitleiste | Regeländerungen sollen als Markierungen im Kontoverlauf sichtbar werden. | Vorgemerkt | [[Q-2026-10-07-Nexus-Core]] |
| 8 | Scout-Treffsicherheit | Scout-Punkte sollen mit unserem Ergebnis je Wallet verglichen werden, wobei wenige Wallets die Aussage begrenzen. | Vorgemerkt | [[Q-2026-10-07-Nexus-Core]] |
| 9 | Wallet entfernen mit Grund | Nur am PC soll eine Wallet mit Datum und Grund auskommentiert werden können, mit Bestätigung, eigenem Commit und STRATEGIE-Eintrag. | Nur nach Entscheidung des Betreibers | [[Q-2026-10-07-Nexus-Core]] |
| 10 | Kurzbericht zum Kopieren | Ein fertiger Text mit Kennzahlen soll sich in den Chat oder fürs Handy kopieren lassen. | Vorgemerkt – als Nächstes | [[Q-2026-10-07-Nexus-Core]] |

Die schreibende Idee 9 wartet am 07.10.2026 wegen des Konflikts mit der Scout-Automatik auf eine Entscheidung des Betreibers. [[Q-2026-10-07-Nexus-Core]]

## Teil 3: Logo und Qualitätsschleife (07.10.2026)

- Das Logo wurde aus einer JPG-Vorlage mit dunklem Hintergrund freigestellt und als PNG mit Transparenz eingebaut, nicht als SVG, weil die Farbverläufe als Vektor nicht treu nachzubauen waren; Erzeuger ist `tools/logo_aus_vorlage.py`. [[Q-2026-10-07-Nexus-Core-Teil3]]
- Der Leitsatz „Centralized Intelligence · Algorithmic Precision“ steht unter dem Logo in der Seitenleiste und in der Fußzeile. [[Q-2026-10-07-Nexus-Core-Teil3]]
- Der Wallet-Wächter beschriftet Entfernungen stiller Wallets durch die Scout-Automatik als „automatisch“; die Zählung gegen das Tageslimit blieb unverändert. [[Q-2026-10-07-Nexus-Core-Teil3]]
- In fünf Fotorunden (je Seite 1280 und 390 px) wurde das Dashboard nachgebessert; Runde 1–3 lautete die ehrliche Antwort auf „Würde ein Mensch das kaufen?“ nein, Runde 5 ja mit kleinen Restpunkten (Zeilenhöhen der Lernen-Tabelle am Handy). [[Q-2026-10-07-Nexus-Core-Teil3]]
- Roh- und Kosten-Kontowerte aller 13 Strategie- und 47 Copy-Konten waren vor und nach dem Umbau auf denselben Daten identisch. [[Q-2026-10-07-Nexus-Core-Teil3]]
- Die Codex-Sandbox hat weder Netzwerk noch Browser; Fotos macht immer Claude mit `tools/foto.py`. [[Q-CLAUDE]]

## Leitplanken

- Für die neuen lesenden Seiten werden nur lokale Daten verwendet; die bestehende News-Seite bleibt die dokumentierte Ausnahme mit öffentlichen RSS-Feeds. [[Q-2026-10-07-Nexus-Core]] [[Q-CLAUDE]]
- Rechnungen laufen nur über `dashboard/rechnung.py`, das auch die Tagesauswertung nutzt. [[Q-2026-10-07-Nexus-Core]] [[Q-CLAUDE]]
- Schreibende Dashboard-Funktionen sind nur am PC erlaubt; vom Handy aus dient auch „Wallets prüfen“ nur zum Anschauen. [[Q-CLAUDE]]
- Das bestehende Dashboard ändert `copy_wallets.txt` nicht; diese Datei ändert die Scout-Automatik, weshalb Idee 9 eine eigene Entscheidung braucht. [[Q-CLAUDE]] [[Q-2026-10-07-Nexus-Core]]

## Quellen

- [[Q-2026-10-07-Nexus-Core]] – Originalpfade von Design, Dashboard-Anleitung, Ideen und Auftragskarte; Stand und Baukennzeichnung vom 07.10.2026.
- [[Q-CLAUDE]] – Abschnitt „Dashboard“ und Wiki-Verbindlichkeit.
- [[Q-2026-10-07-Nexus-Core-Teil3]] – `auswertungen/dashboard/nexus_core/README.md` (Fotos vorher/nachher, Verbesserungen je Runde, Android-Anleitung).
- [[Q-STRATEGIE]] – Änderungsprotokoll vom 07.10.2026, Eintrag zu Nexus Core Teil 1.
