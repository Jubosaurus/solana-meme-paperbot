# Code-Review des Bestands (08.10.2026)

**Stand:** Hauptzweig am 08.10.2026, nach `git pull`. **Geprüft von Codex (Sol)** in 6 von 7 Karten, danach Nachprüfung durch Claude. **Es wurde nichts am Bestand geändert und nichts behoben.** Es gab vorher keinen Code-Review in `auswertungen/`.
Rohdaten (nicht im Repository): `C:\Users\admin\paperbot-daten\code_review_2026-10-08\` (Karten, Berichte, Nachweis-Tests, Logs).

**Karte 7 (Testlücken) ist noch offen:** Der Lauf wurde am 08.10. vom System wegen Speichermangels beendet, ein Bericht liegt nicht vor. Sie wird nachgetragen.

## 1. Zusammenfassung

| | Karte 1 | 2 | 3 | 4 | 5 | 6 | zusammen |
|---|---|---|---|---|---|---|---|
| Hoch (Codex) | 1 | 4 | 7 | 12 | 8 | 3 | **35** (31 verschiedene, 4 Doppelungen) |
| Mittel (Codex) | 3 | 3 | 4 | 6 | 5 | 3 | 24 |
| Niedrig (Codex) | 1 | 0 | 2 | 0 | 1 | 1 | 5 |

Doppelungen bei den hohen Funden: CR2-4 = CR3-2 (Konto überzogen), CR2-3 = CR3-3 (Konto-Datei ohne `bankroll_sol` wird zu neuem Konto), CR2-1 ≈ CR3-1 (Journal und Portfolio laufen auseinander), CR5-6 = CR6-2 (Prüfliste geht beim Sichern verloren).

**Nachprüfung durch Claude (nur hohe Funde):**
- Alle 41 Nachweis-Tests der Karten 1–6 (`review_tmp/`) selbst ausgeführt: alle rot wie vorgesehen, die 2 Kontrolltests grün. Ein roter Test zeigt, dass das beschriebene Verhalten bei den künstlichen Eingaben auftritt; er sagt nicht, wie oft der Fall in den echten Daten vorkommt.
- Zusätzlich am Code gelesen: CR1-1, CR2-1, CR2-2, CR2-3, CR2-4, CR3-3, CR3-4, CR3-5, CR4-1, CR4-2, CR4-12 (alle bestätigt). Die übrigen hohen Funde: nur Testlauf, nicht im Code gelesen.
- An den echten Daten geprüft (DuckDB, nur Zählungen): siehe Abschnitt 2.
- **Ergebnis: 35 bestätigt, 0 falsch, 0 unklar.** Offen bleibt bei fast allen die Häufigkeit in den echten Daten.
- **Falschmeldungen** gab es unter den hohen Funden keine; die von Codex selbst verworfenen Verdachtsfälle stehen in Abschnitt 6.

## 2. Betrifft der Fund die Zahlen für den Strategie-Review?

Alle 35 hohen Funde haben von Codex den Vermerk „Zahlenbezug: ja“. Gewichtet nach tatsächlicher Wirkung (Claude):

| Fund | Kennzahl | Größe / eigener Befund |
|---|---|---|
| CR1-1 | Urteil gegen Kontrollgruppe (beendete Experimente) | Vergleichszeitraum hat kein Ende. Betrifft `ohne_limit`, `endspurt_ohne_filter`, `offene_tuer`; laufende Experimente nicht. Im Test dreht „besser“ auf „schlechter“. |
| CR2-1, CR3-1 | Tradezahl, Kontowert | Nur nach Absturz mitten in der Buchung. **Echte Daten: 0 Fälle** (in allen 12 Konten gleich viele KAUF- und VERKAUF-Zeilen wie abgeschlossene Trades, keine doppelten Zeilen). |
| CR2-2 | Kontowert, Ergebnis je Trade | Nur Verkäufe unter 0,0015 SOL. **Echte Daten: 2 von 2.579 Verkäufen**, höchstens 0,003 SOL. Vernachlässigbar. |
| CR2-3, CR3-3 | Kontostand | Nur bei gültiger, aber unvollständiger Konto-Datei. **Heute: alle 13 Konten vollständig.** Kein Einfluss auf heutige Zahlen. |
| CR2-4, CR3-2 | Positionszahl, Einsatz | Nur bei Guthaben unter etwa 0,4 SOL. Heutiger niedrigster Stand: `offene_tuer` 0,60 SOL (beendet). In der Vergangenheit nicht geprüft. |
| CR3-4, CR3-6 | Filter der Hauptstrategie (Bundle, Transfergebühr) | Ausfall oder Teilantwort gilt als „bestanden“. **Häufigkeit unbekannt.** |
| CR3-5 | Zusammensetzung `heisse_coins` | Kauft bei jedem Ausfall der Bundle-Prüfung, nicht nur bei „zu vielen Transaktionen“. Experiment: 179 Trades, Konto 4,08 SOL. Anteil Ausfälle unbekannt. |
| CR3-7 | Tradezahl, Kontostand | Nur wenn der Start-Abgleich mit GitHub scheitert. Häufigkeit unbekannt. |
| CR3-9 (mittel) | Vergleich Hauptstrategie gegen `notbremse_25` und `drittel_leiter` | Beide Experimente kaufen 2–4 s später, zu einem anderen Kurs. Verzerrt den Vergleich bei Kursbewegung (Größenordnung 0,02 SOL je 10 % Bewegung und Trade). |
| CR4-1 bis CR4-12 | Copy-Ergebnis je Trader, Schatten-Ergebnis, Verzögerung | Je Ereignis 0,01 bis 0,5 SOL. Am ehesten systematisch: CR4-6, CR4-9 (Lücken beim Nachholen), CR4-12 (Schatten −100 % bei fehlendem Kurs). **Häufigkeit nicht gemessen.** Echte Positionen sind bei CR4-12 durch die Jupiter-Quote geschützt (nur Schatten betroffen). |
| CR5-1 bis CR5-4 | Wallet-Bewertung des Scouts | Verzerrt die Auswahl, nicht die Handelsergebnisse. Im Test bis +30 SOL zu hoch. |
| CR5-5 bis CR5-8, CR6-2 | Wallet-Liste, Prüfliste, Tageslimit | Betrifft Auswahl und Datenbasis, keine Kennzahl der Handelsergebnisse. |
| CR6-1 | Listing-Welle: `anstieg_3h_pct`, `anstieg_3d_pct` | Im Test 50 Prozentpunkte zu hoch (Kerzenende statt Kerzenbeginn). Beobachtung, keine Kaufregel. |
| CR6-3 | Alle Datenreihen | Push-Konflikt wird als Erfolg gemeldet; Daten seit der letzten erfolgreichen Sicherung können fehlen. Häufigkeit unbekannt. |

**Einschätzung (Claude):**
- **Hauptstrategie und Experimente:** Der Strategie-Review kann mit den heutigen Zahlen starten. Journal und Konten stimmen überein, die nachgewiesenen Rechenfehler sind klein. Vorbehalte: (1) beendete Experimente bis zu ihrem eigenen Enddatum vergleichen, nicht mit dem heutigen Dashboard-Urteil; (2) `heisse_coins` nur mit Vorbehalt; (3) `notbremse_25` und `drittel_leiter` nur mit Vorbehalt wegen der späteren Käufe.
- **Copy-Trading:** Vor einem Urteil zuerst messen, wie oft die Fälle aus Karte 4 in `copy/journal.csv` vorkommen (reine Auswertung, keine Änderung).
- **Beheben:** Nichts muss vor dem Review behoben werden. Bot-Logik wird nur mit Zustimmung des Betreibers angefasst (siehe Abschnitt 7).

## 3. Hohe Funde (Codex), kurz

Vollständige Texte mit Zeilen, Belegen und Vorschlägen: Berichte in `paperbot-daten/code_review_2026-10-08/ergebnis/`. Nachprüfung: **T** = Test ausgeführt und rot, **C** = zusätzlich am Code gelesen, **D** = zusätzlich an echten Daten geprüft.

### Karte 1 (`dashboard/rechnung.py`)
- **CR1-1** (T, C): `rechnung.py:259`, Kontrollgruppen-Zeitraum endet nie; spätere Kontrolltrades ändern das Urteil beendeter Experimente.

### Karte 2 (`bot.py` Verkauf/Experimente)
- **CR2-1** (T, C, D): `bot.py:1835`, Verkauf wird sofort ins Journal geschrieben, das Portfolio erst am Ende; nach Fehler oder Abbruch wird doppelt verkauft.
- **CR2-2** (T, C, D): `bot.py:1830`, bei Erlös unter der Gebühr wird die volle Gebühr eingetragen, aber nur 0 gutgeschrieben statt eines negativen Betrags.
- **CR2-3** (T, C, D): `bot.py:2223`, Experiment-Datei ohne `bankroll_sol` wird durch neues 10-SOL-Konto ersetzt.
- **CR2-4** (T, C): `bot.py:1760`, mehrere Käufe in einer Serie können das Konto überziehen (Test: −0,153 SOL).

### Karte 3 (`bot.py` Kauf/Filter)
- **CR3-1** (T): `bot.py:1781`, Kauf steht im Journal, aber nicht im Portfolio (Absturz, SIGTERM). Gleiche Ursache wie CR2-1.
- **CR3-2** (T, C): `bot.py:2074`, Guthaben nur vor der Kaufserie geprüft. Wie CR2-4.
- **CR3-3** (T, C): `bot.py:1249`, gültiges JSON ohne `bankroll_sol` oder falscher Typ ergibt neues Konto. Wie CR2-3.
- **CR3-4** (T, C): `bot.py:1204`, fehlende Block-0-Transaktionen gelten als vollständige Prüfung; Teilergebnis bleibt im Cache.
- **CR3-5** (T, C): `bot.py:1205`, jeder Ausfall des Bundle-Checks heißt „BUNDLE_CHECK_NICHT_MOEGLICH“; `heisse_coins` kauft dann.
- **CR3-6** (T): `bot.py:1236`, Ausfall der Transfergebühren-Prüfung gilt als bestanden.
- **CR3-7** (T): `bot.py:2957`, nach fehlgeschlagenem Start-Abgleich wird trotzdem gehandelt.

### Karte 4 (`copy_bot.py`)
- **CR4-1** (T, C): `:1013`, Alter des Trader-Kaufs wird vor der Jupiter-Quote geprüft, danach nicht mehr; Kauf nach über 60 s möglich.
- **CR4-2** (T, C): `:528`, vorgemerkter Verkaufsanteil wirkt rückwirkend auch auf Nachkäufe.
- **CR4-3** (T): `:712`, gleiche Wirkung bei Schatten-Nachkäufen.
- **CR4-4** (T): `:876`, Bestandsabgleich verwirft bereits vorgemerkte Teilverkäufe.
- **CR4-5** (T): `:995`, Signatur wird vor dem Abruf als gesehen markiert; fehlgeschlagener Abruf wird nie nachgeholt.
- **CR4-6** (T): `:1196`, frühe WebSocket-Meldungen laufen vor älteren verpassten Trades (Reihenfolge).
- **CR4-7** (T): `:1344`, Überweisungen bei reinen Schattenpositionen werden ignoriert.
- **CR4-8** (T): `:797`, nachgeholter Verkauf nutzt die Gebühr des vorherigen Trades.
- **CR4-9** (T): `:770`, RPC-Ausfall beim Nachholen wird als lückenlos gespeichert.
- **CR4-10** (T): `:862`, alter Ausstieg vor dem relevanten Kauf schließt die neue Position.
- **CR4-11** (T): `:380`, Tokenkonto-Miete verhindert die USDC-Erkennung.
- **CR4-12** (T, C): `:939`, fehlender `usdPrice` zählt als Preis 0 und schließt Schattenpositionen mit −100 %.

### Karte 5 (`scout_bot.py`)
- **CR5-1** (T): `:318`, Verkäufe älterer Bestände werden neuen Käufen desselben Coins zugerechnet.
- **CR5-2** (T): `:310`, überwiesene Token zählen weiter als gehalten.
- **CR5-3** (T): `:322`, nach Verkauf von mindestens 90 % wird der Rest mit 0 bewertet.
- **CR5-4** (T): `:309`, nicht abrufbare Transaktionen werden still übersprungen, die Bewertung bleibt gespeichert.
- **CR5-5** (T): `:401`, CSV-Erweiterung macht längere historische Zeilen unlesbar (Inhalt bleibt physisch vorhanden).
- **CR5-6** (T): `:430`, Scout-Push überschreibt parallel ergänzte Prüfliste.
- **CR5-7** (T): `:786`, beschlossene Ausnahme für 4DOV ist nicht gegen Ersetzung wegen Verlust geschützt.
- **CR5-8** (T): `:1027`, Tageslimit der Wallet-Änderungen wird nach Abbruch vergessen.

### Karte 6 (Workflows, `listings.py`)
- **CR6-1** (T): `listings.py:413`, Vorlauf nutzt Schlusskurs von Kerzen, die erst nach dem Ereignis enden.
- **CR6-2** (T): `scout_runner.yml:70`, wie CR5-6 im Workflow.
- **CR6-3** (T): `bot_runner.yml:77`, `copy_runner.yml:68`, `scout_runner.yml:74`, letzte Sicherung endet trotz Push-Fehler „erfolgreich“.

## 4. Funde von Codex: Mittel und Niedrig (unverändert übernommen, nicht nachgeprüft)

### Karte 1: dashboard/rechnung.py

**Mittel**

Kontrolliert wurden Korrekturzuordnung sowie die Behandlung fehlender Zeitangaben und unlesbarer Kontodaten; diese Funde wurden ausschließlich anhand des Codes bewertet.

**CR1-2 — [dashboard/rechnung.py:390](C:/Users/admin/paperbot-codex/dashboard/rechnung.py:390): Korrekturen schließen gültige Vergleichspositionen aus.**

Die Ausschlussmenge enthält nur Trader und Mint. Zeile 444 entfernt dadurch sämtliche abgeschlossenen Positionen dieser Kombination, unabhängig von Runde oder Zeitpunkt. Außerdem wird `doppelt_geschlossen` ausgeschlossen, obwohl bei 922M/MODEL die zweite Schließung ausdrücklich gültig bleibt.

**Beleg:** `auswertungen/korrekturen.md:48` verlangt die betroffene Runde; Zeilen 54–55 verlangen bei MODEL ausschließlich das Entfernen der ersten Journalzeile.

**Vorschlag:** Korrekturarten unterscheiden und den Vergleichsausschluss auf die tatsächlich betroffene Position begrenzen.

**Zahlenbezug: ja.** Vergleichsanzahl und Mediane „wir gegen Trader“: eine gültige MODEL-Position sowie gegebenenfalls weitere Wiederkäufe fehlen. Richtung der Medianverschiebung abhängig von deren Ergebnissen; Kontowert und Gesamtergebnis bleiben hiervon unberührt.

**CR1-3 — [dashboard/rechnung.py:261](C:/Users/admin/paperbot-codex/dashboard/rechnung.py:261): Undatierte Trades zählen im Vergleichszeitraum mit.**

Ein fehlendes oder unlesbares `closed_at` wird durch `beginn` ersetzt. Der Trade besteht dadurch immer den Zeitfilter – auch wenn seine zeitliche Zugehörigkeit unbekannt ist.

**Beleg:** Beide Filter verwenden `(zeitpunkt(c.get("closed_at")) or beginn) >= beginn`.

**Vorschlag:** Undatierte Trades gesondert als Datenlücke ausweisen und aus zeitgebundenen Vergleichen ausschließen.

**Zahlenbezug: ja.** Trade-Anzahl, Mittelwerte, Top-3-Bereinigung und Urteil; jeder undatierte Trade erhöht die Anzahl um eins und kann die 200er-Grenze vorzeitig erreichen. Ergebnisrichtung beliebig.

**CR1-4 — [dashboard/rechnung.py:250](C:/Users/admin/paperbot-codex/dashboard/rechnung.py:250): Unlesbare Portfolios erscheinen als frische 10-SOL-Konten.**

`lade_json` ersetzt Lesefehler oder ungültiges JSON durch `{}`. `konto_strategie` setzt anschließend das fehlende Guthaben auf `START_SOL`; der Ladefehler geht verloren.

**Beleg:** Fehlerbehandlung in Zeilen 60–65, Standardguthaben in Zeile 235.

**Vorschlag:** Ladefehler erhalten und Kennzahlen als nicht verfügbar kennzeichnen; Startguthaben nur für ausdrücklich neue Konten verwenden.

**Zahlenbezug: ja.** Kontowert und Rundenergebnis werden auf **10 SOL beziehungsweise 0 SOL** gesetzt. Abweichung entspricht dem Unterschied zum tatsächlichen Kontowert und kann Verluste vollständig verdecken.

**Niedrig**

Kontrolliert wurden Grenzfälle der Urteilsbeschriftung.

**CR1-5 — [dashboard/rechnung.py:283](C:/Users/admin/paperbot-codex/dashboard/rechnung.py:283): Gleichstand wird als „schlechter“ bezeichnet.**

Bei identischen Durchschnittswerten mit und ohne Top 3 sind beide strikten Größer-Vergleiche falsch; daraus entsteht das Urteil „schlechter“.

**Beleg:** Zeilen 275–276 und Bedingung `not besser and not besser_ohne`.

**Vorschlag:** Gleichstand ausdrücklich behandeln.

**Zahlenbezug: ja.** Die Zahlen bleiben korrekt, aber eine Differenz von **0 SOL je Trade** erhält eine negative Bewertung.

### Karte 2: bot.py Verkauf und Experimente

**Mittel**

Rundungen, Graduation-Merkmale und die Wiederherstellung des Experiment-Kontexts wurden am Code geprüft, ohne zusätzliche Nachweistests.

**CR2-5 – Quotierte und abgebuchte Tokenmenge unterscheiden sich**  
**[bot.py:1819](C:/Users/admin/paperbot-codex/bot.py:1819)**, außerdem Zeilen 1826 und 1831.

- **Was passiert:** Die Quote verwendet eine abgerundete Ganzzahlmenge, abgebucht wird der ungerundete Anteil. Bei `raw == 0` kann die Notlösung trotzdem einen Erlös für einen nicht handelbaren Bruchteil erzeugen.
- **Beleg:** Ein Token mit `decimals == 0`, davon die Hälfte: `raw` wird null, während 0,5 Token abgebucht und gegebenenfalls zum Kurs × 0,95 vergütet werden.
- **Vorschlag:** Bestände in kleinsten ganzzahligen Einheiten führen; ausschließlich die quotierte Menge abbuchen und Teilverkäufe mit Menge null auslassen.
- **Zahlenbezug:** **Ja:** Restbestand und Erlös; normalerweise sehr kleine Rundungsverluste, bei wenigen unteilbaren Token potenziell erhebliche fiktive Erlöse. Richtung: Bestand zu niedrig, Erlös bei Nullmengen künstlich positiv.

**CR2-6 – Endspurt-Graduationen erhalten ein falsches gespeichertes Merkmal**  
**[bot.py:1947](C:/Users/admin/paperbot-codex/bot.py:1947)**, außerdem Zeilen 1851 und 1974–1975.

- **Was passiert:** Endspurt schließt bei Graduation vor dem allgemeinen Graduation-Block. Dieser setzt erst später `graduated_during`; im abgeschlossenen Trade bleibt `graduated_waehrend` deshalb falsch.
- **Beleg:** Der Verkaufsgrund lautet `GRADUIERT`, während `close_position` für das Merkmal standardmäßig `False` speichert.
- **Vorschlag:** Die beobachtete Graduation vor dem Endspurt-Ausstieg im Positionsmerkmal festhalten.
- **Zahlenbezug:** **Ja:** Eine aus diesem Feld berechnete Graduation-Quote unterschätzt die tatsächliche Quote bis auf null. SOL-Ergebnisse bleiben davon unberührt; der Verkaufsgrund ermöglicht eine Gegenrechnung.

**CR2-7 – Fehler beim Öffnen eines Experiment-Kontexts lassen die Statistik umgeschaltet**  
**[bot.py:305](C:/Users/admin/paperbot-codex/bot.py:305)**, außerdem Zeilen 307 und 312–317.

- **Was passiert:** `STATS` wird vor `os.makedirs` umgeschaltet. Schlägt die Verzeichniserstellung fehl, wird der schützende `try/finally`-Block nicht erreicht.
- **Beleg:** Die Rücksetzung liegt ausschließlich im späteren `finally`; der Fehlerfang in `load_experiments` stellt die globale Statistik nicht wieder her.
- **Vorschlag:** Sämtliche Schritte nach der ersten Kontextänderung in den Rücksetzungsblock aufnehmen.
- **Zahlenbezug:** **Ja:** Schichtstatistiken zu Käufen, Verkäufen, Ergebnissen und Abrufen können dem falschen Konto zugeschrieben werden; Umfang bis zu den nachfolgenden Schichtaktionen, Richtung kontenabhängig. Gespeicherte Trade-PnLs werden dadurch allein nicht geändert.

**Niedrig**

Bei Abrufbudgets und Vereinfachungen wurde im abgegrenzten Bereich kein zusätzlicher belastbarer Fund festgestellt.

### Karte 3: bot.py Kauf, Filter, Schichtwechsel

**Mittel**

Kontrolliert wurden die Verarbeitung einzelner API-Antworten, Paar-Experimente und die Fehlerbehandlung bei Ablehnungen und Social-Links; die folgenden Funde wurden ausschließlich statisch geprüft.

**CR3-8 – Eine unbrauchbare Token-Antwort bricht den gesamten Scan ab**

- **bot.py:2086**, außerdem 714–738: `token_view()` wird ohne Schutz je Coin aufgerufen. Falsche Feldtypen oder nicht endliche Zahlen können beispielsweise bei `.get()` oder `int(as_float(...))` eine Ausnahme auslösen.
- **Beleg:** Die Ausnahme gelangt bis zur allgemeinen Loop-Behandlung bei 3013; alle weiteren Scan-Schritte fallen aus.
- **Vorschlag:** Token einzeln validieren und Fehler je Coin zählen; den Scan mit den übrigen Kandidaten fortsetzen.
- **Zahlenbezug: ja.** Betroffene Scans liefern keine Käufe, auch nicht für gültige Kandidaten. Bei wiederholt derselben fehlerhaften Antwort kann die Kaufstichprobe länger fehlen; Ergebnisrichtung offen.

**CR3-9 – Paar-Experimente erhalten andere Einstiegskurse**

- **bot.py:2208**, außerdem 2210 und 2309: Notbremse 25 und Drittel-Leiter rufen nach dem Hauptkauf erneut die vollständige Kaufquote ab.
- **Beleg:** Jeder Kauf benötigt zwei Quote-Abfragen bei 1726/1736. Der Jupiter-Takt von 1,1 Sekunden erzeugt bereits ohne Antwortlaufzeiten ungefähr **2,2 beziehungsweise 4,4 Sekunden Abstand** zur ersten Kaufquote.
- **Vorschlag:** Für diese Paar-Experimente denselben Kaufzeitpunkt und dieselbe Einstiegsquote übernehmen.
- **Zahlenbezug: ja.** Der Vergleich enthält neben den Verkaufsregeln unterschiedliche Einstiegskurse. Eine Preisbewegung von 10 % verursacht beim gleichen Einsatz einen Effekt in der Größenordnung von **0,02 SOL**; Richtung abhängig vom Kursverlauf. Zusätzlich entstehen vier Quote-Abfragen je vollständigem Dreierpaar.

**CR3-10 – Fehlgeschriebene Ablehnung wird eine Stunde unterdrückt**

- **bot.py:1655**, außerdem 1660: Der Wiederholungsschutz wird vor dem erfolgreichen CSV-Schreiben gesetzt. Scheitert das Schreiben, werden weitere Versuche für denselben Coin und Grund eine Stunde unterdrückt.
- **Beleg:** Die nächste Ablehnung kehrt bereits bei 1653 zurück; der Schreibfehler bricht zuvor den Scan ab.
- **Vorschlag:** Den Wiederholungsschutz erst nach erfolgreichem Schreiben setzen und Schreibfehler gezielt behandeln.
- **Zahlenbezug: ja.** Ablehnungszahlen in den Dateien werden zu niedrig; der Filter-Trichter ist unvollständig. Eine Ereigniszeile je betroffenem Coin/Grund fehlt bis zum nächsten zugelassenen Versuch.

**CR3-11 – Social-API-Fehler werden als fehlende Links gespeichert**

- **bot.py:2183**, nachgeschlagener Helfer 679–685: Eine HTTP-Fehlerantwort wird zu einer leeren Paarliste. Das daraus entstehende `False` wird für den Coin zwischengespeichert.
- **Beleg:** Der Cache unterscheidet fehlende Links nicht von HTTP 429/5xx und besitzt keine zeitliche Ablaufprüfung.
- **Vorschlag:** Fehlerantworten als unbekannt behandeln und später erneut prüfen; nur erfolgreiche Antworten als Link-Ergebnis speichern.
- **Zahlenbezug: ja.** Käufe werden bis zum Prozessneustart unnötig abgelehnt, `KEINE_STORY_LINKS` wird überschätzt. Anzahl und Ergebnisrichtung hängen von den betroffenen Coins ab.

**Niedrig**

Kontrolliert wurden unnötige Dateiarbeit und die vorhandene Testabdeckung wichtiger Kauf- und Sicherheitsregeln.

**CR3-12 – CSV-Prüfung liest unveränderte Dateien vollständig**

- **bot.py:1619**, außerdem 2958–2968: Auch bei bereits passender Kopfzeile wird zuerst die gesamte CSV in eine Liste geladen. Beim Start betrifft dies sämtliche Ablehnungsdateien und Journale.
- **Beleg:** Die Prüfung der Kopfzeile erfolgt erst nach `list(csv.reader(f))`.
- **Vorschlag:** Zuerst nur die Kopfzeile prüfen; eine erforderliche Erweiterung anschließend zeilenweise durchführen.
- **Zahlenbezug: nein, unmittelbar.** Unnötiger Speicherverbrauch und längere Startzeit; Umfang wurde nicht an großen Bestandsdateien gemessen.

**CR3-13 – Wichtige Fehlerfälle fehlen in den Bestandstests**

- **tests/test_bot_einstieg.py:129**, außerdem 189 und **tests/test_bot_experimente.py:243**: Die Tests decken vollständige Block-0-Antworten, vorhandene Transferwarnungen und syntaktisch kaputtes JSON ab.
- **Beleg:** In diesen Tests fehlen Teilantworten, Shield-Ausfall und strukturell ungültiges JSON; Unterbrechungsschutz während einer Buchung wird in `test_schicht.py` für den Copy-Bot geprüft.
- **Vorschlag:** Nach einer Korrektur die entsprechenden CR-3-Nachweise als dauerhafte Regressionstests übernehmen.
- **Zahlenbezug: nein, eigenständig.** Die Lücken lassen insbesondere CR3-1, CR3-3, CR3-4 und CR3-6 ungesichert.

### Karte 4: copy_bot.py

**Mittel**

Kontrolliert wurden Grenzwerte, Betriebskennzahlen, Aktualität gespeicherter Aktivität und Fehlerbehandlung innerhalb der Wartungsschleifen; folgende Funde wurden gemäß Auftrag nicht zusätzlich getestet.

- **CR4-13: Exakt 20 % können unter die Verkaufsschwelle fallen.**  
  **copy_bot.py:628**: `1 - behalten` kann bei 20 % rechnerisch `0.19999999999999996` ergeben und wird dann in Zeile 630 als kleiner als 0,20 behandelt. Die Bestandstests prüfen 23,5 %, nicht den exakten Grenzfall.  
  **Vorschlag:** Mengenvergleich oder eine kleine numerische Toleranz verwenden; Grenzfall ergänzen.  
  **Zahlenbezug: ja.** Verkaufszeitpunkt und Haltedauer; bei 0,2 SOL bleiben zunächst etwa **0,04 SOL zusätzlich gehalten**, Ergebnisrichtung kursabhängig.

- **CR4-14: Nachgeholte gemerkte Verkäufe werden doppelt gezählt.**  
  **copy_bot.py:1025**, außerdem Zeilen 633 und 650: Der Zähler steigt im Aufrufer und anschließend erneut bei gemerktem beziehungsweise verschobenem Verkauf.  
  **Vorschlag:** Den Zähler an einer Stelle erhöhen und Signalzahl von ausgeführten Verkäufen unterscheiden.  
  **Zahlenbezug: ja.** Kennzahl „Nachgeholt“ ist für diese Ereignisse **um Faktor zwei zu hoch**; direkte PnL-Buchung unverändert.

- **CR4-15: Helius-Hochrechnung bildet die tatsächlichen Abrufe nicht ab.**  
  **copy_bot.py:1409**, außerdem Zeilen 399–407, 770 und 827: Gezählt werden Live-Meldungen unter `fetched`; Wiederholungen, Nachholen, Bestandsabfragen und Kaufprüfungen fehlen. Umgekehrt kann eine bereits bekannte Signatur `fetched` erhöhen, ohne RPC-Abruf.  
  **Vorschlag:** Tatsächliche RPC-Versuche nach Methode zählen und daraus die Verbrauchsschätzung bilden.  
  **Zahlenbezug: ja.** Budget- und Monatshochrechnung, überwiegend zu niedrig; beispielsweise sind bereits **vier Abrufversuche statt eines** möglich. Gesamtabweichung nicht gemessen.

- **CR4-16: Ein defekter Coin beendet den Wartungsdurchlauf für weitere Coins.**  
  **copy_bot.py:839**, außerdem Zeilen 935 und 1043: Abgleich, Verlauf und Bereinigung haben keine Fehlergrenze je Position; abgefangen wird erst außerhalb des gesamten Durchlaufs.  
  **Beleg:** Ein fehlendes erforderliches Positionsfeld oder ungeeigneter Zahlenwert unterbricht die Schleife vor den folgenden Positionen.  
  **Vorschlag:** Je Position abfangen, Fehler zählen und die übrigen Positionen weiterbearbeiten.  
  **Zahlenbezug: ja.** Fehlende Verläufe, verspätete Verkäufe und Bereinigungen; abhängig von der Zahl nachfolgender Positionen, Ergebnisrichtung offen.

- **CR4-17: Historische Trades können die letzte Aktivität zurückdatieren.**  
  **copy_bot.py:1009**: `letzter_trade` wird direkt überschrieben; beim Journal-Laden wird dagegen korrekt das Maximum verwendet, Zeile 191. Nach aktuellen Live-Trades können ältere nachgeholte Trades den Wert zurücksetzen.  
  **Vorschlag:** Auch während der Verarbeitung den bisherigen und neuen Zeitstempel mit `max` zusammenführen.  
  **Zahlenbezug: ja.** Die gemessene Inaktivität kann um die Dauer der Lücke steigen und die **72-Stunden-Regel zu früh auslösen**; zukünftiger PnL-Effekt indirekt und unbestimmt.

- **CR4-18: Zu alte Live-Käufe fehlen im Journal.**  
  **copy_bot.py:1013**: Alte Käufe werden nur bei `nachgeholt=True` dokumentiert; alte Live-Käufe erhöhen ausschließlich den flüchtigen Zähler. Das widerspricht „Alles Ausgelassene steht … im Journal“ aus `STRATEGIE.md:93`.  
  **Vorschlag:** Auch alte Live-Käufe mit Signatur und Ablehnungsgrund journalisieren.  
  **Zahlenbezug: ja.** Ablehnungsquote und Verzögerungsstudien verlieren **eine Zeile je betroffenem Kauf**; journalbasierte Ausschlusszahlen fallen zu niedrig aus.

**Niedrig**

Kontrolliert wurden Kommentare, Konstanten und Vereinfachungsmöglichkeiten; keine zusätzlichen belastbaren niedrigen Funde.

### Karte 5: scout_bot.py, Wallet-Automatik

**Mittel**

Kontrolliert wurden Suchlauf, Fehlerbehandlung, Birdeye-Zähler und Schreiben der Wallet-Liste; diese Funde wurden ausschließlich anhand des Codes bewertet.

9. **CR5-9 — scout_bot.py:1122:** Kandidaten gelten schon vor Stufe 2 für sieben Tage als geprüft.  
   **Beleg:** Die Markierung erfolgt für alle Kandidaten, Stufe 2 verarbeitet bei Zeile 1131 höchstens 15; auch fehlgeschlagene Stufe-2-Prüfungen behalten die Markierung.  
   **Vorschlag:** Vollständig geprüfte und noch wartende Kandidaten getrennt speichern.  
   **Zahlenbezug: ja.** Bei 40 erfolgreichen Stufe-1-Kandidaten bleiben **25 ohne Bewertung** und sind zunächst ausgeschlossen. Bewertungshäufigkeit sinkt; Auswahl wird verzerrt, Gewinnrichtung unbestimmt.

10. **CR5-10 — scout_bot.py:142:** Ein einzelner beschädigter Gewinner-Coin kann den gesamten Scout-Lauf abbrechen.  
    **Beleg:** `peak_multiple=None` oder ein fehlendes `mint` erzeugt einen ungefangenen Fehler; der Aufruf von `search()` bei Zeile 1172 besitzt keinen äußeren Schutz.  
    **Vorschlag:** Einzelne Datensätze abfangen, Fehler zählen und fortfahren.  
    **Zahlenbezug: ja.** Ein Datensatz kann einen kompletten Suchlauf und dessen Kandidatenzahlen ausfallen lassen.

11. **CR5-11 — scout_bot.py:216:** Birdeye-Verbrauch wird erst am Laufende dauerhaft gespeichert.  
    **Beleg:** Der CU-Zähler wird zunächst nur im Arbeitsspeicher erhöht; `save_state()` folgt bei Zeile 1182. Ein vorheriger Abbruch verliert diese Erhöhungen.  
    **Vorschlag:** Verbrauch nach jeder Antwort absturzfest sichern.  
    **Zahlenbezug: ja, für den Betriebsvergleich.** Bis zu **210 gezählte CUs je regulärem Lauf** können vergessen werden. Verbrauch erscheint zu niedrig; die Monatsgrenze verliert bei wiederholten Abbrüchen ihre Wirkung.

12. **CR5-12 — scout_bot.py:864:** Die Wallet-Liste wird unmittelbar überschrieben.  
    **Beleg:** Öffnen mit `"w"` kürzt die Datei vor dem Schreiben; eine Unterbrechung kann eine leere oder unvollständige Liste hinterlassen.  
    **Vorschlag:** Temporäre Datei schreiben und atomar ersetzen, wie bei Status und Warteliste.  
    **Zahlenbezug: ja.** Im Schadensfall fehlen bis zu 30 aktive Wallets beim nächsten Copy-Start; neue Trades und Beobachtungen nehmen ab.

13. **CR5-13 — scout_bot.py:879–888:** Fehler bei `reset`, `checkout`, `add` und `commit` werden nicht geprüft.  
    **Beleg:** Nur `fetch` und `push` entscheiden über Erfolg. Ein fehlgeschlagener Commit mit anschließend erfolgreichem Push kann als erfolgreiche Änderung gemeldet werden.  
    **Vorschlag:** Jeden notwendigen Git-Schritt prüfen und nur nach bestätigter Sicherung Änderungen verbuchen.  
    **Zahlenbezug: ja.** Änderungsprotokoll und Tageszähler können bis zu drei tatsächlich nicht veröffentlichte Aufnahmen/Ersetzungen pro Lauf enthalten.

**Niedrig**

Kontrolliert wurden Rundungen an den Aufnahmegrenzen.

14. **CR5-14 — scout_bot.py:264, 348, 654:** Aufnahmeentscheidungen verwenden bereits gerundete Kennzahlen.  
    **Beleg:** Ein Kauf-Median von **0,0996 SOL** wird zu 0,100 SOL und erfüllt die 0,1-SOL-Grenze; 23,96 Stunden Inaktivität werden zu 24,0 und scheitern an „unter 24“.  
    **Vorschlag:** Entscheidungen mit ungerundeten Werten treffen, nur die Anzeige runden.  
    **Zahlenbezug: ja.** Kleine Grenzfälle beeinflussen die Auswahl: Kaufgröße bis etwa 0,5 % unter der Grenze, Aktivitätsabweichung bis etwa drei Minuten.

### Karte 6: Workflows, listings.py, Hooks, Tools

**Mittel**

Geprüft wurden Listing-Erkennung, Fehlerbehandlung fremder Antworten und der Commit-Schutz.

**CR6-4 — [listings.py:300](/C:/Users/admin/paperbot-codex/listings.py:300): Binance-Handelsstatus hängt vom ersten Paar ab.**

- **Was passiert:** Bei mehreren Paaren desselben neuen Basis-Assets entscheidet ausschließlich das erste Paar über `start`; weitere Paare werden wegen `base in bekannt` übersprungen.
- **Beleg:** Zeilen 302–309: Kommt zuerst ein Paar mit `BREAK`, bleibt `start=None`, selbst wenn ein weiteres Paar bereits `TRADING` meldet. Coinbase fasst dagegen alle Paare zusammen.
- **Vorschlag:** Binance-Paare ebenfalls je Basis-Asset zusammenfassen; bereits handelbar, sobald mindestens ein Paar `TRADING` meldet.
- **Zahlenbezug:** **Ja:** Listing-Trades und Haltedauer. Bei gemischten Statuswerten kann ein zusätzlicher Kauf über **0,2 SOL** entstehen und bis zur nächsten Statusprüfung gehalten werden; Gewinnrichtung offen.

**CR6-5 — [.claude/hooks/git_schutz.py:48](/C:/Users/admin/paperbot-codex/.claude/hooks/git_schutz.py:48): Commit mit ausdrücklichem Dateipfad umgeht den Datenschutz.**

- **Was passiert:** Der Hook kontrolliert gestagte Dateien, `commit -a` und vorgelagerte `git add`-Befehle. Ein Commit mit Dateipfad kann auch ungestagte Änderungen dieser Datei übernehmen.
- **Beleg:** Bei `git commit -- portfolio.json` berücksichtigt die Pfadermittlung in Zeilen 48–62 den Commit-Dateipfad nicht. Eine ungestagte Datenänderung bleibt damit ungeprüft.
- **Vorschlag:** Commit-Dateipfade einschließlich `--only` prüfen oder solche Formen bei geschützten Daten grundsätzlich blockieren; einen Hook-Test ergänzen.
- **Zahlenbezug:** **Ja, potenziell:** Veraltete Kontodaten können eingespielt werden. Größenordnung bis zum gesamten betroffenen Konto; Richtung abhängig vom überschriebenen Stand.

**CR6-6 — [listings.py:407](/C:/Users/admin/paperbot-codex/listings.py:407): Fehlerhafte Kerzen umgehen die zugesagte Rückgabe ohne Fehler.**

- **Was passiert:** `anstiege_aus_kerzen()` liegt außerhalb des `try`-Blocks von `kurs_vorlauf()`. Unbrauchbare Zahlenwerte oder Kerzenstrukturen können deshalb eine Ausnahme weiterreichen.
- **Beleg:** Zeilen 401–406 schützen Abruf und JSON-Zugriff; Zeile 413 konvertiert anschließend ungeschützt mit `float()`. Der aufrufende Listing-Kauf wird dann als Fehler abgebrochen.
- **Vorschlag:** Kerzenvalidierung und Berechnung in die Fehlerbehandlung aufnehmen; bei fehlendem Vorlauf `None` liefern.
- **Zahlenbezug:** **Ja:** Ein ansonsten zulässiger Listing-Kauf über **0,2 SOL** kann fehlen. Tradezahl sinkt; Gewinnrichtung offen.

Mittlere Funde wurden anhand des Codes gemeldet, ohne zusätzliche Nachweis-Tests.

**Niedrig**

Geprüft wurden die lokalen Hilfsskripte und ihre Ausgabeschranken.

**CR6-7 — [tools/foto.py:182](/C:/Users/admin/paperbot-codex/tools/foto.py:182): Neuer Datenordner fehlt in der Fotosperre.**

- **Was passiert:** Die Liste geschützter Ausgabeordner enthält `abgelehnt/` nicht.
- **Beleg:** Ein Ausgabeordner `abgelehnt` passiert diese Prüfung; dort angelegte PNGs würden vom Hauptbot zusammen mit dem Datenordner gesichert.
- **Vorschlag:** `abgelehnt` in die Sperrliste aufnehmen.
- **Zahlenbezug:** **Nein:** Betrifft die Trennung von Daten und Hilfsartefakten.

## 5. Geprüft ohne Fund (Codex)

**Karte 1:** Ohne weiteren Fund geprüft wurden Kosten von 2 % beziehungsweise 4 %, Kostenabzug der aktuellen Strategierunde, Kontowert bei gleichem SOL-Kurs, Copy-Gesamtergebnis über alle Runden, vorsichtige Bewertung wartender Verkäufe, Journal-Korrekturschlüssel, Ausreißer und Exit-Liquidität; im Bereich entstehen keine zusätzlichen API-Abrufe.

**Tests:** 30 Rechnungstests bestanden. Gesamtlauf: **724 bestanden, 1 fehlgeschlagen, 5 Setup-Fehler** durch Windows-Zugriffsfehler beim Ersetzen einer Testdatei beziehungsweise beim Klonen lokaler Test-Repositories. Nachweis CR1-1: **2 erwartete Fehlschläge**. Kein Bestands-Diff.

Angelegte Dateien:

- [review_tmp/test_cr1_zeitraum.py](C:/Users/admin/paperbot-codex/review_tmp/test_cr1_zeitraum.py)
- [review_tmp/angelegte_dateien.txt](C:/Users/admin/paperbot-codex/review_tmp/angelegte_dateien.txt) — vollständige Liste aller 1.013 angelegten Dateien, einschließlich erzeugter Testdateien unter `pytest_dashboard/` und `pytest_bestand/`.

Die automatische Freigabeprüfung blockierte die Bereinigung der erzeugten Testordner mit „blocked by policy“. Diese bleiben unter `review_tmp/`.

**Karte 2:** - Hochstart beim Kaufpreis, Hochfortschreibung und die beiden Trailing-Stufen wurden gegen die Verkaufsregeln und Bestandstests kontrolliert.
- Reguläre Teilverkäufe, Gewinnschutz, Thesenprüfung, Liquiditätsbestätigung und Graduation-Liquiditätswechsel wurden kontrolliert.
- Endspurt-Fenster, Handelsfilter, Slippage-Grenze und Ausstiegsgründe wurden kontrolliert.
- Experiment-Guthabenprüfung, Rundenzuordnung abgeschlossener Trades und Auslaufen beendeter Experimente wurden kontrolliert.
- Die Kontrollgruppe speichert `next_pick` nach erfolgreichem Kauf und verwendet dieselben grundlegenden Buchungsfunktionen.

**Tests:** Ausgeführt wurde `python -B -m pytest review_tmp -q -p no:cacheprovider --tb=short`: **9 fehlgeschlagen, 1 bestanden**. Davon gehören **7 erwartete Fehlernachweise und 1 grüner Gegencheck zu CR-2**; zwei Fehler stammen aus der bereits vorhandenen CR-1-Datei. Die Nachweise laden echte Funktionen ohne Bot-Import und ersetzen sämtliche Datenzugriffe durch Arbeitsspeicher. Die drei genannten Bestandstestdateien wurden gelesen, nicht ausgeführt. Eine tatsächliche Betroffenheit historischer Trades wurde nicht ermittelt.

**Bestand:** `git diff --exit-code` blieb leer; keine Netzwerkzugriffe, Commits oder Pushes.

Angelegte `review_tmp/`-Dateien:

- [test_cr2_nachweise.py](C:/Users/admin/paperbot-codex/review_tmp/test_cr2_nachweise.py)

**Karte 3:** Ohne weiteren Fund geprüft wurden die normalen Schnellfilter einschließlich FOMO-Grenze und Reihenfolge, `follower_of` als reine Beobachtung, Namenswellen-Deduplizierung und Fehlerisolierung, atomarer Austausch einer einzelnen Portfolio-Datei, angehängte CSV-Spalten, Push-Fehlerprüfung und Handelsvormerkung, Jupiter-/Helius-/RugCheck-Taktung sowie der reguläre Solana-Tracker-Tageszähler.

Keine Bestandsdatei wurde geändert; keine Netzwerk-, Commit-, Push- oder Branch-Aktion wurde ausgeführt. Die Auswirkungen auf echte Ergebniszahlen wurden nicht vermessen.

**Angelegte `review_tmp/`-Dateien:**

- [review_tmp/test_cr3_nachweise.py](C:/Users/admin/paperbot-codex/review_tmp/test_cr3_nachweise.py)

**Karte 4:** Ohne zusätzlichen Fund kontrolliert wurden die getrennten Wallet-Konten, reguläre 0,2-SOL-Käufe ab 0,1 SOL, normale Preisabstandsprüfung, unveränderte Verkaufsregeln ohne Take-Profit/Stop-Loss, Flutschutzgrenzen, reguläre Gebührenzerlegung, vollständiger Journal-Signaturschutz und atomisches Speichern; Experiment- und Kontrollgruppenrechnungen werden in `copy_bot.py` nicht durchgeführt.

**Angelegte Dateien:**

- [review_tmp/conftest.py](C:/Users/admin/paperbot-codex/review_tmp/conftest.py)
- [review_tmp/test_cr4_bestand.py](C:/Users/admin/paperbot-codex/review_tmp/test_cr4_bestand.py)
- [review_tmp/test_cr4_nachweise.py](C:/Users/admin/paperbot-codex/review_tmp/test_cr4_nachweise.py)
- [review_tmp/cr4_dateien.txt](C:/Users/admin/paperbot-codex/review_tmp/cr4_dateien.txt) — vollständige Liste einschließlich künstlicher Testdateien.
- Testverzeichnisse: `review_tmp/pytest_cr4_12000/`, `review_tmp/pytest_cr4_13440/`, `review_tmp/pytest_cr4_19224/`, `review_tmp/pytest_cr4_7664/`.

**Karte 5:** Kontrolliert wurden GMGN-Pfadbeschränkung, Weiterleitungen, feste Fehlertexte ohne Zugangsdaten, Speicherung ausschließlich erlaubter Herkunftsangaben, Abbruch bei 429 beziehungsweise drei Fehlern, Quellenverteilung, Adress-/Namensprüfung, Wartelistenalter, Schonfrist sowie Schutz vor Stille-Entfernung bei veralteten Konten.

Die drei angeforderten Bestandstestdateien bestehen mit **131 grünen Tests**. Die acht CR-5-Nachweis-Tests sind **erwartungsgemäß rot**; ausgeführt unter `review_tmp/` mit gesperrtem Netzwerk und ersetzten Git-/Discord-Aufrufen. Tatsächliche Häufigkeiten in Produktionsdaten wurden nicht ermittelt. Projektcode und Daten außerhalb `review_tmp/` wurden nicht geändert.

**Abweichung vom Auftrag:** Die bereits vorhandene Hilfsdatei `review_tmp/conftest.py` wurde versehentlich überschrieben. Ihr ursprünglicher Inhalt ist nicht exakt rekonstruierbar; die gemeinsamen Test-Fixtures funktionieren wieder. Dies ist keine neu angelegte Datei.

Angelegte Dateien:

- [review_tmp/test_cr5_nachweise.py](C:/Users/admin/paperbot-codex/review_tmp/test_cr5_nachweise.py)
- [review_tmp/test_cr5_bestand.py](C:/Users/admin/paperbot-codex/review_tmp/test_cr5_bestand.py)
- [review_tmp/cr5_dateien.txt](C:/Users/admin/paperbot-codex/review_tmp/cr5_dateien.txt) — vollständige Einzelliste einschließlich künstlicher Testdateien unter `pytest_tmp/`, `pytest_cr5_nachweise/`, `pytest_cr5_bestand/` und `pytest_cr5_nachweise_2/`.

**Karte 6:** - Getrennte Bot-Gruppen, stündliche Sicherheitsnetze, Checkout von aktuellem `main` und Kettenstart nur außerhalb des Probemodus wurden ohne weiteren Fund kontrolliert.
- Action-Versionen, deklarierte Rechte, Secret-Referenzen und direkte Workflow-Ausgaben wurden ohne Fund eines ausgegebenen Secret-Werts geprüft.
- Schichtdauer von 5 h 45 min gegenüber 360 Minuten Workflow-Limit wurde ohne rechnerischen Widerspruch geprüft.
- GMGN-Pfadbegrenzung, Zeitlimits, Fehlerabbruch, Abfragetakt und ausschließliche Übernahme von Wallet-Adressen wurden ohne weiteren Fund geprüft.
- `requirements.txt`, Kontowert-Helfer und Logo-Erzeuger wurden ohne weiteren Fund geprüft.

**Tests:** `python -m pytest review_tmp -q` ausgeführt: **255 grün, 45 rot**, davon 39 bereits vorhandene Nachweise aus CR-1 bis CR-5. Der gezielte CR-6-Lauf ergab **55 grüne Bestandstests und sechs rote Nachweise** für CR6-1 bis CR6-3. Keine Bestandsdatei wurde geändert; kein Netzwerkzugriff und kein echter Git-Schreibbefehl wurden ausgeführt.

**Angelegte Dateien unter `review_tmp/`:**

- [test_cr6_nachweise.py](/C:/Users/admin/paperbot-codex/review_tmp/test_cr6_nachweise.py)
- [test_cr6_bestand.py](/C:/Users/admin/paperbot-codex/review_tmp/test_cr6_bestand.py)
- [cr6_dateien.txt](/C:/Users/admin/paperbot-codex/review_tmp/cr6_dateien.txt) — vollständige Liste aller 231 angelegten Dateien einschließlich künstlicher Testdaten unter `pytest_cr6/` und `pytest_cr6_fokus/`.

## 6. Falschmeldungen (von Codex selbst verworfen)

**Karte 1:**

Nachgeprüft und verworfen wurden folgende Verdachtsfälle:

- **Top 3 auf beiden Seiten entfernt:** Bereits dokumentierte Betreiberbewertungen verwenden dieses Verfahren (`STRATEGIE.md:235`); deshalb kein Regelfehler.
- **Kontrollgruppe unter 200 Trades:** Die Entscheidung zur Offenen Tür verwendet ausdrücklich 535 gegenüber 146 Trades; keine zweite Mindestzahl vorgeschrieben.
- **Alte Copy-Positionen im neuen Rundenkontowert:** Ausdrücklich beschlossen; entspricht `copy_bot.py` und dem vorhandenen Runden-Test.
- **Mehrfachzuordnung derselben Mint im Paarvergleich:** Reguläre Wiederkäufe liegen durch den 24-Stunden-Cooldown außerhalb des 600-Sekunden-Paarfensters.
- **Doppelter Verkaufsgebührenabzug:** Verkaufserlöse enthalten bereits den Gebührenabzug; die zusätzliche Subtraktion betrifft korrekt die Kaufgebühr.

**Karte 2:**

- **Verkaufsgebühren generell doppelt abgezogen:** Nicht bestätigt; reguläre Verkaufserlöse enthalten bereits die Verkaufsgebühr, und `close_position` zieht zusätzlich die Kaufgebühr ab – der grüne Gegencheck bestätigt Konto und PnL nach Teil- und Schlussverkauf.
- **Reset trotz offener Positionen erforderlich:** Kein Fehler; der Reset erst ohne offene Positionen und bei unzureichendem Kaufguthaben ist ausdrücklich dokumentiert.
- **Drittel-Leiter müsste bei einem Kurssprung alle Stufen sofort verkaufen:** Nicht als Fehler gewertet; eine Stufe je Durchlauf ist im bestehenden Test ausdrücklich festgeschrieben.
- **Kontrollgruppe müsste sämtliche Strategie- oder Endspurt-Filter übernehmen:** Kein Fehler; ihre abweichende Zufallsauswahl mit Sicherheits- und Altersprüfung ist beschlossen.
- **Notlösung ohne Verkaufsquote grundsätzlich unzulässig:** Kein Fehler; Kurs × 0,95 einschließlich Kennzeichnung ist dokumentiert.

**Karte 3:**

Kontrolliert und verworfen wurden Verdachtsfälle, die durch bestehende Entscheidungen oder vorhandene Schutzmechanismen erklärt werden.

- **Mehrfachzählung derselben Namenswellen-Coins:** Bei **bot.py:897/913** werden bereits zugeordnete Coins über alle Wellen ausgeschlossen; die Einschränkung überlappender Wellen ist ausdrücklich entschieden.
- **Doppelte Kandidaten aus mehreren Jupiter-Listen:** **bot.py:2082** führt sie nach Mint zusammen; ihre Herkunft wird gesammelt.
- **Unterschiedliche Ablehnungszahlen in Schichtmeldung und CSV:** **bot.py:1651/1653** zählt Prüfvorgänge, speichert aber höchstens einmal pro Stunde und Coin/Grund; dies ist im Bestandstest ausdrücklich festgeschrieben.
- **Fehlende zusätzliche Kostenbelastung im Bot:** Der Kostenaufschlag gehört laut `STRATEGIE.md:84` zur Bewertung; Bot-Rechnung und Verkaufsregeln sollen dadurch unverändert bleiben.
- **RugCheck-Ausfall allein blockiert keinen Kauf:** RugCheck ist die zusätzliche Meinung; entscheidend bleibt der eigene Block-0-Check.

**Karte 4:**

Kontrolliert wurden insbesondere vermeintliche Regelverstöße bei Rundenwechsel, Gebühren, Bereinigung und dem Gedächtnis gegen Doppelverarbeitung.

- **Rundenwechsel trotz offener Positionen:** ausdrücklich beschlossen; alte Rundennummern und Erlöse im neuen Konto sind vorgesehen.
- **Tokenkonto-Miete im Trader-Kaufbetrag:** ausdrücklich vorgesehen; CR4-11 betrifft die falsche Swap-Währung, nicht die Einbeziehung der Miete.
- **Bot-Gebühr wird uns belastet:** nicht bestätigt; `trade_fee` verwendet Grundgebühr, Prioritätsgebühr und Jito-Tip, nicht `other`.
- **Jupiter-Ausfall wird generell als wertloser echter Verkauf gebucht:** nicht bestätigt; `None` verschiebt Verkäufe. CR4-12 betrifft gesondert fehlende Preise bei Schattenpositionen.
- **Mehr als 60 Signaturen führen beim normalen Schichtwechsel zwangsläufig zu Doppelverkäufen:** nicht bestätigt; das vollständig geladene Journal ergänzt den Positionsspeicher durch `_done`.
- **Bereinigung muss ausschließlich Coins mit 99 % Kursverlust betreffen:** nicht bestätigt; beschlossen ist die Grenze für den verbleibenden Restwert.

**Karte 5:**

Kontrolliert und verworfen wurden Verdachtsfälle, die durch bestehende Entscheidungen oder Schutzmechanismen erklärt sind.

- **35 statt 25 Birdeye-CUs:** ausdrücklich beschlossene vorsichtige Zählung, kein Rechenfehler.
- **Stille-Entfernung trotz ausgeschöpftem Tageslimit:** ausdrücklich erlaubt; die Grenze von zwei Entfernungen je Lauf bleibt erhalten.
- **Schonfrist schützt nicht vor Bot/Stille:** entspricht der beschlossenen Regel.
- **GMGN-Markierungen werden nicht gespeichert oder als Scout-Urteil übernommen:** erlaubt ist die Adressquelle mit anschließender eigener Bewertung.
- **`SCORING_VERSION` bleibt für die neue Kennzahl schneller Verkäufe unverändert:** diese Kennzahl verändert keine Bewertung.
- **Fehlender Jupiter-Kurs ergibt Restwert null:** ausdrücklich vorgesehene vorsichtige Behandlung; davon getrennt ist CR5-3.

**Karte 6:**

Kontrolliert wurden insbesondere vermeintliche Parallelitätsfehler und Abweichungen von ausdrücklich beschlossenen Regeln.

- **Zwei gleichzeitige Schichten desselben Bots:** Nicht bestätigt; feste Parallelitätsgruppen und `cancel-in-progress: false` serialisieren die Läufe.
- **Hauptbot-Sicherung überschreibt generell Copy-Daten:** Nicht bestätigt; die Sicherungsblöcke übernehmen jeweils ihre eigenen Pfade, mit der beschriebenen Ausnahme fremd gepflegter Scout-Prüflisten.
- **Probe unterbricht die Kette:** In `CLAUDE.md` ausdrücklich dokumentiertes Verhalten; kein neuer Fehler.
- **Upbit/Bithumb handeln nicht anhand ihrer Marktlisten:** Bewusste Strategieentscheidung, kein Fehler.

## 7. Offen und Vorschlag

- **Karte 7 (Testlücken):** offen, wird nachgetragen. Codex hat dazu vor dem Abbruch Nachweis-Tests angelegt (`review_tmp/test_cr7_nachweise.py`, 7 Tests); eine Fundstelle daraus: in einem Bestandstest bleiben die Assertions grün, obwohl `pnl_sol` um eine Gebühr zu hoch ist. Nicht nachgeprüft.
- **Bot-Logik wird nicht angefasst**, bis der Betreiber entschieden hat. Vorschlag zur Reihenfolge, falls beheben gewünscht: (1) Häufigkeit in den echten Daten messen (Karte 4, CR3-4/5/6, CR6-3); (2) kleine, gut abgegrenzte Korrekturen mit Test: CR1-1 (nur Auswertung), CR2-4/CR3-2, CR2-3/CR3-3, CR3-5, CR6-3, CR4-9/CR4-5; (3) alles in Scout und Copy erst nach den Pflicht-Prüfungen (`code-pruefer`, Codex-Prüfung).
- **Grenzen dieser Nachprüfung:** Die Nachweis-Tests benutzen künstliche Daten. Häufigkeiten in den echten Daten wurden nur für CR2-1, CR2-2 und CR2-3 gemessen. Der Gesamt-Testlauf bei Codex (Karte 1: 724 bestanden, 1 fehlgeschlagen, 5 Setup-Fehler durch Windows-Dateizugriffe) wurde von Claude nicht wiederholt.
