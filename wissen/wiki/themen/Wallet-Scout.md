# Wallet-Scout und Automatik

- Eigener Bot (`scout_bot.py`) seit 01.10.; findet Kandidaten für das Copy Trading, erstellt eine Rangliste, kauft nichts. [[Q-STRATEGIE]]
- Quellen: Gewinner-Coins (Hoch mindestens 3x) der letzten 48 h aus eigenen Daten; frühe Käufer über Helius; optional Birdeye-Top-Trader. [[Q-STRATEGIE]]
- Bewertung seit 02.10.: Rendite auf 7 Tage inklusive gehaltener Coins, minus Reibung je nach Haltedauer; Grund: GMGN-Trader halten Tage, der Scout sah nur schnelle Fehlkäufe (Haltedauer 1–2 min statt Tage). [[Q-STRATEGIE]]
- Bewertung 3 (04.10.): Wallets mit Median-Kauf unter 0,05 SOL werden nicht bewertet; Anlass: Kleinstkäufer standen mit 84.602 und 455 Punkten oben (siehe [[Kleinstkaeufer-in-Ranglisten]]). [[Q-STRATEGIE]] [[Q-2026-10-03-Ueberpruefung]]
- Das Kriterium „20–700 Transaktionen“ ist nicht prüfbar, weil der Scout höchstens 1.000 Signaturen liest und fast alle Wallets bei genau 1.000 stehen. [[Q-2026-10-03-Ueberpruefung]]
- Öffentliche Quellen für Wallets, die erlaubt und ohne Konto nutzbar wären, gibt es laut Überprüfung 03.10. nicht (Kolscan/GMGN nur per Scraping, ausgeschlossen; DexScreener liefert keine Trader). [[Q-2026-10-03-Ueberpruefung]]
- Prüfliste: Adressen in `scout/pruefen.txt`; jede wird nur einmal abgefragt (Speicher in `scout/status.json`); Neubewertung erst bei höherer `SCORING_VERSION`. [[Q-STRATEGIE]]
- Probelauf der gelockerten Automatik (04.10.) auf 36 neu bewerteten Wallets: 3 erfüllen die Kriterien (alle Birdeye); mit 5 statt 3 Coins wären es 2 gewesen. [[Q-STRATEGIE]]
- Scout-Zeitplan seit 04.10. stündlich, aber nur ein Lauf je 6-h-Fenster; Grund: seit 03.10. hatte GitHub 2 von 8 geplanten Läufen ausgelassen, die übrigen kamen bis zu 6 h zu spät. [[Q-STRATEGIE]]
- **Automatik (Entscheidung des Betreibers 04.10.; Schalter `AUTO_AUFNAHME`):**
- Aufnahme-Kriterien: kein Bot, aktiv < 24 h, mindestens 3 Coins (bis 04.10. 5), erwartete Rendite nach Reibung > 0 und ohne besten Coin > 0, höchstens 200 Trades pro Tag, Kauf-Median ≥ 0,1 SOL. [[Q-STRATEGIE]] [[Q-CLAUDE]]
- Limit 22 aktive Wallets; bei vollem Limit ersetzen in der Reihenfolge Bot, still (72 h), größter Verlust (≥ 30 Positionen, > 1 SOL); sonst Warteliste (7 Tage). [[Q-STRATEGIE]]
- Höchstens 3 Änderungen pro Tag (UTC); Schonfrist 7 Tage/30 Positionen nur für das Ergebnis; stille Wallets werden auch ohne Ersatz entfernt. [[Q-STRATEGIE]]
- 🕒 Überholt (alter Stand, die Entscheidung vom 04.10. gilt): Vorher galt „Bot entscheidet nichts selbst“, der Scout lieferte nur Ranglisten; seit 04.10. ändert die Automatik `copy_wallets.txt` selbst. [[Q-CLAUDE]] [[Q-Zusammenfassung-Chat]]
- Die vorgemerkte Entfernung von 43Nu und 42wu übernimmt die Automatik (72-h-Regel). [[Q-STRATEGIE]]
- Erste automatische Aufnahme: [[7Cn1]] am 04.10.; [[Loopierr]] wurde am 04.10. automatisch als Bot entfernt. [[Q-Copy-Wallets]]
- Tx-Prüf-Modus (04.10.): Ergebnis für [[2FPk]]/[[54cb]]: alle Trades erkannt, nichts verpasst. [[Q-2026-10-04-Nachtlauf]]
- Siehe [[Kleinstkaeufer-in-Ranglisten]], [[Birdeye]], [[Helius]].
