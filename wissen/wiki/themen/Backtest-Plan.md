# Backtest- und Datenplan (07.10.)

Nur Plan, nichts beschlossen. Offene Entscheidungen stehen am Ende der Rohquelle. [[Q-2026-10-07-Backtest-Plan]]

- Copy-Backtest einer Wallet über 30 Tage ist machbar: Trader-Trades über Helius, Preis „1,8 s später“ zuerst aus der eigenen Verteilung (Käufe < 2 s: Median +1,5 % über Trader-Preis), genauer über Markt-Trades der nächsten 4–6 Slots. Schätzung 300–30.000 Helius-Credits je Wallet. [[Q-2026-10-07-Backtest-Plan]]
- Gut zurückrechenbar: Endspurt, Bündel (Block 0), FOMO-Sprung, Verkaufsregeln, Dev-Regeln, nachgebildete Kontrollgruppe. Nicht zurückrechenbar: Jupiter-Kandidatenlisten, organic-Werte, Shield, RugCheck, Trending. [[Q-2026-10-07-Backtest-Plan]]
- Bitquery-Testphase: 7 Tage, 1.000 Punkte, kein Archiv, Gratisdaten nur „für technische Entwicklung“ – für Backtests zu kurz. Dune-Testphase (14 Tage, 2.500 Credits, Pump.fun-Tabellen ab 01/2024, CSV intern erlaubt) empfohlen. [[Q-2026-10-07-Backtest-Plan]]
- Methodik: nur Daten vom Entscheidungszeitpunkt, tote Coins einschließen, Regeln vorher festlegen, an älteren Wochen suchen und an neueren einmal bestätigen, Testtagebuch gegen zu viele Varianten, erst kalibrieren (Live-Ergebnisse nachbilden), Live-Test bleibt Urteil. [[Q-2026-10-07-Backtest-Plan]]
- Repo: GitHub 2,0 GB, ca. 2.389 Commits/Tag (06.10.); `abgelehnt.csv` (+2,2 MB/Tag) erreicht 50 MB um den 19.10. und die harte GitHub-Grenze 100 MB um den 11.11. [[Q-2026-10-07-Backtest-Plan]]
- Bot prüft 2.330–2.610 Coins/Tag, davon nur 490–580 junge (Rest „Story zu alt“). [[Q-2026-10-07-Backtest-Plan]]
- Entscheidungen des Betreibers 07.10. siehe [[Entscheidungen]]; umgesetzt am 07.10.: Schritt 2 (Repo entlasten) und Schritt 5 (DexScreener). Wirksam ab dem Schichtwechsel ca. 00:45 UTC am 08.10. [[Q-STRATEGIE]]
