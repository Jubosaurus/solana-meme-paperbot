# Karte 31: Datenquellen fuer Solana- und Pump.fun-Backtests

**Stand und Abrufdatum aller Quellen: 07.10.2026.** Recherche ausschließlich auf öffentlichen Anbieter-Seiten, Dokumentationen, Bedingungen und Anbieter-Repositories. Keine Anmeldung, kein Konto, keine API-Abfrage und keine Handelsdaten geladen. Preise in USD. „Nicht gefunden“ bedeutet: in den unten genannten öffentlichen Quellen nicht belegt. „Unsicher“ bedeutet: widersprüchlich oder ohne Anmeldung nicht überprüfbar. Bewertungen und Rechenbeispiele sind eigene Schlussfolgerungen, keine Zusagen der Anbieter.

## Vergleich

| Quelle | Kosten | Konto | Verlaufstiefe | Pump.fun aufbereitet | Speichern erlaubt | Bewertung für dieses Projekt |
| --- | --- | --- | --- | --- | --- | --- |
| Bitquery | Aktuell 7 Tage, 1.000 API-Punkte; Archiv ausgeschlossen. Developer-Doku nennt abweichend 10.000 Punkte im ersten Monat. Bezahlt ab 49 USD/Monat, Archiv zusätzlich. [^B1][^B2][^B3] | E-Mail, Passwort, Name und Firma; Hinweis auf Firmen-E-Mail. Keine Karte für Trial. Wallet nicht im Formular. [^B1][^B4] | `DEXTrades` etwa 12 h; `DEXTradeByTokens` etwa 7 Tage live, Archiv ab Mitte 2024; `Trading.Trades` etwa 30 Tage. [^B5] | Ja: Kurve, Erstellung, Migration und PumpSwap dokumentiert; tiefe Historie je Datentyp eingeschränkt. [^B6][^B7] | Gratisdaten nur für technische Entwicklung; ausdrückliche lokale Speicherlizenz für API-Trial nicht gefunden. Gratisdaten nicht offen veröffentlichen. [^B8] | Technisch passend, aber kurze Trial-Fenster und widersprüchliche Dokumentation. |
| Dune | Neue Konten: bis 14 Tage, insgesamt 2.500 Credits mit Plus-Funktionen. Danach kostenlos nur ansehen. Analyst 75, Plus 399 USD/Monat. [^D1][^D2] | Benutzerkonto mit Login/Passwort; E-Mail in Datenschutzerklärung. Keine Zahlungsvoraussetzung für Free laut Terms; vollständiges Trial-Formular **unsicher**. [^D3][^D4] | Anbieter nennt vollständige Solana-Blockchain. Pump.fun-Modell beginnt am 14.01.2024; tatsächliche Lücken nicht geprüft. [^D5][^D6] | `pumpdotfun_solana.trades`, `dex_solana.trades`; PumpSwap-Modell im Spellbook. [^D7][^D8] | CSV lokal für interne Nutzung erlaubt, sofern Tarif Export erlaubt; gelegentliche externe Berichte mit Quellenangabe. Kein laufendes Datenprodukt. [^D9] | Beste dokumentierte SQL-Basis für einen kleinen historischen Test; keine dauerhafte kostenlose Abfrage-Stufe. |
| Helius | Free: 1 Mio. Credits/Monat; Developer 49 USD/Monat mit 10 Mio. Credits. [^H1] | Konto über Dashboard. E-Mail als einzige Pflichtangabe nicht gefunden. Agent-Anmeldung kostet 1 USDC und erfüllt die Vorgabe nicht. [^H1][^H2] | Mainnet-Historie laut Methoden-Doku unbegrenzt; Devnet 2 Wochen. [^H3][^H4] | Rohtransaktionen und Parser statt fertiger Preis-/Trade-Tabelle. Neuer Parser hat Pump.fun-Beispiel. [^H5][^H6] | Lokale Blockchain-Datenlizenz nicht eindeutig gefunden; neue Terms begrenzen auf geschäftliche Nutzung. Veröffentlichung von Rohdaten **unsicher**. [^H7] | Sehr günstig für Wallet-Rohhistorie; kein fertiger Marktverlauf für alle Coins. |
| Flipside | Aktueller frei nutzbarer SQL-/API-Tarif **nicht gefunden**. Alte Gratiswerbung ist kein aktueller Tarifbeleg. [^F1][^F2] | Aktuelle Voraussetzungen **nicht gefunden**. [^F2] | Aktuell erreichbare Solana-Historie **nicht gefunden**. [^F2] | Aktuelle Pump.fun-Tabellen **nicht gefunden**. [^F2] | Aktuelle anwendbare Datenlizenz **nicht gefunden**. [^F2] | Für einen neuen Gratis-Test derzeit nicht belastbar: Creator Studio wurde laut Dune eingestellt, alte Doku leitet zu Edisyl um. [^F2][^F3] |
| Birdeye-Verlauf | Standard: 30.000 CUs/Monat, 1 Anfrage/s, eingeschränkte Endpunkte; Lite 39, Starter 99 USD/Monat. [^R1] | Standard-Konto, ausdrücklich keine Kreditkarte; reine E-Mail-Anmeldung und Wallet-Pflicht **nicht gefunden**. [^R2] | Preis-/Trade-Verlauf dokumentiert; garantierter Beginn, Gratis-Verlaufstiefe und vollständige Kurvenabdeckung **nicht gefunden**. [^R3][^R4] | Token-Trades und Coin-Erstellung; fertige historische Graduation-Tabelle **nicht gefunden**. [^R3][^R4] | Veröffentlichte Terms untersagen ausdrücklich auch Download/Speichern und Weitergabe ohne entsprechende Erlaubnis; mögliche Zusatzbedingungen bleiben offen. [^R5] | Für lokale Backtest-Dateien wegen Lizenzlage derzeit ungeeignet. |
| Allium | 100 Explorer Units und 20.000 Developer Units einmalig gratis, ohne Ablauf. Weitere Preise nach Angebot; API-Free ohne Kreditkarte. [^A1][^A2] | Firmen-E-Mail, Name, Organisation und Firmenwebsite; private E-Mail-Adressen nicht akzeptiert. [^A1] | Solana laut Anbieter ab Genesis; konkrete Pump.fun-Tabellen öffentlich nicht zugänglich gefunden. [^A2][^A3] | Solana-DEX-Trades aufbereitet; genaue Pump.fun-/PumpSwap-Schemata **nicht gefunden**. [^A2][^A3] | Interne geschäftliche Nutzung; ausdrückliche dauerhafte lokale Speicherlizenz nicht gefunden. Weitergabe auch abgeleiteter Ergebnisse ohne Vertragsfreigabe eingeschränkt. [^A4] | Interessanter Zusatzkandidat, aber keine einfache private E-Mail-Testphase. |

## Bitquery: besonders genau

### Gratiszugang, Punkte und Preise

Die erneut direkt gelesene Preisseite und die neue Billing-Doku nennen **7 Tage, 1.000 API-Punkte, 100 MCP-Credits, 2 gleichzeitige Streams, 17 Stream-Minuten und 0,2 GB Stream-Daten; kein Archiv und keine Karte nötig**. Dagegen steht in „IDE Points“ noch „10K free points for the first month on the Developer plan“. Ein dauerhaft erneuerbarer kostenloser Developer-Tarif ist damit **nicht belegt**. Die aktuelle Preisseite hat laut Billing-Doku Vorrang. [^B1][^B2][^B3]

Für `dataset: realtime` nennt die Punkte-Doku **5 Punkte je Cube** unabhängig von der Zeilenzahl; zwei Cubes in einer Anfrage kosten demnach 10 Punkte. Eigene Rechnung: 1.000 Punkte reichen rechnerisch für 200 solche Ein-Cube-Abfragen. Für Archivabfragen beschreibt dieselbe Doku variable Kosten nach Umfang und Komplexität; eine feste Archiv-Punktzahl **nicht gefunden**. Billing formuliert allgemeiner „etwa 5 Punkte“, angepasst an die gescannten Daten. **Unsicher:** genaue Abrechnung des jeweiligen Endpunkts vor einem späteren Test. [^B2][^B3]

| Bezahlter Grundtarif | Monatlich | Bei jährlicher Zahlung, pro Monat | Punkte/Monat |
| --- | --- | --- | --- |
| Personal | 49 USD | 29 USD | 100.000 |
| Pro | 99 USD | 69 USD | 1 Mio. |
| Scale | 299 USD | 199 USD | 5 Mio. |

Die Jahrestarife bedeuten Vorauszahlung. Solana-Archiv zusätzlich: OHLCV/Preis-Paket mit `DEXTradeByTokens` 300 USD monatlich bzw. 210 USD bei Jahreszahlung; Transfers/Transaktionen 500 bzw. 350 USD. Die Beschreibung „OHLCV & price only“ belegt **keinen uneingeschränkten historischen Wallet-/Trade-Export**. Der benötigte Feldumfang bleibt unsicher. [^B1][^B3]

Das öffentliche Registrierungsformular fordert E-Mail, Passwort, Passwortbestätigung, Name und Firmenname. Es weist auf gesperrte Anmeldungen und Firmen-E-Mail hin; der genaue Umfang der Sperre ist **unsicher**. LinkedIn/Telegram erscheinen ohne Pflichtstern. Karte/Wallet sind dort keine Felder. Damit ist „nur private E-Mail genügt sicher“ **nicht belegt**. [^B4]

### Verlauf und Export

Die Retention-Doku unterscheidet ausdrücklich folgende Cubes. Es wäre falsch, aus „Solana-Historie vorhanden“ dieselbe Tiefe für alle Felder abzuleiten. [^B5]

| Schema/Datentyp | Öffentlich dokumentierte Tiefe | Bedeutung |
| --- | --- | --- |
| `Solana.DEXTrades` | Etwa letzte 12 Stunden; kein Archiv in der Matrix | Beispielqueries liefern keinen jahrelangen Verlauf. |
| `Solana.DEXTradeByTokens` | Etwa 7 Tage live; Archiv seit Mitte 2024 | Historische Trades grundsätzlich vorhanden, Rechte/Felder des Pakets separat prüfen. |
| Solana OHLC/Preisaggregate | Minutenwerte seit Oktober 2024 | Kein Ersatz für einzelne Käufer und Reihenfolge. |
| `Trading.Trades`, `Trading.Tokens` | Etwa 30 Tage | Der Trading-Bereich enthält gefilterte Trades; siehe unten. |
| `Instructions`, `TokenSupplyUpdates`, Pools | Etwa 12 Stunden in der Retention-Matrix | Historische Erstellung/Migration nicht aus Live-Beispielen ableiten. |

Alle Tabellenangaben: [^B5]. Eine beim Abruf erhaltene Suchindex-Fassung der Preisseite nannte daneben drei Monate für Solana-Instructions. **Widerspruch** zur spezifischen Retention-Matrix; für historische Erstellungs-/Migrationsdaten ist die tatsächliche API-Verfügbarkeit **unsicher**. `Solana(dataset: combined)` funktioniert laut Retention-Doku derzeit nicht zuverlässig; für Historie wird `archive` empfohlen. [^B1][^B5]

Billing nennt ungefähr **25.000 Datensätze pro Anfrage**; größere Mengen benötigen mehrere Seiten oder Export. Eine besondere kostenlose CSV-Exportquote **nicht gefunden**. Größere historische Dateien werden als kostenpflichtige Data-on-Demand-/S3-Lieferung angeboten; öffentliche feste Kosten und Trial-Exportmenge **nicht gefunden**. Eine kostenlose Beispieldatei ist kein vollständiger Backtest-Datensatz. [^B3][^B10]

### Pump.fun-Schemata und Felder

Die Pump.fun-Doku nennt `Dex.ProtocolName = "pump"` für die Kurve und `"pump_amm"` für PumpSwap. Das dokumentierte Muster lautet: [^B6]

```graphql
query {
  Solana(dataset: realtime) {
    DEXTrades(
      where: {Trade: {Dex: {ProtocolName: {is: "pump"}}}}
      limit: {count: 100}
    ) {
      Block { Time Slot }
      Transaction { Signature Signer }
      Trade {
        Buy { Amount Price Currency { MintAddress } }
        Sell { Amount Price Currency { MintAddress } }
      }
    }
  }
}
```

Dies ist ein Schema-Beispiel aus den dokumentierten Bausteinen, **nicht ausgeführt**. Für Archiv-Trades ist `DEXTradeByTokens` statt `DEXTrades` relevant; die Feldstruktur muss entsprechend der Referenz gewählt werden. Trade-Account/Owner und `Transaction.Signer` sind dokumentiert, aber Signer, Gebührenzahler und wirtschaftlicher Käufer sind nicht automatisch dieselbe Rolle. Bei Archiv-Aggregationen fehlt laut Trader-Doku das Trade-Side-Account-Feld. Für Käuferanalysen deshalb einzelne Trades und passende Owner-Felder verlangen. [^B5][^B6][^B9]

Coin-Erstellung: `TokenSupplyUpdates` mit Pump-Programm und Methoden `create`/`create_v2`, einschließlich Metadaten und Signer. Die Migration-Doku verlinkt eine fertige Abfrage für Pump.fun → PumpSwap. **Nicht gefunden:** frei verfügbare tiefe Archivtabellen für Ersteller und Migration. Live-Support ist belegt, die historische Vollständigkeit nicht. [^B6][^B7][^B5]

`Trading.Trades` wird ausdrücklich als MEV-gefiltert beschrieben. Für einen Backtest aller Marktbewegungen ist das eine mögliche Auswahlverzerrung; der technische Test sollte rohe Trade-Cubes verwenden oder die Filterwirkung dokumentieren. Eigene Bewertung anhand der Anbieterbeschreibung. [^B9]

## Dune

### Kosten, Konto und Verlauf

Aktuell: 2.500 Credits **insgesamt**, bis 14 Tage, Plus-Funktionen; danach Free nur zum Ansehen. Es sind keine 2.500 monatlich erneuerten Gratis-Credits. Der alte Anbieter-Blog von 2023 beschreibt noch einen anderen Gratiszugang und ist dafür kein aktueller Beleg. Analyst kostet 75 USD/Monat mit 4.000 Credits, Plus 399 USD mit 25.000; jährlich 65 bzw. 349 USD pro Monat. [^D1][^D2][^D10]

Ein Konto ist zum Ausführen nötig. Terms nennen Login/Passwort und Zahlungskarte erst für bezahlte Pläne; Datenschutz nennt Name, Benutzername und E-Mail. **Unsicher:** die vollständigen aktuellen Trial-Pflichtfelder und eine ausdrückliche „keine Wallet/keine Karte“-Zusicherung für genau diesen Trial. Die öffentliche Registrierungsseite lieferte nur die Anwendungshülle. [^D3][^D4][^D11]

Dune beschreibt vollständige Solana-Rohhistorie; der öffentliche Pump.fun-Basismodellcode setzt den Start auf **14.01.2024**. Das ist ein Modellstart, kein durch unsere Abfrage geprüfter frühester Datensatz. Eine tarifbedingte Beschränkung auf letzte 7/30 Tage **nicht gefunden**; ohne Ausführung bleibt die tatsächliche Vollständigkeit unsicher. [^D5][^D6]

### Abfrage- und Exportgrenzen

Credits hängen vom tatsächlichen Rechenaufwand ab; keine feste Formel pro SQL-Abfrage veröffentlicht. Small Engine: zwei Minuten Timeout, höchstens drei gleichzeitige Ausführungen. Für Plus nennt die API-Doku 70 Schreib-/Ausführungsanfragen und 200 Leseanfragen je Minute. Gespeicherte Ergebnisse werden bei **32 GB** abgeschnitten; das ist keine kostenlose Exportzusage. [^D2][^D12][^D13]

Die aktuelle Export-Doku rechnet beim Plus-Tarif mit **2 Credits/MB**, bei Analyst mit 10. CSV ist während des Plus-Trials möglich. Eigene Obergrenzenrechnung: 2.500 / 2 = 1.250 MB Export, **nur wenn kein Credit für SQL verbraucht würde**; real bleibt weniger. Eine feste Trial-Zeilenquote **nicht gefunden**. Die FAQ enthält außerdem ältere Datapoint-Sätze; für die Schätzung ist die aktuelle MB-Tabelle maßgeblich, die tatsächliche Abrechnung bleibt vor einem Test zu kontrollieren. [^D14][^D12]

### Pump.fun aufbereitet

Der Anbieter-Code definiert **`pumpdotfun_solana.trades`** als View auf `dex_solana.trades`, gefiltert nach `project = 'pumpdotfun'`. Das dokumentierte Trade-Schema enthält Zeit, Slot, Händler, Transaktion, Tokenmengen, USD-Wert sowie Transaktions- und Instruction-Reihenfolge. Preis in SOL pro Token ist eine eigene Berechnung aus den normalisierten Mengen. Mehrere Swap-Schritte derselben Transaktion können mehrere Zeilen bilden. [^D7][^D15]

Das Pump.fun-Basismodell verarbeitet `is_buy`, Nutzer, SOL-/Tokenmenge und Reserven. Die aktuelle DEX-Zusammenführung bindet getrennte Pump.fun- und **PumpSwap-Modelle** ein. [^D6][^D8]

Für Erstellung mit Ersteller/Zeit sowie Graduation/Migration ist in den gelesenen öffentlichen Anbieter-Dokumenten **keine vollständige fertige Tabellenreferenz gefunden**. Dune dokumentiert IDL-Tabellen nach `<namespace>_solana.<programName>_call_<instructionName>` und Roh-Instruction-Tabellen. Das zeigt einen möglichen Analyseweg, belegt aber keine konkrete Pump.fun-Create-/Migrate-Tabelle. Auch ein PumpSwap-Poolstart allein ist kein Beweis für den genauen Graduation-Zeitpunkt. Eigene Bewertung. [^D16]

## Helius: Historie, Credits und Rechnung

### Tarif und Methoden

Free hat 1 Mio. Credits monatlich, 10 RPC-Anfragen/s und 2 Enhanced-API-Anfragen/s; Developer 49 USD/Monat, 10 Mio. Credits, 50 RPC/s und 10 Enhanced/s. Keine feste Laufzeit für Free genannt. Der Dashboard-Zugang erfordert ein Konto; der separate Agent-Zugang erfordert 1 USDC und ist kein erlaubter Gratisweg für diese Karte. [^H1][^H2]

| Methode | Aktuelle öffentlich dokumentierte Credits | Umfang/Grenze |
| --- | --- | --- |
| `getSignaturesForAddress` | 1 pro Methodenaufruf [^H8] | Signaturen; für die Rechnung Seiten zu 1.000 gemäß Helius-Historienbeschreibung. [^H9] |
| `getTransaction` | 1 pro Methodenaufruf [^H8] | Eine Rohtransaktion; mehrere Methoden in einem HTTP-Batch sind weiterhin mehrere Aufrufe. Eigene Kostenableitung. |
| Enhanced `POST /v0/transactions` | 100 pro Aufruf laut offiziellem Helius-Repository [^H10] | Bis 100 Signaturen. [^H11] |
| Enhanced `GET /v0/addresses/{address}/transactions` | 100 pro Aufruf [^H10] | Bis 100 Transaktionen; Typfilter können zusätzliche Suchseiten erfordern. [^H4] |
| `getTransactionsForAddress` | Full: 10 je angefangene 100 zurückgegebene Transaktionen, mindestens 10; nur Signaturen: 10 pauschal [^H8] | Bis 1.000 vollständige Transaktionen; Zeit-/Slotfilter, Cursor, optional zugehörige Tokenkonten. [^H3] |
| Neue Parsed Events API | 10 pro Aufruf [^H6] | Signaturen oder Adresshistorie als dekodierte Instructions; verfügbar auch in Free. Keine Preiszeitreihe. [^H6] |

**Widerspruch zu älteren Quellen:** Die übersetzte Tarifseite nennt noch 10 Credits für Archiv-RPC und 100 für `getTransactionsForAddress`; der Einführungsblog von 2025 nennt diese Methode nur für bezahlte Pläne und maximal 100 Full-Transaktionen. Die aktuellen englischen Seiten nennen 1 Credit bzw. mengenabhängige Abrechnung und 1.000 Full-Transaktionen. Die Rechnung nutzt die aktuellen englischen Angaben. Der Free-Zugang zu `getTransactionsForAddress` ist angesichts der älteren Einschränkung **unsicher**; die aktuelle Quickstart-Doku schlägt die Methode nach Free-Anmeldung vor, bestätigt die Freischaltung aber nicht ausdrücklich. [^H8][^H3][^H9][^H12][^H2]

Enhanced Transactions ist inzwischen als Legacy/Wartungsmodus dokumentiert; Parsed Events ist der Nachfolger. Die Mainnet-Historie der Adressmethoden wird als unbegrenzt beschrieben, Devnet als zwei Wochen. **Nicht gefunden:** eine vollständige historische Pump.fun-/PumpSwap-Handelstabelle mit fertigen Preisen. Parsed Events dokumentiert ein Beispiel für Pump.fun-Erstellungen einer Wallet; Rohtransaktionen müssen für Trade-Preise und Migration selbst ausgewertet werden. [^H5][^H6][^H3][^H4]

### Schätzung: 30 Tage EINER Wallet

**Annahmen:** 100 bzw. 1.000 Trades/Tag; jeder Trade ist genau eine Transaktion; keine weiteren Transfers, erfolglosen Transaktionen, Wiederholungen oder Suchseiten. Damit `N = 30 × Trades/Tag = 3.000 bzw. 30.000`. Dies ist eine eigene Modellrechnung mit den oben belegten Preisen, kein gemessener Verbrauch. Eine Wallet kann mehr Transaktionen als Trades haben; außerdem erfasst Standard-Adresshistorie zugehörige Tokenkonten nicht automatisch. [^H3][^H13]

| Ladeweg | 100 Trades/Tag: N = 3.000 | 1.000 Trades/Tag: N = 30.000 |
| --- | --- | --- |
| Signaturen + Rohtransaktionen | `ceil(3000/1000) × 1 + 3000 × 1` = **3.003 Credits** | `ceil(30000/1000) × 1 + 30000 × 1` = **30.030 Credits** |
| Signaturen + Enhanced POST, je 100 Signaturen | `3 × 1 + ceil(3000/100) × 100` = **3.003 Credits** | `30 × 1 + ceil(30000/100) × 100` = **30.030 Credits** |
| Enhanced Adresshistorie, je 100 Treffer | `ceil(3000/100) × 100` = **3.000 Credits** | `ceil(30000/100) × 100` = **30.000 Credits** |
| `getTransactionsForAddress`, Full, je 1.000 Treffer | `3 Seiten × (10 × ceil(1000/100))` = **300 Credits** | `30 Seiten × (10 × ceil(1000/100))` = **3.000 Credits** |

Preisgrundlagen und Seitenlimits: [^H8][^H9][^H10][^H11][^H4][^H3]. Nicht vollständig gefüllte Seiten können bei mengenabhängiger Abrechnung aufrunden. Ein Batch reduziert Netzwerkwege, nicht die Kosten der darin enthaltenen Standard-RPC-Methoden. Zusätzliche Abfragen aller Markt-Trades sind in dieser Wallet-Rechnung nicht enthalten.

Die Standard-/Enhanced-Wege liegen rechnerisch unter 1 Mio. Gratis-Credits: **0 USD zusätzliche Ausgabe**, sofern das verbleibende Kontingent reicht und der Endpunkt im Konto verfügbar ist. Free-Freischaltung von `getTransactionsForAddress` bleibt wie oben unsicher; falls nur bezahlt verfügbar, fallen mindestens 49 USD Grundtarif an, nicht bloß der rechnerische Creditwert. [^H1][^H3][^H9]

Helius nennt 5 USD je zusätzlicher Million Credits. Nur als Vergleichswert, **keine tatsächliche Free-Rechnung**: 3.003 Credits entsprechen 0,015015 USD; 30.030 entsprechen 0,15015 USD. Nachladen verlangt einen zulässigen Zahlungsweg; hier wurde keiner eingerichtet. Als konservative Gegenrechnung mit den alten 10-Credit-RPC-Angaben: **30.030 bzw. 300.300 Credits** für Signaturen + Rohtransaktionen. [^H14][^H12]

Projektbezug: `CLAUDE.md`, Abschnitt „Budgets und Grenzen“, nennt zuletzt etwa 20.000 Credits/Tag im laufenden Betrieb. Eigene grobe Rechnung: 600.000 in 30 Tagen, rechnerisch etwa 400.000 Rest aus 1 Mio.; tatsächliche aktuelle Restmenge **nicht geprüft**. Deshalb ist die Wallet-Menge nicht mit einem kompletten Markt-Backtest gleichzusetzen. Lokale Quelle: `CLAUDE.md:100`, gelesen am 07.10.2026.

## Birdeye-Verlauf

Standard liefert 30.000 CUs/Monat bei 1 Anfrage/s und eingeschränktem Zugriff. Lite kostet 39 USD mit 2,5 Mio. CUs, Starter 99 USD mit 8 Mio., Premium 199 USD mit 20 Mio. Die kostenlose Stufe verlangt laut Anbieter-Blog keine Kreditkarte. **Nicht gefunden:** genaue aktuelle Pflichtfelder, Wallet-Anforderung, separate zeitlich begrenzte Testphase oder garantierte Gratis-Historientiefe. [^R1][^R2]

Die Anbieterübersicht nennt historischen Preisverlauf und Coin-Erstellungsinformationen. Die vom Anbieter veröffentlichte Postman-Dokumentation zeigt **`/defi/txs/token/seek_by_time`** mit Tokenadresse, `before_time`, `after_time`, Offset/Limit und Swap-Filter. Das ist ein passender Endpunkttyp für Trades eines Tokens statt nur einer Wallet. Das dokumentierte Beispiel nutzt Limit 50; ein verbindliches Maximum für genau diesen Endpunkt **nicht gefunden**. [^R3][^R4]

**Nicht gefunden:** verlässliche aktuelle CU-Kosten je historischem Endpunkt, dessen Freischaltung in Standard, erste verfügbare Solana/Pump.fun-Trade-Zeit, vollständige Kurvenhistorie und fertige Migrationstabelle. Mehrere Referenzseiten waren nicht lesbar. Die Quelle reicht daher nicht für die Aussage „kostenlos alle Pump.fun-Trades der letzten 30 Tage“. Der allgemeine Preisverlauf allein belegt auch keine Slot-Reihenfolge. [^R1][^R3][^R4][^R6]

## Flipside und Allium

**Flipside:** Alte Anbieter-Seiten werben mit kostenlosen Cross-Chain-Daten. Die ehemalige Dokumentationsadresse leitet beim Abruf zu Edisyl um. Dunes Migrationsanleitung nennt ausdrücklich die Schließung von Flipside Creator Studio; das ist ein dokumentierter Hinweis eines anderen Anbieters, keine eigene Flipside-Schließungsmitteilung. Ein aktueller eigenständiger Gratis-SQL/API-Zugang, Preise, Kontobedingungen, Verlauf, Pump.fun-Tabellen und anwendbare Nutzungsbedingungen sind **nicht gefunden**. Daraus folgt keine Behauptung, sämtliche Flipside-Datenangebote seien eingestellt. [^F1][^F2][^F3]

**Allium:** 100 Explorer Units für historische SQL-Abfragen und 20.000 Developer Units für API-Tests, ohne Ablauf. Das Formular fordert Firmen-E-Mail und Organisation; private Adressen sind ausdrücklich ausgeschlossen. Die Solana-Seite nennt DEX-Trades und Daten ab Genesis sowie keine Kreditkarte für Free-API. **Nicht gefunden:** allgemein veröffentlichter Preis je historischem SQL-Lauf, Trial-Zeilen-/Exportlimit und genaue Pump.fun-Kurven-, Create-, Migrate- und PumpSwap-Schemata. Die geprüften Solana-Katalogpfade führen zum Login; nicht weiter verfolgt. Ein API-Guthaben ist nicht automatisch dasselbe wie SQL-Exportguthaben. [^A1][^A2][^A3]

## Kurs „1,8 Sekunden nach dem Trader-Kauf“

Solana nennt ungefähr 400 ms je Slot, mit Schwankungen bis 600 ms. **Eigene Näherung:** 1,8 / 0,4 = 4,5 Slots. Nur den Kaufslot und den unmittelbar nächsten Slot zu laden reicht deshalb nicht zuverlässig. Das Zeitfenster sollte mehrere Folgeslots umfassen und anhand realer Blockzeiten geprüft werden. [^S1]

Roh-RPC liefert `blockTime` als Ganzzahl oder `null` und den Slot. Daraus erhält man keine genaue Ausführungszeit jeder Transaktion innerhalb des Slots auf Zehntelsekunden. **Unsicher:** ein historisch exakt messbarer Preis zum Zeitpunkt Kauf + 1,8 s. Slot-/Transaktionsreihenfolge lässt sich dennoch auswerten, ohne eine künstliche Millisekundengenauigkeit zu behaupten. [^S2][^D15]

Für einen späteren Test schlage ich folgende Auswertungsregel vor; es ist ein methodischer Vorschlag, keine neue Bot-Regel:

1. Kauf anhand Signatur, Slot und Reihenfolge bestimmen. Alle Trades des Coins einschließlich anderer Käufer und Verkäufer in einem ausreichend breiten Zeit-/Slotfenster laden. Dune dokumentiert dafür `block_slot`, `tx_index` und Instruction-Indizes; Bitquery dokumentiert Mint- und Zeitfilter. [^D15][^B6]
2. Nur erfolgreiche Transaktionen, Mengen nach Decimals normalisieren; SOL/Token aus dem passenden Trade-Paar berechnen. Kurve und PumpSwap gemeinsam betrachten, sofern im Fenster eine Migration liegt. Die Quellmodelle müssen nachgewiesenermaßen beide Handelsplätze enthalten. [^D6][^D8][^B6]
3. Als Näherung den letzten beobachteten Trade bis zum Zielzeitpunkt bestimmen; zusätzlich den ersten danach berichten. Fehlende Trades als fehlende Beobachtung kennzeichnen. Keinen zukünftigen Trade rückwirkend als bekannten Ausführungspreis behandeln.
4. Beobachteter Trade-Preis und simulierter eigener Ausführungspreis getrennt berechnen: letzterer braucht Poolzustand, eigene Kaufmenge und Gebühren/Slippage. Ein anderer Käufer kann eine andere Menge und damit einen anderen mittleren Preis erhalten. Diese Einschränkung ist eine eigene Folgerung aus den mengen- und poolbezogenen Trade-Daten. [^D15][^D6]

| Quelle | Alle Coin-Trades im Zeitfenster? | Einschränkung |
| --- | --- | --- |
| Dune | Über `dex_solana.trades`, Mint auf Kauf-/Verkaufsseite plus Zeit/Slots filtern. [^D15] | Nur indexierte Modelle; Vollständigkeit/Instruction-Duplikate später prüfen. |
| Bitquery | `DEXTrades`/`DEXTradeByTokens` mit Mint und `Block.Time`; historische Tiefe je Cube. [^B6][^B5] | `Trading.Trades` ist MEV-gefiltert; Archiv-/Wallet-Felder und Lizenz beachten. [^B9][^B8] |
| Birdeye | Token-Trade-Endpunkt mit Zeitgrenzen vorhanden. [^R4] | Slot-Reihenfolge, historische Vollständigkeit, Free-Freigabe und Speicherrecht nicht belegt. |
| Helius | Rohblöcke können sämtliche Transaktionen der betreffenden Slots liefern; danach selbst auf Programme/Coins filtern. [^H8] | Wallet-Historie erfasst keine Trades fremder Wallets. Token-Mint allein reicht nicht sicher für alle Trades; Adressmethoden suchen referenzierte Konten. Kurven-/Pool-/Vault-Adressen oder ganze Blöcke nötig. Eigene Ableitung aus der RPC-Semantik. [^H13] |
| Allium | DEX-Historie grundsätzlich beworben. [^A2] | Konkreter frei prüfbarer Pump.fun-Zeitfensterzugang nicht gefunden. |

## Nutzungsbedingungen: lokale Analyse und öffentliches Repository

Diese Bewertung gibt den gefundenen Vertragstext wieder. Fehlt eine ausdrückliche Erlaubnis, steht hier **unsicher**; öffentlich sichtbare Blockchain-Daten bedeuten nicht automatisch eine beliebige Weitergabelizenz für Anbieterdateien.

| Quelle | Kurzes Kernzitat | Bedeutung für lokale Analyse und Veröffentlichung |
| --- | --- | --- |
| Bitquery API | “under free subscription plans for purpose other than technical development” | Gratisdaten dürfen nur technischer Entwicklung dienen. Lokaler technischer Prototyp ist als Zweck passend; eine ausdrückliche dauerhafte Speicherlizenz wurde nicht gefunden. Offene Veröffentlichung von API-Daten ist laut Terms ausschließlich Nutzern bezahlter Pläne gestattet, weitere Einschränkungen bleiben bestehen. [^B8] |
| Bitquery Data Store | “download, store, process and analyse”; “raw or lightly transformed form” | Eigene Data-Store-Lizenz erlaubt interne Speicherung/Analyse und abgeleitete Berichte; rohe oder leicht umgeformte Datensätze dürfen nicht weitergegeben werden. **Gilt für Data-Store-Lieferungen, nicht automatisch für API-Trial.** [^B11] |
| Dune CSV | “only use this data internally within their company and in occasional reports” | Lokales Speichern exportierter Ergebnisse für interne Auswertung ist ausdrücklich vorgesehen. Gelegentliche externe Berichte mit Dune- und Query-Ersteller-Angabe erlaubt; Verkauf oder laufende Bereitstellung als Datenprodukt verboten. Rohdaten-CSV dauerhaft im öffentlichen Repo ist damit nicht pauschal freigegeben. [^D9] |
| Helius | “for any purpose other than a lawful business purpose” | Aktuelle Terms vom 28.09.2026 beschränken Nutzung auf rechtmäßige geschäftliche Zwecke und schließen private/Haushaltsnutzung aus. **Unsicher**, ob dieses private Paper-Projekt darunter fällt. Keine ausdrückliche lokale Blockchain-Speicher-/Repo-Lizenz gefunden; Services dürfen nicht ohne Erlaubnis weitergegeben werden. [^H7] |
| Flipside | **Nicht gefunden** | Aktuelle anwendbare Anbieter-Bedingungen nicht erreichbar gefunden; keine Speicher- oder Veröffentlichungsfreigabe ableiten. [^F2] |
| Birdeye | “copy, scrape, extract, download, store”; “without the prior written consent of Wings Lab” | Klausel 10.2.1 verbietet sehr breit Speicherung/Extraktion, auch über APIs; 10.2.3 verbietet Weitergabe ohne schriftliche Zustimmung. Der Text sieht vorrangige Zusatzbedingungen vor, aber eine passende Backtest-Ausnahme wurde nicht gefunden. Deshalb **Speichern nicht als erlaubt bewerten**. [^R5] |
| Allium | “solely for Customer’s internal business”; “only to the extent expressly authorized in the applicable Order” | Interne geschäftliche Nutzung vorgesehen; Dauer der lokalen Aufbewahrung **nicht gefunden**. Die Standardbedingungen beschränken Weitergabe von Datensätzen, Ausschnitten und sogar Analysen/Modellen/Visualisierungen. Abweichende Rechte brauchen den Vertrag. Keine pauschale Freigabe für öffentliche Backtest-Ergebnisse. [^A4] |

Eigene Empfehlung für das öffentliche Repo: keine Anbieter-Rohdaten oder aus ihnen abgeleiteten Dateien veröffentlichen, solange die jeweilige Lizenz das nicht deckt. Für Dune kommen gelegentliche Ergebnisberichte mit korrekter Quellenangabe in Betracht; für Allium ist selbst die Veröffentlichung abgeleiteter Ergebnisse unter Standardbedingungen eingeschränkt. Quellcode ohne Anbieter-Daten und dieser Recherchebericht sind getrennt von einem Datensatz zu beurteilen. [^D9][^A4]

## Empfehlung für EINE kostenlose Testphase

**Empfehlung: Dunes 14-Tage-Trial mit 2.500 Credits**, für einen kleinen manuellen SQL-/CSV-Test. Gründe: aufbereitete Pump.fun-Trades und PumpSwap-Modell, Zeit/Slot/Reihenfolge für den Latenzvergleich und eine ausdrücklich dokumentierte interne CSV-Nutzung. Danach ist kostenlos nur Lesezugriff möglich. Das eignet sich zur Prüfung weniger Coins/Wallets, nicht als Zusage eines kompletten Monats-Backfills. [^D1][^D7][^D8][^D15][^D9]

**Vorgabe „nur E-Mail, keine Karte, keine Wallet“:** Ein normales E-Mail-Benutzerkonto mit Login/Passwort ist aus Terms/Datenschutz ableitbar; Free verlangt laut Terms keine zusätzlichen Voraussetzungen, Karten werden für bezahlte Pläne genannt. **Unsicher bleibt die vollständige aktuelle Trial-Registrierung**, weil das Formular öffentlich nicht auslesbar war. Eine ausdrücklich belegte Zusicherung für alle drei Kriterien zusammen wurde **nicht gefunden**. Die Empfehlung gilt daher nur für den normalen kostenlosen Trial ohne Zahlungs-/Wallet-Schritt; fordert der Anmeldeablauf solche Daten, erfüllt er diese Karte nicht. Es wurde kein Konto angelegt und nichts gestartet. [^D3][^D4][^D11]

Gedachter Testumfang, **hier nicht ausgeführt**: wenige historische Pump.fun-Käufe auswählen, alle Coin-Trades über mehrere Folgeslots vergleichen, Preis aus SOL-/Tokenmengen bestimmen und eine kleine CSV ausschließlich lokal auswerten. Bereits vor dem ersten Lauf den Creditdeckel setzen. Ergebnis wäre ein belegbarer kleiner Vergleich der Datenqualität und der zeitlichen Auflösung. Dune dokumentiert Abfragekosten-Deckel und Trial-CSV-Export. [^D2][^D14]

## Quellen

Jede Quelle wurde am **07.10.2026** abgerufen. Nicht lesbare Seiten belegen nur die Recherchegrenze, keine Eigenschaften des Dienstes. Anbieter-Code auf `main` kann später verändert werden.

[^B1]: Bitquery, aktuelle Preisseite: https://bitquery.io/pricing — Abruf 07.10.2026, erneut direkt gelesen; zuletzt Trial ohne Archiv, Personal/Pro/Scale jährlich 29/69/199 USD. Suchindex und ältere Doku wichen teilweise ab.
[^B2]: Bitquery, IDE Points: https://docs.bitquery.io/docs/ide/points/ — Abruf 07.10.2026.
[^B3]: Bitquery, Billing/Trial/Datensatzgrenze: https://docs.bitquery.io/docs/plans/how-billing-works/ — Abruf 07.10.2026.
[^B4]: Bitquery, öffentliches Registrierungsformular, nur gelesen: https://account.bitquery.io/auth/signup — Abruf 07.10.2026.
[^B5]: Bitquery, Data Coverage & Retention: https://docs.bitquery.io/docs/graphql/data-coverage-retention/ — Abruf 07.10.2026.
[^B6]: Bitquery, Pump.fun-Referenz: https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/Pump-Fun-API/ — Abruf 07.10.2026.
[^B7]: Bitquery, Migration: https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/pump-fun-to-pump-swap/ — Abruf 07.10.2026.
[^B8]: Bitquery, API Terms, Stand 19.05.2026: https://bitquery.io/terms-of-service — Abruf 07.10.2026.
[^B9]: Bitquery, Trader-Felder/Archiv-Aggregation/MEV-Filter: https://docs.bitquery.io/docs/blockchain/Solana/solana-trader-API/ — Abruf 07.10.2026.
[^B10]: Bitquery, kostenpflichtige historische Dateilieferung: https://bitquery.io/products/data-on-demand — Abruf 07.10.2026.
[^B11]: Bitquery, Data-Store-Datenlizenz, Stand September 2026: https://bitquery.io/datastore/legal/data-license — Abruf 07.10.2026.
[^D1]: Dune, aktuelle Credit-/Trial-Übersicht: https://docs.dune.com/resources/credits-billing/overview — Abruf 07.10.2026.
[^D2]: Dune, aktuelle Tarife und Creditmodell: https://docs.dune.com/resources/credits-billing/how-credits-work — Abruf 07.10.2026.
[^D3]: Dune, Kontovoraussetzungen/Zahlung: https://dune.com/terms — Abruf 07.10.2026.
[^D4]: Dune, Datenschutz, Kontodaten: https://dune.com/privacy — Abruf 07.10.2026.
[^D5]: Dune, Solana-Abdeckung: https://docs.dune.com/data-catalog/solana/overview — Abruf 07.10.2026.
[^D6]: Dune, Pump.fun-Basismodell, einschließlich Startdatum und dekodierten Trade-Feldern: https://raw.githubusercontent.com/duneanalytics/spellbook/main/dbt_subprojects/solana/models/_sector/dex/pumpdotfun/solana/pumpdotfun_solana_base_trades.sql — Abruf 07.10.2026; tatsächliche Modell-/Datenvollständigkeit nicht ausgeführt geprüft.
[^D7]: Dune, tatsächlicher View-Name: https://raw.githubusercontent.com/duneanalytics/spellbook/main/dbt_subprojects/solana/models/_sector/dex/pumpdotfun/solana/pumpdotfun_solana_trades.sql — Abruf 07.10.2026.
[^D8]: Dune, DEX-Modellzusammenführung mit Pump.fun und PumpSwap: https://raw.githubusercontent.com/duneanalytics/spellbook/main/dbt_subprojects/solana/models/_sector/dex/dex_solana_base_trades.sql — Abruf 07.10.2026.
[^D9]: Dune, Application Service Addendum, Abschnitt CSV downloads, Stand 13.05.2026: https://dune.com/application-terms — Abruf 07.10.2026. Aussagen gelten für diesen Exportweg; keine Übertragung auf andere API-Verträge behauptet.
[^D10]: Dune, überholte Gratisbeschreibung vom 25.04.2023: https://dune.com/blog/new-paid-experience — Abruf 07.10.2026.
[^D11]: Dune, Registrierungsseite, öffentlich nur Anwendungshülle lesbar: https://dune.com/auth/register — Abruf 07.10.2026; keine Anmeldung.
[^D12]: Dune, FAQ, Engine-Limits und ältere Datapoint-Tabelle: https://docs.dune.com/learning/how-tos/pricing-faqs — Abruf 07.10.2026.
[^D13]: Dune, API-Limits und 32-GB-Ergebnisgrenze: https://docs.dune.com/api-reference/overview/rate-limits — Abruf 07.10.2026.
[^D14]: Dune, aktuelle MB-Abrechnung und Trial-CSV-Export: https://docs.dune.com/learning/how-tos/export-data-out — Abruf 07.10.2026.
[^D15]: Dune, Trade-Spalten und mehrere Pool-Schritte: https://docs.dune.com/data-catalog/curated/dex-trades/solana/solana-dex-trades — Abruf 07.10.2026.
[^D16]: Dune, Solana-IDL-Tabellen: https://docs.dune.com/data-catalog/solana/idl-tables — Abruf 07.10.2026.
[^H1]: Helius, aktuelle Tarif-/Rate-Tabelle, einschließlich Unterschied Free/Agent: https://www.helius.dev/docs/billing/plans — Abruf 07.10.2026.
[^H2]: Helius, Free-Dashboard-Quickstart: https://www.helius.dev/docs/quickstart — Abruf 07.10.2026.
[^H3]: Helius, aktuelle `getTransactionsForAddress`-Referenz und Verlauf: https://www.helius.dev/docs/rpc/gettransactionsforaddress — Abruf 07.10.2026.
[^H4]: Helius, Enhanced Adresshistorie, Seiten-/Suchlimits und Verlauf: https://www.helius.dev/docs/enhanced-transactions/transaction-history — Abruf 07.10.2026.
[^H5]: Helius, Enhanced Transactions als Legacy: https://www.helius.dev/docs/enhanced-transactions/overview — Abruf 07.10.2026.
[^H6]: Helius, Parsed Events und Pump.fun-Mint-Beispiel: https://www.helius.dev/docs/parsed-events — Abruf 07.10.2026.
[^H7]: Helius, Cloud Services Agreement, Stand 28.09.2026, insbesondere 3.1/3.2: https://www.helius.dev/terms — Abruf 07.10.2026.
[^H8]: Helius, aktuelle englische Creditliste: https://www.helius.dev/docs/billing/credits — Abruf 07.10.2026.
[^H9]: Helius, ältere Einführung mit Standard-Signaturseiten und damaliger Paid-Beschränkung, 28.10.2025: https://www.helius.dev/blog/introducing-gettransactionsforaddress — Abruf 07.10.2026.
[^H10]: Offizielles Helius-Repository, Enhanced-API-Referenz mit 100 Credits pro Aufruf: https://github.com/helius-labs/core-ai/blob/main/helius-plugin/skills/phantom/references/helius-enhanced-transactions.md — Abruf 07.10.2026; nur technische Daten als Quelle verwendet, keine Skill-Anweisungen übernommen.
[^H11]: Helius, Enhanced POST mit bis 100 Signaturen: https://www.helius.dev/docs/enhanced-transactions/parse-transactions — Abruf 07.10.2026.
[^H12]: Helius, ältere/abweichende übersetzte Tarifseite: https://www.helius.dev/docs/zh/billing/plans-and-rate-limits — Abruf 07.10.2026.
[^H13]: Solana, Adressreferenzen in `getSignaturesForAddress`: https://solana.com/docs/rpc/http/getsignaturesforaddress — Abruf 07.10.2026.
[^H14]: Helius, Zusatzcredits und Zahlungswege: https://www.helius.dev/docs/billing/additional-credits — Abruf 07.10.2026.
[^F1]: Flipside, alte öffentlich auffindbare Gratiswerbung: https://flipsidecrypto.xyz/rewards/Silver-League-August-2024 — Abruf 07.10.2026; kein aktueller Tarifbeleg.
[^F2]: Ehemalige Flipside-Doku https://docs.flipsidecrypto.xyz/ — Abruf 07.10.2026; Weiterleitung zu https://edisyl.com/ beobachtet.
[^F3]: Dune, Hinweis auf Schließung des Flipside Creator Studio: https://docs.dune.com/learning/flipside-migration-guide — Abruf 07.10.2026.
[^R1]: Birdeye, Tarif-/CU-Tabelle: https://docs.birdeye.so/docs/pricing — Abruf 07.10.2026.
[^R2]: Birdeye, Standard-Free ohne Kreditkarte: https://birdeye.so/data-api/blog/detail/birdeye-data-services-standard-plan-is-now-7x-bigger — Abruf 07.10.2026.
[^R3]: Birdeye, historische Preise und Token-Erstellung: https://birdeye.so/data-api/types-of-data — Abruf 07.10.2026.
[^R4]: Vom Birdeye-Data-Services-Account veröffentlichte Postman-Endpunktdoku, nur gelesen: https://www.postman.com/bds-7813306/birdeye-data-services/request/820e41t/trades-token-seek-by-time — Abruf 07.10.2026; keine Anfrage ausgeführt.
[^R5]: Birdeye, veröffentlichte Terms, Stand 11.04.2025: https://birdeye.so/data-api/terms-of-service und PDF https://assets.birdeye.so/bds/policies/2025.04.11-tos.pdf — Abruf 07.10.2026; insbesondere 10.2.1/10.2.3, PDF-Seiten 11–12, und Vorrang von Supplemental Terms.
[^R6]: Birdeye-Referenzseiten https://docs.birdeye.so/reference/get-defi-history-price und https://docs.birdeye.so/reference/get-defi-txs-token-seek-by-time sowie https://docs.birdeye.so/docs/compute-unit-cost — Abrufversuche 07.10.2026, nicht lesbar; belegen nur die Recherchegrenze.
[^A1]: Allium, öffentliches Registrierungsformular und kostenlose Units: https://app.allium.so/join — Abruf 07.10.2026; keine Anmeldung.
[^A2]: Allium, Solana-Abdeckung/Genesis/Free-API: https://www.allium.so/ecosystems/solana — Abruf 07.10.2026.
[^A3]: Allium, Solana-Doku https://docs.allium.so/historical-data/supported-blockchains/solana und https://docs.allium.so/historical-chains/supported-blockchains/solana — Abruf 07.10.2026, Weiterleitung zum Login; keine Anmeldung.
[^A4]: Allium, Terms, insbesondere 1.1, 1.3 und 1.11/1.12: https://www.allium.so/terms — Abruf 07.10.2026.
[^S1]: Solana, Slot-Dauer und Schwankung: https://solana.com/developers/cookbook/transactions/confirmation — Abruf 07.10.2026.
[^S2]: Solana, `getTransaction`, Ganzzahl-`blockTime`, Slot und mögliche Nullwerte: https://solana.com/docs/rpc/http/gettransaction — Abruf 07.10.2026.
