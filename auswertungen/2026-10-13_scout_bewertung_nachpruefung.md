# Nachprüfung: Bericht 2026-10-13_scout_bewertung.md

Gerechnet am 13.10.2026 mit eigenem Skript aus der Berichtstabelle und `copy/konten.json` (`copy_bot.ergebnis_detail`).

| Punkt | Bericht | Nachgerechnet | Urteil |
|---|---|---|---|
| Gleiche Punkte alt/neu | 19 von 29 | 19 | stimmt |
| Aufnahme alt ja / neu ja | 7 / 5 | 7 / 5 | stimmt |
| Neu abgelehnt | nur 3tgb, 4u9a | genau diese beiden | stimmt |
| Wallets mit Überweisung | 6 | 6 | stimmt |
| Spearman (≥5 geschlossen, mit Punkten, Mittelränge) | alt 0,45 / neu 0,53, n=12 | alt 0,455 / neu 0,531, n=12 | stimmt |
| t-Näherung p (zweiseitig, 10 Freiheitsgrade) | alt ~0,14 / neu ~0,08 | t=1,61 (p≈0,14), t=1,98 (p≈0,08) | stimmt |
| Summe Copy-Ergebnis der 25 Auto-Wallets | −7,23 SOL | −7,232 (Tabelle) / −7,233 (aktuelle konten.json) | stimmt |
| Letzte 15 (ab 4fy8) | −2,09 SOL | −2,091 | stimmt |
| Dior / 4DOV | −23,85 / −10,68 | −23,849 / −10,684 | stimmt |
| 16 Wallets mit ≥5 geschlossenen Positionen, alle "Aufnahme neu: nein" | 16, 12 mit Punkten | 16, 12 mit Punkten, 0 mit Aufnahme neu ja (auch alt: 0) | stimmt |

Zusatz: Die Copy-Ergebnisse je Wallet aus `konten.json` weichen nirgends mehr als 0,01 SOL von der Tabelle ab, die Geschlossen-Zahlen stimmen.

Hinweise (keine Abweichungen):
- p-Werte sind nur eine grobe Näherung bei n=12; ob p auch bei Gleichstand (Mittelränge) exakt gilt, ist nicht garantiert.
- Die −7,23 SOL hängen nicht an einem Einzelwert: größter Verlust ist HoneyBadger mit −4,66, größter Gewinn Croco mit +5,47 (ohne ihn wäre die Summe etwa −12,7 SOL). Das steht so nicht im Bericht, ist aber eine Randbemerkung wert.
