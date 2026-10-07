# PumpPortal: Recherche zum kostenlosen Datenstrom

Stand und Abrufdatum aller Quellen: **07.10.2026**. Öffentliche Seiten konnten über das Web-Werkzeug abgerufen werden. Es wurde keine WebSocket-Verbindung aufgebaut, kein Konto und keine Wallet angelegt und kein Schlüssel verwendet. Die Recherche umfasst nur neue Coins und Migrationen; Quellenverweise stehen bei den Aussagen, URL und Abrufdatum im Quellenverzeichnis. Eigene Rechnungen und Schlussfolgerungen sind ausdrücklich gekennzeichnet.

## 1. Nutzungsbedingungen: kostenlos bedeutet keine Speicherfreigabe

**Automatische Nutzung:** Die Doku zeigt programmatische Abonnements. Die FAQ berücksichtigt ausdrücklich lange Verbindungen. Das spricht technisch für einen dauerhaften Empfänger. Eine ausdrückliche rechtliche Erlaubnis für unbegrenzten automatischen Dauerbetrieb ist dagegen **unsicher**. [Q2, Q3]

**Speichern und Weitergabe:** Abschnitt 6 untersagt ohne ausdrückliche Erlaubnis unter anderem Kopieren, Veröffentlichen und Verteilen der Schnittstelle oder ihrer Inhalte. Kurze Kernzitate: „Unless expressly authorized by us, you may not copy“ sowie „publish, distribute“. Eine Sondererlaubnis für kostenlose Ereignisse oder ein eigenes CSV-Archiv steht dort nicht. **Unsicher:** Ob einzelne On-Chain-Fakten oder daraus berechnete Namenshäufigkeiten vollständig unter diese Klausel fallen. Eine Speicherfreigabe lässt sich daraus nicht ableiten. [Q1, Abschnitt 6]

**Öffentliches Repo:** Eigene Schlussfolgerung: Rohereignisse und daraus kopierte Namen/Zeitpunkte vor einer ausdrücklichen Freigabe nicht als erlaubt behandeln. Auch lokales Speichern ist durch das breite Kopierverbot nicht klar freigegeben. [Q1, Abschnitt 6]

**Dauerhafte Verfügbarkeit:** Die persönliche, begrenzte Lizenz ist widerruflich; Kernzitat: „freely revocable by us at any time“. Zugang kann beschränkt werden, Datenrichtigkeit ist nicht garantiert und Bedingungen können geändert werden. Störungen, Umgehung von Zugangssperren und Verletzungen fremder Rechte sind untersagt. [Q1, Abschnitte 1, 3–6, 10]

## 2. Technik und tatsächlich belegte Felder

### Kosten und Zugang ohne Schlüssel

`subscribeNewToken` und `subscribeMigration` sind kostenlos. Seit 01.05.2026 sind Handelsdaten schlüsselpflichtig und kosten 0,01 SOL je 10.000 empfangene Trades; diese gehören nicht zum untersuchten kostenlosen Angebot. [Q4]

Die aktuelle Doku zeigt auch für die Verbindung einen API-Key-Platzhalter. Sie nennt Schlüssel und finanzierte Wallet ausdrücklich für Token-/Account-Handelsabonnements. **Unsicher:** Sie sagt nicht eindeutig, ob der kostenlose Zugang heute ohne Schlüssel garantiert ist. Chainstacks Beispiel und Scorps eigener Betriebsbericht benutzen `wss://pumpportal.fun/api/data` ohne Schlüssel. Das ist ein Hinweis, keine aktuelle Zusicherung des Anbieters; hier wurde es nicht ausprobiert. [Q2, Q5, Q6]

### Verbindung, Limits und Ausfälle

| Punkt | Aussage des Anbieters |
|---|---|
| Verbindungen | Alles über eine Verbindung; die Daten-Doku fordert nur eine gleichzeitig. [Q2] |
| Abonnements | Praktisch unbegrenzt pro Verbindung; höchstens 200 Abonnementnachrichten/s und 5.000 Adressen je Nachricht. Das sind keine Limits für empfangene Ereignisse. [Q3] |
| Überschreitung | Wiederholtes Überschreiten kann zur temporären Sperre führen; Sperren verfallen laut Anbieter stündlich. [Q3] |
| Abbrüche | Netzprobleme und Lastverteilung können Verbindungen beenden; Wiederverbindung wird empfohlen. [Q3] |
| Historie | Nur Live-Daten; historische Daten müssen aus anderer Quelle kommen. [Q3] |
| Bestätigung | Daten kommen auf Solanas Stufe `processed`, also vor endgültiger Bestätigung. [Q3] |

**Unsicher:** Eine feste maximale Sitzungsdauer, Pflichtintervalle für Ping/Pong und garantierte lückenlose Zustellung sind in diesen Seiten nicht dokumentiert. Eigene Schlussfolgerung: Nach einem Abbruch erneut abonnieren, mit zunehmender Wartezeit wiederverbinden und Ausfallzeiten markieren; ein automatisches Nachliefern verpasster Ereignisse ist nicht zugesichert. [Q2, Q3]

Scorp berichtet aus eigenem Betrieb auch von ausbleibenden Ereignissen trotz offenem Socket. **Unsicher:** Das ist keine bestätigte allgemeine Eigenschaft. Eine Überwachung des letzten Ereignisses wäre daher zusätzlich zur Verbindungsprüfung sinnvoll; Scorps zehn Minuten sind kein Anbieterlimit. [Q6]

### Nachrichtenformat

Die offiziellen Beispiele senden JSON und lesen empfangene Nachrichten als JSON. Für die beiden kostenlosen Abonnements reichen die dokumentierten Nachrichten `{"method":"subscribeNewToken"}` und `{"method":"subscribeMigration"}`. Ein vollständiges Antwortschema mit Pflichtfeldern, Datentypen oder Versionsgarantie fehlt auf der Daten-Seite. [Q2]

Die folgende Tabelle trennt Beispiele von Zusicherungen. Chainstack ist die Primärquelle für seinen eigenen Beispielcode, Scorp für seinen eigenen Empfängerbericht; beide sind **keine PumpPortal-Schemaspezifikation**. Ohne einen Live-Test bleibt die heutige Feldbelegung **unsicher**. [Q2, Q5, Q6]

| Merkmal | Neues-Coin-Ereignis: in fremdem Beispiel benutzt | Migrationsereignis: offiziell belegter Stand |
|---|---|---|
| Ereignisart | `txType: "create"` bei Scorp. [Q6] | Abonnement vorhanden; genauer Kennwert wie `migrate`/`migration` **unsicher**. [Q2] |
| Coin-Adresse | `mint`. [Q5, Q6] | Feldname und Pflichtstatus **unsicher**. [Q2] |
| Name / Symbol | `name`, `symbol`. [Q5, Q6] | Mitlieferung **unsicher**. [Q2] |
| Ersteller | `traderPublicKey` wird als Ersteller gelesen. [Q5, Q6] | Mitlieferung **unsicher**. [Q2] |
| Startzeit | Kein Startzeitfeld im geprüften Chainstack-Beispiel. Vorhandensein **unsicher**. [Q5] | Ereignis-/Blockzeitfeld **unsicher**. [Q2] |
| Kurvenkonto | `bondingCurveKey`. [Q5] | Mitlieferung **unsicher**. [Q2] |
| Virtuelle Reserven | `vSolInBondingCurve`, `vTokensInBondingCurve`. [Q5] | Mitlieferung **unsicher**. [Q2] |
| Weitere Angaben | `signature`, `uri`, `marketCapSol`, `initialBuy`; keine verbindliche Einheitenzusage. [Q5] | Signatur, Zielpool, DEX und Reserven **unsicher**. [Q2] |

Eigene Schlussfolgerung: Eine lokal gesetzte UTC-Empfangszeit wäre eine Beobachtungszeit, keine genaue Startzeit auf der Blockchain. Das Kurvenbild beim Start liefert keinen laufenden Fortschritt. Name und Zeit allein erlauben außerdem keine eindeutige Zuordnung eines späteren Migrationsereignisses; dafür müsste eine Coin-Adresse erhalten bleiben. Die Tabelle belegt keine garantierten Pflichtfelder. [Q2, Q5, Q6]

## 3. Menge und Folgen für das Repository

**Ungefähre Größenordnung: 1.000–2.000 neue Coins pro Stunde; aktuelle PumpPortal-Zustellmenge unsicher.** Grundlage sind veröffentlichte eigene Messungen anderer Betreiber, keine Messung dieses Worktrees:

- Alchemii zählte am 04.09.2026 1.048 Coins in 42,3 Minuten, am 27.09.2026 1.047 in 55,4 Minuten. Eigene Umrechnung der veröffentlichten Raten: rund 1.487 bzw. 1.133 pro Stunde. Nur kurze Stichproben, zu verschiedenen Tageszeiten. [Q7]
- SmugCalls nennt 247.639 Starts für 21.–27.09. und 320.670 für 28.09.–04.10.2026. Eigene Rechnung: geteilt durch 168 Stunden ergibt rund 1.474 bzw. 1.909 pro Stunde. Der Betreiber nennt fehlende Starts und zwei Ausfälle von 39 und 64 Minuten in der zweiten Woche; diese Zählungen sind Untergrenzen. [Q8]

**Unsicher:** Netzweite Pump.fun-Starts entsprechen nicht zwingend allen von PumpPortal zugestellten Nachrichten. Die Größenordnung ist eine Planungsannahme, kein Anbieterlimit und keine Prognose für jede einzelne Stunde. [Q2, Q7, Q8]

### Nur Name und Zeit speichern: eigene Modellrechnung

Annahme: im Mittel **60 Byte je CSV-Zeile** in UTF-8, beispielsweise 20 Byte UTC-Zeit, 1 Trennzeichen, 37 Byte Name einschließlich nötiger Maskierung und 2 Byte Zeilenende. Tatsächliche Namenslängen und Kodierung sind **unsicher**; es wurde keine Daten-Datei vermessen. Gerechnet wird mit einer Zeile je Start und durchgehendem Empfang. Mengenansatz: Q7/Q8; Byteansatz: eigene Annahme.

| Coins/Stunde | Zeilen/Tag | MB/Tag | MB/30 Tage | MB/365 Tage |
|---:|---:|---:|---:|---:|
| 1.000 | 24.000 | 1,44 | 43,2 | 525,6 |
| 1.500 | 36.000 | 2,16 | 64,8 | 788,4 |
| 2.000 | 48.000 | 2,88 | 86,4 | 1.051,2 |

Quelle der Tabelle: eigene Rechnung `Coins/Stunde × 24 × Tage × 60 / 1.000.000`; dezimale MB, ohne Kopfzeile und Git-Speicher. Bei 120 statt 60 Byte verdoppeln sich die Werte. Im mittleren Fall entstehen 13,14 Millionen Zeilen/Jahr. **Unsicher:** Git-Kompression und Historie wurden nicht gemessen; die Tabelle beschreibt nur den CSV-Inhalt, nicht die gesamte Repo-Größe.

Eigene Empfehlung, falls Speicherung später ausdrücklich erlaubt wird: Rohdaten zeitlich begrenzen und außerhalb des öffentlichen Repos halten; für Namenswellen verdichtete Zeitfenster prüfen. Auch deren Veröffentlichung ist separat zu klären. Namen/Zeit allein sparen Platz, verhindern aber eine zuverlässige Verknüpfung mit Migrationen und die Erkennung mehrfach empfangener identischer Coins. [Q1, Q5, Q6; eigene Rechnung oben]

## 4. Nutzen für unser Paper-Trading

Für den Projektbezug wurden die relevanten Abschnitte von `STRATEGIE.md` gelesen. `namenswellen.csv` wurde nur für die angeforderten ersten drei Zeilen angesprochen, war jedoch im Worktree nicht vorhanden; auch die Dateinamenssuche fand sie nicht. **Unsicher:** Ihre Kopfzeile und die genaue vorgesehene Namenswellen-Messung können daher nicht beurteilt werden. Quelle: eigene lesende Pfadprüfung vom 07.10.2026; Projektgrundlage P1.

| Zweck | Eigene Einschätzung anhand der Quellen |
|---|---|
| Namenswelle | Größter naheliegender Nutzen: Häufigkeit neuer ähnlicher Namen in Zeitfenstern beobachten. Die Strategie kennt bisher Mitläufer-Verdacht und Auswahl bei gleichem Namen/Symbol. Namenshäufigkeit belegt aber keine Käufer, Holder oder organische Verbreitung. **Unsicher:** Anschluss an die fehlende CSV. [P1, Regeln; Q5, Q6] |
| Kontrollgruppe | Startmeldungen könnten einen Kandidatenbestand liefern. Die bestehende Gruppe verlangt Alter 15 Minuten bis 6 Stunden und Sicherheitsprüfungen. Auswahl müsste zum gleichen Zeitpunkt aus gleich alten, gleich geprüften Coins erfolgen. Nur bereits migrierte Coins wären eine Vorauswahl erfolgreicher Kurven und damit eine andere Kontrollgruppe. Ausfälle können die Stichprobe verzerren. [P1, Experimente; Q2, Q3] |
| Endspurt / Graduation | Migration kann ein zusätzliches Umzugssignal liefern. Die Strategie braucht davor 95–108 vSol sowie für „viele Trades“ mindestens 2.000 Trades seit Start. Start- und Migrationsmeldungen allein liefern diese laufenden Werte nicht. Der kostenlose Strom ersetzt daher keine Endspurt-Überwachung. [P1, Experimente; Q2, Q4, Q5] |
| Einstieg nach Migration | Als Ereignisauslöser interessant. Ein Ereignis allein belegt keinen verfügbaren Kauf-/Verkaufskurs, Liquidität oder Gewinn nach Kosten. Die Strategie sieht bereits Nachrechnung mit sechs Stunden Kursnachlauf der beendeten Experimente vor. Für einen Vergleich braucht es zusätzlich Kurse und Sicherheitsdaten zum tatsächlichen Entscheidungszeitpunkt. [P1, Experimente und Nachlauf; Q2, Q4] |

Eigene Bewertung: Zuerst Speicher- und Veröffentlichungsrechte sowie Zugang ohne Schlüssel klären. Fachlich passt der kostenlose Strom am ehesten zur Namensbeobachtung und zum Migrationszeitpunkt. Ein vollständiges kostenloses Handelssignal ist daraus nicht belegt. Neue Bewertungen müssten weiterhin die Projektregeln erfüllen: mindestens 200 Trades, zeitgleiche Kontrollgruppe, Ergebnis auch ohne die drei besten Trades und Kostenaufschlag. [Q1–Q6; P1, Testregeln]

## Quellenverzeichnis

Jeder Verweis oben umfasst die folgende URL und das Abrufdatum **07.10.2026**. Projektquellen verwenden eine relative Repository-URL und wurden lokal gelesen; eigene Prüfungen und Rechnungen haben keine externe URL.

- **Q1:** PumpPortal, [Terms of Use](https://pumpportal.fun/legal/), besonders Abschnitte 3, 5, 6 und 10. Abruf: 07.10.2026.
- **Q2:** PumpPortal, [Real-time Pump.fun Data](https://pumpportal.fun/data-api/real-time/). Abruf: 07.10.2026.
- **Q3:** PumpPortal, [Frequently Asked Questions](https://pumpportal.fun/FAQ/), Fragen zu Limits, Historie, Datenstufe und Verbindungsabbrüchen. Abruf: 07.10.2026.
- **Q4:** PumpPortal, [Fees](https://pumpportal.fun/fees/), Abschnitt Data API. Abruf: 07.10.2026.
- **Q5:** Chainstack Labs, [eigener PumpPortal-Empfänger als Python-Beispiel](https://raw.githubusercontent.com/chainstacklabs/pumpfun-bonkfun-bot/main/learning-examples/listen-new-tokens/listen_pumpportal.py). Abruf: 07.10.2026. Fremdes Beispiel, keine offizielle Feldgarantie; Datei kann sich ändern.
- **Q6:** Scorp Trader, [eigener Empfänger und Betriebsbericht vom 27.09.2026](https://trader.scorplabs.online/blog/serial-rugger-launch-alert-webhook-tutorial). Abruf: 07.10.2026. Herangezogen werden nur eigener Beispielcode und eigene Betriebserfahrungen.
- **Q7:** Alchemii, [eigene Pump.fun-Stichproben](https://www.alchemii.io/blog/why-is-solana-going-up), Abschnitt „How many meme coins are launching now“ und Einschränkungen. Abruf: 07.10.2026. Anbieter mit kommerziellem Interesse; seine Messungen wurden nicht unabhängig reproduziert.
- **Q8:** SmugCalls, [eigene On-Chain-Zählung](https://smugcalls.com/pumpfun-graduation-tracker.html?s=faq), Wochenzählungen und „Known gap“. Abruf: 07.10.2026. Bekannte Erfassungslücken; Werte können sich ändern.
- **P1:** [STRATEGIE.md](../STRATEGIE.md), Abschnitte „Regeln und ihre Herkunft“ und „Experimente (seit 29.09.)“, einschließlich Nachlauf und Testregeln. Lokal gelesen: 07.10.2026.

Arbeitsumfang: Nur dieser Bericht wurde neu erstellt. Keine Umsetzung, keine Datenänderung, kein Commit/Push; Tests gemäß Auftragskarte nicht ausgeführt. Quelle: Durchführung der Karte 20 am 07.10.2026.
