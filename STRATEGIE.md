# Strategie NARRATIV

Paper-Trading-Bot für Solana-Memecoins. Die Regeln stammen aus 13 Lernvideos
(„Learning everything I know about memecoins", Tag 1–13). Es wird nur auf
Papier gehandelt.

## Regeln und ihre Herkunft

| Tag | Aussage im Video | Umsetzung im Bot |
|---|---|---|
| 1 | Nur Coins kaufen, die nicht gebündelt sind | TrenchBot: Bundle-Wallets halten < 10 %, beim Launch < 30 % gebündelt. Ohne Check kein Kauf |
| 2 | Bei großem Gewinn etwas vom Tisch nehmen | Bei 2x wird die Hälfte verkauft |
| 3 | Vor dem Kauf These und Verkaufsbedingung notieren | `journal.csv` mit These und Verkaufsbedingung. Verkauf, wenn die These bricht |
| 4 | Gewinner halten, solange die Story wächst | Der Rest nach 2x läuft weiter, Ausstieg erst 40 % unter dem Hoch oder bei Thesenbruch |
| 5 | Früh rein, solange es sich verbreitet | 15 Minuten bis 6 Stunden alt, Holder +15 % pro Stunde, Netto-Käufer, mindestens 3 organische Käufer, Social-Links vorhanden |
| 6 | Dev prüfen | Keine Rugs in der Dev-Historie, kein hohes Risiko, Dev hält höchstens 10 % |
| 7 | Nicht hinterherjagen, nicht größer setzen | Höchstens 3 Mio. USD Marktwert, höchstens +150 % in der letzten Stunde, feste Größe 0,2 SOL |
| 8 | Kein Copy-Trading | Keine Wallet-Signale |
| 9 | Ruhiger Markt: weniger handeln | Marktphase begrenzt die Positionen: heiß 3, normal 2, ruhig 1 |
| 12 | Vamping: den echten Coin finden | Bei gleichem Namen oder Symbol nur der Coin mit den meisten Holdern |
| 13 | Marktsignale prüfen | Marktphase aus Anzahl frischer Coins über 1 Mio. USD und deren Volumen, verglichen mit dem eigenen Verlauf |

Nicht automatisierbar: Tag 10 und 11 (Netzwerk, Community). Die Verbreitung
auf X oder TikTok (Tag 5) kann der Bot nicht direkt lesen. Er misst die
On-Chain-Spur, die eine Story hinterlässt.

## Wann verkauft wird

1. **2x erreicht:** Hälfte verkaufen
2. **These gebrochen:** Holder schrumpfen und Netto-Verkäufer, zweimal in Folge
3. **Liquidität abgezogen:** 30 % unter dem Einstieg
4. **Story abgekühlt:** nach dem Teilverkauf 40 % unter dem Hoch
5. **Notbremse:** −40 %
6. **Höchstdauer:** 24 Stunden

## Dateien

| Datei | Inhalt |
|---|---|
| `bot.py` | Der Bot |
| `portfolio.json` | Kontostand, offene und geschlossene Positionen |
| `journal.csv` | Jeder Kauf mit These, jeder Verkauf mit Grund |
| `abgelehnt.csv` | Geprüfte Coins und warum sie nicht gekauft wurden |
| `marktphase.json` | Verlauf der Marktphase |

Alle Schwellen stehen oben in `bot.py` und lassen sich dort ändern.
