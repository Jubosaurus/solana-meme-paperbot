# Copy Trading

- Eigener Bot (`copy_bot.py`) seit 30.09.; jede Wallet hat ein eigenes Konto mit 10 SOL; Erkennung per Helius-WebSocket (`logsSubscribe`). [[Q-STRATEGIE]]
- Kauf: jeder Kauf des Traders ab 0,1 SOL = 0,2 SOL bei uns, auch Nachkäufe; Kauf blockiert bei mehr als ±15 % Preisabstand zum Trader; Kaufmeldungen älter als 60 s nie nachkaufen. [[Q-STRATEGIE]] [[Q-CLAUDE]]
- Verkauf: derselbe Anteil wie der Trader, gesammelt ab 20 % oder beim kompletten Ausstieg; Verkäufe nie blockiert; kein Take-Profit, kein Stop-Loss. [[Q-STRATEGIE]]
- Schattenpositionen verfolgen blockierte Käufe virtuell weiter; am 01.10. waren 27 % der Käufe an der Preisgrenze blockiert. [[Q-STRATEGIE]]
- Wallet-Regeln: Bot (Flutschutz: > 30 Meldungen/min und ≥ 80 % fehlgeschlagen, oder > 300/min) → ersetzen; 72 h ohne Trade → ersetzen; nach 30 Positionen und > 1 SOL Verlust → ersetzen. [[Q-CLAUDE]]
- Flutschutz nur nach Menge meldete am 01.10. den echten Vieltrader [[922M]] ab; seither gilt Menge und Fehleranteil. [[Q-STRATEGIE]] [[Q-CLAUDE]]
- Neue Runde mit 10 SOL, sobald das Geld für keinen Kauf reicht, auch bei offenen Positionen (seit 02.10.), weil 922M mit 0,19 SOL stehen blieb und 291 Käufe ausgelassen wurden. [[Q-STRATEGIE]]
- Seit 04.10. Obergrenze 22 aktive Wallets; die Scout-Automatik nimmt auf und ersetzt (siehe [[Wallet-Scout]]). [[Q-STRATEGIE]]
- Stand 03.10. 20:20 UTC: Alle 36 Wallets seit Start, mit entfernten: −42,21 SOL; die 21 aktiven +0,67 SOL; davon fast alles [[HEBO]] und dort ein einziger Coin ([[PIGEON]]). [[Q-2026-10-03-Ueberpruefung]]
- Stand 04.10. ~05:45 UTC: seit Start −44,0 SOL über alle Wallets; die 22 aktiven zusammen +21,7 SOL, ohne PIGEON −10,3 SOL. [[Q-Zusammenfassung-Chat]]
- Die Summe der Aktiven beschönigt: Durch das Entfernen von Zrool, Putrick und Cooker sind deren Verluste daraus verschwunden; mit ihnen standen die Aktiven am Vorabend bei etwa +0,7 SOL. [[Q-Zusammenfassung-Chat]]
- ⚠️ Abweichende Gesamtwerte je Stand: −36 SOL (Dashboard 03.10. nachmittags), −37,0 SOL (16:45 UTC), −42,2 SOL (03.10. 20:20 UTC), −44,0 SOL (04.10. ~05:45 UTC); die Zeitpunkte unterscheiden sich, vor allem fielen offene Positionen von HEBO und 922M. [[Q-STRATEGIE]] [[Q-2026-10-03-Ueberpruefung]] [[Q-Zusammenfassung-Chat]]
- Die alte Copy-Zahl (+7,9 SOL) zählte nur laufende Runden und verschwieg frühere; Hauptzahl ist seither das Ergebnis seit Start über alle Runden. [[Q-STRATEGIE]]
- Grenzen der Simulation: Kauf zum Jupiter-Kurs in dem Moment, in dem wir den Trade sehen; die Gebühren-Vorteile des Traders lassen sich auf Papier nicht nachbilden. [[Q-STRATEGIE]]
- Hauptstrategie und Copy-Coins sind fast getrennte Welten: Nur 14 von 680 Copy-Coins kaufte auch die Hauptstrategie. [[Q-2026-10-04-Video-Nachrechnung]]
- Siehe [[Exit-Liquiditaet]], [[Bot-Wallets]], [[Kopieren-nicht-blind]], [[Wallet-Signal-Nachrechnung]], [[Wallets-entfernt-Uebersicht]], [[Copy-Fehlbuchungen-bis-03-10]].
- Aktive Wallets (Stand 04.10.): [[4DOV]], [[6ANG]], [[HEBO]], [[Troupe]], [[Gake]], [[Pikalosi]], [[Dior]], [[3zsr]], [[C7bF]], [[2FPk]], [[haru]], [[43Nu]], [[koko]], [[Eshi]], [[54cb]], [[42wu]], [[77n6]], [[G7b2]], [[GeFg]], [[499R]], [[2Nxj]], [[7Cn1]].
