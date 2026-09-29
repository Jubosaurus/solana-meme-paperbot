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

## Dateien seit 28.09.

| Datei | Inhalt |
|---|---|
| `verlauf/JJJJ-MM-TT.csv` | Kursverläufe eines Tages: offene Positionen (~12 s), nach dem Verkauf (~36 s), knapp abgelehnt (~2 min) |
| `knapp_abgelehnt.csv` | Jeder knapp abgelehnte Coin mit Grund, Abstand zur Grenze und allen Merkmalen (seit 29.09. mit Herkunftsliste) |
| `verlauf.csv` | Alte Datei bis 27.09., wird nicht mehr fortgeschrieben |

