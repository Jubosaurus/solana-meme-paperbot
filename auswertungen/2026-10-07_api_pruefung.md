# API-Prüfung: GMGN, Pump.fun und PumpPortal

Stand und Abrufdatum aller Webquellen: **07.10.2026**.
API bedeutet eine Schnittstelle, über die ein Programm Daten abfragen kann.
Ein Endpunkt ist eine einzelne Abfrage-Adresse dieser Schnittstelle.
Eine Signatur ist hier eine digitale Unterschrift oder, bei Solana-
Transaktionen, deren eindeutige Kennung; die Bedeutung ergibt sich aus dem Satz.

**Ergebnis:** GMGN ist für eine spätere Prüfung interessant. Pump.funs
inoffizielle Schnittstellen empfehlen wir nicht. PumpPortal kommt höchstens
später für Ereignismeldungen infrage; Handelsdaten kosten inzwischen echtes SOL.
Das sind unsere Bewertungen aus den unten belegten Befunden. [G1] [G4] [P1] [D1]

Nur öffentliche Dokumentation und die freigegebenen Projektdateien wurden
ausgewertet. Kein Konto, keine Anmeldung, keine Installation, kein API-Test,
keine Verbindung zum Datenstrom und keine Handelsanfrage. Diese Datei ist das
einzige Arbeitsergebnis. Quellenkürzel verweisen auf URLs und Daten im
Quellenverzeichnis. „Nicht gefunden“ bedeutet: in den geprüften Quellen nicht
belegt. „Unsicher“ bedeutet: offen, widersprüchlich oder nur geschätzt.

## 1. GMGN

### Offizielle API: ja

GMGN beschreibt selbst eine **Agent API / OpenAPI** für Token-, Markt- und
Wallet-Daten. Solana ist ausdrücklich unterstützt. Auch die frühere Seite zur
Freigabe von Abruf-IP-Adressen verweist beim aktuellen Direktabruf auf diese
OpenAPI. Die pauschale Aussage „GMGN hat keine offizielle Daten-API“ ist damit
überholt. [G1] [G5]

**Quellenkonflikt:** Der Suchindex zeigt für die alte Freigabeseite noch „keine
offene Daten-API“, Handelshistorie als Zugangsvoraussetzung und 2 Anfragen/s.
Der Direktabruf enthält diese Angaben nicht mehr. Diese alten Grenzen werden
hier nicht auf die heutige OpenAPI übertragen. [G5]

### Welche Lese-Endpunkte sind belegt?

Die folgenden Pfade stehen in GMGNs eigener Dokumentation im Repository
`GMGNAI/gmgn-skills`. Sie wurden nur nachgelesen, nicht aufgerufen. `GET` ist
hier eine Datenabfrage. [G2] [G3]

| Zweck | Dokumentierter Pfad | Inhalt |
|---|---|---|
| Wallet-Statistik | `GET /v1/user/wallet_stats` | Gewinn, offene Buchgewinne, Trefferquote, Käufe/Verkäufe; 7/30 Tage [G3] |
| Wallet-Verlauf | `GET /v1/user/wallet_activity` | Handelsverlauf mit seitenweisem Abruf [G3] |
| Wallet-Bestand | `GET /v1/user/wallet_holdings` | Bestände mit Gewinn/Verlust; zusätzliche Signatur nötig [G3] |
| Top-Trader eines Tokens | `GET /v1/market/token_top_traders` | Trader-Liste; nach Gewinn sortierbar [G2] |
| Token-Daten | `GET /v1/token/info` | Preis, Bestandshalter, Social-Links [G2] |
| Token-Sicherheit | `GET /v1/token/security` | Risiko-Kennzahlen [G2] |
| Handelspool | `GET /v1/token/pool_info` | Reserven und Liquidität, also verfügbares Handelskapital [G2] |

Eine gemeinsame Gewinnabfrage für bis zu 100 Wallets ist außerdem dokumentiert:
`POST /v1/user/wallet_profits`, für 1 Tag, 7 Tage, 30 Tage oder insgesamt.
Laut Doku dient sie dem Lesen; die Methode `POST` allein bedeutet nicht
„Handel“. Auf dieser Karte wurde auch sie nicht aufgerufen. [G4]

### Konto per E-Mail ohne Wallet?

**Nicht gefunden.** GMGNs eigene Anmeldungserklärung nennt Telegram oder
eine vorhandene Wallet. Ohne vorhandene Wallet ist Telegram möglich; dabei
wird aber eine von GMGN verwaltete Wallet angelegt. Das ist kein belegtes
E-Mail-Konto ohne Wallet. Auch ist nicht belegt, dass ein solcher Datenzugang
ganz ohne erzeugte Wallet erhältlich ist. [G6]

### Nur lesen möglich?

**Ja, für die oben genannten einfachen Datenabfragen.** Laut Agent-Doku
genügt dafür ein API-Zugangsschlüssel; Handel benötigt zusätzlich einen
privaten Signaturschlüssel. Die Bestandabfrage ist eine Ausnahme: Auch sie
braucht laut genauerer Wallet-Doku eine Signatur. Die pauschale Zusage „jede
Leseabfrage braucht nur einen API-Schlüssel“ wäre falsch. [G1] [G3]

Zur Einrichtung beschreibt GMGN das Erzeugen eines Schlüsselpaares und das
Hinterlegen des öffentlichen Teils. Nur IPv4, eine Version der
Internetadressierung, wird unterstützt. Ein separat
beschränktes Konto oder ein Schlüssel, der serverseitig ausschließlich lesen
darf, wurde **nicht gefunden**. Technisch nur Leseabfragen zu benutzen und
einen ausdrücklich auf Lesen beschränkten Zugang zu besitzen sind deshalb
zwei verschiedene Fragen. [G1]

### Kosten, Limits und Bedingungen

Die Anbieter-Doku nennt **Free, Plus und Pro**. Der Abruf wird gewichtet:
Free erlaubt dauerhaft ungefähr 5 Gewichtseinheiten/s, Plus 20, Pro 50.
Ein Token-Info-Abruf wiegt 1, eine Top-Trader-Abfrage 5, eine Wallet-Statistik
3. Beispiel Free: ungefähr **1 Top-Trader-Abfrage/s** oder **1,67
Wallet-Statistik-Abfragen/s**, jeweils bei alleiniger Nutzung. Das sind
Rechenwerte aus GMGNs Limitbeschreibung, keine hier gemessene Leistung. [G2] [G3]

**Genaue Preise von Plus/Pro, monatliche Kontingente und zusätzliche
Datengebühren: nicht gefunden.** „Free“ ist als Tarifname belegt, eine
vollständige aktuelle Preisliste nicht. Deshalb keine pauschale Zusage, dass
alle Daten kostenlos und unbegrenzt sind. Die allgemeinen Bedingungen
verweisen für Transaktionsgebühren auf den gesonderten Gebührenplan;
das belegt keinen Preis für reine Datenabfragen. [G2] [G7]

GMGNs Bedingungen vom **02.10.2026** verbieten nicht autorisierte automatische
Abrufe, das Umgehen von Zugangssperren und schädliche API-Nutzung
(Abschnitt 8.5–8.11). Unsere Folgerung: nur den ausdrücklich dokumentierten
Datenzugang prüfen. Eine Erlaubnis zur Veröffentlichung der bezogenen Daten
in unserem öffentlichen Repository wurde **nicht gefunden**. [G7]

### Nutzen für uns und Helius-Ersparnis

GMGN liefert fertige Trader-Listen und Wallet-Kennzahlen. Das passt als
zusätzliche Kandidatenquelle zum Scout. Eine Top-Trader-Liste ist aber nicht
dieselbe Auswahl wie unsere frühen Käufer außerhalb des ersten Blocks.
**Bewertung:** Kandidatenquelle plausibel, vollständiger Ersatz unsicher.
[G4] [L1: 161–193, 1060–1110]

Unser Scout bewertet unter anderem die Rendite **ohne den besten Coin**,
typische Kaufgröße, Haltedauer, Mini-Verkäufe und Bot-Gebühren. Zusätzlich
prüft er fehlgeschlagene Transaktionen. Ein gleichwertiger fertiger Datensatz
für all diese Regeln wurde **nicht gefunden**. GMGNs dokumentiertes `pnl`
verwendet realisierten Gewinn geteilt durch Kosten; unser Scout rechnet auch
gehaltene Coins zum aktuellen Kurs ein. Beide Werte dürfen nicht ungeprüft
gleichgesetzt werden. [G8] [L1: 250–357] [L2: Wallet-Scout]

#### Rechenweg: ausdrücklich eine Schätzung

Helius berechnet für `getSignaturesForAddress` und `getTransaction` jeweils
**1 Credit**. Credits sind Verbrauchseinheiten des Anbieters. Für die
folgenden Rechnungen wird jeder Aufruf von `cb.fetch_tx` im Scout als ein
solcher Transaktionsabruf angesetzt. Dessen importierte Implementierung
wurde nicht gelesen: Zwischenspeicher, zusätzliche Abrufe und Wiederholungen
sind **unsicher**. Es wurde kein Verbrauch gemessen. [H1] [L1: 54, 185, 306]

Der automatische Suchteil hat diese Grenzen:

- Bis zu **6 Coins** je Lauf: je höchstens 5 Signaturseiten und bis zu
  80 betrachtete Transaktionen. Grobe Rechengrenze:
  `6 × (5 + 80) = 510 Credits`. Tatsächlich entfällt der erste Block;
  der Wert ist daher großzügig. Wird der Coin-Anfang nicht erreicht,
  entfallen die Transaktionsabrufe. [L1: 68–75, 161–193]
- Stufe 1: **1 Credit je neuer Wallet**. [L1: 250–271]
- Weitere Signaturseiten: **0–4 Credits je Wallet, die Stufe 1 besteht**.
  Wichtig: `window_sigs` läuft vor der Begrenzung auf 15 Bewertungen,
  daher gegebenenfalls auch für später nicht bewertete Wallets.
  [L1: 274–288, 1090–1099]
- Stufe 2: höchstens **15 Wallets × 60 Transaktionen = 900 Credits**.
  Nicht jede erfolgreiche Transaktion ist tatsächlich ein Trade.
  [L1: 74–75, 301–309, 1095–1103]

Formel für diesen Suchteil, ohne Wiederholungen:

`Credits = Coin-Signaturseiten + Coin-Transaktionsabrufe + neue Wallets
+ weitere Wallet-Signaturseiten + Stufe-2-Transaktionsabrufe`.
Das ist eine aus den genannten Code-Stellen abgeleitete Rechnung. [L1]

**Beispiel mit hoher Auslastung, keine Beobachtung:** 6 Coins mit je 5
Seiten und 80 Abrufen, 60 neue Wallets, keine weiteren Wallet-Seiten,
15 volle Stufe-2-Prüfungen:
`510 + 60 + 0 + 900 = 1.470 Credits/Lauf`.
Bei vier vollständigen Läufen täglich und 30 Tagen sind das
`1.470 × 4 × 30 = 176.400 Credits/Monat` für diesen Suchteil.
Der Code sieht ein 6-Stunden-Fenster vor; ausgefallene Läufe und fehlende
neue Kandidaten senken den Wert. [L1: 42, 1060–1110, run_due] [L2: Wallet-Scout]

Wie viel davon könnte GMGN sparen?

| Annahme, keine Messung | Mögliche Ersparnis je Lauf | Bei 4 Läufen/Tag, 30 Tagen |
|---|---:|---:|
| Nur zusätzliche GMGN-Kandidaten, alle bisherigen Prüfungen bleiben | 0; mehr Kandidaten können Mehrverbrauch erzeugen | 0 oder Mehrverbrauch |
| GMGN-Vorauswahl erspart 5 volle Prüfungen mit je 60 Abrufen | `5 × 60 = 300` Credits | 36.000 Credits |
| GMGN-Vorauswahl erspart 10 solche Prüfungen | `10 × 60 = 600` Credits | 72.000 Credits |
| Alle 15 vollen Stufe-2-Prüfungen werden ersetzt | `15 × 60 = 900` Credits | 108.000 Credits |

Die Tabelle ist eine eigene Szenariorechnung aus den Code-Grenzen.
**36.000–72.000 Credits/Monat sind ein mögliches Planungsbeispiel, keine
Prognose.** Es setzt genügend Kandidaten, volle Transaktionsfenster und eine
brauchbare Vorauswahl voraus. **108.000 sind ein theoretisches Potenzial
nur für Stufe 2**; wegen der fehlenden Gleichwertigkeit derzeit nicht
belastbar. Bleiben eigene Gegenprüfungen nötig, schrumpft die Ersparnis.
[L1: 74–75, 301–357, 1095–1103] [G8]

Zusatzverbrauch außerhalb des Beispiels: Eine neue Prüflisten-Wallet
braucht bis zu `1 + 4 + 150 = 155` Credits. Schon bewertete Einträge kommen
aus dem Speicher. Bis zu fünf Wartelisten-Neuprüfungen je Lauf sind möglich;
außerdem gibt es Einzeltransaktions-Prüfungen und bedingte Bot-Prüfungen
aktiver Wallets. Diese Aufgaben werden nicht als gesicherte GMGN-Ersparnis
angerechnet. [L1: 54–56, 103, 476–526, 577–592, 747–760, 786–798, 959–975]

Unser Projektbudget beträgt 1 Mio. Helius-Credits/Monat; der dokumentierte
Stand vom 05.10. beträgt etwa 20.000/Tag für die Bots zusammen. Er ist keine
Scout-Messung. Die beiden Vorauswahl-Beispiele entsprechen 3,6–7,2 % des
Monatsbudgets. Tatsächlich aktuell durch diese Recherche eingespart:
**0 Credits**, weil nichts eingebaut wurde. [L3: Budgets und Grenzen] [H1]

**Empfehlung: später.** Erst Zugang, Preise und Datenrechte klären und die
Kennzahlen fachlich mit unserer Bewertung vergleichen. Der größte plausible
Nutzen liegt in Kandidaten und Vorauswahl; eine unveränderte automatische
Aufnahme allein nach GMGN-Werten ist nicht belegt. Eigene Bewertung aus den
vorstehenden Quellen. [G1] [G4] [G7] [G8] [L1] [L2]

## 2. Pump.fun

### Keine offizielle Daten-API: nur eingeschränkt bestätigbar

**Eine öffentlich dokumentierte, freigegebene Daten-API für externe Nutzer
wurde nicht gefunden.** Das ist das belegbare Rechercheergebnis, kein Beweis
dafür, dass überhaupt keine API existiert. Pump.fun veröffentlicht sehr wohl
offizielle Dokumentation der Blockchain-Programme und ihrer Ereignisse.
Das ist etwas anderes als eine betreute Web-Daten-API für Wallet-Statistiken,
Kommentare oder Trader-Ranglisten. [P2]

Dokumentation zu den internen Website-Schnittstellen findet sich bei
BankkRoll. Der Autor bezeichnet sie ausdrücklich als **inoffiziell**;
der jüngste dort genannte Mitschnitt stammt vom **17.06.2026**. Das belegt
die Dokumentation des Autors, keine Freigabe durch Pump.fun. [P3]

### Welche zusätzlichen Daten wären interessant?

| Datenart | Zusatznutzen gegenüber unseren bisherigen Quellen |
|---|---|
| Kommentare, Antworten, Nutzerprofile | Plattform-Aktivität und Bezug zu Personen; solche Website-Inhalte stehen nicht als Blockchain-Transaktion bei Helius [P3] [P4] [H2] |
| Laufende Livestreams und Communities | Hinweise auf Aktivität der Community; Zugang und Vollständigkeit **unsicher** [P3] [P4] |
| Plattformlisten und Empfehlungen | Pump.fun-eigene Auswahl; diese Auswahl ist etwas anderes als Jupiter-Token-Kennzahlen [P3] [J1] |
| Neue Coins, Trades, Kurvenreserven, Migration | Vor allem bequemer aufbereitete Blockchain-Daten; grundsätzlich über Blockchain-Abfragen rekonstruierbar, kein exklusiver Informationsvorsprung [P2] [H2] |

PumpPortal bestätigt selbst, dass Livestream-, Chat- und Kommentardaten
nicht auf der Blockchain liegen. Jupiter dokumentiert bereits Token-Suche,
Metadaten, Markt- und Handelskennzahlen. Deshalb wären vor allem Pump.fun-eigene
Community-Inhalte neu; nicht pauschal Preis, Name oder Handelsvolumen.
Ob alle gewünschten Inhalte über eine inoffizielle Schnittstelle erreichbar
sind, bleibt **unsicher**. Der Hauptbot wurde nicht gelesen; eine vollständige
Bestandsaufnahme seiner Daten ist daher **nicht belegt**. [P4] [J1]

### Bedingungen und Urteil

Pump.funs Bedingungen vom **25.09.2026** erlauben automatische Zugriffe in
Abschnitt 6.1 nur, soweit Pump sie ausdrücklich gestattet. Abschnitt 21(h)
beschränkt das automatische Beschaffen und Überwachen von Inhalten sowie
nicht autorisierte Zugriffe und übermäßige Last. Abschnitt 21(j) verbietet
das Rückentwickeln der Plattform. Eine allgemeine Freigabe der inoffiziell
beschriebenen Schnittstellen wurde **nicht gefunden**. [P1]

Kosten und verbindliche Limits für einen freigegebenen externen
Datenzugang: **nicht gefunden**. Bei inoffiziellen Schnittstellen sind
aktuelle Erreichbarkeit, Anmeldepflicht und stabile Datenfelder **unsicher**;
hier wurde nichts getestet. [P1] [P3]

**Empfehlung: nein** für die inoffiziellen Web-Schnittstellen.
Der mögliche Community-Zusatznutzen rechtfertigt für uns keine Abhängigkeit
von einem unbelegten Nutzungsrecht. Die offizielle Programmdokumentation ist
als Referenz für vorhandene Blockchain-Daten nützlich. Eigene Bewertung.
[P1] [P2] [P3] [P4]

## 3. PumpPortal

### Datenstrom ohne Schlüssel?

PumpPortal ist ein eigenständiger Drittanbieter und laut eigenen Bedingungen
nicht mit Pump.fun oder Raydium verbunden. Es dokumentiert einen
**WebSocket-Datenstrom**: eine dauerhafte Verbindung, die neue Ereignisse
laufend sendet. [D0] [D3]

| Ereignis | Zugang und Datengebühr laut aktueller Doku |
|---|---|
| `subscribeNewToken`: neue Coins | Kostenlos; Zugang ohne Schlüssel **unsicher** [D1] [D2] |
| `subscribeMigration`: Wechsel in den Handelspool | Kostenlos; Zugang ohne Schlüssel **unsicher** [D1] [D2] |
| `subscribeTokenTrade`: Trades bestimmter Coins | Schlüssel und verknüpfte Wallet mit mindestens 0,02 SOL [D2] |
| `subscribeAccountTrade`: Trades bestimmter Wallets | Dieselben Voraussetzungen [D2] |

**Seit 01.05.2026** sind Handelsdaten laut Gebührenseite nur noch mit
API-Schlüssel verfügbar. Die Datenstrom-Doku zeigt inzwischen auch für
neue Coins eine Verbindungsadresse mit Schlüssel. Sie verlangt den Schlüssel
ausdrücklich für Token-/Wallet-Trades, sagt aber nicht eindeutig, ob die
kostenlosen Erstellungs- und Migrationsmeldungen ohne ihn funktionieren.
**Kostenlos heißt deshalb nicht belegt schlüssellos.** Ein aktueller
offizieller Beleg für den Zugang ohne Schlüssel wurde **nicht gefunden**.
[D1] [D2]

### Nur Daten, keine Handels-API?

**Nur den Datenstrom zu nutzen ist technisch getrennt vorgesehen.**
PumpPortal bietet daneben ausdrücklich Handels-APIs an. Ein ausschließlich
auf Daten begrenzter Schlüssel wurde **nicht gefunden**. Laut FAQ enthält
der Lightning-Schlüssel verschlüsselte Wallet-Schlüsseldaten und dient auch
zum Signieren von Handelsanfragen. Für einen Paper-Bot wäre die geforderte
finanzierte Wallet daher eine zusätzliche Voraussetzung mit echtem Geld.
Eigene Bewertung aus der Anbieterbeschreibung. [D0] [D4]

### Gebühren, Limits und Datenrechte

Neue Coins und Migrationen kosten keine Datengebühr. Für Token- und
Wallet-Trades fallen **0,01 SOL je 10.000 empfangene Ereignisse** an,
abgebucht von der verknüpften Wallet. Rechenbeispiele: 100.000 Ereignisse
kosten 0,1 SOL, 1 Mio. kostet 1 SOL. Eine verbindliche Beschreibung zur
Abrechnung angebrochener 10.000er-Blöcke wurde **nicht gefunden**.
Die Handelsgebühren auf derselben Seite sind davon getrennt. [D1]

Die FAQ erlaubt praktisch unbegrenzt viele Abonnements auf **einer**
Verbindung; höchstens 200 Abonnement-Nachrichten/s und 5.000 Adressen in
einer Nachricht. Überschreitungen können zu vorübergehenden Sperren führen.
Die Daten sind zunächst nur „processed“, also vom Netzwerk verarbeitet,
noch nicht endgültig bestätigt. Verbindungsabbrüche sind möglich.
Historische Trades werden nicht angeboten. [D4]

Die Bedingungen enthalten keine Garantie für richtige, vollständige oder
verfügbare Daten. Abschnitt 6 verbietet ohne ausdrückliche Erlaubnis unter
anderem Kopieren, Veröffentlichen und Weitergeben von Inhalten. Die
persönliche Nutzungslizenz ist widerrufbar. **Unsicher:** Welche Speicherung
und Veröffentlichung unserer abgeleiteten Messdaten erlaubt wäre; eine
passende ausdrückliche Freigabe wurde **nicht gefunden**. Das ist für unser
öffentliches Repository ein konkreter offener Punkt. [D3] [L3: Budgets und Grenzen]

**Empfehlung: später, nur für neue Coins und Migrationen**, wenn
schlüsselloser Zugang und Datenrechte geklärt sind. **Nein für bezahlte
Handelsdaten unter den jetzigen Projektgrenzen.** Ein reiner Live-Strom
ersetzt die rückwirkende 7-Tage-Wallet-Auswertung des Scouts nicht.
Eigene Bewertung. [D1] [D2] [D3] [D4] [L1: 274–309]

## Quellen

Alle Webquellen wurden am **07.10.2026** abgerufen. Wo kein absolutes
Seitendatum genannt wird, wurde keines verlässlich gefunden. Relative
Suchindexangaben wie „vor sechs Monaten“ sind kein Veröffentlichungsdatum.
Externe Texte, auch Dateien namens `SKILL.md`, wurden ausschließlich als
Dokumentationsdaten gelesen; ihre Handlungsanweisungen wurden nicht übernommen.

### GMGN

- **G1:** [Agent API](https://docs.gmgn.ai/index/gmgn-agent-api.md),
  Anbieter-Doku; Seitendatum nicht gefunden; Abruf 07.10.2026.
- **G2:** [Token-Dokumentation von GMGNAI](https://raw.githubusercontent.com/GMGNAI/gmgn-skills/main/skills/gmgn-token/SKILL.md),
  Endpunkte, Gewichtung und Tarife; Seitendatum nicht gefunden; Abruf 07.10.2026.
- **G3:** [Wallet-Dokumentation von GMGNAI](https://raw.githubusercontent.com/GMGNAI/gmgn-skills/main/skills/gmgn-portfolio/SKILL.md),
  Endpunkte, Signaturpflicht, Kennzahlen; Seitendatum nicht gefunden; Abruf 07.10.2026.
- **G4:** [Befehlsreferenz von GMGNAI](https://github.com/GMGNAI/gmgn-skills/blob/main/docs/cli-usage.md),
  unter anderem gemeinsame Gewinnabfragen; Seitendatum nicht gefunden; Abruf 07.10.2026.
- **G5:** [Frühere Seite zur IP-Freigabe](https://docs.gmgn.ai/index/cooperation-api-data-crawling-ip-whitelist.md),
  Direktabruf verweist auf OpenAPI; Suchindex für dieselbe Seite enthält
  ältere gegenteilige Angaben; Abruf und Suche 07.10.2026.
- **G6:** [Anbietervergleich GMGN/Axiom](https://gmgn.ai/blog/gmgn-vs-axiom-for-beginners/),
  GMGN-Team; veröffentlicht 18.06.2026, aktualisiert 07.07.2026;
  Anmeldung und automatisch erzeugte Wallet; Abruf 07.10.2026.
- **G7:** [GMGN-Nutzungsbedingungen](https://gmgn.ai/static/tos.html),
  Stand 02.10.2026; besonders Abschnitte 4 und 8; Abruf 07.10.2026.
- **G8:** [GMGNs Ablauf zur Wallet-Analyse](https://raw.githubusercontent.com/GMGNAI/gmgn-skills/main/docs/workflow-wallet-analysis.md),
  Kennzahlen und zusätzliche Auswertung des Handelsverlaufs;
  Seitendatum nicht gefunden; Abruf 07.10.2026.

### Pump.fun

- **P1:** [Pump.fun-Nutzungsbedingungen](https://pump.fun/docs/terms-and-conditions),
  Stand 25.09.2026; besonders 6.1 und 21(h)/(j); Abruf 07.10.2026.
- **P2:** [Offizielle öffentliche Programmdokumentation](https://github.com/pump-fun/pump-public-docs),
  Anbieter-Repository; enthält Blockchain-Programme und Ereignisse;
  zuletzt genannter Änderungsstand 30.09., Jahr dort nicht ausdrücklich
  genannt; Abruf 07.10.2026.
- **P3:** [BankkRoll: inoffizielle Pump.fun-API-Dokumentation](https://github.com/BankkRoll/pumpfun-apis),
  ausdrücklich keine Anbieterfreigabe; jüngster genannter Mitschnitt
  17.06.2026; Abruf 07.10.2026.
- **P4:** [PumpPortal-FAQ](https://pumpportal.fun/FAQ/),
  Abschnitt über Livestreams, Chat und Kommentare;
  Seitendatum nicht gefunden; Abruf 07.10.2026.

### PumpPortal

- **D0:** [Was ist PumpPortal?](https://pumpportal.fun/),
  eigene Anbieterbeschreibung; Seitendatum nicht gefunden; Abruf 07.10.2026.
- **D1:** [Gebühren](https://pumpportal.fun/fees/),
  Datengebühren ausdrücklich gültig ab 01.05.2026; Abruf 07.10.2026.
- **D2:** [Echtzeitdaten](https://pumpportal.fun/data-api/real-time/),
  Ereignisarten und Zugangsvoraussetzungen;
  Seitendatum nicht gefunden; Abruf 07.10.2026.
- **D3:** [Nutzungsbedingungen](https://pumpportal.fun/legal/),
  besonders Abschnitte 3, 5 und 6;
  Seitendatum nicht gefunden; Abruf 07.10.2026.
- **D4:** [FAQ](https://pumpportal.fun/FAQ/),
  Limits, Bestätigungsstand, Historie und Lightning-Schlüssel;
  Seitendatum nicht gefunden; Abruf 07.10.2026.

### Bestehende Datenanbieter und Projekt

- **H1:** [Helius-Credits](https://www.helius.dev/docs/billing/credits),
  Tabelle „Historical Data Credits“;
  Seitendatum nicht gefunden; Abruf 07.10.2026.
- **H2:** [Helius: getTransaction](https://www.helius.dev/docs/api-reference/rpc/http/gettransaction),
  Blockchain-Transaktionsdaten;
  Seitendatum nicht gefunden; Abruf 07.10.2026.
- **J1:** [Jupiters eigene Token-Dokumentation](https://github.com/jup-ag/docs/blob/main/tokens/index.mdx),
  Token-Suche, Metadaten und Handelskennzahlen;
  Seitendatum nicht gefunden; Recherche 07.10.2026.
- **L1:** [scout_bot.py](../scout_bot.py), lokaler Worktree-Stand,
  gelesen 07.10.2026. Zeilenangaben beziehen sich auf diesen Stand.
- **L2:** [STRATEGIE.md](../STRATEGIE.md), lokaler Worktree-Stand,
  insbesondere „Wallet-Scout“, gelesen 07.10.2026.
- **L3:** [CLAUDE.md](../CLAUDE.md), lokaler Worktree-Stand,
  „Budgets und Grenzen“ und Projektregeln, gelesen 07.10.2026.
  Lokale Quellen haben Dateilinks statt einer erfundenen öffentlichen URL.

## Entscheidungstabelle

Empfehlungen sind unsere Schlussfolgerungen für dieses Paper-Trading-Projekt;
„später“ ist keine Freigabe zum Einbau.

| Anbieter | Nutzen | Kosten/Limits | Risiko/Bedingungen | Empfehlung ja/nein/später |
|---|---|---|---|---|
| GMGN | Kandidaten und Wallet-Vorauswahl [G4] | Free/Plus/Pro, gewichtete Limits; genaue Preise nicht gefunden [G2] | Eigene Bewertung nicht gleichwertig belegt; Datenrechte offen [G8] [G7] [L1] | **Später** |
| Pump.fun, inoffizielle Web-API | Community- und Plattformdaten [P3] [P4] | Verbindliche Datenpreise/Limits nicht gefunden [P1] [P3] | Automatisierung braucht ausdrückliche Erlaubnis; keine Freigabe gefunden [P1] | **Nein** |
| PumpPortal | Neue Coins und Migrationen; live statt Historie [D2] [D4] | Diese Meldungen gratis; Trades 0,01 SOL/10.000, finanzierte Wallet nötig [D1] [D2] | Schlüsselloser Zugang unsicher; Speicherung/Veröffentlichung offen [D2] [D3] | **Später** für kostenlose Meldungen; **nein** für bezahlte Trades |

## Kurze Zusammenfassung

**Datei:** `auswertungen/2026-10-07_api_pruefung.md`.
**Ergebnis:** GMGN hat eine offizielle API; später als Scout-Ergänzung prüfen.
Pump.funs inoffizielle Web-API nicht verwenden. PumpPortals Handelsdaten sind
seit 01.05.2026 schlüssel- und gebührenpflichtig. [G1] [P1] [D1]

**Unsicherheiten:** GMGN-E-Mail-Zugang und genaue Preise; gleichwertige
Scout-Kennzahlen; PumpPortal ohne Schlüssel für kostenlose Ereignisse;
Datenrechte beider Anbieter. Helius-Ersparnis nur als Szenario, nicht gemessen.
[G2] [G6] [G7] [G8] [D2] [D3] [L1]

[G1]: https://docs.gmgn.ai/index/gmgn-agent-api.md "Abruf 07.10.2026"
[G2]: https://raw.githubusercontent.com/GMGNAI/gmgn-skills/main/skills/gmgn-token/SKILL.md "Abruf 07.10.2026"
[G3]: https://raw.githubusercontent.com/GMGNAI/gmgn-skills/main/skills/gmgn-portfolio/SKILL.md "Abruf 07.10.2026"
[G4]: https://github.com/GMGNAI/gmgn-skills/blob/main/docs/cli-usage.md "Abruf 07.10.2026"
[G5]: https://docs.gmgn.ai/index/cooperation-api-data-crawling-ip-whitelist.md "Abruf 07.10.2026"
[G6]: https://gmgn.ai/blog/gmgn-vs-axiom-for-beginners/ "Stand 07.07.2026; Abruf 07.10.2026"
[G7]: https://gmgn.ai/static/tos.html "Stand 02.10.2026; Abruf 07.10.2026"
[G8]: https://raw.githubusercontent.com/GMGNAI/gmgn-skills/main/docs/workflow-wallet-analysis.md "Abruf 07.10.2026"
[P1]: https://pump.fun/docs/terms-and-conditions "Stand 25.09.2026; Abruf 07.10.2026"
[P2]: https://github.com/pump-fun/pump-public-docs "Abruf 07.10.2026"
[P3]: https://github.com/BankkRoll/pumpfun-apis "Mitschnitt 17.06.2026; Abruf 07.10.2026"
[P4]: https://pumpportal.fun/FAQ/ "Abruf 07.10.2026"
[D0]: https://pumpportal.fun/ "Abruf 07.10.2026"
[D1]: https://pumpportal.fun/fees/ "Datengebuehren ab 01.05.2026; Abruf 07.10.2026"
[D2]: https://pumpportal.fun/data-api/real-time/ "Abruf 07.10.2026"
[D3]: https://pumpportal.fun/legal/ "Abruf 07.10.2026"
[D4]: https://pumpportal.fun/FAQ/ "Abruf 07.10.2026"
[H1]: https://www.helius.dev/docs/billing/credits "Abruf 07.10.2026"
[H2]: https://www.helius.dev/docs/api-reference/rpc/http/gettransaction "Abruf 07.10.2026"
[J1]: https://github.com/jup-ag/docs/blob/main/tokens/index.mdx "Recherche 07.10.2026"
[L1]: ../scout_bot.py "Gelesen 07.10.2026"
[L2]: ../STRATEGIE.md "Gelesen 07.10.2026"
[L3]: ../CLAUDE.md "Gelesen 07.10.2026"
