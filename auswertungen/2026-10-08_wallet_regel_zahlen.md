# Wallet-Regel „30 Positionen und über 1 SOL Verlust“: welche Zahl gilt? (08.10.2026)

Nur Auswertung, nichts geändert. Anlass: Die Entscheidung vom 08.10. nennt für 4DOV 80 Positionen und −4,25 SOL, `copy/konten.json` zeigte am Abend 84 Positionen und +0,20 SOL.

## Ergebnis

Es sind **zwei verschiedene Rechnungen**, beide stimmen:

- **A. Realisiert** (geschlossene Positionen, alle Runden): Summe `pnl_sol` der Liste `geschlossen` in `copy/konten.json`. Das rechnen die Regel im Code (`copy_bot.py` Zeile 982–984 und `scout_bot.py` `replaceable_wallets`, Zeile 784–786) und der Scout bei Verlust-Ersetzung. Offene Positionen zählen nicht.
- **B. Kontowert minus 10 SOL** (Ergebnis der laufenden Runde mit offenen Positionen zum Kurs; Dashboard „Ergebnis Runde“) bzw. **„Ergebnis seit Start“** (alle Runden, geschlossen plus offene Positionen; `dashboard/rechnung.py` `copy_konto`). Das stand in der Tagesauswertung vom 08.10. und in der Entscheidung.

Die Auswertung vom 08.10. nannte die Zahl B, die Automatik prüft aber A. Bei 4DOV ist der Unterschied groß, weil 18 bis 20 Positionen offen sind, die zusammen deutlich im Minus stehen.

## Zahlen je Wallet

Stand 1: `copy/konten.json` vom 08.10. 05:19 UTC (Zeitpunkt der Tagesauswertung, aus der Git-Historie). Stand 2: heute Abend (ca. 21:00 UTC).

| Wallet | Stand | geschlossen (Anzahl) | A realisiert, alle Runden | B Kontowert − 10 (laufende Runde) | B „seit Start“ (Dashboard) | offen | genannt am 08.10. |
|---|---|---|---|---|---|---|---|
| 4DOV | 08.10. früh | 80 | +1,21 | −4,25 | – | 18 | 80 / −4,25 |
| 4DOV | heute Abend | 86 | 0,00 | −5,84 | −5,84 | 20 | |
| G7b2 | 08.10. früh | 44 | −2,05 | +7,53 (Runde 2) | – | 4 | 44 / −2,40 |
| G7b2 | heute Abend | 46 | −1,71 | +7,45 (Runde 2) | −2,41 | 2 | |
| 7Cn1 | 08.10. früh | 39 | −3,19 | +7,32 (Runde 2) | – | 4 | 39 / −2,69 |
| 7Cn1 | heute Abend | 41 | −2,70 | +7,23 (Runde 2) | −2,71 | 2 | |
| 2Nxj | 08.10. früh | 77 | −1,40 | −1,40 | – | 0 | 77 / −1,40 |
| 2Nxj | heute Abend | 77 | −1,40 | −1,40 | −1,40 | 0 | |

„Kontowert − 10“ ist bei Wallets in Runde 2 irreführend, weil das Konto beim Rundenwechsel neu aufgefüllt wird. Dort ist „seit Start“ (alle Runden) die richtige Größe. Die korrigierten Journal-Zeilen (`auswertungen/korrekturen.csv`) ändern bei diesen vier Wallets nichts: Journal roh und bereinigt ergeben dieselben Summen wie `konten.json`.

## Ursache der Unterschiede

1. **4DOV:** Die −4,25 sind Kontowert minus 10 SOL einschließlich der 18 offenen Positionen (am 08.10. früh). Realisiert war 4DOV zu dem Zeitpunkt sogar im Plus (+1,21), jetzt bei 0,00. Nach der Regel im Code (A) ist 4DOV **gar nicht** unter der Grenze (−1 SOL). Der Verlust steckt in offenen Positionen, die noch nicht verkauft sind (mögliche Rugs und Totalverluste, die erst bei Schließung zählen).
2. **G7b2 und 7Cn1:** Die genannten −2,40 und −2,69 entsprechen eher „seit Start“ einschließlich offener Positionen (heute −2,41 und −2,71). Realisiert (A) war es am 08.10. −2,05 und −3,19. Beide Wallets liegen nach A und nach B über der Grenze von 1 SOL, die Entfernung ist also nach beiden Rechnungen gedeckt.
3. **2Nxj:** keine offenen Positionen, A gleich B, −1,40.
4. Die Abweichung zwischen „84 / +0,20“ (Abend, aus meinem Bericht zur Häufigkeit) und „86 / 0,00“ (jetzt) ist nur der Lauf der Zeit: 4DOV schließt laufend Positionen.

## Was die Regel meint

Die Regel im Code (A) rechnet **nur realisierte Ergebnisse** über **alle Runden** (die Liste `geschlossen` wird nie zurückgesetzt). Die Texte in `CLAUDE.md` („nach 30 Positionen und > 1 SOL Verlust“) und `STRATEGIE.md` sagen nicht, ob offene Positionen zählen. Der Regel-Hinweis im Dashboard (`copy_trading.py`, ab 30 Positionen und `pnl_geschlossen` unter −1) rechnet ebenfalls A; die Ergebnis-Anzeigen („Ergebnis seit Start“) zeigen B. Daraus folgt:

- Die Automatik **ersetzt 4DOV wegen Verlust derzeit nicht** (A = 0,00), unabhängig von der Beschlusslage. Sie würde es erst tun, wenn A auf −1 SOL oder weniger fällt, und auch dann nur bei vollem Konto (30 Wallets; heute 24).
- Der Fund CR5-7 war am Beispiel „−4,25“ getestet. Bei A = 0,00 ist die Ausnahme heute nicht nötig. Sie wäre eine Absicherung für den Fall, dass die realisierten Verluste später die Grenze erreichen (offene Verlustpositionen werden irgendwann geschlossen und zählen dann).
- **Frage an den Betreiber (Schritt 2):** Soll 4DOV (und künftig weitere) per Ausnahmeliste geschützt bleiben? Und soll die Regel künftig weiter nur realisiert (A) rechnen, oder offene Positionen zum Kurs einbeziehen (B)? Letzteres wäre eine Regeländerung und braucht die Zustimmung.
