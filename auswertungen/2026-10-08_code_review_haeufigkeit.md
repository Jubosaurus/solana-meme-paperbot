# Code-Review 08.10.: Wie oft kommen die hohen Funde in den echten Daten vor?

Stand: 08.10.2026, ca. 20:40 UTC (22:40 deutsche Zeit). Nur Auswertung, am Code und an den Daten wurde nichts geändert.
Grundlage: `auswertungen/2026-10-08_code_review.md`. Datenquellen: `journal.csv`, `experimente/heisse_coins/journal.csv`, `copy/journal.csv`, `copy/verlauf/`, `copy/konten.json`, `scout/warteliste.csv`, `copy_wallets.txt` und die GitHub-Actions-Logs der drei Workflows (letzte 14 Tage, höchstens 100 Läufe je Workflow). Kosten: 2 % je Rundlauf = 0,004 SOL je Trade (Einsatz 0,2 SOL), wie in `dashboard/rechnung.py`.

**Wichtig vorweg:** Bei mehreren Funden hinterlässt der Fehler selbst keine Spur in den Daten. Dort steht „nicht messbar“ und, was sich ersatzweise messen ließ.

## Übersicht

| Fund | Faelle | SOL betroffen | Einfluss auf Strategie-Review |
|---|---|---|---|
| CR3-4 Bundle-Check unvollständig | nicht messbar. Obergrenze: 22 fehlgeschlagene Transaktionsabrufe in den Logs, **0** davon kurz vor einem Hauptstrategie-Kauf | 0 nachweisbar | nein |
| CR3-6 Transfergebühren-Prüfung fällt aus | **0** Fehlerzeilen in 73 Hauptbot-Logs (nicht je Kauf aufgezeichnet) | 0 nachweisbar | nein |
| CR3-5 `heisse_coins`: Kauf bei jedem Ausfall | 181 Käufe; davon 36 (20 %) mit RPC-Ausfall davor, 144 (80 %) vermutlich „zu viele Transaktionen“ | Ausfall-Gruppe +0,31 roh / +0,17 mit Kosten; übrige −6,33 roh / −6,91 mit Kosten; gesamt −6,02 / −6,74 | nein (Urteil bleibt: klar im Minus, auch ohne die 36) |
| CR6-3 Sicherung meldet Erfolg trotz Push-Fehler | 5 Fälle in 14 Tagen (Hauptbot 2, Copy 3), alle in abgebrochenen Läufen; dazu 12 Push-Fehler im Lauf | kein Datenverlust nachweisbar | nein |
| CR4-1 Copy-Kauf nach über 60 s | 1 von 4.377 Käufen (62,4 s, Cooker, 02.10.) | 0,2 SOL Einsatz, Position noch nicht geschlossen | nein |
| CR4-2 / CR4-3 Verkaufsanteil wirkt auf Nachkäufe | 521 Nachkäufe (11,9 % aller Käufe) in 177 Positionen; CR4-3 (Schatten) nicht messbar | Risikobetrag 8,9 SOL von 104 SOL Nachkauf-Einsatz; Ergebnis der 173 geschlossenen Positionen +5,51 roh / +4,82 mit Kosten (Wirkung des Fehlers selbst nicht herauszurechnen) | nein (nur Copy-Bewertung der Trader) |
| CR4-5 / CR4-9 Lücken beim Nachholen | nicht messbar (Fehler hinterlässt keine Spur). Folgen sichtbar: 1.107 dokumentierte verpasste Käufe, 23 vom Stundenabgleich gefangene Verkäufe | die 15 ganz verpassten Verkäufe: −3,22 SOL | nein |
| CR4-12 Schatten −100 % ohne Kurs | **0** Schatten-Zeilen mit Kurs 0 (von 180.250); 2 Schatten-Bereinigungen (−0,11 SOL); 8 Schatten mit −100 %, alle durch Überweisung | −2,2 SOL (nur Schatten, kein echtes Geld) | nein |
| CR5-1 bis CR5-3 Scout-Bewertung | nicht nachrechenbar ohne neue Helius-Abfragen, deshalb nicht gemacht | – | nein |
| CR5-7 4DOV nicht geschützt | heute **0** Fälle: 24 aktive Wallets, 6 freie Plätze | – | nein |

## Hauptstrategie und Experimente (Funde 1 und 2)

**CR3-4 (Bundle-Check unvollständig).** Beim Kauf wird nicht gespeichert, ob Transaktionen im Erstellungsblock übersprungen wurden. Eine Messung je Kauf ist deshalb nicht möglich. Ersatzweise: In den Logs vom 26.09. bis 01.10. stehen 22 fehlgeschlagene `getTransaction`-Abrufe (21 mal „zu viele Anfragen“, 1 Fehlermeldung); danach keine mehr. Kein Hauptstrategie-Kauf (0 von 189) lag höchstens 3 Minuten nach einem solchen Fehler. Auffällig, aber nicht beweisend: 19 von 189 Käufen haben „Block 0: 0 Käufer“ (−0,22 roh / −0,30 mit Kosten, im Schnitt −0,012 je Trade); ob das echt leere Blöcke oder Ausfälle waren, sagt das Journal nicht. Zum Vergleich: Käufe mit 1 Käufer in Block 0: 76 Trades, −2,72 roh; mit 2 oder mehr: 94 Trades, +2,03 roh. Lücke: 27 der 100 Hauptbot-Läufe haben kein abrufbares Log.

**CR3-6 (Transfergebühren-Prüfung fällt aus).** Ein Ausfall der Jupiter-Abfrage `/ultra/v1/shield` würde als Zeile `[JUPITER …] /ultra/v1/shield` im Log stehen. In 73 Hauptbot-Logs gibt es keine einzige (es gibt Fehler bei anderen Jupiter-Abfragen, zusammen über 800 Zeilen, vor allem „zu viele Anfragen“). Der Fund ist im Code richtig, ist in der Praxis aber bisher nicht aufgetreten. Eine abgelehnte Transfergebühr gab es einmal (`abgelehnt/`, 08.10.). Grenze: 27 Läufe ohne Log, ein Fehler dort wäre unsichtbar.

**CR3-5 (`heisse_coins`).** Das Journal schreibt bei allen 181 Käufen denselben Text „zu viele Transaktionen“. Den echten Grund hält der Bot nicht fest. Ersatzmessung: Ich habe geprüft, ob in den 2 Minuten vor dem Kauf ein Helius-Fehler bei `getSignaturesForAddress` oder `getTokenSupply` im Log steht (das sind die Ausfälle, die den Bundle-Check ebenfalls scheitern lassen). Das trifft bei 36 von 180 abgeschlossenen Trades zu. Die Zuordnung ist ungenau (Ergebnis wird 30 Minuten zwischengespeichert, 27 Läufe ohne Log), die 20 % sind also eher eine Untergrenze. Beide Gruppen getrennt: Ausfall-Gruppe 36 Trades, +0,31 roh / +0,17 mit Kosten; übrige 144 Trades, −6,33 roh / −6,91 mit Kosten. Das Experiment bleibt auch ohne die 36 klar im Minus; das Urteil ändert sich dadurch nicht.

## Betrieb (Fund 3)

**CR6-3 (Sicherung).** Der Schritt „Sicherung“ gibt bei fehlgeschlagenem Push nur eine gelbe Warnung aus, der Lauf gilt als erfolgreich bzw. bleibt „abgebrochen“. Gefunden:
- **5 Warnungen „Sicherung fehlgeschlagen“** in 14 Tagen: Hauptbot 30.09. (07:40 UTC) und 07.10. (13:54), Copy-Bot 02.10. (12:11), 02.10. (18:35) und 07.10. (18:59). Alle fünf in Läufen, die von Hand oder durch den Kettenstart abgebrochen wurden, nicht in regulär beendeten. Scout: 0 von 44 Läufen.
- **12 Push-Fehler während eines Laufs** („[GIT] push“): 11 am 07.10. beim Hauptbot zwischen etwa 15:07 UTC und dem Abbruch um 19:00 UTC, einer am 04.10. um 22:19. Danach ging das Speichern jeweils wieder.
- **Kein Datenverlust nachweisbar:** Bei allen fünf Warnungen steht die letzte Journal- bzw. Verlaufszeile höchstens 1 Minute (einmal 4 Minuten) vor dem Laufende bereits im Repository, weil der Bot zwischendurch selbst pusht. Ein „Journal-Loch am Schichtende“ gibt es nicht.
- **Lücken in `verlauf/`** (Hauptbot, seit 28.09.): 5 Lücken über 10 Minuten, die längste 250 Minuten (05.10. 19:57 bis 06.10. 00:07). Copy-Verlauf: 1 Lücke (01.10., 288 Minuten). Nur die Lücke 30.09. 07:40 bis 09:53 passt zu einem Schichtende mit Sicherungs-Warnung; dort endet die Datenzeile aber 25 s vor Laufende, es fehlt also nichts vom Lauf selbst. Es ist ein Kettenabbruch (kein neuer Lauf für 133 Minuten), kein Push-Problem.
- Grenze: Für je 27 Hauptbot- und Copy-Läufe gibt es kein abrufbares Log (abgebrochen, bevor sie starteten, oder abgelaufen).

## Copy Trading (Karte 4)

Zeitraum: 30.09. bis 08.10. (4.377 Käufe, 5.403 Verkäufe, 1.943 geschlossene Positionen, Summe −65,5 SOL roh).

**CR4-1 (Kauf nach über 60 s).** Genau 1 Fall (Cooker, 02.10. 19:40 UTC, 62,4 s). Zwischen 30 und 60 s liegen 62 weitere Käufe, die nach der Regel richtig durchgingen. Median der Verzögerung 1,6 s. Praktisch ohne Wirkung.

**CR4-2 / CR4-3 (Verkaufsanteil auf Nachkäufe).** Ich habe aus dem Journal nachgespielt: Immer wenn bei einem Nachkauf schon ein Teilverkauf des Traders gesammelt vorgemerkt war (`VERKAUF_GEMERKT`), zählt das als Fall. Ergebnis: 521 Nachkäufe in 177 Positionen. Gewichtet waren im Schnitt 8,5 % der Nachkäufe betroffen (8,89 SOL von 104,2 SOL Nachkauf-Einsatz: der Teil, der beim nächsten Verkauf zu früh mitverkauft wird). Die 173 geschlossenen Positionen davon haben zusammen +5,51 SOL (+4,82 mit Kosten), die übrigen 1.770 Positionen −71,03 SOL. Das heißt **nicht**, dass der Fehler nützt: Positionen mit Nachkäufen kommen von Tradern, die sich gut halten, die Gruppen sind nicht vergleichbar. Wie viel SOL der Fehler selbst gekostet hat, lässt sich aus den Zeilen nicht herausrechnen (man müsste den späteren Verkaufskurs der zu früh verkauften Token kennen). CR4-3 (gleiche Wirkung bei Schattenpositionen): Teilverkäufe von Schatten werden nicht einzeln ins Journal geschrieben, deshalb nicht messbar.

**CR4-9 / CR4-5 (Lücken beim Nachholen).** Der Fehler besteht gerade darin, dass keine Spur bleibt, daher nicht direkt messbar. Sichtbare Folgen: 1.107 Zeilen „Kauf des Traders verpasst (Lücke)“ bei 19 Tradern seit 01.10. (nur dokumentiert, kein Geld) und 23 `ABGLEICH`-Zeilen, also Verkäufe, die weder live noch beim Nachholen ankamen und erst der Stundenabgleich fing. 15 davon waren komplette Ausstiege (zusammen −3,22 SOL, zum Kurs der Abgleichszeit statt zum Kurs des Traders), 8 Teilverkäufe ohne eigenes Ergebnis. Wie viele davon durch die Fehler CR4-5/CR4-9 und wie viele durch gewöhnliche Netzausfälle entstanden, ist nicht trennbar.

**CR4-12 (Schatten −100 % ohne Kurs).** Im Copy-Verlauf gibt es 180.250 Schatten-Zeilen, **keine** mit Kurs 0. Schatten-Bereinigungen am Schichtende: 2 (zusammen −0,11 SOL, im Schnitt −26,5 %, nicht −100 %). Schatten mit −100 %: 8 (Cooker 7, 9LXM 1; 01.10. bis 02.10., zusammen −2,2 SOL), alle durch eine Token-Überweisung des Traders und nicht durch einen fehlenden Kurs. Ob dort ein letzter Kurs fehlte oder der Coin wirklich wertlos war, ist aus den Daten nicht zu sehen. Bei echten Positionen steht der Kurs 0 in zwei Fällen im Verlauf (Troupe: TESTla, BOBCOIN, 2.933 Zeilen), das betrifft nur die Anzeige; verkauft wird über die Jupiter-Quote.

## Scout (Karte 5)

**CR5-1 bis CR5-3 (Bewertung).** Die gespeicherten Bewertungen in `scout/kandidaten.csv` enthalten nur die Ergebnisse (Gewinn, Rendite, Coins), nicht die einzelnen Transaktionen. Mit korrigierter Rechnung neu bewerten ginge nur mit neuen Helius-Abfragen. Das habe ich wie verlangt nicht gemacht. Richtung der Fehler: CR5-1 und CR5-2 machen Wallets besser, als sie sind; CR5-3 macht sie schlechter.
Ersatzweise ein Blick auf die Wirklichkeit seit Aufnahme (10 Wallets, die die Automatik seit 05.10. aufgenommen hat; Prognose = „für uns +X %“ bei Aufnahme; realisiert = bereits geschlossene Positionen):

| Wallet | Prognose | geschlossen | realisiert (SOL) |
|---|---|---|---|
| Croco-AC7K | +72 % | 34 | +3,34 |
| HoneyBadger-6kfX | +13 % | 11 | −1,54 |
| 8K7Z | +9 % | 24 | −2,02 |
| FKJE | +20 % | 8 | −0,31 |
| 2z7o | +18 % | 47 | +0,35 |
| BlueMoon | +3 % | 1 | −0,18 |
| 54QZ | +29 % | 23 | −0,86 |
| HuyE | +1 % | 8 | −0,14 |
| DWRA | +48 % | 0 | noch kein Kauf |
| CCBV | +38 % | 0 | noch kein Kauf |

Summe der acht mit Ergebnis: −1,36 SOL. Die vier mit den knappsten Aufnahmewerten (ohne besten Coin höchstens +16 %: HoneyBadger, 8K7Z, BlueMoon, HuyE) stehen alle im Minus, die vier mit hoher Prognose gemischt (+3,34, −0,31, +0,35, −0,86). Stichprobe klein und in der Schonfrist, deshalb nur ein Hinweis: Knappe Aufnahmen sind das Risiko, wenn die Rechnung zu optimistisch ist. CR5-2 (Überweisungen) spielt bei diesen Wallets bisher kaum eine Rolle: nur HuyE hat 2 Überweisungen.

**CR5-7 (4DOV).** Bestätigt: `copy_wallets.txt` hat 24 aktive Wallets, das Limit ist 30 (`AUTO_MAX_WALLETS`). Die Ersetzung wegen Verlust wird nur geprüft, wenn alle Plätze belegt sind; heute sind **6 Plätze frei**, 4DOV kann also nicht ersetzt werden. Die Warteliste hat 5 Einträge; selbst wenn alle aufgenommen würden, blieben 1 Platz frei (und höchstens 3 Änderungen pro Tag). Hinweis zur Zahl: Die Entscheidung vom 08.10. nennt für 4DOV 80 Positionen und −4,25 SOL; `copy/konten.json` zeigt jetzt 84 geschlossene Positionen und **+0,20 SOL realisiert**. Die beiden Zahlen passen nicht zusammen (andere Rechnung, z. B. mit offenen Positionen oder Kosten, ist möglich, nicht geklärt). Nach der jetzigen Kontenzahl würde 4DOV die Verlust-Regel (mehr als 1 SOL Minus) gar nicht auslösen.

## Vorschlag zur Reihenfolge

**Vor dem Strategie-Review muss nichts behoben werden.** Keiner der gemessenen Funde verändert das Urteil über Hauptstrategie oder Experimente. Die Funde, die die Bewertung am ehesten verzerren könnten (CR3-4, CR3-6), kamen in den Logs nicht oder nur in Einzelfällen vor.

Wenn überhaupt etwas vorher: **nur Aufzeichnung, keine Verhaltensänderung.** Beim Kauf von `heisse_coins` und bei Block-0-Prüfungen den echten Grund und die Zahl übersprungener Transaktionen mitschreiben (neue Spalte hinten, nach `ensure_csv_columns`). Dann lässt sich CR3-4/CR3-5 künftig messen statt schätzen. Pflicht-Prüfungen für Bot-Logik gelten auch dafür.

**Danach (nach dem Review, in dieser Reihenfolge):**
1. CR6-3: Sicherungsschritt soll bei Push-Fehler rot werden oder es erneut versuchen. Klein, aber 5 Fälle in 14 Tagen.
2. CR5-1 bis CR5-3 mit Erhöhung von `SCORING_VERSION` (kostet Helius-Credits für die Neubewertung, vorher Budget prüfen) und CR5-7 (Ausnahme für 4DOV absichern). CR5-7 vorher klären, welche 4DOV-Zahl gilt.
3. CR4-2/CR4-3: häufigster gemessener Fund (jeder achte Kauf), Wirkung aber unklar. Behebung ändert die Copy-Ergebnisse rückwirkend nicht, aber vergleichbar machen kann die Auswertung.

**Nie / nur wenn nebenbei billig (zu selten):** CR4-1 (1 von 4.377), CR3-6 (0 Fälle in den Logs), CR4-12 (kein Kurs-0-Fall bei Schatten, die 8 Fälle sind echte Überweisungen). CR4-5/CR4-9 erst, wenn eine einfache Spur (Zähler in der Endmeldung) zeigt, dass es oft vorkommt.

## Grenzen der Auswertung

- Logs: Für 27 Hauptbot- und 27 Copy-Läufe war kein Log abrufbar. Alle Aussagen „kommt in den Logs nicht vor“ gelten nur für die übrigen Läufe (73 Hauptbot, 44 Copy, 44 Scout).
- CR3-5: Die Trennung nach Ausfallgrund ist eine Näherung (2-Minuten-Fenster vor dem Kauf).
- CR4-2: Der Risikobetrag ist der vorgemerkte Anteil mal Einsatz des Nachkaufs, nicht der tatsächliche Verlust.
- Ergebnisse „roh“ sind die `pnl_sol`-Werte aus den Journalen; „mit Kosten“ zieht pauschal 0,004 SOL je Trade ab (bei Copy ebenso je geschlossener Position, nur als grobe Näherung; die Copy-Zeilen enthalten die Netzwerkgebühren bereits).
