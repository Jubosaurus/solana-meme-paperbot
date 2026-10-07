# Karte 32: DexScreener als Datenquelle

Stand und Abrufdatum: **07.10.2026**. Nur öffentliche Dokumentation gelesen, keine API-Abfragen und keine WebSocket-Verbindungen. Alle Beispiele unten sind selbst erstellte Schema-Beispiele, keine gemessenen Antworten. Es wurde nichts eingebaut.

## Quellen und Beleggrenzen

Jeder Quellenverweis führt zur URL; das Abrufdatum steht hier und im Linktitel. Aussagen mit **Eigene Schlussfolgerung**, **Eigene Rechnung** oder **Vorschlag** sind unsere Ableitung aus den genannten Quellen. **Nicht gefunden** heißt: in der gelesenen Dokumentation nicht gefunden. Es bedeutet nicht, dass eine Eigenschaft ausgeschlossen ist.

| Kürzel | Öffentliche Dokumentation | Abrufdatum |
|---|---|---|
| R | [API-Referenz][R] | 07.10.2026 |
| W | [WebSockets][W] | 07.10.2026 |
| T | [API-Nutzungsbedingungen][T] | 07.10.2026 |
| M | [Metas: Erklärung und Zuordnung][M] | 07.10.2026 |
| B | [Boosting: Erklärung][B] | 07.10.2026 |

**Wichtige Beleggrenze:** Die aktuelle Textansicht von R enthält für Token-Batches und HTTP-Boosts teilweise nur Verweise auf eine eingebettete Spezifikation. Felder und Limits dieser Abschnitte waren in der indexierten HTML-Ansicht derselben offiziellen Seite lesbar. Das Recherchewerkzeug datiert deren Crawl auf „vor sechs Monaten“. Diese Angaben sind daher belegt, ihre unveränderte Aktualität ist **unsicher**. Die Rechnungen verwenden diese dokumentierten Werte als Annahme. Meta-, Profil-, Ads- und Takeover-Schemata sowie W und T waren unmittelbar lesbar. [R][W][T]

Die Bedingungen erwähnen kostenlose und kostenpflichtige Nutzung. Eine verbindliche Gratis-Verfügbarkeitsgarantie für jeden aufgeführten Dienst wurde nicht gefunden. [T]

## Übersicht der HTTP-Endpunkte

Die Feldgruppen **Meta**, **Paar**, **Profil**, **Boost** und **Anzeige** sind unten vollständig aufgeschlüsselt. Der Nutzen ist jeweils eine **eigene Schlussfolgerung** aus den Feldern. Zahlen mit † stammen aus der oben beschriebenen indexierten Referenz. [R][W]

| Endpunkt | Limit | Felder / Antwort | Nutzen für uns |
|---|---|---|---|
| `/metas/trending/v1` | 60/min | Liste von Meta-Objekten [R] | Themen beobachten |
| `/metas/meta/v1/{slug}` | 60/min | Meta plus `pairs[]` [R] | Kandidaten eines Themas finden |
| `/tokens/v1/{chainId}/{tokenAddresses}` | 300/min†; höchstens 30 Adressen† | Liste von Paar-Objekten [R] | Beobachtung bekannter Coins bündeln |
| `/token-profiles/latest/v1` | 60/min | Profil [R] | Beschreibung und Links entdecken |
| `/token-profiles/recent-updates/v1` | 60/min | Profil [R] | Profiländerungen beobachten |
| `/token-boosts/latest/v1` | 60/min† | Boost [R][W] | Neue Boost-Aktivität erkennen |
| `/token-boosts/top/v1` | 60/min† | Boost [R][W] | Meiste aktive Boosts beobachten |
| `/community-takeovers/latest/v1` | 60/min | Liste; Profil plus `claimDate` [R] | Community-Übernahmen beobachten |
| `/ads/latest/v1` | 60/min | Liste von Anzeigen [R] | Werbung erkennen |

**Nicht gefunden:** Geltungsbereich der Limits, etwa je IP, je Endpunkt oder gemeinsam; Tageskontingent; Regeln für kurze Lastspitzen. Deshalb die Tabellenlimits nicht als unabhängig addierbare Budgets behandeln. Die HTTP-Schemata zeigen Profile und Boosts als Objekt, Takeovers und Ads als Liste. Die tatsächliche Antwortform wurde nicht geprüft. [R]

## 1. Metas und Narrativ-Signal

### Felder und Beispiel

`Meta`: `name,slug,description` (Text), `icon.{type,value}` (Text), `marketCap,liquidity,volume` (Zahlen), `tokenCount` (Ganzzahl), `marketCapChange,marketCapDelta` (je Zahlen für `m5,h1,h6,h24`). Der Detail-Endpunkt ergänzt `pairs[]` im Paar-Schema. [R]

**Selbst erstellte Beispielantwort** für Trending; Werte sind Platzhalter ohne Aussage über Einheiten oder tatsächliche Themen. [R]

```json
[
  {
    "name": "Beispielthema",
    "slug": "beispielthema",
    "description": "Beispielbeschreibung",
    "icon": {"type": "BEISPIEL", "value": "BEISPIEL"},
    "marketCap": 100,
    "liquidity": 20,
    "volume": 30,
    "tokenCount": 2,
    "marketCapChange": {"m5": 1, "h1": 2, "h6": 3, "h24": 4},
    "marketCapDelta": {"m5": 5, "h1": 6, "h6": 7, "h24": 8}
  }
]
```

Weitere Meta-Endpunkte, Aktualisierungstakt, Rangformel, Listenlänge, Volumenzeitraum, Einheiten sowie Berechnung von Change/Delta: **nicht gefunden**. Prozent bzw. absolute Änderung als Bedeutung der beiden Feldnamen: **unsicher**. [R]

Metas sind Themen-Gruppen. Moderatoren und Community-Mitglieder ordnen sie manuell zu. [M]

**Eigene Schlussfolgerung:** Das passt grundsätzlich zur Frage „Welches Thema ist gerade heiß?“. Ein möglicher Beobachtungsablauf wäre: Thema erkennen, über den Slug zugehörige Paare ansehen und Solana-Kandidaten gegen unsere bestehenden Prüfungen halten. Manuelle Zuordnung kann neue Themen oder Coins verspätet erfassen. Ohne Rangformel und Aktualisierungstakt ist das Signal als zusätzlicher Hinweis geeignet; seine Zuverlässigkeit als Kaufbedingung bleibt **unsicher**. Eine beobachtete Veränderung kann auch aus einer geänderten Gruppenzuordnung stammen. [R][M]

## 2. Token-Batches und Abrufrechnung

### Paar-Felder

Ein Aufruf betrifft eine `chainId`; mehrere Token-Adressen werden durch Kommas getrennt. Die dokumentierte Antwort ist eine Paar-Liste. [R]

| Gruppe | Dokumentierte Felder und Typen |
|---|---|
| Kennung | `chainId,dexId,url,pairAddress`: Text; `labels[]`: Text/null [R] |
| Token | `baseToken.{address,name,symbol}`: Text; `quoteToken.{address,name,symbol}`: Text/null [R] |
| Preis | `priceNative`: Text; `priceUsd`: Text/null [R] |
| Transaktionen | `txns.<Zeitfenster>.{buys,sells}`: Ganzzahlen [R] |
| Verlauf | `volume.<Zeitfenster>`: Zahl; `priceChange.<Zeitfenster>`: Zahl; `priceChange` kann null sein [R] |
| Liquidität | `liquidity`: Objekt/null; darin `usd`: Zahl/null, `base,quote`: Zahlen [R] |
| Bewertung und Alter | `fdv,marketCap`: Zahl/null; `pairCreatedAt`: Ganzzahl/null [R] |
| Zusatzinfos | `info.imageUrl`: Text/null; `info.websites[].url`: Text; `info.socials[].{platform,handle}`: Text; Listen können null sein [R] |
| Boosts | `boosts.active`: Ganzzahl [R] |

**Beleggrenzen:** Das Paar-Schema lässt Zeitfensterschlüssel offen. `m5/h1` bei `txns`, `volume` und `priceChange` sind daher nicht ausdrücklich garantiert. Einheit von `pairCreatedAt`, Prozentdefinition von `priceChange`, eindeutige Käufer/Holder und eine Garantie vollständig vorhandener Felder: **nicht gefunden**. [R]

**Eigene Schlussfolgerung:** Für einen späteren Leser wären `txns.get("m5")` und `txns.get("h1")` optionale Zugriffe. Fehlende Daten dürfen nicht zu null Käufern oder null Volumen umgedeutet werden. Käufe und Verkäufe erlauben keinen Schluss auf die Anzahl unterschiedlicher Personen. Außerdem sollte ein Token nicht blind mit genau einer Ergebniszeile verbunden werden: Die Antwort beschreibt Paare. Ein Paarwechsel kann unseren Preisverlauf verfälschen. Das Alter eines Handelspaars belegt nicht automatisch das Erstellungsalter des Coins. [R]

### Eigene Rechnung: HTTP-Abrufe, nicht einzelne Coin-Messungen

Annahmen: alle Coins auf Solana, pro Runde alle Adressen einmal, Batchgröße bis 30, Beobachtung rund um die Uhr, keine Ausfälle, Wiederholungsversuche oder zusätzlichen Abrufe. Quelle der Batchgrenze und des Vergleichslimits: R†. Zahlen unabhängig durch einen Daten-Prüfer nachgerechnet. [R]

```text
Batches je Runde B = aufrunden(N / 30)
Runden pro Tag       = 86.400 / X
HTTP-Abrufe pro Tag  = B * 86.400 / X
HTTP-Abrufe pro Min. = B * 60 / X       (Durchschnitt)
HTTP-Abrufe pro 6 h  = B * 21.600 / X
```

| N Coins | X Sekunden | Batches/Runde | Abrufe/Tag | Abrufe/min im Mittel | Abrufe/6 h |
|---:|---:|---:|---:|---:|---:|
| 100 | 30 | 4 | 11.520 | 8 | 2.880 |
| 100 | 60 | 4 | 5.760 | 4 | 1.440 |
| 100 | 120 | 4 | 2.880 | 2 | 720 |
| 300 | 30 | 10 | 28.800 | 20 | 7.200 |
| 300 | 60 | 10 | 14.400 | 10 | 3.600 |
| 300 | 120 | 10 | 7.200 | 5 | 1.800 |
| 1.000 | 30 | 34 | 97.920 | 68 | 24.480 |
| 1.000 | 60 | 34 | 48.960 | 34 | 12.240 |
| 1.000 | 120 | 34 | 24.480 | 17 | 6.120 |

Beispiel, **eigene Rechnung**: 1.000 Coins alle 30 Sekunden brauchen `aufrunden(1.000/30)=34` Batches; `86.400/30=2.880` Runden; `34*2.880=97.920` Abrufe/Tag. Der letzte Batch enthält zehn Adressen. [R]

**Eigene Schlussfolgerung:** Alle neun Durchschnittswerte liegen unter den dokumentierten 300/min†. Das ist keine Zusage für 34 gleichzeitige Abrufe. Batches über die Runde verteilen und Reserve für Fehler, andere Bots und weitere Endpunkte vorsehen. Bei mehreren Chains muss je Chain aufgerundet und danach addiert werden. Tageszahlen sind Modellwerte; sie garantieren weder Gratis-Betrieb noch lückenlose Daten während Schichtwechseln. [R][T]

## 3. WebSockets gegenüber HTTP-Abfragen

Die WebSocket-Doku nennt Echtzeit-Updates und den Server `wss://api.dexscreener.com`. Für alle sechs Pfade beschreibt sie beim Verbindungsaufbau Status 101 sowie `{limit: Ganzzahl, data: Liste}`. Die Pfade stimmen mit den gleichnamigen HTTP-Endpunkten überein. [W][R]

| WebSocket-Strom | Felder eines Eintrags in `data` |
|---|---|
| `/token-profiles/latest/v1` | Profil [W] |
| `/token-profiles/recent-updates/v1` | Profil [W] |
| `/community-takeovers/latest/v1` | Profil plus `claimDate` als Datum/Zeit-Text [W] |
| `/ads/latest/v1` | Anzeige [W] |
| `/token-boosts/latest/v1` | Boost [W] |
| `/token-boosts/top/v1` | Boost [W] |

Feldgruppen für HTTP und WebSocket; Details sind Schemainformation, keine geprüfte Live-Antwort. [W][R]

| Gruppe | Felder |
|---|---|
| Profil | `url,chainId,tokenAddress,icon,header,description,links[].{type,label,url}` [W][R] |
| Boost | `url,chainId,tokenAddress,amount,totalAmount,icon,header,description,links[].{type,label,url}` [W][R] |
| Anzeige | `url,chainId,tokenAddress,date,type,durationHours,impressions` [W][R] |

Im W-Schema sind `amount,totalAmount,durationHours,impressions` Zahlen; `date,claimDate` haben das Format Datum/Zeit. Profil-`header,description,links` und Link-`type,label` können null sein; Boost-`icon` ebenfalls; Anzeigen-`durationHours,impressions` ebenfalls. Zulässige Anzeigen-Typen und Einheiten der Boost-Mengen: **nicht gefunden**. [W]

**Selbst erstelltes Beispiel** des dokumentierten Startformats, bewusst nur mit einem kleinen Ausschnitt der Profilfelder. Die Zahl 1 behauptet keine reale Listenlänge. [W]

```json
{"limit":1,"data":[{"chainId":"solana","tokenAddress":"BEISPIEL","description":"Beispielprofil"}]}
```

**Nicht gefunden:** Format späterer Nachrichten, vollständige Listen gegenüber Einzeländerungen, Bedeutung/Wert von `limit`, Verbindungszahl, Verbindungsdauer, Nachrichtenlimit, Ping/Heartbeat, Close-Codes, Wiederverbindungsregeln, Wiederaufnahme ab letzter Nachricht und Nachlieferung verpasster Ereignisse. `limit` ist deshalb nicht als Verbindungsgrenze interpretierbar. Preis- oder Transaktionsströme für die Token-Beobachtung sind auf W ebenfalls **nicht gefunden**. [W]

Boosts werden gekauft und erhöhen zeitweise den Trending Score eines Tokens. [B]

**Eigene Schlussfolgerung:** Boosts und Ads können Vermarktungsaktivität zeigen. Daraus folgt keine organische Nachfrage. Das ist für unsere Narrativ-Prüfung ein ergänzender Hinweis, kein Ersatz für Käufer-, Liquiditäts- und Sicherheitsprüfungen. Profiltexte und Links sollten auch in Zukunft als Daten behandelt werden. [B][W]

### Eigener Vergleich für die etwa sechsstündigen Schichten

| Punkt | Regelmäßige HTTP-Abfragen | WebSockets |
|---|---|---|
| Schichtstart | Abruf des aktuellen Zustands; wenig Verbindungszustand | Verbindung pro benötigtem Strom; Startformat dokumentiert [R][W] |
| Abbruch | Nächster Abruf kann einen neuen Zustand liefern; Zustand dazwischen kann fehlen | Wiederverbinden nötig; Nachlieferung nicht dokumentiert [R][W] |
| Aufwand | Vorschlag: Timeout, Fehlerzählung, verzögerte Wiederholung und Dublettenprüfung | Zusätzlich Verbindung überwachen und unklare Folgeformate behandeln [W] |
| Verzögerung | Durch gewählten Abfragetakt bestimmt | Als Echtzeit beschrieben; feste maximale Verzögerung nicht gefunden [W] |
| Vollständigkeit | „latest“/„top“ belegt kein vollständiges Ereignisarchiv | Auch keine dokumentierte Garantie, jedes Ereignis nachzuliefern [R][W] |

**Eigene Empfehlung:** Zuerst HTTP für diese Zusatzsignale vorsehen. Es ist für regelmäßig neu startende Schichten einfacher zu betreiben, und seine Fehlerbehandlung lässt sich gezielt planen. Dieser Vergleich ist eine Architekturbeurteilung, kein gemessener Stabilitätstest. Kurze Ereignisse können bei beiden Wegen unbemerkt bleiben; bei WebSockets kommt die nicht beschriebene Wiederaufnahme hinzu. [R][W]

**Eigene Rechnung/Vorschlag:** Fünf gewünschte Feeds einmal je Minute ergeben `5*1.440=7.200` Abrufe/Tag, sechs einschließlich Profiländerungen `8.640`. Bei einem gemeinsamen 60/min-Budget wären das 5 bzw. 6/min zuzüglich aller anderen Abrufe. Die gemeinsame Geltung ist **unsicher**; die Liste wird nicht allein durch häufigere Abfragen vollständig. [R]

## 4. Nutzungsbedingungen und öffentliches Repository

Die Seite nennt als letzten Änderungsstand den 18.08.2023. Kernzitate bleiben sehr kurz; Übersetzungen und Schlussfolgerungen stehen daneben. [T]

| Thema | Kernzitat / Befund | Bedeutung laut Text |
|---|---|---|
| Speichern | ausdrückliche Regel: **nicht gefunden** | Keine genannte Speicherfrist oder klare Archivfreigabe; daraus folgt keine pauschale Erlaubnis. [T] |
| Weitergabe, § 2 | „available for third parties“ | Nicht autorisierte Weitergabe der API Services oder von Teilen ist untersagt; der genaue Umfang für Datenexporte ist **unsicher**. [T] |
| Rechte, § 3 | „or the data obtained through it“ | Die Nutzung verschafft keine Eigentumsrechte an der API oder den erhaltenen Daten. [T] |
| Attribution | ausdrückliche Pflicht: **nicht gefunden** | Eine Namensnennung allein belegt keine Weitergabe-Erlaubnis. [T] |
| Kommerziell, § 4 | „both non-commercial and commercial purposes“ | Beides ist erlaubt, innerhalb der übrigen Vertragsgrenzen. [T] |
| Konkurrenz, § 1 | kurze Zusammenfassung | Keine Produkte mit dem Hauptzweck, unmittelbar mit DexScreener oder der API zu konkurrieren. [T] |

Eine begrenzte, widerrufliche Nutzungslizenz ist vorgesehen. Sperrung und Änderungen bleiben möglich; die genannten Vorankündigungen betreffen zahlende Kunden. [T]

**Eigene Schlussfolgerung für unser öffentliches GitHub-Repo:**

- Eigener Bot-Code, eigene Rechnungen, dieser Quellenbericht und selbst erfundene Testdaten sind die naheliegenden Inhalte. Eine spezielle GitHub-Freigabe steht nicht in T; dies ist unsere Einschätzung für selbst erstellte Inhalte. [T]
- Rohantworten, laufende CSV-Exporte, historische API-Sammlungen sowie fremde Beschreibungen oder Bilder nicht als frei weiterverteilbar behandeln. Ihre Veröffentlichung würde Dritten Daten zugänglich machen; ob § 2 das im Einzelfall erlaubt, bleibt **unsicher**. Vor einer solchen Veröffentlichung wäre eine ausdrückliche Klärung mit DexScreener nötig. [T]
- Auch für intern gespeicherte Messdaten ist eine allgemeine Speichererlaubnis **nicht gefunden**. Eigene aggregierte Auswertungen sind keine automatisch belegte Ausnahme. Ein Quellenhinweis mit Link ist sinnvoll, beseitigt aber keine unklaren Rechte. [T]
- „Paper-Trading“ und nicht kommerzielle Nutzung heben die Weitergabe- und Konkurrenzgrenzen nicht auf. [T]

Es wurde keine Aussage getroffen, dass bestehende Daten-Dateien rechtlich freigegeben seien; ihr Inhalt wurde für diese Aufgabe nicht geprüft.

## Ergebnis

**Eigene Bewertung:** Metas sind als zusätzlicher Themenhinweis interessant. Token-Batches ermöglichen unter den dokumentierten Annahmen eine sparsame Beobachtung; selbst 1.000 Coins alle 30 Sekunden ergeben rechnerisch 68 Abrufe/min. Für die Zusatzfeeds erscheint HTTP für unsere Schichten einfacher. Aktualität einzelner Referenzangaben, WebSocket-Folgeformate und Rechte an öffentlichen Rohdatenexporten bleiben die wichtigsten offenen Punkte. [R][M][W][T]

[R]: https://docs.dexscreener.com/api/reference "API-Referenz; Abrufdatum 07.10.2026; für eingebettete HTTP-Abschnitte zusätzlich indexierte Ansicht, Aktualität unsicher"
[W]: https://docs.dexscreener.com/api/websockets "WebSockets; Abrufdatum 07.10.2026"
[T]: https://docs.dexscreener.com/api/api-terms-and-conditions "API-Nutzungsbedingungen; Abrufdatum 07.10.2026"
[M]: https://docs.dexscreener.com/metas "Metas; Abrufdatum 07.10.2026"
[B]: https://docs.dexscreener.com/boosting "Boosting; Abrufdatum 07.10.2026"
