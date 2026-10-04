# Testregeln für Experimente und Urteile

- Seit 30.09.: Entscheidung frühestens nach 200 Trades, Vergleich mit der Kontrollgruppe aus demselben Zeitraum; ein Experiment gilt nur als besser, wenn es das auch ohne seine 3 besten Trades bleibt. [[Q-STRATEGIE]]
- Jedes Experiment hat ein eigenes 10-SOL-Konto; ist es aufgebraucht, startet es neu mit 10 SOL (Rundennummer wird gespeichert). [[Q-STRATEGIE]]
- Beendete Experimente kaufen nichts mehr; offene Positionen laufen aus, die Daten bleiben (Liste `EXP_BEENDET` in `bot.py`). [[Q-STRATEGIE]]
- Messgenauigkeit: Unterschiede unter etwa 0,01 SOL je Trade sind vom Zufall der Ausführung kaum zu trennen (siehe [[Ausfuehrungsrauschen]]). [[Q-2026-10-03-Ueberpruefung]]
