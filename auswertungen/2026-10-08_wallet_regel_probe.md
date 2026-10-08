# Probe: neue Wallet-Verlust-Regel auf die heutigen Wallets (08.10.2026, Abend)

Nur Auswertung vor dem Einbau, gerechnet mit den neuen gemeinsamen Funktionen `copy_bot.verlust_regel` und `scout_bot.replaceable_wallets` auf `copy/konten.json` (24 aktive Wallets, 6 freie Plätze). „Seit Start“ = Kontowert über alle Runden, offene Positionen zum letzten Kurs im Verlauf (kein zusätzlicher Abruf).

| Wallet | geschlossen | realisiert | seit Start (mit offenen) | offen | ohne Kurs | Urteil |
|---|---|---|---|---|---|---|
| 4DOV | 86 | 0,00 | −5,76 | 20 | 0 | **Regel erfüllt**, aber geschützt |
| Dior | 29 | −5,73 | −10,96 | 9 | 0 | 1 Position bis zur Regel (wäre sofort erfüllt) |
| C7bF | 29 | −1,27 | −1,50 | 3 | 0 | 1 Position bis zur Regel |
| 54QZ | 26 | −1,05 | −1,24 | 9 | 0 | 4 Positionen bis zur Regel |
| 8K7Z | 24 | −2,02 | −2,53 | 1 | 0 | 6 Positionen bis zur Regel |
| Pikalosi | 24 | −2,23 | −2,20 | 1 | 0 | 6 Positionen bis zur Regel |
| 77n6, Troupe, HoneyBadger-6kfX, 499R | 6 bis 19 | −0,5 bis −2,6 | −1,6 bis −2,8 | 0 bis 7 | 0 | unter 30 Positionen, noch kein Fall |

Alle anderen aktiven Wallets liegen über −1 SOL seit Start. Bei keiner aktiven Wallet fehlt ein Kurs.

## Antworten

- **Erfüllen die neue Regel heute:** genau eine, 4DOV (Schutzliste). Nach der alten Rechnung (nur realisierte) war es keine.
- **Ersetzbar wegen Verlust, sobald Kandidaten da sind:** heute 0. Ohne Schutzliste wäre es 4DOV. Mit der Schutzliste ist die nächste Wallet wahrscheinlich Dior (eine Position fehlt), danach C7bF, 54QZ, 8K7Z und Pikalosi, sobald sie 30 Positionen erreichen.
- **Zum Vergleich ohne Verlust-Regel:** Pikalosi und 2z7o stehen wegen des Bot-Hinweises aus dem Flutschutz (06.10. bzw. 07.10., Gültigkeit 7 Tage) ersetzbar da. Das ist die bisherige Bot-Regel, sie ändert sich nicht.
- Das Konto hat 24 von 30 Plätzen, die Automatik ersetzt Verlust-Wallets nur bei vollem Konto; die Warteliste hat 5 Einträge. Praktisch greift die neue Regel also erst, wenn die 30 voll sind.
