# Strategie NARRATIV

Paper-Trading-Bot für Solana-Memecoins. Die Regeln stammen aus 13 Lernvideos
(„Learning everything I know about memecoins", Tag 1–13). Es wird nur auf
Papier gehandelt.

## Regeln und ihre Herkunft

| Tag | Aussage im Video | Umsetzung im Bot |
|---|---|---|
| 1 | Nur Coins kaufen, die nicht gebündelt sind | Eigener Block-0-Check (Methode wie SolBundler): ab 2 Käufern mit zusammen 15 % im Erstellungsblock gilt ein Coin als gebündelt, ebenso wenn diese Käufer noch 10 % halten. Zweitmeinung RugCheck-Insider. Ohne Daten kein Kauf |
| 2 | Bei großem Gewinn etwas vom Tisch nehmen | Bei 2x wird die Hälfte verkauft |
| 3 | Vor dem Kauf These und Verkaufsbedingung notieren | `journal.csv` mit These und Verkaufsbedingung. Verkauf, wenn die These bricht |
| 4 | Gewinner halten, solange die Story wächst | Der Rest nach 2x läuft weiter, Ausstieg bei Thesenbruch oder 30 % unter dem Hoch (ab 10x 25 %) |
| 5 | Früh rein, solange es sich verbreitet | 15 Minuten bis 6 Stunden alt, Holder +15 % pro Stunde, Netto-Käufer, mindestens 3 organische Käufer, Social-Links vorhanden |
| 6 | Dev prüfen | Dev hat höchstens 50 Coins gestartet und hält höchstens 10 % (Jupiter) |
| 7 | Nicht hinterherjagen, nicht größer setzen | Höchstens 3 Mio. USD Marktwert, höchstens +150 % in der letzten Stunde, feste Größe 0,2 SOL |
| 8 | Kein Copy-Trading | Keine Wallet-Signale |
| 9 | Ruhiger Markt: weniger handeln | Marktphase begrenzt die Positionen: heiß 3, normal 2, ruhig 1 |
| 12 | Vamping: den echten Coin finden | Bei gleichem Namen oder Symbol nur der Coin mit den meisten Holdern |
| 13 | Marktsignale prüfen | Marktphase aus Anzahl frischer Coins über 1 Mio. USD und deren Volumen, verglichen mit dem eigenen Verlauf |
| 16 | Würde ich heute zu diesem Preis neu kaufen? | Sinngemäß über die Thesen-Regel und die Höchstdauer umgesetzt; strengere Fassung an den Verläufen geprüft und verworfen (hätte die großen Gewinner zu früh verkauft) |
| 17 | Nicht aus FOMO kaufen, wenn der Preis schon gelaufen ist | Seit 02.10.: kein Kauf nach mehr als 30 % Anstieg in den letzten 5 Minuten (FOMO_SPRUNG). Alle so abgelehnten Coins werden als knapp abgelehnt weiterverfolgt. Grundlage: in Hauptstrategie und Kontrollgruppe deutlich schlechtere Ergebnisse nach solchen Sprüngen |

**Mitläufer-Verdacht (nur Beobachtung, seit Tag 15):** Teilt ein gekaufter Coin einen Namensteil mit einem mindestens zehnmal größeren Trending-Coin ab 5 Mio. USD (z. B. „K/ACC" und „e/acc"), wird das beim Kauf vermerkt. Das beeinflusst den Kauf nicht, sondern dient der späteren Auswertung.

Nicht automatisierbar: Tag 10 und 11 (Netzwerk, Community). Die Verbreitung
auf X oder TikTok (Tag 5) kann der Bot nicht direkt lesen. Er misst die
On-Chain-Spur, die eine Story hinterlässt.

## Wann verkauft wird

1. **2x erreicht:** Hälfte verkaufen
2. **These gebrochen:** Holder schrumpfen und Netto-Verkäufer, zweimal in Folge
3. **Liquidität abgezogen:** 30 % unter dem Einstieg
4. **Story abgekühlt:** nach dem Teilverkauf, gemessen am Höchststand seit dem Kauf: 30 % unter dem Hoch, ab 10x 25 %
5. **Gewinn geschützt:** Wer vor dem Teilverkauf 1,5x erreicht hat, wird spätestens bei Einstand verkauft
6. **Notbremse:** −40 %
7. **Höchstdauer:** 24 Stunden

## Dateien

| Datei | Inhalt |
|---|---|
| `bot.py` | Der Bot |
| `portfolio.json` | Kontostand, offene und geschlossene Positionen |
| `journal.csv` | Jeder Kauf mit These, jeder Verkauf mit Grund |
| `abgelehnt.csv` | Geprüfte Coins und warum sie nicht gekauft wurden |
| `marktphase.json` | Verlauf der Marktphase |

Alle Schwellen stehen oben in `bot.py` und lassen sich dort ändern.

## Experimente (seit 29.09.)

Die Experimente laufen im selben Bot auf denselben Daten (seit 04.10.: neun aktiv, zwei beendet), aber mit eigenen Konten (je 10 SOL, gleicher Einsatz; Ausstiegsregeln wie die Hauptstrategie, außer bei den beiden Endspurt-Experimenten). Ist ein Konto aufgebraucht, startet es mit 10 SOL neu; die Rundennummer bleibt bei jedem Trade gespeichert. Die Hauptstrategie wird dadurch nicht verändert.

| Experiment | Kauft, wenn … | Frage dahinter |
|---|---|---|
| Zweite Welle | ein Coin, den die Hauptstrategie per Notbremse verkauft hat, innerhalb von 6 h wieder über ihren Einstiegskurs steigt | Lohnt sich der Wiedereinstieg in Coins wie WARP (nach der Notbremse bis 15,7x)? |
| Heiße Coins | alle Prüfungen bestanden sind, nur der Bundle-Check wegen zu vieler Transaktionen nicht möglich war | Bringen die heißesten Coins mehr, als das Bundle-Risiko kostet? |
| Ohne Limit (**beendet 04.10.**) | die Hauptstrategie kaufen würde, auch wenn ihr Positionslimit voll ist | Kostet das Positionslimit Gewinn? – Nicht messbar: 60 von 60 Käufen identisch mit der Hauptstrategie, das Limit griff nie |
| Kontrollgruppe | etwa alle 30 min ein zufälliger junger Coin, der nur die Sicherheitsprüfungen besteht (Alter 15 min bis 6 h, Liquidität, sicherer Contract, keine Transfergebühr) | Sind die Filter der Strategie besser als Zufall? |
| Endspurt viele Trades | wie „Endspurt ohne Filter“, aber nur Coins mit mindestens 2.000 Trades seit Start (seit 01.10.; vorher Filter der Studie: unter 800 Trades und organischer Handel, wurde nie erfüllt) | Graduieren Coins mit vielen Trades häufiger? In den ersten 74 Käufen: 52 % gegenüber 24 % |
| Endspurt ohne Filter (**beendet 04.10.**: 266 Trades, besser als Zufall, aber im Minus) | Pump.fun-Coin bei 95–108 vSol (76–92 % bis zur Graduation), Quote höchstens 3 % über Kurvenpreis. Verkauf komplett bei der Graduation, bei 12 vSol Rückfall, nach 45 min oder bei der Notbremse | Lohnt der Kauf kurz vor der Graduation? (arXiv 2602.14860) |
| Notbremse 25 (seit 04.10.) | genau dann, wenn die Hauptstrategie kauft (gleicher Coin, gleicher Moment); alle Ausstiege gleich, nur die Notbremse greift schon bei −25 % statt −40 %. Zeichnet nach dem Verkauf 6 h weiter auf | Spart eine frühere Notbremse mehr Verluste, als sie spätere Gewinner kostet? (Überprüfung 03.10., Hypothese H1: Hauptstrategie-Verläufe dafür, Kontrollgruppe dagegen) |
| Offene Tür (seit 04.10.) | ein Coin dieselben Story-Filter wie die Hauptstrategie besteht (Alter, Holder-Wachstum, echte Käufer, organisch, Liquidität, kein FOMO-Sprung) – **ohne** jede Sicherheitsprüfung (Dev, Contract, Nachahmer, Vamp, Transfergebühr, Bundle/Block 0, Links); höchstens 4 Positionen. Ausstiege wie Hauptstrategie, 6 h Nachlauf | Was sparen bzw. kosten unsere Sicherheitsprüfungen? Kauft bewusst auch Rugs, um ihre Muster im Flugschreiber aufzuzeichnen |
| Serien-Devs (seit 04.10.) | ein junger Coin (15 min–6 h, Liquidität ≥ Minimum) von einem Dev stammt, dessen früherer Coin mindestens 300.000 $ Marktwert erreichte (eigene Liste aus den Jupiter-Daten, `experimente/serien_devs/devs.json`); keine weiteren Prüfungen; höchstens 4 Positionen. Ausstiege wie Hauptstrategie **plus** „Dev verkauft“: Dev hält weniger als die Hälfte seines Bestands beim Kauf | Lohnen erfahrene Devs, auch wenn sie später rugen – und erkennt man den Rug am Dev-Verkauf rechtzeitig? |
| Große Coins (seit 04.10.) | ein Coin alle Prüfungen der Hauptstrategie besteht (Alter, Verbreitung, Käufer, organisch, Liquidität, Sicherheit, FOMO, Links, Transfergebühr, Bundle/Block 0) – nur der Marktwert liegt **über** 3 Mio. $ statt darunter; Positionslimit je Marktphase wie die Hauptstrategie. Ausstiege wie Hauptstrategie, 6 h Nachlauf. Erwartet selten: etwa 0–3 Kandidaten pro Tag | Kostet uns die 3-Mio.-Grenze (Tag 7) Gewinner? (Video-Idee OrangieWEB3: größte Gewinne in Coins über 3 Mio.) |
| Drittel-Leiter (seit 04.10.) | genau dann, wenn die Hauptstrategie kauft (gleicher Coin, gleicher Moment). Verkauf je ein Drittel bei 1,5x / 2x / 3x (bei 3x ist alles verkauft) statt der Hälfte bei 2x; Abstand zum Hoch ab der 2x-Stufe, alle anderen Ausstiege wie die Hauptstrategie. 6 h Nachlauf. Auswertung zusätzlich Coin für Coin gegen die Hauptstrategie (Dashboard, `rechnung.paarvergleich`) | Bringt Verkauf in Stücken mehr als „Hälfte bei 2x“? (Nachrechnung 04.10.: auf 96 Verläufen −0,94 statt −1,17 SOL mit Kosten, auch ohne die 3 besten besser; beste Variante hinterher ausgewählt) |

„Ohne Limit“ und „Endspurt ohne Filter“ zeichnen Coins nach dem Verkauf 6 h weiter auf. Bei „Endspurt ohne Filter“ sind das die Kursverläufe nach der Graduation, damit lässt sich auch eine Strategie „Einstieg nach der Migration“ nachrechnen. Damit lassen sich strengere Filter, ein Einstieg erst nach der ersten Korrektur und andere Ausstiege nachrechnen, ohne eigene Experimente.

Dateien: `experimente/<name>/portfolio.json` und `journal.csv`; Kursverläufe in `verlauf/` mit dem Präfix `exp_<name>_`. Meldungen gehen in den Discord-Kanal des Secrets `DISCORD_WEBHOOK_EXPERIMENTE`.

**Beendete Experimente** kaufen nichts mehr. Ihre offenen Positionen laufen regulär zu Ende, die Daten bleiben (Liste `EXP_BEENDET` in `bot.py`).

**Testregeln für alle Experimente** (seit 30.09.): Entscheidung frühestens nach 200 Trades. Vergleich mit der Kontrollgruppe aus demselben Zeitraum. Ein Experiment gilt nur als besser, wenn es das auch ohne seine 3 besten Trades bleibt.

## Copy Trading (eigener Bot, seit 30.09.)

Getrennt vom Hauptbot: eigenes Programm `copy_bot.py`, eigener Workflow `copy_runner.yml`, eigene Dateien in `copy/`, eigener Discord-Kanal (Secret `DISCORD_WEBHOOK_COPY`). Stürzt der Copy-Bot ab, läuft der Hauptbot unverändert weiter.

- **Wallets:** `copy_wallets.txt`, eine Zeile pro Wallet im Format `Name: Adresse`. Austauschen ohne Code-Änderung.
- **Erkennung:** Helius-WebSocket (`logsSubscribe` je Wallet, im Gratis-Tarif enthalten), danach die vollständige Transaktion (bis Version 1). Abgefragt wird nur, was nach Handel aussieht; reine Transfers nur, wenn eine Position offen ist. Wallets mit mehr als 30 Meldungen pro Minute, von denen mindestens 80 % fehlschlagen, werden für die Schicht abgemeldet (Flutschutz); über 300 pro Minute immer. Echte Vieltrader wie 922M bleiben angemeldet. Kauf, Verkauf und Überweisung werden an den Salden erkannt, unabhängig von der Börse (Pump.fun, PumpSwap, Raydium, Meteora, Jupiter); Handel gegen USDC wird in SOL umgerechnet.
- **Konto:** jede Wallet 10 SOL. Neue Runde mit 10 SOL, sobald das Geld für keinen Kauf mehr reicht, auch wenn noch Positionen offen sind (seit 02.10.; diese behalten ihre alte Rundennummer, ihre Erlöse fließen ins neue Konto).
- **Kauf:** jeder Kauf des Traders ab 0,1 SOL = 0,2 SOL bei uns, auch Nachkäufe. Kleinere Käufe (Tests, Staub) werden ignoriert. Weicht unser Kaufkurs mehr als ±15 % vom Kurs des Traders ab, wird der Kauf blockiert. Kaufmeldungen älter als 60 s werden nie nachgekauft. Alles Ausgelassene steht als AUSGELASSEN mit Grund im Journal.
- **Verkauf:** derselbe Anteil, den der Trader verkauft, aber gesammelt: Teilverkäufe werden gemerkt (VERKAUF_GEMERKT) und erst ausgeführt, wenn mindestens 20 % der Position zusammenkommen. Steigt der Trader komplett aus oder überweist er die Coins (ÜBERWEISUNG), verkaufen wir sofort alles. Verkäufe sind nie blockiert.
- **Nachholen:** Der Bot merkt sich pro Wallet, bis wann er lückenlos zugehört hat (`abgedeckt_bis`). Nach Lücken (Schichtwechsel, Verbindungsabbruch, Flutschutz) holt er die verpassten Transaktionen über Helius nach: Verkäufe laufen normal durch, mit dem echten Kurs des Traders (Trader-Vergleich gültig, unser Verkauf als „nachgeholt“ markiert, nicht in der Verzögerungsstatistik); Käufe werden nicht nachgekauft, nur als VERPASST_KAUF dokumentiert. Jede Position merkt sich die verarbeiteten Signaturen, nichts wird doppelt angewendet.
- **Bestandsabgleich:** beim Schichtstart und dann stündlich prüft der Bot für jede offene Position den tatsächlichen Bestand des Traders auf der Blockchain. Hält er nichts mehr, verkaufen wir alles; hält er mindestens 20 % weniger als bei seinem letzten gesehenen Trade, verkaufen wir denselben Anteil (ABGLEICH). Findet er eine Differenz, versucht er zuerst nachzuholen; nur wenn das nichts findet, verkauft er ohne Trader-Kurs (ABGLEICH, dann kein Trader-Vergleich).
- **Kein Take-Profit, kein Stop-Loss.** Am regulären Schichtende werden Positionen mit höchstens 1 % Restwert (−99 %) bereinigt.
- **Prüfungen** des Hauptbots laufen bei jedem Kauf mit und werden gespeichert, entscheiden aber nichts (ohne Solana Tracker).
- **Gebühren:** unsere Gebühr je Transaktion = die tatsächliche Netzwerkgebühr des Traders für diesen Trade (Grundgebühr, Prioritätsgebühr, Jito-Tip). Bot-Gebühren des Traders (z. B. 1 %) rechnen wir uns nicht an.
- **Vergleich mit dem Trader:** nur aufgezeichnete Trades. Hielt er Coins schon vor unserem Start, zählt bei seinen Verkäufen nur der Anteil aus aufgezeichneten Käufen. Nach einer Überweisung ist kein Vergleich möglich.
- **Gespeichert je Trade** (`copy/journal.csv`): Signatur, Zeit, Menge, Preis und Gebühren des Traders (Grundgebühr, Prioritätsgebühr, Jito-Tip, sonstige wie Bot-Gebühren), unser Preis, unsere Gebühr, Verzögerung in Sekunden, Preisabstand in %, Ergebnis. In `copy/konten.json` pro Wallet Konto, offene und geschlossene Positionen, jeweils mit dem Ergebnis des Traders auf demselben Coin.
- **Schattenpositionen:** Käufe, die an der Preisgrenze scheitern, werden virtuell weiterverfolgt (SCHATTEN_KAUF, SCHATTEN_ENDE im Journal). Ausstieg zum Verkaufskurs des Traders, also leicht optimistisch. Zeigt, ob die Grenze von ±15 % richtig liegt.
- **Kursverläufe:** etwa jede Minute für alle offenen Positionen und Schattenpositionen in `copy/verlauf/JJJJ-MM-TT.csv`. Damit lassen sich Take-Profit und Stop-Loss pro Trader nachrechnen.
- **Wallet-Prüfung** in jeder Endmeldung, nach festen Regeln: Bot (Flutschutz oder ≥ 200 Meldungen pro Schicht, ≥ 90 % fehlgeschlagen, kein eigener Trade) → ersetzen; 72 h kein eigener Trade → ersetzen; schlechtes Ergebnis erst ab 30 geschlossenen Positionen und mehr als 1 SOL Verlust bewerten. Der Bot entfernt nichts selbst. Entfernte Wallets werden in `copy_wallets.txt` mit Datum und Grund auskommentiert, ihre Daten bleiben erhalten.
- **Grenzen der Simulation:** Wir kaufen zum Jupiter-Kurs in dem Moment, in dem wir den Trade sehen. Die Gebühren-Vorteile des Traders lassen sich auf Papier nicht nachbilden; messbar sind Verzögerung und Preisabstand. Beim Kaufbetrag des Traders ist die Miete für ein neues Token-Konto (~0,002 SOL) enthalten.

## Wallet-Scout (eigener Bot, seit 01.10.)

Findet Kandidaten für das Copy Trading und erstellt eine Rangliste. Kauft nichts und ändert keine Wallet-Liste; die Entscheidung trifft der Mensch. Programm `scout_bot.py`, Workflow `scout_runner.yml` (alle 6 Stunden zu Minute 29), Dateien in `scout/`, Meldungen in `DISCORD_WEBHOOK_SCOUT` (sonst im Copy-Kanal).

1. **Gewinner-Coins** aus unseren eigenen Daten der letzten 48 h: Hoch mindestens 3x (Hauptstrategie, Experimente, Kursverläufe inkl. Copy). Bis zu 6 neue Coins pro Lauf.
2. **Kandidaten:** frühe Käufer dieser Coins (Helius, ohne den ersten Block mit Dev und Bundlern; nur wenn der Start des Coins in 5.000 Signaturen erreichbar ist) und, wenn `BIRDEYE_API_KEY` gesetzt ist, bis zu 5 Top-Trader je Coin laut Birdeye: nur mit realisiertem Gewinn auf dem Coin und ohne Markierung als Bundler, Sniper, Bot, MEV, Insider oder Dev (35 CUs je Coin; Zähler stoppt bei 28.000 CUs im Monat, Gratis-Tarif 30.000). Bekannte Wallets (aktiv oder auskommentiert) und in den letzten 7 Tagen geprüfte werden übersprungen.
3. **Stufe 1** (1 Helius-Credit): letzte 1.000 Transaktionen. Raus bei über 50 % fehlgeschlagen, über 300 Transaktionen pro Stunde, über 24 h inaktiv oder unter 20 Transaktionen.
4. **Stufe 2** (seit 02.10. abends): Transaktionen der letzten 7 Tage (automatisch bis 60, Prüfliste bis 150), ausgewertet mit der Logik des Copy-Bots. Wie bei GMGN zählen alle im Zeitraum gekauften Coins; noch gehaltene werden zum aktuellen Jupiter-Kurs bewertet. Kennzahlen: Rendite auf den Einsatz, dieselbe ohne den besten Coin, Coins (davon noch gehalten), Trefferquote, Kaufgröße, Trades pro Tag, Haltedauer abgeschlossener Coins, Mini-Verkäufe, Bot-Gebühren. Vorher zählten nur Coins, die in den letzten 60 bzw. 150 Transaktionen gekauft und wieder verkauft wurden; das hat Trader, die Coins tagelang halten, systematisch schlecht gerechnet (nur ihre schnellen Fehlkäufe waren sichtbar).
5. **Punkte = für uns erwartete Rendite:** Rendite des Traders ohne seinen besten Coin, minus Reibung je nach Haltedauer (unter 10 min 10 Punkte, bis 60 min 6, darüber oder überwiegend gehalten 3); −10 bei überwiegend Mini-Verkäufen, −10 bei überwiegend Käufen unter 0,1 SOL. Erst ab 3 Coins im Zeitraum. Stufe 1: Bot nur bei über 80 % fehlgeschlagenen Transaktionen oder über 50 % bei mehr als 60 pro Stunde; Prüfliste erlaubt 72 h Inaktivität. Nach einer Änderung der Bewertung wird eine bereits geprüfte Liste erneut geprüft.

**Prüfliste** (seit 02.10.): Wallets, die du selbst findest (z. B. aus GMGN oder Kolscan), kommen in `scout/pruefen.txt` (`Name: Adresse`, nur die Adresse oder eine eingefügte Python-Liste). Der nächste Scout-Lauf bewertet jede davon mit denselben Stufen, aber mit 150 statt 60 Transaktionen, und meldet das Ergebnis aller Wallets, auch der durchgefallenen mit Grund, in einer eigenen Discord-Meldung. Dieselbe Liste wird nur einmal geprüft; nach einer Änderung erneut.

Grenzen: Vergangene Gewinne garantieren keine künftigen; frühe Käufer können Insider sein. Der eigentliche Test bleibt das Copy Trading.

## Änderungen

| Datum | Änderung | Grund |
|---|---|---|
| 27.09. | Abstand vom Hoch gestaffelt 40/30/25 % | Große Gewinner gaben zu viel zurück |
| 28.09. | Abstand 30 % bis 10x, darüber 25 % | Kursverläufe vom 27.09.: alle 4 betroffenen Gewinner besser |
| 28.09. | Gewinnschutz ab 1,5x | WARP und SOCIALBAGS standen bei 1,8x/1,9x und endeten bei −44 %/−56 % |
| 28.09. | Bundle-Regel: 2 statt 3 Käufer | Alle 3 Coins mit ≥15 % in Block 0 verloren (u. a. 2 Wallets mit 54 %) |
| 28.09. | Mitläufer-Verdacht (nur Beobachtung) | Vier ACC-Mitläufer am 26.09. alle verloren |
| 28.09. | Offene Positionen alle ~12 s statt 35 s prüfen | Notbremse verkaufte im Schnitt bei −46 % statt −40 % |
| 28.09. | Knapp abgelehnte Coins 6 h beobachten | Klären, ob Regeln spätere Gewinner aussortieren |
| 28.09. | Mehr Merkmale beim Kauf speichern | Später auswerten, was Gewinner von Verlierern unterscheidet |
| 29.09. | Graduation zählt nicht mehr als Liquiditätsabzug, ein Abzug muss 2 Prüfungen bestehen | SHORK und MINEPAD wurden beim Umzug in den PumpSwap-Pool fälschlich verkauft |
| 29.09. | 6 statt 2 Kandidatenlisten (Trending, meistgehandelt, organisch, je 5 min und 1 h), Herkunft wird gespeichert | Von 2.169 gesehenen Coins lagen nur 277 im Altersfenster |
| 29.09. | Solana Tracker als Zweitmeinung (nur Beobachtung, höchstens 70 Abfragen am Tag) | Anteile von Snipern, Bundlern und Insidern |
| 29.09. | Discord-Meldungen mit bis zu 3 Versuchen | Am 28.09. gingen 2 Meldungen verloren |
| 29.09. | Positionslimit und Filtergrenzen unverändert | Nahfälle bringen im Schnitt +0,014 SOL pro Trade, praktisch wie echte Trades; Ausreißer treiben die Einzelwerte |
| 29.09. | Vier Experimente mit eigenen Konten zu je 10 SOL (Zweite Welle, Heiße Coins, Ohne Limit, Kontrollgruppe) | Paper Trading erlaubt riskante Tests, ohne die Hauptstrategie zu verfälschen |
| 29.09. | Korrektur: Kontrollgruppe kaufte bei jeder Suche statt alle 30 min; Experimente zeichnen offene Positionen alle ~36 s auf | Zeitpunkt des nächsten Kaufs wurde nicht gespeichert |
| 29.09. | Kauf-, Teilverkaufs- und Verkaufsmeldungen enthalten eine Portfolio-Übersicht (alle offenen Positionen zum aktuellen Kurs) | Wunsch nach Überblick in Discord |
| 29.09. | Jede Schicht startet am Ende selbst die nächste; Zeitplan nur noch als Sicherheitsnetz (Minute 17 statt volle Stunde) | Nach manuellen Starts fiel ein geplanter Lauf aus, der Bot stand von 16:45 bis zum manuellen Start still |
| 30.09. | Experimente Endspurt Kurve und Endspurt ohne Filter (je 10 SOL) | Recherche: Kauf kurz vor der Graduation laut Studie über der Gewinnschwelle, wenn menschliche Käufer überwiegen |
| 30.09. | Korrektur: Das Hoch einer Position startet beim Kaufpreis statt beim Signalkurs | Bei cum (Rug, Kauf 62 % unter Signal) stand das Hoch sonst bei 2,65x und hätte den Gewinnschutz fälschlich scharf geschaltet; 1 von 122 Trades betroffen |
| 30.09. | Copy-Trading-Bot mit 20 Wallets, je 10 SOL (eigener Workflow, eigene Dateien) | Test, ob einzelne Trader für uns profitabel wären |
| 30.09. | Copy: Verkäufe gesammelt ab 20 %, reale Gebühren des Traders, Käufe unter 0,1 SOL ignoriert, Preisgrenze ±15 %, Trader-Vergleich nur aufgezeichnet, feinerer Filter, Altersgrenze 60 s | Erste 2 Stunden: 922M verkaufte 156-mal in 2-%-Schritten, Gebühren fraßen den Erlös |
| 01.10. | Endspurt: Filter umgekehrt auf ≥ 2.000 Trades; Filtermerkmale werden gespeichert | Studienfilter nie erfüllt; viele Trades graduierten häufiger |
| 01.10. | Copy: Schattenpositionen, Kursverläufe, Wallet-Prüfung; 8NQ3, DTVM, 9EWQ ersetzt durch Cooker, Gake, Jijo | 27 % der Käufe an der Preisgrenze blockiert; TP/SL pro Trader auswertbar machen |
| 01.10. | Helius: bei 429 bis zu drei weitere Versuche; Hauptbot ~6,5, Copy-Bot ~3 Anfragen/s; Jijo entfernt (Bot) | Beide Bots trieben sich gegenseitig ins Limit, Bundle-Checks fielen öfter aus |
| 01.10. | Copy: Flutschutz nur bei ≥ 80 % fehlgeschlagenen Meldungen (oder > 300/min); Wallet-Prüfung „Ergebnis“ erst ab 1 SOL Verlust; BGOK entfernt | 922M (echter Vieltrader) wurde abgemeldet, 14 Positionen ohne Verkaufssignale; Putrick mit −0,03 SOL markiert |
| 01.10. | Copy: Bestandsabgleich beim Start und stündlich (ABGLEICH) | 922M war abgemeldet, 14 Positionen offen, obwohl er teilweise schon verkauft hatte |
| 01.10. | Copy: verpasste Transaktionen werden nachgeholt (mit echtem Trader-Kurs); Abgleich nur noch als letztes Netz | Hinweis: der Verkaufskurs ist auch bei verpasstem Signal auf der Blockchain abrufbar |
| 01.10. | Wallet-Scout (Helius, optional Birdeye), alle 6 Stunden, Rangliste | Systematisch neue Wallets für das Copy Trading finden statt manuell |
| 01.10. | Copy: leere oder unlesbare WebSocket-Nachrichten führen zu Neuverbindung statt Absturz; Sicherheitsnetz für unerwartete Fehler | Copy-Bot stürzte um 14:34 UTC ab (leere Nachricht nach Verbindungsende durch den Server) und stand danach still |
| 01.10. | Scout: Birdeye-Kandidaten nur ohne Bundler-/Sniper-/Bot-Markierung und mit Gewinn; frühe Käufer nur bei erreichbarem Coin-Start | Probelauf: Top-Trader nach Volumen waren u. a. Bundler; PARASITE zu aktiv, 30 Seiten ohne frühe Käufer |
| 02.10. | Tag 17: kein Kauf nach > 30 % Anstieg in 5 min (FOMO_SPRUNG) | Video Tag 17; Hauptstrategie seit 28.09.: diese Käufe −0,56 SOL bei 12 Trades, Kontrollgruppe −0,93 SOL bei 15 |
| 02.10. | Copy: neue Runde auch bei offenen Positionen | 922M blieb mit 0,19 SOL und 1 offenen Position stehen, 291 Käufe ausgelassen |
| 02.10. | Scout: Bewertung nach Rendite je Coin minus 10 Prozentpunkte Reibung; Birdeye mit Gesamtgewinn; Filtergründe in der Meldung | Zwei Läufe ohne Kandidaten; Vieltrader wie 922M sind für uns nicht kopierbar (er +1,7 %, wir −11,3 % je Coin) |
| 02.10. | Scout: Prüflisten-Modus (`scout/pruefen.txt`) | Selbst gefundene Wallets aus unserer Sicht als Nachahmer bewerten, bevor sie ins Copy Trading kommen |
| 02.10. | Scout: Bewertung über 7 Tage inkl. gehaltener Coins, Reibung nach Haltedauer, Bot-Regel mit Takt, 72 h für die Prüfliste | GMGN-Trader halten Tage; der Scout sah nur ihre schnellen Fehlkäufe (Haltedauer 1–2 min statt Tage) |
| 02.10. | Copy: fomo, Cendol, 8K1B, FKUJ, AFYP, GYYR, ENKM, 9LXM entfernt; Pikalosi, Dior und 10 GMGN-Wallets neu (22 aktiv) | Stille oder klar verlierende Wallets; neue Kandidaten mit langen Haltezeiten live testen |
| 02.10. | Copy: Konto-Zeile zeigt aktuellen Wert der offenen Positionen und Kontowert statt Einsatz | „Einsatz“ enthielt bereits zurückgeflossene Teilverkäufe; frei + Einsatz wirkte wie 19 SOL bei tatsächlich ~9,8 SOL |
| 02.10. | Testsammlung `tests/` (145 automatische Tests für alle drei Bots, ohne echte APIs; Start mit `python -m pytest`); Regressionsprobe der Hauptstrategie festgeschrieben: 33 aufgezeichnete Verläufe, −0,021 SOL ohne Gebühren. Bot-Code unverändert | Änderungen künftig vor dem Push automatisch prüfen; frühere Probe (+0,068 SOL auf 28 Verläufen) war nicht nachvollziehbar |
| 02.10. | Copy: Endmeldung zeigt je Trader Kontowert (frei + offene Positionen zum Kurs) und Plus/Minus gegenüber den 10 SOL der laufenden Runde, sortiert nach Kontowert (vorher: frei und realisierter Gewinn, sortiert nach realisiert) | Gleiche Rechnung wie die Konto-Zeile der Einzelmeldungen; realisiert seit Start ließ Runden und offene Verluste außen vor |
| 03.10. | `requirements.txt` mit festen Versionen (requests 2.34.2, websocket-client 1.9.2) statt „mindestens“; Test prüft das | Prüfbericht 03.10.: ein neues Paket-Release hätte beim nächsten Schichtstart alle drei Bots stoppen können |
| 03.10. | Korrektur: Jupiter-Ausfall gilt nie mehr als „wertlos“. Hauptbot/Experimente zählen „Coin verschwunden“ nur, wenn Jupiter geantwortet hat (sonst bleibt die Position offen). Copy-Bot: Quote ohne Antwort (Timeout, 429, 5xx) = Ausfall; nur Jupiters Antwort „nicht handelbar / keine Route“ zählt als Wert 0. Bei Ausfall: Kauf ausgelassen, Verkauf vorgemerkt und beim nächsten Verkaufssignal oder stündlichen Abgleich nachgeholt, Abgleich und Schichtende-Bereinigung lassen die Position offen; Endmeldung zeigt die Ausfälle. Regressionsprobe unverändert | Prüfbericht 03.10.: ~6 min Jupiter-Ausfall hätte alle offenen Positionen zu 0 geschlossen; Copy hatte bereits 4 Verkäufe mit Wert 0 gebucht |
| 03.10. | Korrektur Copy-Nachholen: Der Bot liest beim Start aus `copy/journal.csv`, welche Trader-Signaturen schon verarbeitet sind, und überspringt sie beim Nachholen (ohne 60er-Grenze, über Schichtgrenzen). Verkäufe nur einer Schattenposition bekommen eine Journalzeile (`SCHATTEN_VERKAUF`). Kaputte Zeitangabe im Journal verhindert den Start nicht mehr. Workflows: `concurrency` war schon gesetzt (nie zwei Schichten desselben Bots gleichzeitig), jetzt durch Test abgesichert. Fehlbuchungen bis 03.10. in `auswertungen/korrekturen.md`/`.csv`, Daten nicht umgeschrieben | Prüfbericht 03.10.: 15 Verkäufe doppelt ausgeführt (1,01 SOL Erlös), 279 falsche `VERPASST_KAUF`; Ursache: neue Schicht holte bis zur Positionseröffnung nach, gemerkt waren nur 60 Signaturen je Position |
| 03.10. | Korrektur Copy-Abbruch: Das Abbruch-Signal wird nicht mehr von den Sicherheitsnetzen verschluckt. Kommt es mitten in einer Buchung (Kauf, Verkauf, Abgleich), wird diese erst vollständig gebucht. Danach wird gespeichert und die Endmeldung geschickt; ein zweites Signal stört das Speichern nicht. Fehler in Bereinigung oder Endmeldung verhindern weder das Speichern noch den Kettenstart | Prüfbericht 03.10. (Fehler C): Beim Abbruch von Hand am 02.10. lief der Bot weiter und speicherte nicht; Zrool-Position verloren, 922M-Position doppelt geschlossen |
| 03.10. | Messung (nur Aufzeichnung, keine Regeländerung): Bei jedem Kauf und Verkauf wird dieselbe Jupiter-Quote 2 s später noch einmal abgefragt. Ergebnis in eigenen Dateien `messung.csv` (Hauptbot und Experimente, Spalte `konto`) und `copy/messung.csv`, Spalte `abweichung_pct` (+ = 2 s später schlechter für uns). Die zweite Quote läuft nie während des Handels: Hauptbot in der 12-s-Pause zwischen zwei Durchläufen, Copy nur bei freiem Jupiter-Takt; verworfen nach 10 s. Neue Journal-Spalte hinten `notloesung` (1 = Verkauf ohne Quote, Kurs × 0,95 angenommen). Endmeldungen zeigen Median und Anzahl. Regressionsprobe unverändert | Prüfbericht 03.10.: Die Simulation rechnet mit sofortiger Ausführung; erst messen, wie viel Verzögerung real kosten würde, statt einen Aufschlag zu schätzen. Notlösung 0,95 war bisher nicht gezählt |
| 03.10. | Dashboard `dashboard/` (Streamlit, nur lokal, nur lesen, alle 5 min `git pull`, Start mit `dashboard/start.bat`): Übersicht mit Bot-Zustand und Testurteil je Konto, Strategie & Experimente, Copy Trading, Scout, Betrieb. Gemeinsame Rechnung in `dashboard/rechnung.py` (auch für die Tagesauswertung), Kontowert wie in Discord (per Test abgesichert), Korrekturen herausgerechnet, wartende Positionen zusätzlich mit Wert 0. Bot-Code unverändert | Wunsch des Betreibers: in 10 Sekunden sehen, was gut läuft, was schlecht läuft und ob etwas kaputt ist |
| 03.10. | Dashboard v2: Copy-Hauptzahl jetzt Ergebnis seit Start über alle Runden und Wallets (auch entfernte), laufende Runde nur als Zusatz, dazu „ohne besten Trader“; Testurteil trennt „besser/schlechter als Zufall“ und „im Plus/Minus“; Ausreißer-Hinweis, wenn ein Trader/Konto mehr als die Hälfte des Gesamtergebnisses ausmacht; auf dem Handy Kontokarten statt breiter Tabelle; neues dunkles Design (CSS und Diagramm-Thema gebündelt in `dashboard/stil.py`). Bot-Code unverändert | Wunsch des Betreibers: Die alte Copy-Zahl (+7,9 SOL, nur laufende Runden) verschwieg frühere Runden; seit Start sind es rund −36 SOL. HEBO (+24,5 SOL) beruht fast ganz auf einem Coin (PIGEON, +32 SOL), keine Fehlbuchung |
| 03.10. | Copy: 922M entfernt (in `copy_wallets.txt` auskommentiert, Daten bleiben) | Nicht kopierbar: −37 SOL über 5 Runden (Konto viermal aufgebraucht), ~70 % des Helius-Verbrauchs; Ersatz über die anstehende Überprüfung |
| 04.10. | Experimente: „Endspurt ohne Filter“ und „Ohne Limit“ beendet (keine neuen Käufe, offene Positionen laufen aus, Daten bleiben); neues Experiment „Notbremse 25“ (10 SOL, kauft genau mit der Hauptstrategie, Notbremse −25 % statt −40 %). Hauptstrategie unverändert (Regressionsprobe gleich) | Überprüfung 03.10.: Endspurt ohne Filter nach 266 Trades besser als Zufall, aber in beiden Hälften im Minus; Ohne Limit misst seine Idee nicht (60/60 identisch); Notbremse −25 % bestand die Hälften-Probe auf den Hauptstrategie-Verläufen (Kontrollgruppe dagegen) – auf Papier riskant erlaubt (Leitlinie 04.10.) |
| 04.10. | Copy: Zrool, Putrick, Cooker entfernt (Daten bleiben, offene Positionen über den stündlichen Abgleich) | Wallet-Regel ≥ 30 Positionen und > 1 SOL Verlust (Überprüfung 03.10.) |
| 04.10. | Scout-Bewertung 3: Wallets mit Median-Kauf unter 0,05 SOL werden nicht bewertet („Kleinstkäufe“ statt nur −10 Punkte); Prüfliste wird dadurch neu bewertet. Kriterium 20–700 Transaktionen vorerst nicht geprüft (nicht messbar) | Überprüfung 03.10.: Kleinstkäufer standen mit 84.602 und 455 Punkten oben, Rendite in % durch 0,002-SOL-Käufe aufgebläht |
| 04.10. | Scout: Prüf-Modus für einzelne Transaktionen (`scout/pruefen_tx.txt` → `scout/tx_pruefung.csv` + Discord): je Transaktion, ob der Copy-Bot sie als Kauf/Verkauf erkennt und ob der Live-Filter sie geholt hätte; läuft im Scout (eigene Workflow-Gruppe, stört die Copy-Kette nicht) | Überprüfung 03.10.: 8 Transaktionen von 2FPk/54cb waren über den öffentlichen RPC nicht prüfbar |
| 04.10. | DexScreener-Beobachtung (nur Aufzeichnung, keine Regel): je gekauftem und knapp abgelehntem Coin bezahltes Profil, Werbung, Community-Übernahme, Boosts und Zahlungszeitpunkte relativ zum Ereignis → `dexscreener.csv`. Offizielle API ohne Schlüssel, Abfrage in der 12-s-Pause (kein Kauf wartet), je Coin und Art höchstens alle 6 h | Überprüfung 03.10., Teil F: Tag 5 („früh rein, solange es sich verbreitet“) besser messen; Auswertung ab ≥ 100 Käufen |
| 04.10. | Flugschreiber (nur Aufzeichnung): je offene Position in Hauptstrategie und Experimenten etwa jede Minute Liquidität, Holder, Top-10-Anteil, Dev-Bestand, Käufe/Verkäufe 5 min → `flugschreiber/JJJJ-MM-TT.csv` (Jupiter-Daten, 0 Helius); alle 10 min Bestand von bis zu 8 Block-0-Käufern (Bundler) über Helius, geschätzt ≤ 69.000 Credits/Monat. Copy: dieselben Felder als neue Spalten hinten in `copy/verlauf/` (keine zusätzliche Abfrage) | Nachtlauf-Auftrag 04.10.: Rugs und Manipulation später als Muster auswerten (was passierte in den Minuten davor) |
| 04.10. | Neue Experimente „Offene Tür“ (Story-Filter ohne Sicherheitsprüfungen, max. 4 Positionen) und „Serien-Devs“ (Coins von Devs mit früherem Coin ≥ 300.000 $, Ausstieg zusätzlich bei Dev-Verkauf, max. 4 Positionen); je 10 SOL, nur Jupiter-Daten (0 Helius). Hauptstrategie unverändert (quick_checks Standard gleich, Regressionsprobe gleich) | Nachtlauf 04.10., Leitlinie „Mutig starten, streng urteilen, nichts ohne Aufzeichnung“: Rugs und Serien-Devs als Muster aufzeichnen |
| 04.10. | Copy: 4 Wallets neu (G7b2, GeFg, 499R, 2Nxj) – lockere Aufnahme: kein Bot, aktiv, Trader im Plus über 7 Tage (Scout/Birdeye); damit 22 aktive (Grenze). Bot-Verdacht ausgeschlossen: 8 „frühe Käufer“ mit identischen Kennzahlen (Sniper-Netz, Haltedauer ~6 s), Deh9, 8zkg, 9Df3 | Nachtlauf-Auftrag 04.10.: bis 22 auffüllen; Urteil nach 7 Tagen oder 30 Positionen |
| 04.10. | Dashboard: Exit-Liquidität je Copy-Trader (Anteil unserer Käufe, bei denen der Trader ≤ 60 s nach seinem Kauf bzw. schon vor unserem Kauf verkauft), aus den Trader-Zeiten im Journal | Nachtlauf 04.10., Experiment-Idee c: Verlierer (922M, Zrool, Cooker, 6ANG) verkaufen in 51–71 % der Fälle binnen 60 s, in 11–37 % schon vor unserem Kauf; Gewinner (4DOV, HEBO) halten Minuten bis eine halbe Stunde |
| 04.10. | Video-Auswertung (nur Doku, keine Regeländerung): 14 Videos von OrangieWEB3 in `videos/regeln.md` und `auswertungen/2026-10-04_videos.md`; weitere Kanäle durch YouTube-Sperre nicht abrufbar. 4 Vorschläge warten auf Zustimmung | Nachtlauf-Auftrag 04.10., Schritt 2 |
| 04.10. | Neues Experiment „Große Coins“ (10 SOL): alle Prüfungen der Hauptstrategie, aber nur Coins über 3 Mio. $ Marktwert; Ausstiege wie Hauptstrategie. Hauptstrategie unverändert (Regressionsprobe gleich). Helius: Bundle-Check nur für die wenigen Kandidaten, geschätzt < 15.000 Credits/Monat | Entscheidung des Betreibers 04.10. nach der Video-Auswertung (Widerspruch zu Tag 7) |
| 04.10. | Gebühren-Feld nur aufzeichnen (keine Regel): Feld `fees` der Jupiter-Antwort als Merkmal `jup_fees` – neue letzte Spalte in `knapp_abgelehnt.csv`, gespeichert bei jedem Kauf (`entry_view`) und bei Copy-Käufen (Merkmale). Jupiter dokumentiert das Feld nicht; liefert Jupiter es nicht, bleibt es leer. 0 zusätzliche Abfragen | Entscheidung des Betreibers 04.10. (Video-Idee: Coins mit wenig gezahlten Gebühren sind oft gebündelt) |
| 04.10. | Neues Experiment „Drittel-Leiter“ (10 SOL): kauft genau mit der Hauptstrategie, verkauft je ⅓ bei 1,5x / 2x / 3x, sonst gleiche Ausstiege. Dashboard: Coin-für-Coin-Vergleich für Paar-Experimente (Notbremse 25, Drittel-Leiter) gegen die Hauptstrategie. Hauptstrategie unverändert (Regressionsprobe gleich), 0 zusätzliche Abfragen | Entscheidung des Betreibers 04.10. nach der Nachrechnung `auswertungen/2026-10-04_video_nachrechnung.md` |
| 04.10. | Spar-Regel (nur Doku): große Dateien nur per Skript auswerten, Helfer bekommen nur nötige Zahlen – in CLAUDE.md, Daten-Prüfer, Strategie-Tester, Skill Tagesauswertung. Bericht `auswertungen/2026-10-04_tokenverbrauch.md` | Auftrag des Betreibers 04.10.: Token sparen (session-report: 288 Mio. Token, 73 % in einer einzigen langen Sitzung am 03.10.) |

## Dateien seit 28.09.

| Datei | Inhalt |
|---|---|
| `verlauf/JJJJ-MM-TT.csv` | Kursverläufe eines Tages: offene Positionen (~12 s), nach dem Verkauf (~36 s), knapp abgelehnt (~2 min) |
| `knapp_abgelehnt.csv` | Jeder knapp abgelehnte Coin mit Grund, Abstand zur Grenze und allen Merkmalen (seit 29.09. mit Herkunftsliste) |
| `verlauf.csv` | Alte Datei bis 27.09., wird nicht mehr fortgeschrieben |

