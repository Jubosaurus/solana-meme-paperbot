# GMGN-Lesetest (08.10.2026)

Zweck: Prüfen, ob die GMGN-OpenAPI mit unserem Schlüssel Daten liefert und was abgelehnt wird. Plan: `2026-10-08_gmgn_plan.md`.
Hier stehen nur Feldnamen und Erkenntnisse, **keine GMGN-Werte** (Entscheidung vom 08.10.).

## Ergebnis in Kürze

- Alle 10 getesteten Endpunkte lieferten Daten (HTTP 200, `code 0`). Keine Ablehnung wegen **Guthaben**, **IP** oder **Signatur**.
- Die GMGN-Wallet hatte dabei kein Guthaben. Aufladen ist nach jetzigem Stand nicht nötig. Ob die 100-$-Schwelle später bei den Wallet-Abfragen greift, ist damit nicht ausgeschlossen.
- Die signierte Abfrage (`wallet_holdings`, Ed25519) wurde angenommen. Die Signatur-Form aus dem Plan stimmt: Nachricht `Pfad:sortierte Query:Body:Zeit`, Base64.
- Unsignierte POST-Abfragen (Trenches, Hot-Searches) brauchen nur den API-Key im Header, keine Signatur.
- Nicht aufgerufen: Swap, Order, Cooking, `follow_wallet`.
- Der Schlüssel wurde nirgends ausgegeben oder gespeichert; die Windows-Variable `GMGN_API_KEY` ist danach gelöscht. Der Schlüssel kommt später als GitHub-Secret.

## Tempo-Regel (Lehre)

- Gewicht je Abfrage, Gratis-Tarif: Rate 5. Abfragen pro Sekunde = 5 / Gewicht. Takt im Test: nach jeder Abfrage mindestens 2 × Gewicht / 5 s warten.
- Fehler im ersten Versuch: 4 Abfragen ohne Pause. Folge: HTTP 429 „IP rate limit exceeded“, dann „IP is temporarily banned due to repeated rate limit violations“. Die Sperre war nach wenigen Minuten wieder weg (Dauer nicht angegeben). Im zweiten Lauf mit Takt kein 429.
- Weitere Lehre: Im ersten Lauf wurde die falsche Adresse aus `copy_wallets.txt` genommen (Zeilenformat `Name: Adresse`) → `invalid wallet address`. Beim Einbau die Adresse nach dem Doppelpunkt lesen.

## Endpunkte

Gewicht in Klammern. „Signiert“ = zusätzlicher Header `X-Signature`.

| Endpunkt | Gewicht | Kommt an | Felder (Auswahl) | Nutzen |
|---|---|---|---|---|
| `GET /v1/token/info` | 1 | ja | Adresse, Symbol, Name, Decimals, Logo, Pool, Start- und Migrationszeit, Holder, Liquidität, Launchpad und Fortschritt, ATH-Kurs, Kurs und Käufe/Verkäufe je Zeitfenster (1 m bis 24 h), Twitter/Website | Scout: Coin-Kontext. Namenswelle/Tag 20: Name, Startzeit und Social-Links eines Coins. |
| `GET /v1/user/wallet_stats` | 3 | ja | realisierter Gewinn, Käufe/Verkäufe, Kosten, Gewinnstufen-Verteilung, Trefferquote, durchschnittliche Haltedauer, Tags, Tag-Ränge, Twitter-Angaben | Scout: Gegenprobe zu Stufe 2 (Gewinn, Trefferquote, Haltedauer), Markierungen Bot/Smart. |
| `GET /v1/user/wallet_activity` | 3 | ja | Tx-Hash, Zeit, Art (Kauf/Verkauf/Transfer), Coin, Menge, Kosten in USD, Gebühren (Gas, DEX, Priority, Tip), Launchpad, `next` zum Blättern | Scout: eigene Transaktionsprüfung gegenprüfen. Copy: Gegenprobe zu aufgezeichneten Trades. |
| `GET /v1/user/wallet_holdings` (signiert) | 2 | ja | je Coin: Bestand, Kosten, realisierter/unrealisierter Gewinn, Käufe/Verkäufe, Haltebeginn/-ende, letzte Aktivität | Scout: gehaltene Coins zum Kurs (Fehler „Tage gehaltene Coins“). |
| `GET /v1/user/created_tokens` | 2 | ja | bis 100 frühere Coins (Zeit, ATH-Marktkapitalisierung, Bundler-Rate, offen ja/nein), Summen `inner_count`/`open_count`/`open_ratio`, bester Coin | Serien-Devs-Experiment, Dev-Prüfung. |
| `GET /v1/market/token_top_traders` | 5 | ja | je Trader: Adresse, Bestand, Kauf-/Verkaufsvolumen, Gewinn, Anzahl Käufe/Verkäufe, Netto-Fluss | Scout: Kandidaten finden. Teuer (Gewicht 5), nur gezielt. |
| `GET /v1/user/smartmoney` | 1 | ja | live Käufe/Verkäufe: Wallet, Coin, Menge, USD, Preis, Zeit, Seite, Wallet-Infos | Scout: Kandidatenquelle. Tag 20: Smart-Money-Käufe als Spur. |
| `GET /v1/user/kol` | 1 | ja | gleiche Felder wie Smartmoney, für bekannte Influencer-Wallets | Tag 20: Influencer-Käufe als On-Chain-Spur von Aufmerksamkeit. |
| `POST /v1/trenches` | 2 | ja | je Gruppe `new_creation`/`near_completion`/`completed` (bis 60 Coins): Bundler-Rate, Bot-Degen-Rate, Entrapment, Dev-Haltequote, Ersteller-Zähler, Zeit bis Graduation, Marketing-Marker (DexScreener-Anzeige/-Boost) | Hauptbot: Frühwarnfelder zu Bundler/Dev. Namenswelle/Tag 20: neue Coins mit Namen und DexScreener-Markern. |
| `POST /v1/market/hot_searches` | 3 | ja | je Coin: Kursänderung (1 m/5 m/1 h), Volumen, Liquidität, Käufe/Verkäufe, Holder, Top-10-Quote, Twitter/Website | Tag 20: Trending-Liste wie DexScreener-Trending; Namenswelle: aufkommende Namen. |

## Nutzen für „News vor Chart“ (Tag 20)

Tag 20 = Nachrichten als Vorsignal, Spur on-chain über Namenswelle und DexScreener-Trending (Quelle: `STRATEGIE.md`).

- **Hot-Searches** und **Trenches** liefern Name, Symbol, Startzeit und Social-Links neuer/laufender Coins. Damit lässt sich die Namenswelle (viele Coins mit gleichem Namen) mit einer zweiten Quelle neben DexScreener gegenprüfen.
- Trenches zeigt zusätzlich DexScreener-Marker (Anzeige, Boost, Trending-Balken) je Coin, als zusätzliche Trending-Spur.
- **KOL** und **Smartmoney** zeigen, wann bekannte Wallets einen Namen kaufen. Das kann die Spur früher bestätigen als der Chart.
- Offen: Ob diese Quellen vor unseren bisherigen Signalen liegen, ist **nicht** gemessen. Dafür bräuchte es eine Aufzeichnung über mehrere Tage (nur Namen und Zeiten, keine GMGN-Statistiken im Repository).

## Offene Punkte / nächste Schritte

1. Einbau in den Scout nur nach Zustimmung des Betreibers zum Plan (Bot-Logik: Pflicht-Prüfungen, `--ohne-automatik` bei Gegenproben).
2. GitHub-Secret `GMGN_API_KEY` anlegen. Wallet-Zugriff und IP-Verhalten auf GitHub-Rechnern (wechselnde IPs, nur IPv4) ist **nicht** getestet; der Lesetest lief von der Heim-IP.
3. Tempo im Code erzwingen (Takt 2 × Gewicht / 5 s, bei 429 Pause und Abbruch statt Wiederholen).
4. Rechte zur Veröffentlichung abgeleiteter Werte bleiben ungeklärt: keine GMGN-Werte ins öffentliche Repository.
