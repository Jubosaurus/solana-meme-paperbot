# Backtest- und Datenplan (Aufgabe 8)

Stand 07.10.2026, ca. 20:45 UTC (22:45 deutsche Zeit). **Nur geprüft und geplant. Nichts gebaut, kein Konto angelegt, keine API-Abfrage.**

Arbeitsteilung: Recherche durch Codex (Sol) mit drei Auftragskarten. Die ausführlichen Berichte mit allen Quellen liegen daneben:
- `auswertungen/2026-10-07_datenquellen.md` – Bitquery, Dune, Helius, Flipside, Birdeye, Allium
- `auswertungen/2026-10-07_dexscreener_api.md` – DexScreener-Schnittstellen und Nutzungsbedingungen
- `auswertungen/2026-10-07_bitquery_abfragen.md` – fertige Abfrage-Entwürfe und Tag-0-Plan für Bitquery

Unsere eigenen Zahlen hat Claude per Skript gerechnet, der Daten-Prüfer hat sie nachgerechnet (`auswertungen/2026-10-07_backtest_plan_pruefung.md`; zwei kleine Korrekturen sind eingearbeitet).

---

## Kurzfassung

1. **Copy-Backtest geht, und zwar ohne neues Konto:** Die Käufe und Verkäufe des Traders kommen über Helius (unser vorhandener Parser `parse_trade` passt dafür). Den Preis „1,8 s später“ bekommen wir am besten aus unseren eigenen 4.090 echten Copy-Käufen. Dort kennen wir den Abstand zwischen dem Trader-Preis und unserem Preis. Dazu kommen später die Trades anderer Käufer in den nächsten 4–6 Slots (1 Slot ≈ 0,4 s). Kosten: etwa 300 bis 30.000 Helius-Credits je Wallet für 30 Tage, je nach Methode.
2. **Wichtigster Recherchefund: Die Bitquery-Testphase taugt kaum für Backtests.** Sie läuft 7 Tage mit nur 1.000 Punkten (≈ 200 Abfragen), **ohne Archiv**. Die nutzbaren Trades reichen nur etwa 12 h bis 7 Tage zurück. Laut Bedingungen sind Gratisdaten außerdem nur „für technische Entwicklung“ gedacht. **Dune** ist deutlich besser geeignet: 14 Tage, 2.500 Credits, Pump.fun-Trades fertig aufbereitet ab Januar 2024, CSV für die interne Nutzung ausdrücklich erlaubt. **Das entscheidest du** (du hattest Bitquery bevorzugt).
3. **Ein Teil lässt sich nie zurückrechnen:** Jupiters Kandidatenlisten (trend/traded/organic), der „organic“-Wert, Shield-Warnungen, RugCheck, Trending. Deshalb gilt: Ein Backtest der **Hauptstrategie** ist nur eine Näherung. **Gut zurückrechnen** lassen sich Endspurt, Bündel (Block 0), FOMO-Sprung, Verkaufsregeln und Dev-Starts.
4. **Dringend fürs Repo:** `abgelehnt.csv` wächst um ca. 2,2 MB/Tag. In etwa 12 Tagen (um den 19.10.) erreicht sie die GitHub-Warnschwelle von 50 MB, in etwa 35 Tagen (um den 11.11.) die **harte Grenze von 100 MB**. Ab dann schlägt jeder Push des Hauptbots fehl. Das ist der erste Punkt der Reihenfolge.
5. **Am meisten Daten pro Aufwand bringt:** (1) Repo entlasten, (2) junge abgelehnte Coins 6 h verfolgen (nur Jupiter, ca. 5.000–10.000 zusätzliche Abrufe/Tag, kein Helius). So entstehen eigene Daten zum Entscheidungszeitpunkt, die keine historische Quelle hat. (3) Copy-Backtest mit Helius. (4) Erst dann die Testphase für breite Coin-Backtests.

---

## 1. Copy-Backtest: eine Wallet 30 Tage nachspielen

**Ja, das geht.** So würde es ablaufen:

| Schritt | Woher | Bemerkung |
|---|---|---|
| Alle Trades des Traders, 30 Tage | Helius, Adress-Historie der Wallet | Mainnet-Verlauf laut Helius unbegrenzt. Unser `parse_trade` (copy_bot.py) erkennt Kauf/Verkauf, Menge, Gebühren schon heute, Tests vorhanden |
| Kauf ab 0,1 SOL → 0,2 SOL bei uns, auch Nachkäufe | eigene Regel | deterministisch, wie live |
| Preis „1,8 s später“ | siehe unten | der schwierige Teil |
| Preisgrenze ±15 % | Vergleich unser Preis gegen Trader-Preis | wie live; geblockte Käufe als Schatten zählen |
| Verkäufe gesammelt ab 20 % | Verkäufe des Traders | deterministisch, wie live |
| Kosten | `copy/messung.csv` und unser Aufschlag 2 % je Rundlauf | Median der Abweichung „sofort zu 2 s später“: Kauf 0,0 %, Mittel −0,26 % (858 Fälle); Verkauf Mittel +0,1 % (792) |
| Runden (neue 10 SOL, wenn kein Kauf mehr möglich) | eigene Regel | wie live |

### Woher kommt der Preis „1,8 s später“?

Unsere echte Verzögerung im Copy-Bot: **Median 1,6 s, p90 10,7 s** (4.090 Käufe). Drei Wege, vom einfachsten zum genauesten:

- **A – Unsere eigene Messung (sofort, kostenlos):** Bei 2.807 Käufen mit weniger als 2 s Verzögerung lag unser Preis im **Median 1,5 % über dem Trader** (10 % der Fälle unter −1,3 %, 10 % über +8,4 %). Verkäufe unter 2 s: Median −0,49 %. Diese Verteilung legen wir als Zuschlag auf jeden Trader-Preis (Ziehung aus der echten Verteilung, nicht nur der Median). Der Nachteil: Der Weg kennt den einzelnen Coin nicht. Ein Coin, der gerade explodiert, wird zu günstig gerechnet.
- **B – Trades anderer Käufer im selben Coin (genau, kostet Abrufe):** 1,8 s ≈ 4–5 Slots. Man lädt alle Trades des Coins in den Slots nach dem Trader-Kauf und nimmt den letzten Preis bis zum Zielzeitpunkt. Bei Pump.fun-Coins gehen alle Trades über das Konto der Bonding-Curve. Dessen Verlauf lässt sich bei Helius abfragen, mit einem Abruf je Trader-Kauf. Bei Dune geht es mit der Tabelle `dex_solana.trades` nach Slot. **Vorsicht:** Die Blockzeit hat nur ganze Sekunden, deshalb nach Slot und Reihenfolge rechnen, nicht nach Uhrzeit.
- **C – Kurvenrechnung (nur Pump.fun-Kurve):** Aus den Kurvenreserven nach den Trades bis Slot +5 den Preis für **unsere** 0,2 SOL ausrechnen. Unsere vSol-Rechnung (`curve_vsol`) ist durch echte Graduationen bestätigt. Das ist am genauesten, braucht aber Weg B als Grundlage.

**Empfehlung:** A sofort als erste Fassung. B für Stichproben, um A zu prüfen.

### Helius-Kosten je Wallet (30 Tage)

Rechnung aus dem Codex-Bericht (Creditpreise laut aktueller Helius-Doku, **Schätzung**):

| Methode | 100 Trades/Tag | 1.000 Trades/Tag |
|---|---|---|
| Signaturen + jede Transaktion einzeln (`getTransaction`, 1 Credit) | ≈ 3.000 | ≈ 30.000 |
| `getTransactionsForAddress` (bis 1.000 Transaktionen je Abruf, 10 Credits je 100) | ≈ 300 | ≈ 3.000 |
| Weg B zusätzlich: Markt-Trades je Trader-Kauf | + ≈ 10–20 je Kauf | dito |

**Unsicher:** Ob `getTransactionsForAddress` im Gratis-Tarif freigeschaltet ist, ist widersprüchlich belegt. Das lässt sich mit einem Probeabruf klären (etwa 10 Credits). Ältere Helius-Seiten nennen außerdem 10 statt 1 Credit für Archivabrufe. Dann wäre die erste Zeile 10-mal so teuer (30.000 bzw. 300.000).

### Gegenprobe mit unseren echten Ergebnissen

Bevor ein Backtest etwas zählt, muss er unsere Wirklichkeit nachbilden:
1. 3–5 Wallets wählen, die wir mindestens 7 Tage kopiert haben, darunter eine gute, eine schlechte und eine Vieltrader-Wallet.
2. Genau ihren Live-Zeitraum nachspielen.
3. Vergleichen mit `copy/journal.csv` und `copy/konten.json`: Anzahl Käufe, Anteil geblockter Käufe (live: 573 Schatten-Käufe gegenüber 4.090 Käufen), Ergebnis je Runde.
4. **Vorher festlegen, wann es „passt“:** Vorschlag: Käufe ±5 %, Ergebnis je Wallet innerhalb von ±10 % des Umsatzes.
5. **Bekannte Abweichung:** Live verpassen wir Käufe (1.017 „verpasst“ gegenüber 4.090 Käufen, vor allem 01.–03.10.). Der Backtest verpasst nichts. Deshalb beide Varianten rechnen: ohne Lücken und mit einer zufälligen Lückenquote wie live.

**Nutzen:** Scout-Kandidaten könnten vor der Aufnahme 30 Tage „probekopiert“ werden, statt 7 Tage Schonfrist live zu verbrauchen. Das ist eine **Idee für später**, keine Regeländerung.

---

## 2. Was lässt sich nur mit Blockchain-Daten zurückrechnen?

| Experiment / Filter | Zurückrechenbar? | Wie / warum nicht |
|---|---|---|
| **Endspurt** (95–108 vSol, ≥ 2.000 Trades, Verkauf bei Graduation) | **ja, gut** | vSol aus Kurven-Trades, Trade-Zahl zählen, Graduation aus Migrations-Ereignis |
| **Bündel / Block 0** (Tag 1) | **ja, gut** | Käufer im Erstellungs-Slot und ihr Anteil, später ihr Restbestand |
| **FOMO-Sprung** (Tag 17, +30 % in 5 min) | **ja, gut** | Preisreihe aus Trades |
| **Verkaufsregeln** (2x Hälfte, Abstand zum Hoch, Notbremse, Gewinnschutz, 24 h) | **ja**, bis auf „These gebrochen“ | Preis ja. „These gebrochen“ braucht Holder-Zahl und Netto-Verkäufer: Netto-Verkäufer ja, Holder nur angenähert (Bestände aus allen Trades und Überweisungen) |
| **Dev-Starts** (≤ 50 Coins), **Serien-Devs** (früherer Coin ≥ 300.000 $) | **ja** | Erstellungs-Tabelle: Coins je Ersteller; Höchstwert aus den Trades |
| **Dev-Bestand** (≤ 10 %) | **teilweise** | Käufe/Verkäufe des Erstellers ja. Überweisungen an Zweit-Wallets machen es unscharf, und Jupiters Wert ist anders berechnet |
| **Kontrollgruppe** (zufälliger junger Coin mit Sicherheitsprüfung) | **ja, mit Vorbehalt** | Wichtig ist die **Grundgesamtheit**: Live zieht der Bot nur aus Jupiters Listen. Im Backtest muss man sie nachbilden (z. B. die meistgehandelten Coins der letzten 5 min/1 h), sonst vergleicht man Äpfel mit Birnen |
| Holder +15 %/h, Netto-Käufer 5 min (Tag 5) | **teilweise** | Netto-Käufer aus Trades ja. Holder nur angenähert |
| Organische Käufer / `organicScore` | **nein** | Jupiter-eigene Bewertung, nicht öffentlich nachrechenbar. Allenfalls grob: bekannte Bot-Wallets herausfiltern |
| **Jupiter-Kandidatenlisten** (trend/traded/organic 5m/1h) | **nein** | Nur Näherung über „meistgehandelt“ |
| **Social-Links** (Tag 5) | **teilweise** | Pump.fun-Metadaten bei der Erstellung enthalten oft X/Telegram/Website (Stand Erstellung, also sauber). Später hinzugefügte DexScreener-Infos sind **nicht** sauber (sie liegen in der Zukunft) |
| **RugCheck**, Jupiter-Shield | **nein** | Nur der heutige Stand abrufbar |
| **DexScreener-Profil/Boost/Werbung** | **ja, teilweise** | `/orders/v1` liefert Zahlungszeitpunkte. Unsere Aufzeichnung nutzt das schon (`erste_zahlung_min_vor_ereignis`) |
| **Trending** (Jupiter, DexScreener-Metas) | **nein** | Keine Historie. Nur ab jetzt aufzeichnen |
| **Marktphase** (Tag 9/13) | **angenähert** | Zahl frischer Coins über 1 Mio. $ und deren Volumen aus Trades, zusätzlich `marktphase.json` seit Start |
| Vamp (Tag 12) | angenähert | Name aus der Erstellung, Holder angenähert |
| Zweite Welle, Notbremse 25, Drittel-Leiter | **nur so gut wie die Hauptstrategie-Näherung** | hängen an den Käufen der Hauptstrategie. Besser: mit unseren aufgezeichneten Verläufen rechnen (wie bisher) |
| Listing-Welle | nein (keine Blockchain-Frage) | Börsen-Listings |

**Folge:** Saubere Backtests sind möglich für **Endspurt, Bündel, FOMO, Verkaufsregeln, Dev-Regeln** und eine nachgebildete **Kontrollgruppe**. Für die **Hauptstrategie als Ganzes** bleibt der Live-Test das Urteil. Deshalb ist Punkt 5a (eigene Aufzeichnung) so wertvoll.

---

## 3. Datenquellen im Vergleich

Kurzfassung aus `2026-10-07_datenquellen.md` (Quellen dort, Stand 07.10.):

| Quelle | Gratis möglich | Konto | Verlauf | Pump.fun fertig | Speichern | Urteil |
|---|---|---|---|---|---|---|
| **Dune** | 14 Tage, 2.500 Credits insgesamt, danach nur ansehen | Benutzerkonto. „Keine Karte“ steht für Free in den Bedingungen, das Formular selbst ist **unsicher** | Solana komplett, Pump.fun-Modell ab 14.01.2024 | **ja** (`pumpdotfun_solana.trades`, `dex_solana.trades` mit Slot und Reihenfolge, PumpSwap) | CSV **intern ausdrücklich erlaubt**, gelegentliche Berichte mit Quellenangabe | **beste Wahl für eine Testphase** |
| Bitquery | 7 Tage, 1.000 Punkte (≈ 200 Abfragen), **kein Archiv** | E-Mail, Passwort, Name, **Firmenname**, Hinweis auf Firmen-E-Mail | Trades nur ca. 12 h bis 7 Tage, Wallet-Trades ca. 30 Tage | ja (Kurve, Erstellung, Migration) | Gratis nur „für technische Entwicklung“ | für Backtests zu kurz |
| Helius | haben wir (1 Mio. Credits/Monat) | vorhanden | Mainnet unbegrenzt | nein, Rohtransaktionen (unser Parser) | unklar. Neue Bedingungen (28.09.) sprechen von „lawful business purpose“, ob unser privates Projekt darunter fällt, ist **unsicher** | ideal für **Wallet-Verlauf**, zu teuer für den ganzen Markt |
| Birdeye | 30.000 CUs/Monat (haben wir) | vorhanden | unklar | teilweise | Bedingungen **verbieten Speichern** | für Backtest-Dateien ungeeignet |
| Allium | einmalig Guthaben | **nur Firmen-E-Mail** | ab Genesis | unklar | sehr eng | erfüllt die Vorgabe nicht |
| Flipside | nicht mehr belegbar | – | – | – | – | ausgeschieden |

**Empfehlung:** Das eine erlaubte Konto bei **Dune** statt bei Bitquery anlegen. Bei Bitquery bekäme man für 1.000 Punkte höchstens etwa 50 Coins mit vollem Datenpaket, und nur aus der letzten Woche. Dafür reicht unsere eigene Aufzeichnung fast schon. Bei Dune kann man **auf dem Server rechnen und nur kleine Ergebnistabellen exportieren** (2 Credits je MB Export). Ein Beispiel: eine Zeile je Coin mit den Merkmalen zum Entscheidungszeitpunkt und dem Ergebnis nach 1/6/24 h. Damit passen tausende Coins über mehrere Wochen ins Budget. **Unsicher:** wie viele Credits eine einzelne SQL-Abfrage kostet (nach Rechenaufwand, keine feste Formel). Deshalb am Tag 0 klein anfangen und den Credit-Deckel setzen.

**Abbruchregel für die Anmeldung (gilt für jeden Anbieter):** Fragt das Formular nach Karte, Wallet, Zahlung oder Abo, wird sofort abgebrochen. Es wird nichts gekauft. Bei Bitquery wäre zusätzlich ein Firmenname nötig.

**Daten nur lokal**, außerhalb des Repos, z. B. `C:\Users\admin\paperbot-daten\` (nicht im Projektordner, damit nichts versehentlich committet wird). Ins Repo kommen nur unsere eigenen Ergebnisse (Kennzahlen, Urteile), keine Anbieter-Rohdaten.

---

## 4. Methodik: damit der Backtest nicht lügt

1. **Nur Daten vom Entscheidungszeitpunkt.** Jedes Merkmal wird mit dem Stand „bis zur Kaufsekunde“ berechnet. Verboten sind zum Beispiel: heutige Holder-Zahl, später hinzugefügte Links, das Feld „graduiert“, der spätere Höchstwert.
2. **Tote Coins gehören dazu.** Die Grundgesamtheit kommt aus den **Erstellungs-Ereignissen**, nicht aus heutigen Listen. Wer nur Coins nimmt, die heute noch existieren, rechnet sich reich.
3. **Regeln vorher festlegen.** Jede Regel samt Schwelle wird mit Datum in eine Datei geschrieben, **bevor** die Daten ausgewertet werden (Vorschlag: `auswertungen/backtest_vorab.md`).
4. **An älteren Wochen finden, an neueren bestätigen.** Beispiel: Wochen 1–2 zum Suchen, Woche 3 nur **einmal** zum Bestätigen. Wer an Woche 3 nachbessert, braucht eine neue, unberührte Woche.
5. **Nicht zu viele Varianten an denselben Daten.** Jede getestete Variante kommt in ein **Testtagebuch**, auch die verworfenen. Wer 20 Varianten probiert, findet zufällig eine, die gut aussieht. Faustregel: höchstens 5 Varianten je Frage. Wer mehr testet, muss ein deutlich stärkeres Ergebnis verlangen.
6. **Unsere Testregeln gelten weiter:** mindestens 200 Trades, Vergleich mit der Kontrollgruppe aus demselben Zeitraum, das Ergebnis muss auch ohne die 3 besten Trades halten, roh **und** mit Kosten (2 %, Endspurt 4 %).
7. **Erst kalibrieren, dann glauben.** Der Backtest muss zuerst unsere echten Live-Ergebnisse im selben Zeitraum nachbilden (Copy: Abschnitt 1; Hauptbot: unsere `verlauf/`-Kurse gegen die Trades der Quelle). Klappt das nicht, zählt kein weiteres Ergebnis.
8. **Der Live-Test bleibt das letzte Urteil.** Ein guter Backtest macht eine Regel nur zum Kandidaten für ein neues Experiment.

---

## 5. Datenausbau im Live-Betrieb

### a) Wie viele Coins sieht der Bot, und was kostet es, alle 6 h zu verfolgen?

Aus `abgelehnt.csv` (01.–06.10.):
- **2.330–2.610 verschiedene Coins pro Tag** geprüft, 12.800–15.800 Prüfzeilen pro Tag.
- Davon wurden **89 % der Zeilen** mit „Story zu alt“ abgelehnt (Coin älter als 6 h). Nur **490–580 Coins pro Tag** sind junge Coins, die an einem anderen Filter scheiterten.
- Heute werden davon nur ca. 130–230 „knapp abgelehnte“ Coins pro Tag weiterverfolgt.

Rechnung für die Verfolgung über 6 h mit Jupiter (`/tokens/v2/search`, 100 Coins je Abruf, wie der Bot es schon macht). Annahmen: gleichmäßige Verteilung, ca. 100 Byte je Zeile.

| Umfang | gleichzeitig verfolgt | Takt | zusätzliche Jupiter-Abrufe/Tag | Zeilen/Tag | Datenmenge/Tag |
|---|---|---|---|---|---|
| alle ~2.500 Coins | ~625 | 60 s | ≈ 10.000 | ≈ 900.000 | ≈ 90 MB |
| alle ~2.500 Coins | ~625 | 120 s | ≈ 5.000 | ≈ 450.000 | ≈ 45 MB |
| **nur junge ~550 Coins** | ~140 | 60 s | ≈ 2.900 | ≈ 198.000 | ≈ 20 MB |
| **nur junge ~550 Coins** | ~140 | 120 s | ≈ 1.400 | ≈ 99.000 | ≈ 10 MB |

Zum Vergleich: Der Hauptbot macht heute etwa 1 Jupiter-Abruf je Sekunde (≈ 86.000/Tag). „Alle Coins, 60 s“ wären etwa +12 %. **Kein zusätzliches Helius.**

**Empfehlung:** nur die **jungen** Coins (die „zu alten“ sind für unsere Regeln ohnehin außerhalb), Takt 60 s in der ersten Stunde, danach 120 s. Gespeichert wird in einer eigenen Tagesdatei in kompaktem Format. **Erst nach Punkt b**, sonst wächst das Repo noch schneller.

### b) Repo-Größe: was wächst, und welche Möglichkeiten gibt es?

**Messung:**
- GitHub meldet **2,0 GB**, lokal ist `.git` 5,2 GB groß (lose, noch nicht gepackte Objekte; die 3,7 GB waren vermutlich ein früherer lokaler Stand).
- Am 06.10. gab es **2.389 Commits** (meist einer pro Minute je Bot).
- Jeder Commit speichert jede geänderte Datei **komplett neu**. Git packt das später als Unterschiede zusammen, aber die Rohmenge ist riesig: am 06.10. ca. **57.700 MB unkomprimiert**.

| Was | Roh am 06.10. | Grund |
|---|---|---|
| `copy/verlauf/` (Tagesdatei) | 17.400 MB | Tagesdatei bis 25 MB, ca. 1.400-mal neu gespeichert |
| `abgelehnt.csv` | 16.300 MB | **eine** 23-MB-Datei, ca. 800-mal neu gespeichert |
| `copy/` (Journal, Konten, Messung) | 12.100 MB | `copy/journal.csv` 15 MB, oft neu |
| `verlauf/` (Tagesdatei) | 7.000 MB | Tagesdatei bis 18 MB |
| `experimente/` | ca. 4.000 MB | darunter die beendeten Experimente `endspurt_ohne_filter` und `ohne_limit`, die noch täglich geschrieben werden (prüfen, ob nötig) |

**Harte Grenze:** GitHub lehnt Dateien über 100 MB ab. `abgelehnt.csv` (23,5 MB, +2,2 MB/Tag) erreicht die Warnschwelle von 50 MB um den **19.10.** und 100 MB um den **11.11.** `copy/journal.csv` (15 MB, ca. +0,5 MB/Tag) hat noch Monate Zeit.

**Möglichkeiten (ohne Datenverlust, ohne Kosten). Nur Optionen, nichts umgesetzt:**

| Option | Wirkung | Vorteile | Nachteile |
|---|---|---|---|
| **A. Seltener committen** (z. B. alle 5–10 min statt jede Minute) | Historie wächst 5–10× langsamer | sehr einfach, eine Zahl in jedem Bot | Dashboard bis zu 10 min älter. Bei einem harten Absturz fehlen bis zu 10 min Daten im Repo (die Bots speichern beim regulären Ende) |
| **B. Wachsende Dateien in Tages- oder Monatsdateien teilen** (`abgelehnt/2026-10-07.csv` wie `verlauf/`) | jeder Commit schreibt nur die kleine Tagesdatei; löst die 100-MB-Grenze dauerhaft | kein Datenverlust, gleiche Spalten | Leser anpassen (Dashboard, Tagesauswertung, Skripte). **`copy/journal.csv` ausgenommen** (Schutz gegen doppeltes Nachholen liest das ganze Journal); dort nur mit angepasstem Schutz |
| **C. Abgeschlossene Tage packen** (`verlauf/2026-10-01.csv` → `.csv.gz`) | Arbeitsordner 5–10× kleiner | Lesen mit pandas/DuckDB direkt möglich | ändert die alte Historie nicht. Leser müssen `.gz` kennen |
| **D. Eigener Daten-Branch** (Bots pushen Daten auf `daten`, Code bleibt auf `main`) | `main` bleibt klein und schnell | Codex-Worktree und Code-Klone schnell | gleiches Repo, also gleiche Gesamtgröße. Dashboard und Workflows umstellen |
| **E. Zweites Repo nur für Daten** | wie D, sauber getrennt | Code-Repo klein | braucht einen Zugangs-Token als Secret, Einrichtung aufwendiger |
| **F. Alte Historie zusammenfassen** (Neuschreiben der Historie, Dateiinhalte bleiben vollständig) | Repo schrumpft stark | einmalig große Wirkung | riskant: alle Klone (Bots, Dashboard, Codex-Worktree) müssen neu klonen. Bots müssen dafür pausieren. Nur mit großer Vorsicht |
| G. Git LFS | – | – | Gratis nur 1 GB Speicher/Monat, danach kostenpflichtig. **Nicht empfohlen** |

**Empfehlung:** **A + B** zuerst (geringes Risiko, B löst das 100-MB-Problem). C bei Bedarf. D/E/F erst, wenn das Repo trotzdem unhandlich wird. Das sind technische Änderungen an den Bots, sie gehen nur nach deiner Zustimmung.

### c) Helius-Reserve

- Stand 06.10. laut Dashboard: **145.870 Credits**, Zuwachs etwa **18.600/Tag** (≈ 560.000 im Monat).
- Freie Reserve damit grob **440.000 Credits/Monat (≈ 14.000/Tag)**. **Unsicher:** Seit dem 06.10. laufen bis zu 30 Copy-Wallets (vorher 28). Den Beginn des Abrechnungsmonats kennen wir nicht genau. Neu bewerten bei der Tagesauswertung am 08.10. (steht schon im Gedächtnis).

**Wofür lohnt sie sich am meisten (Reihenfolge):**
1. **Copy-Backtest** (Abschnitt 1): bestehende Wallets und Scout-Kandidaten 30 Tage nachspielen. Pro Wallet etwa 300–30.000 Credits. Bei rund 10 Wallets im Monat ist das gut im Rahmen und verbessert direkt die Wallet-Auswahl (Beispiel HEBO: −20 SOL).
2. **Stichproben für Weg B** (Preis 1,8 s später) und die Kalibrierung: wenige tausend Credits.
3. **Nicht** für breite Markt-Backtests über Rohblöcke (dafür ist Dune besser) und **nicht** für `transactionSubscribe` (nicht im Gratis-Tarif).

### d) DexScreener

Details in `2026-10-07_dexscreener_api.md`.

- **`/metas/trending/v1` als Narrativ-Signal:** Metas sind Themengruppen, die **Moderatoren und Community von Hand zuordnen**. Die Doku nennt keine Rangformel und keinen Aktualisierungstakt. Das Signal kommt also eher **spät**. Unsere Namenswelle (Tag 20) misst die On-Chain-Spur und dürfte früher sein. Ein **Vergleich** ist sinnvoll: Taucht ein Wellen-Wort später in den Trending-Metas auf, und wie viele Minuten später? Kosten: alle 5 min ein Abruf = **288 Abrufe/Tag** (Limit 60/min). Zuerst nur beobachten, keine Kaufregel.
- **`/tokens/v1` für Punkt a:** bis 30 Coins je Abruf, 300/min. Die jungen ~140 gleichzeitigen Coins sind 5 Abrufe je Runde. Bei 60 s ergibt das ≈ 7.200/Tag, das passt locker. Liefert Käufe/Verkäufe (5 min/1 h), Volumen, Liquidität und Preisänderung, aber **keine Holder und keine organischen Käufer**. **Empfehlung:** Jupiter bleibt die Hauptquelle (hat Holder und organic). DexScreener ist nur eine Ergänzung, wenn wir Käufe/Verkäufe aus einer zweiten Quelle wollen. Die Zeitfenster `m5`/`h1` sind laut Doku nicht garantiert, fehlende Werte also nicht als 0 werten.
- **WebSocket oder Abfrage?** Die WebSocket-Doku beschreibt nur die erste Nachricht. Folgeformat, Wiederverbinden, Nachlieferung und Grenzen sind **nicht dokumentiert**. Für unsere 6-h-Schichten sind **regelmäßige Abfragen einfacher und robuster**: 5 Ströme (Profile, Boosts neu, Boosts top, Community-Übernahmen, Werbung) je 1/min = 7.200 Abrufe/Tag. Ob die 60/min je Endpunkt oder gemeinsam gelten, ist **unsicher**, deshalb lieber jeden Strom nur alle 2 min abfragen (3.600/Tag).
- **Laufen Coins nach Profil oder Boost besser oder schlechter?** Das lässt sich **schon heute mit vorhandenen Daten** auswerten, ohne neue Abrufe. `dexscreener.csv` hat 1.463 Einträge (731 Käufe, 732 knapp abgelehnt) mit Profil 0/1, Boosts, Werbung, Community-Übernahme und Zahlungszeitpunkt. Profil haben 63 %, Boosts nur 4 %, für ein Urteil über Boosts sind es also noch zu wenige. Die Ströme bräuchte man nur, um **alle** Coins mit Profil zu sehen, nicht nur unsere.
- **Was speichert die DexScreener-Aufzeichnung heute?** `dexscreener.csv`: Zeit, Konto, Art, Symbol und Mint (aus Jupiter), Ablehnungsgrund, Coin-Alter, **Kennzahlen 0/1 bzw. Anzahl** (Profil, Werbung, Community-Übernahme, Boosts), Minuten zwischen Zahlung und Ereignis, `zahlungen` als „Art@Zeitstempel“ und eine Fehlerspalte. `has_social` speichert nur ja/nein. **Keine Texte, Bilder, Links oder kompletten Antworten.** Das entspricht schon fast deinem Vorschlag. Einzige Rohdaten-Nähe ist die Spalte `zahlungen` (Liste der Zahlungsarten mit Zeitstempel). Vorschlag: künftig nur noch Anzahl und Minuten speichern. Für neue Aufzeichnungen (Metas, Ströme) gilt dieselbe Regel: nur Zahlen und eigene abgeleitete Werte, also z. B. „Wellen-Wort steht in Trending-Meta: ja/nein, Rang, Minuten seit Welle“ statt Name/Beschreibung des Metas.

### e) Zurückgestellt bzw. abgelehnt

PumpPortal zurückgestellt (Speichern ohne Erlaubnis nicht erlaubt, `2026-10-07_pumpportal.md`), GMGN-API abgelehnt (100 $ Guthaben in einer Wallet). Birdeye-Verlauf und Allium scheiden aus denselben Gründen aus (Speicherverbot bzw. nur Firmen-E-Mail).

---

## 6. Empfohlene Reihenfolge (Daten pro Aufwand)

| # | Was | Aufwand | Kosten | Nutzen |
|---|---|---|---|---|
| 1 | **Repo entlasten** (Option A + B), vor allem `abgelehnt.csv` in Tagesdateien | klein–mittel | 0 | nötig vor dem 100-MB-Stopp (≈ 11.11.), Voraussetzung für mehr Daten |
| 2 | **Auswertung vorhandener Daten**: DexScreener-Profil/Boost gegen Ergebnis, Preisabstand-Verteilung für den Copy-Backtest | klein | 0 | sofort Antworten ohne neue Abrufe |
| 3 | **Junge abgelehnte Coins 6 h verfolgen** (5a, nur Jupiter) | mittel | ≈ 1.400–2.900 Jupiter-Abrufe/Tag | **wertvollste Datenquelle**: Entscheidungszeitpunkt-Daten inkl. Holder/organic, die keine historische Quelle hat. Nach 2–3 Wochen tausende Coins für Filter-Tests |
| 4 | **Copy-Backtest-Prototyp** mit Helius (1 Wallet + Gegenprobe, dann Scout-Kandidaten) | mittel | 300–30.000 Credits/Wallet | bessere Wallet-Auswahl, schneller als 7 Tage Schonfrist |
| 5 | **Testphase Dune** (empfohlen) für Endspurt, Bündel, FOMO, Verkaufsregeln, Kontrollgruppe | mittel (Abfragen vorher fertig) | 0 (Trial) | Wochen bis Monate Historie auf einmal |
| 6 | DexScreener-Metas gegen Namenswelle aufzeichnen | klein | 288 Abrufe/Tag | Antwort auf „ist Trending früher oder später als unsere Welle?“ |

Punkte 1, 3, 4 und 6 sind Code-Änderungen an den Bots bzw. neue Skripte. Jeder einzelne braucht deine Zustimmung, die Prüfungen (Tests, code-pruefer, kritische Codex-Prüfung) und einen Eintrag im Änderungsprotokoll.

---

## 7. Checkliste „Tag 0 bis 7 der Testphase“

Geschrieben für **Dune** (Empfehlung). Bei Bitquery gilt derselbe Ablauf mit den Entwürfen aus `2026-10-07_bitquery_abfragen.md`, aber nur für die letzten ca. 7 Tage, mit höchstens ≈ 200 Abfragen und Start mit höchstens 100 Punkten für Feldprüfungen.

**Vor Tag 0 (ohne Konto, alles vorbereitet):**
- [ ] Entscheidung: Dune oder Bitquery.
- [ ] Alle SQL-Abfragen fertig geschrieben und von Claude **und** Codex gelesen. Jede Abfrage hat Zweck, Zeitfenster, erwartete Zeilenzahl und Exportgröße.
- [ ] Vorab-Datei `auswertungen/backtest_vorab.md` mit Regeln, Schwellen, Suchwochen und Bestätigungswoche, datiert.
- [ ] Stichprobe für die Kalibrierung: 20 Coins aus `journal.csv` (Hauptbot) + 20 Endspurt-Coins + 5 Copy-Käufe mit bekannter Signatur.
- [ ] Lokaler Ordner `C:\Users\admin\paperbot-daten\` außerhalb des Repos. Auswerte-Skripte liegen im Repo, Daten nicht.
- [ ] Der Betreiber legt das Konto selbst an (Claude meldet sich nirgends an).

**Tag 0 – Anmelden und Felder prüfen**
- [ ] Konto nur mit E-Mail anlegen. **Abbruch bei Karte, Wallet, Zahlung oder Abo-Pflicht.**
- [ ] Tatsächliches Guthaben, Ablaufdatum und Exportrechte ablesen und in dieser Datei notieren.
- [ ] Credit-Deckel je Abfrage setzen (Dune bietet das an).
- [ ] Je Tabelle eine Mini-Abfrage (1 Coin, 1 Minute, `LIMIT 10`). Verbrauch notieren.
- [ ] Felder gegen eigene bekannte Trades prüfen: Zeit, Slot, Käufer, SOL-Menge, Preis.

**Tag 1 – Kalibrierung (Gegenprobe)**
- [ ] Trades der 20 Hauptbot-Coins (6 h ab Kauf) zu Minutenkursen verdichten und gegen unsere `verlauf/`-Kurse halten. Abweichung im Median unter 2 %?
- [ ] 5 Copy-Käufe: Trader-Trade finden, Markt-Trades der nächsten 5 Slots gegen unseren echten Preis halten (prüft Weg B).
- [ ] **Stopp, wenn die Kalibrierung nicht passt.** Ursache klären, bevor weitere Credits verbraucht werden.

**Tag 2 – Grundgesamtheit**
- [ ] Alle Pump.fun-Erstellungen für die Such- und Bestätigungswochen: nur Anzahl je Tag und eine Zeile je Coin (Mint, Zeit, Ersteller).
- [ ] Ersteller-Statistik serverseitig rechnen: Coins je Dev, bester früherer Coin (für die Dev-Regeln und Serien-Devs).

**Tag 3 – Merkmale zum Entscheidungszeitpunkt (serverseitig rechnen, nur Ergebnis exportieren)**
- [ ] Endspurt: Zeitpunkt 95–108 vSol, Trades bis dahin, Graduation ja/nein und Zeitpunkt, Kurs nach 45 min.
- [ ] Bündel: Käufer und Anteil im Erstellungs-Slot.
- [ ] FOMO: Anstieg der letzten 5 min zum Prüfzeitpunkt.
- [ ] Nachgebildete Kandidatenliste („meistgehandelt 5 min/1 h“) für Kontrollgruppe und Hauptstrategie-Näherung.

**Tag 4 – Kursreihen**
- [ ] Minutenkurse für 6 h (Endspurt bis zur Graduation + 45 min) für alle Kandidaten aus Tag 3. Nur Zeit, Preis, Käufe, Verkäufe je Minute.
- [ ] Exportgröße gegen das Restguthaben prüfen. Notfalls nur die Suchwochen.

**Tag 5 – Copy (falls nicht über Helius)**
- [ ] 30 Tage Trades von 3–5 Wallets und die Markt-Trades im Fenster nach jedem Kauf.
- [ ] Sonst: Tag 5 als Reserve.

**Tag 6 – Lücken und Reserve**
- [ ] Fehlgeschlagene oder abgeschnittene Abfragen wiederholen (Fenster teilen, nicht still kürzen).
- [ ] Alle Exporte lokal sichern, Zeilen zählen, Prüfsummen notieren.

**Tag 7 – Abschluss**
- [ ] Letzte Exporte. Prüfen, dass kein Abo und keine Zahlungsart hinterlegt ist. Konto nicht verlängern.
- [ ] Verbrauch und Erfahrungen in diese Datei bzw. eine Folgedatei eintragen.
- [ ] Danach offline auswerten: suchen an den älteren Wochen, **einmal** bestätigen an der neueren Woche, mit Testtagebuch. Gute Regeln werden höchstens zu neuen Live-Experimenten.

(Dune läuft 14 Tage. Die Tage 8–14 sind Puffer, nicht verplant.)

---

## 8. Offene Entscheidungen für dich

1. **Testphase bei Dune statt Bitquery?** (Empfehlung: Dune; Begründung in Abschnitt 3.)
2. **Repo entlasten:** Sollen Option A (seltener committen) und B (`abgelehnt.csv` in Tagesdateien) als technische Korrektur vorbereitet werden? Das ist dringend vor dem ca. 11.11.
3. **Junge abgelehnte Coins 6 h verfolgen** (5a) als neue Aufzeichnung, nach Punkt 2?
4. **Copy-Backtest-Prototyp** mit Helius (1 Wallet + Gegenprobe)?
5. DexScreener: Spalte `zahlungen` auf Anzahl/Minuten reduzieren und Metas gegen Namenswelle aufzeichnen?
