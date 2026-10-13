# Nachrechnung heisse_coins / endspurt gegen Kontrollgruppe (13.10.2026)

Eigenes Skript, nur Lesen von `experimente/*/portfolio.json` (Feld `closed`). Kosten = invested_sol x 2 % (endspurt 4 %). Zeitraum: Kontrollgruppe gefiltert nach `closed_at` >= Startzeit des Experiments (heisse_coins und Kontrollgruppe starteten gleichzeitig, 29.09. 08:33 UTC; endspurt 30.09. 09:53 UTC).

| Behauptung | Nachgerechnet | Urteil |
|---|---|---|
| heisse_coins 241 Trades, Summe -7.324, pro Trade -0.0304 (Kosten -0.0344), ohne 3 beste -0.0404 (-0.0444), 44 Gewinner | 241, -7.3237, -0.0304 (-0.0344), -0.0404 (-0.0444), 44 | stimmt |
| Kontrollgruppe (Zeitraum heisse) 614, -18.364, -0.0299 (-0.0339), ohne 3 beste -0.0325 (-0.0365) | 614, -18.3644, -0.0299 (-0.0339), -0.0325 (-0.0365), 110 Gewinner | stimmt |
| endspurt 515, -3.681, -0.0071 (-0.0151), ohne 3 beste -0.0087 (-0.0167), 216 Gewinner | 515, -3.6814, -0.0071 (-0.0151), -0.0087 (-0.0167), 216 | stimmt |
| Kontrollgruppe (Zeitraum endspurt) 563, -17.726, -0.0315 (-0.0355), ohne 3 beste -0.0343 (-0.0383) | 563, -17.7257, -0.0315 (-0.0355), -0.0343 (-0.0383), 97 Gewinner | stimmt |
| Kontowert heisse_coins 2.676, endspurt 6.319; offene Positionen 0 | frei (bankroll_sol) 2.6763 bzw. 6.3186, offene Positionen 0 und 0, also Kontowert = frei | stimmt |
| closed enthaelt nur eine Runde? | heisse_coins und endspurt: nur Runde 1 (runde = 1). Kontrollgruppe: Runden 1 und 2, jetzt 4 offene Positionen | stimmt fuer die beiden Experimente |

Hinweise:
- Keine Abweichung > 0.001. Fehlende Werte (pnl_sol, invested_sol): 0, Standard 0.3 kam nie zum Einsatz.
- Die Kontrollgruppe hat zwei Runden (Rundenwechsel); der Vergleich laeuft ueber alle Runden, was fuer Pro-Trade-Werte ok ist. Ihre 4 offenen Positionen sind nicht eingerechnet.
- Zeitfilter der Kontrollgruppe nach Verkaufszeit (closed_at), nicht nach Kaufzeit; Randeffekt maximal wenige Trades.
- Heisse_coins ist auch ohne Kontrollgruppe-Vergleich schlechter als roh/ohne die 3 besten (-0.0404 gegen -0.0325); endspurt liegt klar vor seiner Kontrolle, bei 515 Trades (>= 200) und halt ohne die 3 besten.
