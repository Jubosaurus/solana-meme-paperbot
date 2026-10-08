# Nachrechnung 08.10.2026 (Stand: Repo nach git pull, Journal bis 08.10. 05:22 UTC)

Direkt aus `portfolio.json` und `experimente/*/portfolio.json`, `copy/journal.csv`, `namenswellen.csv`, git.

## A) Geschlossen seit 06.10. 19:20 UTC (n / Summe SOL / Gewinner)

| Konto | Deine Zahl | Nachgerechnet | Urteil |
|---|---|---|---|
| Hauptstrategie | 20 / -0,662 / 3 | 20 / -0,662 / 3 | stimmt |
| Kontrollgruppe | 21 / -0,819 / 2 | 21 / -0,819 / 2 | stimmt |
| Endspurt viele Trades | 63 / +0,546 / 30 | 64 / +0,650 / 31 | Stand neuer (1 Trade mehr), kein Fehler |
| Offene Tuer | 174 / -4,927 / 36 | 175 / -5,037 / 36 | Stand neuer (1 Trade mehr) |
| Serien-Devs | 64 / -1,028 / 15 | 64 / -1,028 / 15 | stimmt |
| Heisse Coins | 27 / -1,629 / 3 | 27 / -1,629 / 3 | stimmt |

Gesamt seit Start (n, Ø je Trade roh): Haupt 185 / -0,0041 stimmt; Kontrolle 363 / -0,0277 stimmt; Endspurt 304 / -0,0054 (du 303 / -0,0058, Stand); Offene Tuer 528 / -0,0364 (du 527 / -0,0363, Stand); Notbremse 25 74 / -0,0128 stimmt; Drittel-Leiter 68 / -0,0095 stimmt.
Abweichung Endspurt/Offene Tuer: Summe +0,10 bzw. -0,11 SOL durch je 1 neu geschlossenen Trade nach deiner Rechnung (Live-Daten). Die Abweichung der Summe bei Endspurt (+19 %) kommt von einem einzelnen Gewinn-Trade von ca. +0,10 SOL.

## B) Paarvergleich gegen Hauptstrategie (gleicher Mint)

- Notbremse 25: 74 Paare, Differenz -0,412, ohne 3 beste -0,589, 48 besser / 24 schlechter / 2 gleich. Stimmt.
- Drittel-Leiter: 68 Paare, -0,375, ohne 3 beste -0,518, 34 / 28 / 6. Stimmt.
- Hinweis: Paarung nur ueber Mint; bei Mehrfachkaeufen desselben Mints wird der letzte Haupt-Trade genommen. Unter 200 Trades, also nur Hinweis, kein Urteil.

## C) Copy (copy/journal.csv, 318 Zeilen aus korrekturen.csv herausgerechnet)

| Punkt | Deine Zahl | Nachgerechnet | Urteil |
|---|---|---|---|
| Kauf Preisabstand, alle | Median 1,41 (n=4214, Mittel 2,14) | 1,41 (n=4216, Mittel 2,14) | stimmt (n +2 durch neuere Zeilen) |
| Kauf, Zeitraum | 0,44 (n=472, Mittel 1,14) | 0,45 (n=474, Mittel 1,13) | stimmt (Rundung/Stand) |
| Verkauf, alle | -0,53 (n=5291) | -0,53 (n=5291) | stimmt |
| Verkauf, Zeitraum | -0,82 (n=297) | -0,82 (n=297) | stimmt |
| 4DOV Kauf | -0,0 (n=316) | -0,04 (n=316) | stimmt |
| 4DOV Verkauf | +0,5 (n=163) | +0,52 (n=163) | stimmt |
| Summe pnl_sol "Position geschlossen" ohne HEBO | -8,83 | -8,829 bei exakt gleichem Hinweis; -9,706 wenn Hinweis nur "enthaelt" (inkl. nachgeholt, gesammelt, keine Quote); mit HEBO -10,705 | stimmt, aber nur bei exakter Textgleichheit (177 Zeilen). Mit allen Varianten von "Position geschlossen" sind es 204 Zeilen und -9,71 (ca. 10 % mehr). Nicht enthalten: TRADER_AUSSTIEG (-1,55) und Schichtende (-0,93) |
| 27 aktive Wallets | 27 | 27 | stimmt |

Hinweis: Mittel der Verkaeufe ist durch Ausreisser unbrauchbar (5000 bzw. 25000 %), Median ist richtig. Die Korrekturen aendern nur die Verkaufs-n (5307 auf 5291) und fast nichts am Median.

## D) Repo

- Commits 07.10. 00:00-24:00 UTC: 2347, stimmt.
- Seit 08.10. 00:45 UTC: jetzt 230 (NARRATIV 109, COPY 121) gegen deine 225 (106/119); Stand neuer, stimmt.
- Groesse: lokal `.git` loose 1,17 GiB, Pack 4,59 GiB (lokale Zahl, nicht die GitHub-Anzeige). Deine 2.116.732 KB (2,02 GiB) von GitHub ist nicht pruefbar ohne API-Zugriff.

## E) namenswellen.csv

12 Zeilen. Start: 7 (EVE, FROGE, ALT, HUMAN, CAP, GIRAFFE, WIF, SAM sind 8 Starts: EVE, FROGE, ALT, HUMAN, CAP, GIRAFFE, WIF, SAM = 8). Ende: 4 (EVE, FROGE, ALT als DEV_VERDAECHTIG; HUMAN als STORY_ZU_ALT), nicht 5.

| Punkt | Deine Zahl | Nachgerechnet | Urteil |
|---|---|---|---|
| Zeilen | 12 | 12 | stimmt |
| Starts | 8 | 8 | stimmt |
| Enden | 5 | 4 (Spalte art = ende) | weicht ab (4 statt 5; 8 + 4 = 12 passt) |
| Gruende | 3x DEV_VERDAECHTIG, 1x STORY_ZU_ALT, "1 EVE DEV_VERDAECHTIG" | 3x DEV_VERDAECHTIG (EVE, FROGE, ALT), 1x STORY_ZU_ALT (HUMAN) | EVE ist schon unter den 3 gezaehlt, nicht ein fuenftes Ende. Wellen insgesamt 8, 4 davon abgeschlossen (alle abgelehnt), 4 noch offen |

## Wichtigste Abweichungen

1. E: 4 Enden, nicht 5 (EVE doppelt gezaehlt); es sind 8 Wellen, nicht 5.
2. C: die -8,83 SOL gelten nur fuer den exakten Text "Position geschlossen"; inklusive der Varianten sind es -9,71 SOL.
3. A/D: Kleine Unterschiede (Endspurt, Offene Tuer, Commits) sind reiner Live-Datenzuwachs.
