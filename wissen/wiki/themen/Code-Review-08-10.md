# Code-Review des Bestands (08.10.2026)

- Codex (Sol) prüfte `dashboard/rechnung.py`, `bot.py` (Verkauf/Experimente, Kauf/Filter), `copy_bot.py`, `scout_bot.py`/`gmgn.py` und Workflows in 6 Karten; Karte 7 (Testlücken) ist noch offen. Es wurde nichts am Bestand geändert. [[Q-2026-10-08-Code-Review]]
- Codex meldete 35 hohe Funde (31 verschiedene, 4 Doppelungen), 24 mittlere und 5 niedrige. Claude führte alle 41 Nachweis-Tests aus: alle rot wie vorgesehen; bei 11 hohen Funden zusätzlich am Code gelesen. Ergebnis: 35 bestätigt, 0 falsch. [[Q-2026-10-08-Code-Review]]
- Gemessen an den echten Daten: In allen 12 Konten stimmen KAUF-/VERKAUF-Zeilen im Journal mit den abgeschlossenen Trades überein (keine Doppelten); nur 2 von 2.579 Verkäufen hatten Erlös 0 (Gebührenfehler höchstens 0,003 SOL). [[Q-2026-10-08-Code-Review]]
- Für den Strategie-Review gilt laut Bericht: Hauptstrategie und Experimente können mit den heutigen Zahlen bewertet werden, mit Vorbehalt bei beendeten Experimenten (Vergleichszeitraum der Kontrollgruppe endet nie), `heisse_coins` (kauft bei jedem Ausfall der Bundle-Prüfung) und `notbremse_25`/`drittel_leiter` (Kauf 2–4 s später). [[Q-2026-10-08-Code-Review]]
- Copy-Trading: 12 hohe Funde (u. a. Lücken beim Nachholen, Schatten-Ergebnis −100 % bei fehlendem Kurs); Häufigkeit in den echten Daten ist nicht gemessen. [[Q-2026-10-08-Code-Review]]
- Beheben ist nicht entschieden; Bot-Logik wird nur mit Zustimmung des Betreibers geändert. [[Q-2026-10-08-Code-Review]]

## Häufigkeit in den echten Daten (08.10., Abend)

- Hauptstrategie: CR3-4 (Bundle-Check unvollständig) und CR3-6 (Transfergebühren-Prüfung fällt aus) nicht je Kauf messbar; in den Logs 22 fehlgeschlagene Transaktionsabrufe (26.09.–01.10.), kein Kauf kurz danach, und keine einzige Ausfallzeile der Transfergebühren-Prüfung in 73 Hauptbot-Logs. [[Q-2026-10-08-Code-Review-Haeufigkeit]]
- `heisse_coins` (CR3-5): 181 Käufe, davon geschätzt mindestens 36 (20 %) nach einem RPC-Ausfall, Ergebnis dieser Gruppe +0,31 SOL roh; die übrigen 144 −6,33 roh (−6,91 mit Kosten). Urteil ändert sich nicht, das Experiment bleibt klar im Minus. Zuordnung ist eine Näherung (27 Läufe ohne Log). [[Q-2026-10-08-Code-Review-Haeufigkeit]]
- Sicherung (CR6-3): 5 Warnungen „Sicherung fehlgeschlagen“ in 14 Tagen (Hauptbot 2, Copy 3, alle in abgebrochenen Läufen) und 12 Push-Fehler im Lauf (11 am 07.10.); kein Datenverlust nachweisbar. [[Q-2026-10-08-Code-Review-Haeufigkeit]]
- Copy: CR4-1 (Kauf nach über 60 s) 1 von 4.377 Käufen; CR4-2 (Verkaufsanteil auf Nachkäufe) 521 Nachkäufe in 177 Positionen, Risikobetrag 8,9 SOL, tatsächliche Wirkung nicht herauszurechnen; CR4-12 (Schatten −100 %): kein Kurs-0-Fall in 180.250 Schatten-Zeilen, die 8 Fälle mit −100 % (−2,2 SOL) sind Überweisungen; CR4-5/CR4-9 nicht messbar, Folgen: 1.107 verpasste Käufe und 23 vom Stundenabgleich gefangene Verkäufe. [[Q-2026-10-08-Code-Review-Haeufigkeit]]
- Scout: CR5-1 bis CR5-3 ohne neue Helius-Abfragen nicht nachrechenbar; von 8 seit 05.10. automatisch aufgenommenen Wallets mit Ergebnis liegen 6 im Minus (zusammen −1,36 SOL), alle vier mit knappster Aufnahme-Prognose im Minus (kleine Stichprobe). CR5-7: 24 aktive Wallets, 6 Plätze frei, 4DOV heute nicht ersetzbar; die Zahlen zu 4DOV (−4,25 SOL am 08.10. gegen +0,20 SOL in `copy/konten.json`) passen nicht zusammen. [[Q-2026-10-08-Code-Review-Haeufigkeit]]
- Vorschlag im Bericht: vor dem Strategie-Review nichts beheben (höchstens den echten Grund und übersprungene Transaktionen mitschreiben); danach CR6-3, CR5-1 bis CR5-3 und CR5-7, dann CR4-2/CR4-3; CR4-1, CR3-6 und CR4-12 wegen Seltenheit nicht. Beschlossen ist nichts. [[Q-2026-10-08-Code-Review-Haeufigkeit]]

## Wallet-Regel: welche Zahl gilt (08.10., Abend)

- Die Regel im Code (`copy_bot.py`, `scout_bot.py`, Regel-Hinweis im Dashboard) rechnet nur **realisierte** Ergebnisse (geschlossene Positionen, alle Runden). Die Tagesauswertung vom 08.10. nannte dagegen „Kontowert minus 10 SOL“ bzw. „seit Start“ mit offenen Positionen. [[Q-2026-10-08-Wallet-Regel-Zahlen]]
- 4DOV am 08.10. früh: 80 Positionen, realisiert +1,21 SOL, mit 18 offenen Positionen −4,25 SOL; am Abend 86 Positionen, realisiert 0,00, mit offenen −5,84. Nach der Regel im Code ist 4DOV also nicht unter der Grenze und wird derzeit nicht wegen Verlust ersetzt. [[Q-2026-10-08-Wallet-Regel-Zahlen]]
- G7b2 (realisiert −2,05, genannt −2,40), 7Cn1 (−3,19, genannt −2,69) und 2Nxj (−1,40) liegen nach beiden Rechnungen über der Grenze; ihre Entfernung ist nach beiden gedeckt. [[Q-2026-10-08-Wallet-Regel-Zahlen]]

## Korrektur-Paket (08.10., Abend)

- CR6-3 behoben (eingespielt 08.10.): Sicherung der drei Workflows mit bis zu 4 Versuchen, danach roter Lauf; der Scout schreibt die Prüfliste dabei nie zurück. Aufzeichnung des echten Bundle-Check-Grundes (zwei neue Spalten hinten in `knapp_abgelehnt.csv`). Kauf- und Ablehnungsverhalten unverändert. Siehe `STRATEGIE.md`, Änderungsprotokoll 08.10. [[Q-2026-10-08-Wallet-Regel-Zahlen]]

## Regeländerung Wallet-Verlust (Entscheidung Betreiber, 08.10. Abend)

- Die Verlust-Regel rechnet seit 08.10. mit dem Kontowert seit Start über alle Runden, offene Positionen zum aktuellen Kurs (gemeinsame Rechnung `copy_bot.ergebnis_seit_start`, gleiche Zahl wie Dashboard „seit Start“); ohne Kurs einer offenen Position kein Urteil. [[Q-2026-10-08-Wallet-Regel-Probe]]
- Schutzliste `AUTO_GESCHUETZT`: 4DOV wird bis zum Strategie-Review nie wegen Verlust oder Stille ersetzt; die Bot-Regel gilt weiter. [[Q-2026-10-08-Wallet-Regel-Probe]]
- Probe vor dem Einbau: Heute erfüllt nur 4DOV (−5,76 SOL seit Start bei 86 Positionen) die neue Regel; ersetzbar sind 0. Nächste Kandidaten: Dior (29 Positionen, −10,96), C7bF (29, −1,50), 54QZ, 8K7Z, Pikalosi. [[Q-2026-10-08-Wallet-Regel-Probe]]

## Position ohne Kurs (Entscheidung Betreiber, 08.10. spät)

- Antwortet Jupiter bei einem Verkauf ausdrücklich „keine Route“, zählt der Rest der Position in der Verlust-Regel sofort mit Wert 0; liefert Jupiter 24 h lang keinen gültigen Kurs, zählt sie danach mit Wert 0; kürzer und bei Ausfall bleibt es bei „kein Kurs = kein Urteil“. Scout-Grund, Copy-Endmeldung und Wallet-Wächter nennen, wenn eine Wallet nur deshalb unter die Grenze fällt. Der frühere offene Punkt (gerugter Coin ohne Kurs) ist damit geschlossen. [[Q-2026-10-08-Wallet-Regel-Probe]]

