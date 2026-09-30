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

Sechs Experimente laufen im selben Bot auf denselben Daten, aber mit eigenen Konten (je 10 SOL, gleicher Einsatz; Ausstiegsregeln wie die Hauptstrategie, außer bei den beiden Endspurt-Experimenten). Ist ein Konto aufgebraucht, startet es mit 10 SOL neu; die Rundennummer bleibt bei jedem Trade gespeichert. Die Hauptstrategie wird dadurch nicht verändert.

| Experiment | Kauft, wenn … | Frage dahinter |
|---|---|---|
| Zweite Welle | ein Coin, den die Hauptstrategie per Notbremse verkauft hat, innerhalb von 6 h wieder über ihren Einstiegskurs steigt | Lohnt sich der Wiedereinstieg in Coins wie WARP (nach der Notbremse bis 15,7x)? |
| Heiße Coins | alle Prüfungen bestanden sind, nur der Bundle-Check wegen zu vieler Transaktionen nicht möglich war | Bringen die heißesten Coins mehr, als das Bundle-Risiko kostet? |
| Ohne Limit | die Hauptstrategie kaufen würde, auch wenn ihr Positionslimit voll ist | Kostet das Positionslimit Gewinn? |
| Kontrollgruppe | etwa alle 30 min ein zufälliger junger Coin, der nur die Sicherheitsprüfungen besteht (Alter 15 min bis 6 h, Liquidität, sicherer Contract, keine Transfergebühr) | Sind die Filter der Strategie besser als Zufall? |
| Endspurt Kurve | ein Pump.fun-Coin auf der Bonding Curve bei 95–108 vSol steht (etwa 76–92 % bis zur Graduation), höchstens 800 Trades seit Start hat und organischen Handel zeigt (Jupiter-Label mittel/hoch oder ≥ 30 % organischer Kaufanteil); Quote höchstens 3 % über Kurvenpreis. Verkauf komplett bei der Graduation, bei 12 vSol Rückfall, nach 45 min oder bei der Notbremse | Lohnt der Kauf kurz vor der Graduation? (arXiv 2602.14860) |
| Endspurt ohne Filter | wie Endspurt, aber ohne die Filter zu Trades und organischem Handel | Bringen die Filter der Studie etwas? |

„Ohne Limit“ und „Endspurt ohne Filter“ zeichnen Coins nach dem Verkauf 6 h weiter auf. Bei „Endspurt ohne Filter“ sind das die Kursverläufe nach der Graduation, damit lässt sich auch eine Strategie „Einstieg nach der Migration“ nachrechnen. Damit lassen sich strengere Filter, ein Einstieg erst nach der ersten Korrektur und andere Ausstiege nachrechnen, ohne eigene Experimente.

Dateien: `experimente/<name>/portfolio.json` und `journal.csv`; Kursverläufe in `verlauf/` mit dem Präfix `exp_<name>_`. Meldungen gehen in den Discord-Kanal des Secrets `DISCORD_WEBHOOK_EXPERIMENTE`.

**Testregeln für alle Experimente** (seit 30.09.): Entscheidung frühestens nach 200 Trades. Vergleich mit der Kontrollgruppe aus demselben Zeitraum. Ein Experiment gilt nur als besser, wenn es das auch ohne seine 3 besten Trades bleibt.

## Copy Trading (eigener Bot, seit 30.09.)

Getrennt vom Hauptbot: eigenes Programm `copy_bot.py`, eigener Workflow `copy_runner.yml`, eigene Dateien in `copy/`, eigener Discord-Kanal (Secret `DISCORD_WEBHOOK_COPY`). Stürzt der Copy-Bot ab, läuft der Hauptbot unverändert weiter.

- **Wallets:** `copy_wallets.txt`, eine Zeile pro Wallet im Format `Name: Adresse`. Austauschen ohne Code-Änderung.
- **Erkennung:** Helius-WebSocket (`logsSubscribe` je Wallet, im Gratis-Tarif enthalten), danach die vollständige Transaktion (bis Version 1). Abgefragt wird nur, was nach Handel aussieht; reine Transfers nur, wenn eine Position offen ist. Wallets mit mehr als 30 Meldungen pro Minute werden für die Schicht abgemeldet (Flutschutz). Kauf, Verkauf und Überweisung werden an den Salden erkannt, unabhängig von der Börse (Pump.fun, PumpSwap, Raydium, Meteora, Jupiter); Handel gegen USDC wird in SOL umgerechnet.
- **Konto:** jede Wallet 10 SOL, neue Runde, wenn leer und keine Position offen.
- **Kauf:** jeder Kauf des Traders ab 0,1 SOL = 0,2 SOL bei uns, auch Nachkäufe. Kleinere Käufe (Tests, Staub) werden ignoriert. Weicht unser Kaufkurs mehr als ±15 % vom Kurs des Traders ab, wird der Kauf blockiert. Kaufmeldungen älter als 60 s werden nie nachgekauft. Alles Ausgelassene steht als AUSGELASSEN mit Grund im Journal.
- **Verkauf:** derselbe Anteil, den der Trader verkauft, aber gesammelt: Teilverkäufe werden gemerkt (VERKAUF_GEMERKT) und erst ausgeführt, wenn mindestens 20 % der Position zusammenkommen. Steigt der Trader komplett aus oder überweist er die Coins (ÜBERWEISUNG), verkaufen wir sofort alles. Verkäufe sind nie blockiert.
- **Kein Take-Profit, kein Stop-Loss.** Am regulären Schichtende werden Positionen mit höchstens 1 % Restwert (−99 %) bereinigt.
- **Prüfungen** des Hauptbots laufen bei jedem Kauf mit und werden gespeichert, entscheiden aber nichts (ohne Solana Tracker).
- **Gebühren:** unsere Gebühr je Transaktion = die tatsächliche Netzwerkgebühr des Traders für diesen Trade (Grundgebühr, Prioritätsgebühr, Jito-Tip). Bot-Gebühren des Traders (z. B. 1 %) rechnen wir uns nicht an.
- **Vergleich mit dem Trader:** nur aufgezeichnete Trades. Hielt er Coins schon vor unserem Start, zählt bei seinen Verkäufen nur der Anteil aus aufgezeichneten Käufen. Nach einer Überweisung ist kein Vergleich möglich.
- **Gespeichert je Trade** (`copy/journal.csv`): Signatur, Zeit, Menge, Preis und Gebühren des Traders (Grundgebühr, Prioritätsgebühr, Jito-Tip, sonstige wie Bot-Gebühren), unser Preis, unsere Gebühr, Verzögerung in Sekunden, Preisabstand in %, Ergebnis. In `copy/konten.json` pro Wallet Konto, offene und geschlossene Positionen, jeweils mit dem Ergebnis des Traders auf demselben Coin.
- **Grenzen der Simulation:** Wir kaufen zum Jupiter-Kurs in dem Moment, in dem wir den Trade sehen. Die Gebühren-Vorteile des Traders lassen sich auf Papier nicht nachbilden; messbar sind Verzögerung und Preisabstand. Beim Kaufbetrag des Traders ist die Miete für ein neues Token-Konto (~0,002 SOL) enthalten.

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

## Dateien seit 28.09.

| Datei | Inhalt |
|---|---|
| `verlauf/JJJJ-MM-TT.csv` | Kursverläufe eines Tages: offene Positionen (~12 s), nach dem Verkauf (~36 s), knapp abgelehnt (~2 min) |
| `knapp_abgelehnt.csv` | Jeder knapp abgelehnte Coin mit Grund, Abstand zur Grenze und allen Merkmalen (seit 29.09. mit Herkunftsliste) |
| `verlauf.csv` | Alte Datei bis 27.09., wird nicht mehr fortgeschrieben |
