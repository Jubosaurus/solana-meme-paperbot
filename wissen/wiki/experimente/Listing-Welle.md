# Experiment Listing-Welle (seit 04.10.)

- Misst „Kauf kurz vor/zum Handelsstart“, nicht „Kauf bei Ankündigung“: Bei Binance und Coinbase wird das neue Handelspaar in der offiziellen Marktliste erkannt, nicht die Ankündigung. [[Q-STRATEGIE]]
- Upbit und Bithumb: nur Aufzeichnung, kein Kauf; Upbits Ankündigungs-Schnittstelle lieferte dem Bot 403 und wird nicht umgangen (Schalter `LISTING_UPBIT_ANKUENDIGUNG` auf `False`). [[Q-STRATEGIE]]
- Gekauft wird, wenn ein neues Binance-/Coinbase-Asset erscheint, die Erkennung jünger als 10 min ist und der Token über Jupiter eindeutig gefunden wird (gleicher Ticker, Liquidität ≥ 100.000 $, Jupiter-verifiziert); 0,2 SOL; Verkauf bei voller Handelbarkeit des Paars, sonst nach 72 h; Notbremse −40 %. [[Q-STRATEGIE]]
- Binance-Ankündigungsseite (robots.txt verbietet /bapi/) und Bithumb-Seite (Cloudflare 403) werden nicht benutzt. [[Q-STRATEGIE]]
- Hauptwert ist die Aufzeichnung (`ereignisse.csv`, `geruechte.csv`); erwartet werden 0,3–1 kaufbares Listing pro Woche (geschätzt), das Urteil nach 200 Trades dauert voraussichtlich Jahre. [[Q-STRATEGIE]]
- Studiengrundlage: Ante (2019) „Market Reaction to Exchange Listings of Cryptocurrencies“ (327 Listings, 22 Börsen) und `github.com/Asalio123/binance-listing-study` (alle Binance-USDT-Listings 2021–2026, nicht begutachtet), jeweils als Quelle im Experiment-Eintrag von STRATEGIE.md genannt. [[Q-STRATEGIE]]
- Video-Hinweis (05.10.2026, Eigenangabe rasmr): Erwartete Auslöser (angekündigte Auftritte, bekannte Börsen-Listings) werden vorab gekauft, beim Ereignis folgt oft ein Ausverkauf; unerwartete Auslöser tragen länger. Passt zum Anstieg vor der Ankündigung und Abklingen danach, den diese Studie annimmt; Verkauf zum Handelsstart ist bereits so umgesetzt. [[Q-2026-10-05-Video-Erkenntnisse]]
