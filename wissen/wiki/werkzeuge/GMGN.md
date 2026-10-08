# GMGN

- GMGN dokumentiert am 07.10.2026 eine offizielle Agent-API/OpenAPI für Token-, Markt- und Wallet-Daten mit Solana-Unterstützung. [[Q-2026-10-07-API-Pruefung]]
- Die frühere Aussage, GMGN habe keine offizielle Daten-API, ist laut der Prüfung überholt; frühere Grenzen aus einer alten Freigabeseite wurden nicht auf die aktuelle OpenAPI übertragen. [[Q-2026-10-07-API-Pruefung]]
- Für einen späteren Test kommen laut Bericht Wallet-Statistik, Wallet-Verlauf, Wallet-Bestände, Top-Trader, Token-Informationen und Token-Sicherheitsdaten in Betracht; keiner dieser Endpunkte wurde aufgerufen. [[Q-2026-10-07-API-Pruefung]]

- Beim Lesetest am 08.10. lieferten die gepr?ften Lese-Endpunkte Daten; Guthaben, IP und Signatur f?hrten dabei zu keiner Ablehnung. [[Q-2026-10-08-GMGN-Lesetest]]
- Zu schnelles Abfragen f?hrte zu HTTP 429 und kurzzeitiger IP-Sperre; die Sperrdauer ist nicht bestimmt. Beim Einbau Abstand einhalten und bei 429 pausieren/abbrechen. [[Q-2026-10-08-GMGN-Lesetest]]
- Adressen aus `copy_wallets.txt` stehen im Format `Name: Adresse`; beim Einlesen die Adresse nach dem Doppelpunkt verwenden. [[Q-2026-10-08-GMGN-Lesetest]]
- Entscheidung vom 08.10.: GMGN-Wallet nur als Zugang, kein Handel. Schl?ssel ausschlie?lich als GitHub-Secret; keine GMGN-Werte ins Repository. [[Q-2026-10-08-GMGN-Lesetest]]
- GMGN-Einbau nur als zus?tzliche Kandidatenquelle: am 08.10. vom Betreiber freigegeben, Umsetzung l?uft. [[Q-2026-10-08-GMGN-Lesetest]]
