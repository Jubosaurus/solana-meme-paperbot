# Experiment Listing-Welle (seit 04.10.)

- Misst „Kauf kurz vor/zum Handelsstart“, nicht „Kauf bei Ankündigung“: Bei Binance und Coinbase wird das neue Handelspaar in der offiziellen Marktliste erkannt, nicht die Ankündigung. [[Q-STRATEGIE]]
- Upbit und Bithumb: nur Aufzeichnung, kein Kauf; Upbits Ankündigungs-Schnittstelle lieferte dem Bot 403 und wird nicht umgangen (Schalter `LISTING_UPBIT_ANKUENDIGUNG` auf `False`). [[Q-STRATEGIE]]
- Gekauft wird, wenn ein neues Binance-/Coinbase-Asset erscheint, die Erkennung jünger als 10 min ist und der Token über Jupiter eindeutig gefunden wird (gleicher Ticker, Liquidität ≥ 100.000 $, Jupiter-verifiziert); 0,2 SOL; Verkauf bei voller Handelbarkeit des Paars, sonst nach 72 h; Notbremse −40 %. [[Q-STRATEGIE]]
- Binance-Ankündigungsseite (robots.txt verbietet /bapi/) und Bithumb-Seite (Cloudflare 403) werden nicht benutzt. [[Q-STRATEGIE]]
- Hauptwert ist die Aufzeichnung (`ereignisse.csv`, `geruechte.csv`); erwartet werden 0,3–1 kaufbares Listing pro Woche (geschätzt), das Urteil nach 200 Trades dauert voraussichtlich Jahre. [[Q-STRATEGIE]]
