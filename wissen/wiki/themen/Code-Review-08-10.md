# Code-Review des Bestands (08.10.2026)

- Codex (Sol) prüfte `dashboard/rechnung.py`, `bot.py` (Verkauf/Experimente, Kauf/Filter), `copy_bot.py`, `scout_bot.py`/`gmgn.py` und Workflows in 6 Karten; Karte 7 (Testlücken) ist noch offen. Es wurde nichts am Bestand geändert. [[Q-2026-10-08-Code-Review]]
- Codex meldete 35 hohe Funde (31 verschiedene, 4 Doppelungen), 24 mittlere und 5 niedrige. Claude führte alle 41 Nachweis-Tests aus: alle rot wie vorgesehen; bei 11 hohen Funden zusätzlich am Code gelesen. Ergebnis: 35 bestätigt, 0 falsch. [[Q-2026-10-08-Code-Review]]
- Gemessen an den echten Daten: In allen 12 Konten stimmen KAUF-/VERKAUF-Zeilen im Journal mit den abgeschlossenen Trades überein (keine Doppelten); nur 2 von 2.579 Verkäufen hatten Erlös 0 (Gebührenfehler höchstens 0,003 SOL). [[Q-2026-10-08-Code-Review]]
- Für den Strategie-Review gilt laut Bericht: Hauptstrategie und Experimente können mit den heutigen Zahlen bewertet werden, mit Vorbehalt bei beendeten Experimenten (Vergleichszeitraum der Kontrollgruppe endet nie), `heisse_coins` (kauft bei jedem Ausfall der Bundle-Prüfung) und `notbremse_25`/`drittel_leiter` (Kauf 2–4 s später). [[Q-2026-10-08-Code-Review]]
- Copy-Trading: 12 hohe Funde (u. a. Lücken beim Nachholen, Schatten-Ergebnis −100 % bei fehlendem Kurs); Häufigkeit in den echten Daten ist nicht gemessen. [[Q-2026-10-08-Code-Review]]
- Beheben ist nicht entschieden; Bot-Logik wird nur mit Zustimmung des Betreibers geändert. [[Q-2026-10-08-Code-Review]]
