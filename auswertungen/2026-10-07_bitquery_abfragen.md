# Karte 33: Bitquery-Abfragen für eine spätere Testphase

Stand: 07.10.2026. Recherche ausschließlich in öffentlicher Bitquery-Dokumentation. Keine Abfrage ausgeführt, keine Anmeldung, kein Konto und keine API-Verbindung eingerichtet. Die folgenden GraphQL-Blöcke sind **Entwürfe aus dokumentierten Beispielen**, keine gegen ein Schema oder Ergebnis geprüften Abfragen.

## Ergebnis für die Planung

Für neu entstehende Pump.fun-Coins lassen sich Erstellungen, die ersten sechs Handelsstunden und Migrationen mit kurzen Echtzeitfenstern planen. Ein späterer Abruf der gesamten Testwoche aus den Rohdaten-Cubes ist dagegen nicht zugesichert. Für 30 Tage Wallet-Trades eignet sich der dokumentierte `Trading.Trades`-Ansatz; dessen Daten sind aufbereitet und ersetzen keine vollständige Transaktionshistorie. Historische Erstellerbestände haben einen gesonderten V1-Entwurf. Historische Top-Halter sind noch nicht verlässlich als fertige Abfrage belegbar.

**Budgetannahme: zunächst 1.000 API-Punkte für sieben Tage.** Die Billing-Doku nennt diese Testmenge und schließt `archive`/`combined` aus. Die IDE-Punkteseite nennt abweichend 10.000 Gratispunkte für den ersten Monat. Das sind widersprüchliche Angaben, keine gemeinsam zugesicherte Gratisleistung. Am Tag 0 gelten die tatsächlich angezeigten Berechtigungen. [Billing: Trials](https://docs.bitquery.io/docs/plans/how-billing-works/#trials), [IDE-Punkte](https://docs.bitquery.io/docs/ide/points/).

## 1. Verwendung der Entwürfe

- `MINT_EINSETZEN`, `WALLET_EINSETZEN` und `ERSTELLER_EINSETZEN` sind Textplatzhalter, keine echten Adressen. Öffentlich dokumentierte Programmadressen sind keine Zugangsschlüssel.
- Beispielzeiten in den Blöcken vor einer späteren Nutzung ersetzen. `Z` bedeutet UTC. Am 07.10.2026 entsprechen 00:00–06:00 UTC dem Zeitraum 02:00–08:00 Uhr in Deutschland.
- Für Coin-Trades gilt: Start = tatsächliche Erstellungszeit aus (a), Ende = Start + sechs Stunden. Ein Zeitraum von „jetzt minus sechs Stunden“ wäre eine andere Fragestellung.
- Jeder Block liefert zunächst eine **begrenzte Seite**, nicht automatisch „alle“. Für vollständige Ergebnisse sind die Zeitfenster und Seiten nach Abschnitt 3 abzuarbeiten. Ein volles `limit` darf nicht als Vollständigkeit gewertet werden.
- Die Zusammenstellung dokumentierter Felder, zusätzliche Filter und Wechsel von `subscription` zu `query` sind eigene Ableitungen. Ihre Kombination muss am Tag 0 im gewählten Schema geprüft werden. Keine unbewiesenen Feldnamen werden als garantiert dargestellt.

Die Doku erlaubt den Wechsel vieler Streaming-Beispiele zu einer Abfrage mit Zeitfilter. Absolute `since`/`till`-Filter sind ebenfalls dokumentiert. [Trading-Abfragehinweise](https://docs.bitquery.io/docs/trading/crypto-trades-api/trades-api/), [GraphQL-Filter](https://docs.bitquery.io/docs/graphql/filters/).

## 2. GraphQL-Entwürfe

### (a) Pump.fun-Coin-Erstellungen in einem Zeitfenster

**Zweck:** Mint, Name, Symbol, Blockzeit und dokumentierte Erstellerhinweise für `create` und `create_v2` abrufen. Ein Zeitfenster kann viele Coins gemeinsam erfassen.

```graphql
query PumpFunCreations {
  Solana(dataset: realtime) {
    TokenSupplyUpdates(
      limit: { count: 100, offset: 0 }
      orderBy: { ascending: Block_Time }
      where: {
        Block: { Time: {
          since: "2026-10-07T00:00:00Z"
          till: "2026-10-07T00:01:00Z"
        } }
        Transaction: { Result: { Success: true } }
        Instruction: { Program: {
          Address: { is: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" }
          Method: { in: ["create", "create_v2"] }
        } }
      }
    ) {
      Block { Time }
      Transaction { Signature Signer }
      TokenSupplyUpdate {
        Currency { MintAddress Name Symbol UpdateAuthority }
      }
    }
  }
}
```

**Quelle:** Beispiel „How do I get newly created Pump.fun tokens?“ sowie die Creation-/Metadata-Beispiele auf der [Pump.fun-API-Seite](https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/Pump-Fun-API/). Limit und Sortierung aus [Limits](https://docs.bitquery.io/docs/graphql/limits/) und [Sorting](https://docs.bitquery.io/docs/graphql/sorting/).

**Geschätzte Kosten:** ein Echtzeit-Cube, nach IDE-Punktedoku **5 Punkte je Seite**; am Tag 0 bestätigen. Metadatenabrufe pro Coin sind hier zunächst unnötig.

**Unsicherheiten:** Die Doku verwendet `Transaction.Signer` als Dev-Hinweis. Unterzeichner, Metadaten-`UpdateAuthority` und tatsächlicher Ersteller dürfen trotzdem nicht ungeprüft gleichgesetzt werden. Bei einem Muster-Launch die Accounts und Argumente einer Creation-Instruction prüfen; bei fehlender eindeutiger Zuordnung Ersteller als unbekannt behandeln. Mehrere Supply-Zeilen desselben Launchs nach Mint und Creation-Transaktion abgleichen. Retention und Vollständigkeit des Cubes separat prüfen.

**Optionaler Entwurf zur Erstellerprüfung:** liefert belegte Rohfelder statt einer erfundenen `Creator`-Spalte.

```graphql
query PumpFunCreationContext {
  Solana(dataset: realtime) {
    Instructions(
      limit: { count: 10 }
      orderBy: { ascending: Block_Slot }
      where: {
        Transaction: { Result: { Success: true } }
        Block: { Time: {
          since: "2026-10-07T00:00:00Z"
          till: "2026-10-07T00:01:00Z"
        } }
        Instruction: {
          Accounts: { includes: { Address: { is: "MINT_EINSETZEN" } } }
          Program: { Name: { is: "pump" }, Method: { in: ["create", "create_v2"] } }
        }
      }
    ) {
      Block { Time }
      Transaction { Signature Signer }
      Instruction {
        Accounts { Address Token { Mint Owner } }
        Program {
          AccountNames
          Arguments {
            Name
            Value {
              ... on Solana_ABI_String_Value_Arg { string }
              ... on Solana_ABI_Address_Value_Arg { address }
            }
          }
        }
      }
    }
  }
}
```

**Quelle und Ableitung:** Creation-Accounts aus den Pump.fun-Beispielen oben, dekodierte Argumente aus der [Solana-Instructions-Doku](https://docs.bitquery.io/docs/blockchain/Solana/solana-instructions/). **Kosten:** weitere 5 Punkte. **Unsicher, am Tag 0 prüfen:** tatsächliche Argumentnamen und Account-Zuordnung für beide Creation-Varianten; aus Arraypositionen wird hier keine Erstelleradresse geraten.

### (b) Alle Trades eines Coins in seinen ersten sechs Stunden

**Zweck:** einzelne erfolgreiche Swap-Zeilen einschließlich Blockzeit, Slot, Handelsaccounts, Wallet-Eigentümern, beider Mengen und Preise. Kein DEX-Filter, damit Handel nach einer Migration auf anderen indexierten DEXs mit erfasst werden kann.

```graphql
query CoinFirstSixHours {
  Solana(dataset: realtime) {
    DEXTrades(
      limit: { count: 100, offset: 0 }
      orderBy: { ascending: Block_Slot }
      where: {
        Block: { Time: {
          since: "2026-10-07T00:00:00Z"
          till: "2026-10-07T06:00:00Z"
        } }
        Transaction: { Result: { Success: true } }
        any: [
          { Trade: { Buy: { Currency: { MintAddress: { is: "MINT_EINSETZEN" } } } } }
          { Trade: { Sell: { Currency: { MintAddress: { is: "MINT_EINSETZEN" } } } } }
        ]
      }
    ) {
      Block { Time Slot }
      Transaction { Signature Index Signer }
      Trade {
        Index
        Dex { ProgramAddress ProtocolName }
        Buy {
          Amount Price PriceInUSD
          Currency { MintAddress Symbol }
          Account { Address Owner }
        }
        Sell {
          Amount Price PriceInUSD
          Currency { MintAddress Symbol }
          Account { Address Owner }
        }
      }
    }
  }
}
```

**Quellen:** Slot, Zeit und Trade-/Transaktionsindex aus „Subscribe to Latest Solana Trades“ in der [Solana-DEXTrades-Doku](https://docs.bitquery.io/docs/blockchain/Solana/solana-dextrades/); beidseitige Mengen, Mints und `Account.Owner` aus „How do I get the latest PumpSwap trades?“ in der [PumpSwap-Doku](https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/pump-swap-api/). Die OR-Verknüpfung `any` ist in der [Filter-Doku](https://docs.bitquery.io/docs/graphql/filters/) beschrieben.

**Auswertung als eigene Ableitung:** Liegt der Zielmint unter `Buy.Currency`, ist dies ein Kauf des Zielcoins; unter `Sell.Currency` ein Verkauf. Tokenmenge aus der jeweiligen Seite, Gegenmenge aus der anderen. Käufer-/Verkäuferhinweise sind die zugehörigen `Account.Owner`-Werte; `Address` kann ein Tokenaccount sein. Beide Seiten müssen nicht zwei verschiedene Menschen darstellen. Bei SOL/WSOL-Gegenwährung ergibt `Gegenmenge / Tokenmenge` den ausgeführten Preis in SOL pro Token. Native SOL-Adresse `11111111111111111111111111111111` und WSOL-Mint `So11111111111111111111111111111111111111112` sind dokumentiert. [Solana-RFQ-Doku](https://docs.bitquery.io/docs/blockchain/Solana/solana-rfq-api/).

**Geschätzte Kosten:** **5 Punkte je Echtzeit-Seite**, also `5 × Seitenzahl`; viele Trades können mehrere Seiten erfordern.

**Unsicherheiten:** SOL-Menge und SOL-Preis bleiben bei einer anderen Gegenwährung unbekannt; USD ist keine SOL-Umrechnung. `PriceInUSD` kann fehlen oder null/0 sein. Zuordnung der Buy-/Sell-Seiten an einem Pump.fun-Kauf und -Verkauf am Tag 0 prüfen. Roh-Swaps können mehrere Schritte einer Wallet-Transaktion enthalten. Signer ist insbesondere bei RFQ nicht zwingend der Trader. Keine Garantie für jede denkbare Handelsplattform. Daten nach sechs Stunden zeitnah abrufen: `DEXTrades` hält ungefähr zwölf Stunden, nicht sieben Tage.

### (c) Alle indexierten Trades einer Wallet über 30 Tage

**Zweck:** aufbereitete Handelszeilen aus dem längeren Trading-Fenster statt eines unzulässigen 30-Tage-Filters auf `Solana.DEXTrades`.

```graphql
query WalletThirtyDays {
  Trading {
    Trades(
      limit: { count: 100, offset: 0 }
      orderBy: { ascending: Block_Time }
      where: {
        Pair: { Market: { Network: { is: "Solana" } } }
        Trader: { Address: { is: "WALLET_EINSETZEN" } }
        Block: { Time: {
          since: "2026-09-07T00:00:00Z"
          till: "2026-10-07T00:00:00Z"
        } }
      }
    ) {
      Block { Time }
      TransactionHeader { Hash Index }
      Trader { Address }
      Side
      Amounts { Base Quote }
      AmountsInUsd { Quote }
      Price PriceInUsd
      Pair {
        Token { Id Address Symbol }
        QuoteToken { Id Address Symbol }
        Market { Address Network Program }
      }
    }
  }
}
```

**Quellen:** „How Do I Get All Trades for a Specific Wallet on Solana?“ und „Scope and window“ in der [Crypto-Trades-Doku](https://docs.bitquery.io/docs/trading/crypto-trades-api/trades-api/); 30-Tage-Walletfilter im Beispiel „Get count of Buys and Sells of a Trader“ der [Solana-Trader-Doku](https://docs.bitquery.io/docs/blockchain/Solana/solana-trader-API/). Die expliziten Zeiten frieren den geplanten Zeitraum ein; am Tag 0 an das dann verfügbare Fenster anpassen.

**Geschätzte Kosten:** Planwert **ungefähr 5 Punkte je Seite** gemäß Billing-Doku; die Anwendung auf `Trading.Trades` im Testkonto bestätigen. Kein Archivaufschlag eingeplant.

**Unsicherheiten:** ungefähr 30 Tage sind ein rollendes Fenster, kein garantierter Monatsanfang. Aufbereiteter Feed, daher keine Garantie auf alle rohen On-Chain-Trades/MEV-Vorgänge. `Side` und Mengen beziehen sich auf `Pair.Token`/`QuoteToken`. Mehrere Swap-Schritte pro Transaktion und dokumentierte Dubletten berücksichtigen. Der in der Doku vorgeschlagene Dublettenschlüssel ist `(TransactionHeader.Hash, Trader.Address, Side, Amounts.Base)`; identische echte Teilfills dürfen beim Abgleich nicht versehentlich verschwinden. Kein belegtes `Slot`-Feld in diesem Entwurf. Genaue rohe 30-Tage-Trades mit Slots: unsicher, am Tag 0 prüfen; gegebenenfalls separates Cloud-Dataset erforderlich.

### (d1) Pump.fun-Migrationen anhand des Programm-Logs

**Zweck:** erfolgreiche Pump.fun-Instructions mit dokumentiertem `Migrate`-Log in einem Fenster. Durch die zurückgegebenen Accounts später den Mint zuordnen; optional den belegten `Accounts.includes.Address.is`-Mintfilter aus (a) hinzufügen.

```graphql
query PumpFunMigrationLogs {
  Solana(dataset: realtime) {
    Instructions(
      limit: { count: 100, offset: 0 }
      orderBy: { ascending: Block_Slot }
      where: {
        Block: { Time: {
          since: "2026-10-07T00:00:00Z"
          till: "2026-10-07T00:01:00Z"
        } }
        Transaction: { Result: { Success: true } }
        Instruction: {
          Program: { Address: { is: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" } }
          Logs: { includes: { includes: "Migrate" } }
        }
      }
    ) {
      Block { Time }
      Transaction { Signature }
      Instruction {
        Program { Name Method AccountNames }
        Accounts { Address Token { Mint Owner } }
        Logs
      }
    }
  }
}
```

**Quelle:** „Check if the Pump Fun Token has migrated to PumpSwap“ in der [Marketcap-/Bonding-Curve-Doku](https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/Pump-Fun-Marketcap-Bonding-Curve-API/). Eigene Vereinfachung: ohne Join und ohne Einzelmintfilter, mit Zeitgrenze und Limit.

**Geschätzte Kosten:** **5 Punkte je Seite**. Der auf der Quellseite gezeigte Join wird hier bewusst durch den gesonderten Entwurf (d2) ersetzt; seine Kosten sind nicht vorab belegt.

**Unsicherheiten:** Logtext und Account-Zuordnung müssen für aktuelle Programmversionen geprüft werden. Migration und Erreichen der Graduation-Schwelle sind unterschiedliche Zeitpunkte; hier wird kein eigenes `GraduationTime` erfunden. Retention ungefähr zwölf Stunden. Ältere Raydium-Migrationen werden durch einen PumpSwap-Abgleich nicht automatisch vollständig abgedeckt.

### (d2) PumpSwap-Poolerstellung als Migration-Abgleich

**Zweck:** das zweite, dokumentierte Signal für Pump.fun → PumpSwap. Mit (d1) über Transaktionssignatur und Mint abgleichen.

```graphql
query PumpSwapMigrationPools {
  Solana(dataset: realtime) {
    Instructions(
      limit: { count: 100, offset: 0 }
      orderBy: { ascending: Block_Slot }
      where: {
        Transaction: { Result: { Success: true } }
        Block: { Time: {
          since: "2026-10-07T00:00:00Z"
          till: "2026-10-07T00:01:00Z"
        } }
        Instruction: {
          CallerIndex: { eq: 2 }
          Depth: { eq: 1 }
          CallPath: { includes: { eq: 2 } }
          Program: {
            Address: { is: "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA" }
            Method: { is: "create_pool" }
          }
        }
      }
    ) {
      Block { Time }
      Transaction { Signature }
      Instruction {
        Program { Method AccountNames }
        Accounts { Address Token { Mint Owner } }
      }
    }
  }
}
```

**Quelle:** „How do I track Pump.fun pool migrations to PumpSwap in real time?“ in der [PumpSwap-Doku](https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/pump-swap-api/). **Geschätzte Kosten:** weitere **5 Punkte je Seite**.

**Unsicherheiten:** Die festen Aufrufpositionen stammen aus dem Beispiel und sind kein universeller Nachweis für jede Transaktionsform. Am Tag 0 gegen (d1) prüfen. Ein bloßes `create_pool` ohne Pump.fun-Kontext belegt keine Graduation. Falls die Positionsfilter Treffer auslassen, breitere Poolerstellungsdaten abrufen und über Pump.fun-Log plus Signatur abgleichen; dies ist ein später zu prüfender Ansatz.

### (e1) Top-Halter zu einem Zeitpunkt innerhalb des Echtzeitfensters

**Zweck:** letzte dokumentierte Balance pro Tokenaccount bis zum Stichtag, nach Menge sortiert. Zunächst eine Account-Rangliste, keine garantierte Rangliste zusammengefasster Wallets.

```graphql
query RecentTopTokenAccounts {
  Solana(dataset: realtime) {
    BalanceUpdates(
      limit: { count: 10 }
      orderBy: { descendingByField: "BalanceUpdate_balance_maximum" }
      where: {
        Block: { Time: { till: "2026-10-07T06:00:00Z" } }
        Transaction: { Result: { Success: true } }
        BalanceUpdate: { Currency: { MintAddress: { is: "MINT_EINSETZEN" } } }
      }
    ) {
      BalanceUpdate {
        Account { Address Owner }
        Currency { MintAddress Symbol }
        balance: PostBalance(maximum: Block_Slot)
      }
    }
  }
}
```

**Quellen:** Top-Halter-Snapshot aus der [Solana-Token-Holders-Doku](https://docs.bitquery.io/docs/blockchain/Solana/solana-token-holders/), Account-/Owner-Bedeutung aus dem [BalanceUpdates-Cube](https://docs.bitquery.io/docs/cubes/balance-updates-cube/). Eigene Ableitung: zusätzliche obere Zeitgrenze.

**Geschätzte Kosten:** **5 Punkte** für einen Echtzeit-Cube, vorbehaltlich Bestätigung.

**Unsicherheiten:** Es werden nur Accounts mit Updates im vorhandenen Datenfenster erfasst. Ein leerer Treffer bedeutet keinen Nullbestand. Die Holder-Seite nennt ungefähr acht Stunden, die Retention-Matrix ungefähr zwölf; vorsichtig mit höchstens acht Stunden planen und tatsächliche Abdeckung messen. Ein sechs Stunden alter Coin ist nur dann gut abgedeckt, wenn seine ganze Lebensdauer noch im Fenster liegt. Mehrere Tokenaccounts einer Wallet zusammenzählen; zehn größte Accounts ergeben nicht zwingend zehn größte Wallets. Pool-/Bonding-Curve-Accounts separat kennzeichnen. Keine historische Vollständigkeitszusage.

### (e2) Erstellerbestand zu einem Zeitpunkt im Echtzeitfenster

**Zweck:** letztes `PostBalance` je Account einer bekannten Erstellerwallet, später lokal zur Wallet-Summe addieren. Ohne `Account.Address` könnten mehrere Tokenaccounts in eine nicht belastbare Einzelzahl zusammenfallen.

```graphql
query RecentCreatorTokenBalances {
  Solana(dataset: realtime) {
    BalanceUpdates(
      limit: { count: 100 }
      where: {
        Block: { Time: { till: "2026-10-07T06:00:00Z" } }
        Transaction: { Result: { Success: true } }
        BalanceUpdate: {
          Account: { Owner: { is: "ERSTELLER_EINSETZEN" } }
          Currency: { MintAddress: { is: "MINT_EINSETZEN" } }
        }
      }
    ) {
      BalanceUpdate {
        Account { Address Owner }
        Currency { MintAddress }
        balance: PostBalance(maximum: Block_Slot)
      }
    }
  }
}
```

**Quelle:** Owner-/Mintfilter und Aggregat aus „Get Token Holdings and Holding time of an address“ der [Solana-BalanceUpdates-Doku](https://docs.bitquery.io/docs/blockchain/Solana/solana-balance-updates/). Eigene Ableitung: Stichtag und Gruppierung nach Account. **Geschätzte Kosten:** **5 Punkte je Seite**.

**Unsicherheiten:** Der Ersteller muss vorher aus (a) bestätigt sein. Accounts ohne vorhandene Updates fehlen. Bestände nach demselben Slot können mehrere Änderungen enthalten; `maximum: Block_Slot` allein löst Gleichstände innerhalb eines Slots nicht sicher auf. Für einen sekundengenauen historischen Gesamtbestand außerhalb des Fensters (e3) prüfen.

### (e3) Historischer Erstellerbestand über V1-Transfers

**Zweck:** dokumentierte Alternative für einen früheren UTC-Stichtag: gesamte erfasste Historie der Zu- und Abflüsse des Zielmints bis dahin summieren. **Anderes Schema:** kleines `solana`, `transfers`, V1; nicht in denselben V2-Block kopieren.

```graphql
query CreatorHistoricalBalance($creator: String!, $mint: String!) {
  solana(network: solana) {
    transfers(
      time: { till: "2026-10-07T06:00:00Z" }
      currency: { is: $mint }
      any: [
        { receiverAddress: { is: $creator } }
        { senderAddress: { is: $creator } }
      ]
      options: { limit: 1 }
    ) {
      sum_in: amount(calculate: sum, receiverAddress: { is: $creator })
      sum_out: amount(calculate: sum, senderAddress: { is: $creator })
      balance: expression(get: "sum_in - sum_out")
      currency { address symbol }
    }
  }
}
```

Variablen später ersetzen:

```json
{
  "creator": "ERSTELLER_EINSETZEN",
  "mint": "MINT_EINSETZEN"
}
```

**Quelle:** „Solana Wallet Balances per Token Up to a Point in Time“, einschließlich ausdrücklich dokumentiertem `time.till`, und „Solana Per-Token Sent, Received, and Balance for an Address“ in der [V1-Transfers-Doku](https://docs.bitquery.io/v1/docs/Examples/Solana/transfers).

**Geschätzte Kosten:** **nicht seriös vorab bezifferbar**. Historische Transferaggregation fällt nicht unter die zugesicherte V2-Echtzeit-Pauschale. Zugriff im Testkonto und V1-Abrechnung sind unsicher, am Tag 0 prüfen; nicht als Gratisbestandteil planen. `limit: 1` begrenzt die aggregierte Ausgabe, nicht die Zahl der verarbeiteten Transfers.

**Unsicherheiten:** vollständige Transferabdeckung ab Mint-Erstellung, Behandlung von Mint/Burn und Zusammenführung von Tokenaccounts unter Walletadressen an einem jungen Mustercoin gegenprüfen. Leere Ergebnisse nicht als Null ausgeben. Keine verkürzte Startzeit verwenden, die frühere Bestände unterschlägt.

**Historische Top-Halter:** Die [Holder-Doku](https://docs.bitquery.io/docs/blockchain/Solana/solana-token-holders/) bietet einen V1-Entwurf, aber dort stehen `sum_in` und `sum_out` beide als identisches `amount(calculate: sum)` ohne Richtungsfilter. Daraus ist die behauptete Nettobilanz nicht nachvollziehbar. Diesen Entwurf nicht als geprüfte Lösung übernehmen. Für eine komplette Rangliste braucht es korrekt getrennte Zu-/Abflüsse je Halter ab Erstellung; passende Gruppierung und Berechtigungen sind **unsicher, am Tag 0 prüfen**. Cloud-Transfers/Balance-Updates wären eine gesonderte Alternative.

## 3. Kosten, Mengen und technische Grenzen

### Punkte und Credits

Die offizielle [IDE-Punktedoku](https://docs.bitquery.io/docs/ide/points/) nennt für `dataset: realtime` **5 Punkte pro Cube**, unabhängig von der Zeilenzahl. Mehrere Cubes werden einzeln berechnet. An anderer Stelle derselben Seite stehen dynamische Kosten nach Umfang und Komplexität. Die [Billing-Doku](https://docs.bitquery.io/docs/plans/how-billing-works/) formuliert allgemein `Punkte = verbrauchte Ressourcen × Preis je Einheit` und ungefähr fünf Punkte pro Aufruf. Ein vollständig numerischer Ressourcenpreis für Archiv/V1 ist daraus nicht ableitbar.

Planungsregel: 5 Punkte je einfacher Echtzeit-Seite; tatsächlichen Verbrauch im IDE ablesen. Aliase, Joins und andere Schnittstellen nicht ungeprüft zur selben Pauschale rechnen. Kleine Filter helfen der Ausführung; bei der beschriebenen Echtzeit-Pauschale senkt `limit: 1` die fünf Punkte nicht. Auch ein ausgeführter Aufruf mit anschließendem Client-Timeout kann Punkte verbrauchen. [IDE-Punkte: Berechnung und Timeouts](https://docs.bitquery.io/docs/ide/points/).

API-Punkte, MCP-Credits und Stream-Kontingente sind getrennt. Die Trial-Doku nennt zusätzlich 100 MCP-Credits, zwei parallele Streams, 17 Stream-Minuten und 0,2 GB Streamdaten. Diese Entwürfe sind normale Abfragen; dafür keine MCP- oder Streaming-Credits in API-Punkte umrechnen. [Billing: Trials und Streams](https://docs.bitquery.io/docs/plans/how-billing-works/).

### Wie viele Coins oder Trades passen ungefähr hinein?

**Eigene Rechenbeispiele, keine gemessene Leistung:** unter der Annahme einer erfolgreich gelieferten Seite je 5 Punkte und passender Berechtigung.

| Rechenfall | 1.000 Punkte | 10.000 Punkte, nur falls tatsächlich zugeteilt |
|---|---:|---:|
| Einfache Seiten, ohne Reserve | 200 | 2.000 |
| Seiten mit je 100 Trade-Zeilen | bis 20.000 Zeilen | bis 200.000 Zeilen |
| Seiten mit je 1.000 Trade-Zeilen | bis 200.000 Zeilen | bis 2.000.000 Zeilen |
| Coin-Paket: Trades + Migration (d1) + Top-Accounts + Erstellerbestand, je eine Seite | 50 Coins | 500 Coins |
| Dasselbe Paket nach einer gemeinsamen Creation-Seite und 100 Punkten Reserve | 44 Coins | 494 Coins |

Das Coin-Paket kostet rechnerisch `4 × 5 = 20` Punkte. Die letzte Zeile ergibt `floor((Budget − 100 − 5) / 20)`. Optionaler Creation-Kontext, (d2), Wallet-Analyse und zusätzliche Trade-Seiten kommen dazu. Bei `p` Trade-Seiten kostet dieses Paket `5 × (p + 3)`. Holder- und Migration-Abfragen können nach Coins/Zeitfenstern gebündelt werden; dadurch muss eine Seite nicht einem Coin entsprechen.

Die Trade-Zahlen sind **Zeilenobergrenzen für voll gefüllte Seiten**, keine garantierte Menge eindeutiger Trades. Retention, Dubletten, Ausgabegrenzen, nicht erfasste Märkte und freie Berechtigungen können die nutzbare Menge erheblich verkleinern. Die Doku liefert keine feste Zahl „Credits pro Coin“ oder „Credits pro Trade“.

### Zeilen, Paginierung und Reihenfolge

Die [Limit-Doku](https://docs.bitquery.io/docs/graphql/limits/) nennt standardmäßig 25.000 V2-Zeilen und erlaubt ein explizites `limit: { count, offset }`. Die [Billing-Doku](https://docs.bitquery.io/docs/plans/how-billing-works/) spricht dagegen von einer Grenze um 25.000; die [Fehler-Doku](https://docs.bitquery.io/docs/start/errors/) nennt 10.000 als Default und zeigt ein höheres explizites Limit. **Default ist nicht gleich garantiertes hartes Maximum.** Für den Versuch zunächst 100, später höchstens 1.000 Zeilen pro Seite planen; akzeptierte Grenze am Tag 0 prüfen.

Die Doku warnt ausdrücklich vor Offset-Paginierung bei veränderlichen Daten oder ohne starke Sortierung. `Block_Time` beziehungsweise `Block_Slot` alleine ordnet gleichzeitige Trades nicht eindeutig. Die Blöcke oben sind daher noch keine lückenlose Export-Pipeline. Für größere Datenmengen:

1. Ein abgeschlossenes Zeitfenster festlegen und in kleine Teilfenster zerlegen.
2. Wenn eine Seite voll ist, das Fenster weiter teilen oder mit bestätigter Gesamtsortierung paginieren; volle Seiten nicht still abschneiden.
3. Für Trades die belegten Felder Slot, Transaktionsindex und Trade-Index als Sortier-/Abgleichschlüssel verwenden. Die konkrete kombinierte `orderBy`-Eingabe im Solana-Schema am Tag 0 prüfen.
4. Gleichzeitige Ereignisse an Fensterrändern überlappend abholen und anhand geeigneter Ereignisschlüssel abgleichen. Bei `Trading` sind `since` und `till` dokumentiert inklusiv.
5. Eine Transaktionssignatur kann mehrere echte Swaps enthalten; nicht allein nach Signatur deduplizieren. Bei Trading-Rows die in (c) genannte Dublettenproblematik berücksichtigen.

[Grenzen und Offset-Warnung](https://docs.bitquery.io/docs/graphql/limits/), [Trading-Paginierung](https://docs.bitquery.io/docs/trading/query-operators/sweeps-and-pagination/), [Solana-Sortierhinweise](https://docs.bitquery.io/docs/blockchain/Solana/solana-dextrades/).

### Verlaufstiefe und Datenbanken

| Oberfläche | Öffentlich dokumentierte Reichweite | Folge für diesen Auftrag |
|---|---|---|
| `Solana.DEXTrades`, `Instructions`, `TokenSupplyUpdates` | ungefähr zwölf Stunden, realtime | Erstellungen/Migrationen fortlaufend in kurzen Fenstern; sechs Stunden Trades zeitnah sichern |
| `Solana.BalanceUpdates` | ungefähr zwölf Stunden in der Matrix; ungefähr acht Stunden auf der Holder-Seite | Nur kurze, vollständig abgedeckte Coin-Lebensdauer als Snapshot-Kandidat |
| `Solana.DEXTradeByTokens` realtime | ungefähr sieben Tage | Längerer Trade-Ansatz; kein Ersatz für alle Rohfelder oder 30 Tage |
| `Solana.DEXTradeByTokens` archive | Aggregate ab 01.06.2024; eingeschränkte Detailfelder | Historische OHLCV/Volumen getrennt von rohen Trade-/Accountdaten behandeln |
| `Trading.Trades` | ungefähr 30 Tage; nur realtime | Wallet-Entwurf (c), Zugang und genaue früheste Zeit am Tag 0 prüfen |
| Solana V1-Transfers | historische Transferdaten, separate API | Kandidat für (e3), Kosten/Zugriff gesondert prüfen |
| Cloud-Datasets | Historie je gekauftem Dataset | Große Rücktests möglich, gesondertes Angebot |

[Retention-Matrix](https://docs.bitquery.io/docs/graphql/data-coverage-retention/), [Solana-Historie und Feldgrenzen](https://docs.bitquery.io/docs/blockchain/Solana/historical-aggregate-data/), [V1-Transfers](https://docs.bitquery.io/v1/docs/Examples/Solana/transfers).

`archive` ist kein Synonym für „dieselben Livefelder, nur älter“. Die Solana-Historienseite beschränkt unter anderem Account-/Side-Details. Die allgemeine [Archive-Seite](https://docs.bitquery.io/docs/graphql/dataset/archive/) beschreibt Genesis-Abdeckung; für Solana-Aggregate ist die spezifische Reichweite ab Juni 2024 maßgeblich. Historienzugang benötigt ein gesondertes Archivpaket und ist laut Doku auch in selbst gebuchten Standardplänen nicht enthalten.

**Widerspruch bei `combined`:** Die Solana-Seiten beschreiben dieselben Daten wie `archive`, ohne Live-Anhang; die Retention-Seite meldet Solana-Fehler auf `/graphql`. Deshalb hier kein Entwurf mit `combined`, keine angenommene Zusammenführung. [Solana-Historie](https://docs.bitquery.io/docs/blockchain/Solana/historical-aggregate-data/), [Retention](https://docs.bitquery.io/docs/graphql/data-coverage-retention/).

**EAP:** Einige Beispiele nennen `eap` als Solana-Endpunkt, während die aktuelle IDE-Doku `streaming.bitquery.io/graphql` für V2 nennt. Das belegt keinen zusätzlichen `dataset: eap`-Wert und keine eigene Archiv-Reichweite. Endpunktauswahl, Schema und verfügbare Solana-Cubes sind **unsicher, am Tag 0 prüfen**. Keine Anmeldung und kein Endpunktaufruf in dieser Recherche. [Solana-Endpunkthinweis](https://docs.bitquery.io/docs/stablecoin-APIs/stablecoin-trades-api/), [IDE-V2-Hinweis](https://docs.bitquery.io/docs/ide/query/).

### Massenexport und Kosten

Ja: Parquet-Dumps für Solana-Trades, Transfers, Balance-Updates, Blöcke und weitere Themen; Lieferung über S3/GCS sowie Snowflake/BigQuery. Es gibt öffentliche Beispiel-Dateien zur Schema-/Formatprüfung. **Ein kostenloser vollständiger Pump.fun-Massenexport ist nicht zugesichert.** Für volle Datasets verweist die Doku auf Kauf oder gesonderten Trial. Datasetpreis, Umfang eines möglichen Cloud-Trials und zusätzliche Cloudkosten sind offen; nicht gegen die 1.000 API-Punkte verrechnen. Hier wurden weder Samples heruntergeladen noch Exporte ausgelöst. [Solana-Cloud-Doku](https://docs.bitquery.io/docs/cloud/solana/), [Cloud-Übersicht](https://docs.bitquery.io/docs/cloud/).

## 4. Vorabprüfung ohne Konto

**Jetzt möglich:** öffentliche GraphQL-Beispiele lesen, Feldpfade vergleichen und Entwürfe vorbereiten. Ein lokaler GraphQL-Parser könnte später reine Syntax prüfen, ohne Netzwerk/Konto; das bestätigt jedoch weder Bitquery-Feldtypen noch Berechtigungen oder Daten. Hier wurde kein Parser installiert und kein Test ausgeführt.

Die Doku beschreibt IDE-Schemahilfe und Fehlermarkierung, verlangt im First-Query-Leitfaden jedoch ein Konto für das IDE-Fenster. Öffentliche gespeicherte Queries sind laut anderer Doku über Links sichtbar. Daraus folgt keine belastbare Zusage für anonyme Ausführung oder vollständige Schema-Prüfung. **Ein offizieller kontofreier Dry-Run mit Schema- und Kostenprüfung ist in den gelesenen Seiten nicht belegt.** IDE-Beispiele lassen sich bereits aus der Dokumentation übernehmen; ihre Run-Links wurden hier nicht ausgeführt. [First Query](https://docs.bitquery.io/docs/start/first-query/), [IDE-Schemahilfe](https://docs.bitquery.io/docs/ide/query/), [Query-Korrektheit](https://docs.bitquery.io/docs/graphql/query/), [öffentliche/private Queries](https://docs.bitquery.io/docs/ide/private/).

**„Nur E-Mail“:** Keine Kreditkarte ist laut Trial-Doku nötig. Der Registrierungsleitfaden nennt zusätzlich Passwort, Name und Firmenname; eine Anmeldung ausschließlich per E-Mail ist daraus nicht zugesichert. Das tatsächliche Formular später prüfen. Jetzt wurde keine Registrierung begonnen. [Trial](https://docs.bitquery.io/docs/plans/how-billing-works/#trials), [Registrierungsbeschreibung](https://docs.bitquery.io/docs/start/first-query/).

## 5. Sparsamer Tag-0-Plan, ausschließlich für später

1. Tatsächlich zugeteilte API-Punkte, Testende, Solana-/Trading-Berechtigung und Endpunktschema ansehen. Falls nur 1.000 Punkte verfügbar sind, damit planen. Keine Archive-/Cloud-Käufe aus diesem Auftrag ableiten.
2. Zunächst nur Schemahilfe verwenden: Feldpfade, Filter, Inline-Fragments und `orderBy` prüfen. Dies ist noch keine Datenabfrage.
3. (a) auf ein **abgeschlossenes, sehr frisches Fenster von 30–60 Sekunden** mit `limit: { count: 1 }` verkleinern. Mint und Zeit übernehmen. Ein Einzeltreffer dient der Feldprüfung, nicht einer vollständigen Launchliste.
4. Optionalen Creation-Kontext für diesen Mint prüfen. Ersteller-/Signer-Zuordnung dokumentieren; wenn unklar, keine scheinbar sichere Erstelleranalyse.
5. (b) zunächst nur **eine Minute ab Erstellung**, `limit: 1`; anschließend höchstens zehn Zeilen, um Kauf, Verkauf, Mengen, Owner und SOL-Preis abzugleichen. Für jeden zusätzlich ausgeführten Block Verbrauch notieren.
6. (c) zuerst denselben Mint-Trader über **eine Minute**, `limit: 1`, prüfen; erst anschließend 30 Tage in festen Tagesfenstern. Ein leerer Treffer belegt weder Inaktivität noch volle Verlaufstiefe.
7. (d1)/(d2) für ein kurzes aktuelles Fenster mit `limit: 1` testen. Am Tag 0 muss nicht gerade eine Migration stattfinden. Nach einem belegten Ereignis beide Signale abgleichen; nicht das ganze Wochenfenster blind durchsuchen.
8. (e1)/(e2) für einen gerade erzeugten Coin und einen Zeitpunkt in dessen belegter Lebensdauer prüfen; zunächst wenige Accounts. (e3) erst nach Klärung von V1-Zugriff und Kosten, außerhalb der pauschalen Kalkulation.

**Eigener Budgetrahmen:** Acht einfache Erstabfragen für (a), Creation-Kontext, (b), (c), (d1), (d2), (e1), (e2) entsprechen bei fünf Punkten etwa **40 Punkten**. Für zusätzliche Feldprüfungen insgesamt höchstens **100 Punkte** vorsehen, also ungefähr 20 einfache Aufrufe. Größere Läufe erst nach Sichtung von Ergebnissen, Retention und Verbrauch. Keine ständig laufenden Subscriptions nötig; deren separates Trial-Kontingent ist kurz.

Für eine spätere ganze Testwoche ist die kurze Retention der Engpass: vollständige Rohfenster innerhalb ihrer Aufbewahrungszeit abrufen und die spätere Speicherung separat beauftragen. Bei ausgeschöpften Fenstern bleibt eine Historien-/Cloud-Lösung erforderlich. Diese Karte liefert ausschließlich die Planung.

## 6. Lieferung und Prüfung

Neu angelegt: ausschließlich `auswertungen/2026-10-07_bitquery_abfragen.md`. Keine Projekt-Daten, Bot-Dateien oder andere Doku geändert. Keine Tests laut Auftragskarte. Budgetrechnungen gemäß Projektregel unabhängig nachgerechnet, ohne Abweichung. Alle Feldentwürfe nur anhand öffentlicher Dokumentation zusammengestellt; Syntax-, Schema-, Ergebnis- und Kostenvalidierung am Tag 0 ausdrücklich offen.
