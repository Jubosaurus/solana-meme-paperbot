# Gegenprobe Scout-Bewertung alt (Version 3) gegen neu (Version 4) – 13.10.2026

**Auftrag:** Betreiber 13.10., Schritt 2 (vor dem Einbau von `SCORING_VERSION` 4). Korrekturen CR5-1 bis CR5-4 aus dem Code-Review vom 08.10. (`auswertungen/2026-10-08_code_review.md`).

**Methode:**
- Rohdaten am 13.10. um 09:24 UTC auf GitHub geholt (Workflow `scout_gegenprobe.yml`, Lauf 38375908971): je Wallet die letzten bis zu 60 erfolgreichen Transaktionen aus 7 Tagen, dazu aktuelle Kurse. 1.619 Helius-Aufrufe (grob), 0 Fehler, 0 fehlende Transaktionen.
- Alte und neue Bewertung rechnen auf **denselben** Transaktionen und Kursen (lokal, `tools/scout_gegenprobe_rechnen.py`, alte Funktion wortgleich aus Commit 8d72e20073).
- Copy-Ergebnis: unser Ergebnis **seit Start** je Konto (`copy_bot.ergebnis_detail`, Stand `copy/konten.json` am 13.10. ca. 09:40 UTC).
- 29 Wallets: alle 25 seit 05.10. automatisch aufgenommenen (davon 15 seit 09.10.) plus Dior, C7bF, 6ANG, 4DOV.
- Sicherheit: Artefakt und Log enthalten 0 Treffer für `api-key`, `helius-rpc` und `http`. Rohdaten liegen nur lokal in `../paperbot-daten/gegenprobe_2026-10-13/` (nicht im Repository), das Artefakt wird nach 1 Tag gelöscht.

**Wichtige Grenze:** Die Bewertung nutzt die Transaktionen von **heute**, nicht die vom Tag der Aufnahme. „Aufnahme alt ja/nein“ heißt also: Würde die Wallet heute mit der alten Rechnung aufgenommen? Ob die neue Rechnung die Verlierer **damals** abgelehnt hätte, lässt sich mit diesen Daten nicht sagen (dafür bräuchte es die Transaktionen aus dem damaligen Fenster).

## Tabelle (sortiert nach Copy-Ergebnis)

Punkte = „für uns“ nach Reibung (Kopierkosten). Copy-Ergebnis 0,000 mit 0 geschlossenen Positionen = Konto vorhanden, aber noch kein kopierter Trade (5 Wallets erst seit 12./13.10. dabei; 3tgb seit 10.10. nur eine blockierte Schattenposition; FBXi am 12.10. wegen Stille entfernt).

| Name | Punkte alt | Punkte neu | Ohne besten % alt/neu | Gewinn SOL alt/neu | Coins alt/neu | Coins gehalten alt/neu | Überwiesen | Fehlend/abgerufen | Aufnahme alt | Aufnahme neu + Grund | Copy-Ergebnis SOL | Geschlossen | Ohne Kurs | Fehler |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| Croco-AC7K | -15,8 | -15,8 | -9,8/-9,8 | -2,052/-2,052 | 15/15 | 1/1 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | 5,467 | 48 | 0 | – |
| 2z7o | -9,2 | -9,2 | -3,2/-3,2 | 0,350/0,350 | 22/22 | 0/0 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | 2,759 | 182 | 0 | – |
| FKJE | – | – | -37,5/-37,5 | -8,715/-8,715 | 2/2 | 2/2 | 0 | 0/60 | nein | nein: zu wenig Coins im Zeitraum | 1,813 | 22 | 0 | – |
| 28ez | -2,6 | -2,6 | 7,4/7,4 | 4,854/4,854 | 13/13 | 0/0 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | 0,029 | 37 | 0 | – |
| FBXi | -39,4 | -39,4 | -33,4/-33,4 | -5,938/-5,938 | 4/4 | 0/0 | 0 | 0/60 | nein | nein: letzte Aktivitaet nicht unter 24 h | 0,000 | 0 | 0 | – |
| 3tgb | 0,8 | -27,3 | 3,8/-24,3 | 18,147/5,873 | 13/13 | 0/0 | 0 | 0/60 | ja | nein: fuer uns nicht im Plus nach Reibung | 0,000 | 0 | 0 | – |
| 5ixS | 165,3 | 110,9 | 168,3/120,9 | 22,983/20,685 | 7/7 | 3/2 | 1 | 0/37 | ja | ja | 0,000 | 0 | 0 | – |
| FZb6 | 23,8 | 23,8 | 26,8/26,8 | 8,608/8,608 | 4/4 | 2/2 | 0 | 0/32 | ja | ja | 0,000 | 0 | 0 | – |
| 7DFZ | 110,8 | 110,8 | 120,8/120,8 | 13,195/13,195 | 4/4 | 1/1 | 0 | 0/22 | nein | nein: letzte Aktivitaet nicht unter 24 h | 0,000 | 0 | 0 | – |
| 4u9a | 9,1 | -22,1 | 22,1/-9,1 | 10,405/-0,570 | 5/5 | 3/4 | 0 | 0/60 | ja | nein: fuer uns nicht im Plus nach Reibung | 0,000 | 0 | 0 | – |
| EToT | 1,3 | 1,3 | 4,3/4,3 | 4,687/4,687 | 4/4 | 2/2 | 0 | 0/27 | ja | ja | 0,000 | 0 | 0 | – |
| HMHv | 64,4 | 64,4 | 74,4/74,4 | 17,825/17,825 | 12/12 | 0/0 | 0 | 0/60 | ja | ja | 0,000 | 0 | 0 | – |
| DuEo | -37,8 | -37,8 | -31,8/-31,8 | -0,960/-0,961 | 3/3 | 0/0 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -0,133 | 8 | 0 | – |
| 9zWb | 9,7 | 4,8 | 15,7/10,8 | 63,416/51,821 | 11/11 | 1/0 | 1 | 0/57 | ja | ja | -0,247 | 2 | 0 | – |
| 4fy8 | -68,6 | -56,5 | -62,6/-50,5 | 68,879/-14,508 | 7/7 | 2/1 | 1 | 0/35 | nein | nein: letzte Aktivitaet nicht unter 24 h | -0,337 | 4 | 0 | – |
| 7LnP | -29,7 | -69,1 | -16,7/-53,1 | 0,992/-1,161 | 16/16 | 8/2 | 6 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -0,415 | 3 | 0 | – |
| DPQX | -110,0 | -110,0 | -100,0/-100,0 | -12,719/-13,063 | 3/3 | 0/0 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -0,491 | 3 | 0 | – |
| EoZs | -7,9 | -11,0 | 2,1/-1,0 | 6,180/5,292 | 17/17 | 1/0 | 1 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -0,497 | 8 | 0 | – |
| BlueMoon | – | – | –/– | 0,000/0,000 | 0/0 | 0/0 | 0 | 0/60 | nein | nein: zu wenig Coins im Zeitraum | -0,855 | 2 | 0 | – |
| HuyE | -6,1 | -6,1 | 3,9/3,9 | 14,244/14,244 | 11/11 | 0/0 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -0,912 | 39 | 0 | – |
| DWRA | -50,4 | -50,8 | -40,4/-40,8 | -9,179/-9,278 | 13/13 | 0/0 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -1,384 | 12 | 0 | – |
| CCBV | -52,9 | -52,9 | -42,9/-42,9 | -10,573/-10,573 | 12/12 | 0/0 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -2,010 | 8 | 0 | – |
| 8K7Z | – | – | –/– | -0,726/-0,726 | 1/1 | 1/1 | 0 | 0/60 | nein | nein: zu wenig Coins im Zeitraum | -2,259 | 38 | 0 | – |
| C7bF | -33,7 | -33,7 | -23,7/-23,7 | -5,371/-5,371 | 13/13 | 2/2 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -2,972 | 43 | 0 | – |
| 54QZ | -9,5 | -24,6 | -6,5/-21,6 | 13,629/-7,970 | 4/4 | 2/2 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -3,098 | 65 | 0 | – |
| 6ANG | -15,9 | -15,9 | -5,9/-5,9 | -2,846/-2,846 | 20/20 | 0/0 | 0 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -3,573 | 162 | 0 | – |
| HoneyBadger-6kfX | -45,4 | -47,3 | -39,4/-41,3 | -6,788/-8,588 | 7/7 | 2/1 | 1 | 0/60 | nein | nein: fuer uns nicht im Plus nach Reibung | -4,662 | 19 | 0 | – |
| 4DOV | – | – | –/– | -15,107/-15,107 | 1/1 | 1/1 | 0 | 0/60 | nein | nein: zu wenig Coins im Zeitraum | -10,684 | 120 | 0 | – |
| Dior | – | – | –/– | 0,000/0,000 | 0/0 | 0/0 | 0 | 0/60 | nein | nein: zu wenig Coins im Zeitraum | -23,849 | 48 | 0 | – |

## Was die Korrektur ändert

- Bei 19 von 29 Wallets ändern sich die Punkte nicht (davon 5 ohne Punkte, zu wenig Coins; sonst keine Altbestände, Überweisungen oder Reste in den 60 Transaktionen).
- Deutlich schlechter: 3tgb (+0,8 → −27,3), 4u9a (+9,1 → −22,1), 7LnP (−29,7 → −69,1), 5ixS (+165,3 → +110,9), 54QZ (−9,5 → −24,6), 9zWb (+9,7 → +4,8). Beim Gewinn des Traders: 4fy8 +68,9 → −14,5 SOL, 54QZ +13,6 → −8,0 SOL, 3tgb +18,1 → +5,9 SOL.
- Leicht besser (Rest nach Verkauf jetzt zum Kurs, CR5-3): 4fy8 (−68,6 → −56,5).
- Überweisungen kamen bei 6 Wallets vor (7LnP: 6 Coins).
- **Heute aufgenommen würden:** alt 7 Wallets, neu 5. Neu abgelehnt: **3tgb und 4u9a** (beide noch ohne kopierten Trade).

## Zusammenhang Scout-Punkte und unser Copy-Ergebnis (Rangkorrelation nach Spearman)

| Gruppe | alt | neu | n |
|---|---:|---:|---:|
| mindestens 5 geschlossene Positionen | 0,45 | 0,53 | 12 |

- Richtung positiv, aber bei 12 Wallets **nicht belastbar** (grobe t-Näherung: alt p ≈ 0,14, neu p ≈ 0,08; üblich wäre p < 0,05).
- Die Gruppe „alle mit Copy-Konto“ (n = 24, ρ ≈ 0,5) ist nicht aussagekräftig: Sie enthält 9 Wallets ohne einen einzigen kopierten Trade (Ergebnis 0).
- Auch hier gilt: Es sind die Punkte von **heute** gegen unser Ergebnis **der Vergangenheit**. Das zeigt eher, ob gute Trader gut bleiben, als ob der Scout vorhersagt.

## Weitere Zahlen

- Copy-Ergebnis seit Start der 25 automatisch aufgenommenen Wallets zusammen: **−7,23 SOL**, davon die 15 seit 09.10.: −2,09 SOL. Zum Vergleich: Dior −23,85 SOL und 4DOV −10,68 SOL (beide nicht von der Automatik aufgenommen).
- Von den 16 Wallets mit mindestens 5 geschlossenen Positionen (12 davon mit Punkten) bekämen heute **alle** weder alt noch neu eine Aufnahme. Bei der Aufnahme lagen sie laut Scout im Plus (z. B. HoneyBadger +13 %, 54QZ +29 %, DWRA +48 %, CCBV +38 %). Das gute Bild hielt also nicht an.

## Einordnung (Claude)

Die Rechenfehler CR5-1 bis CR5-4 sind real und jetzt behoben. Nach diesen Daten erklären sie aber nur einen kleinen Teil der Verluste. Das größere Problem: Ein gutes 7-Tage-Bild sagt wenig über die nächsten Tage voraus. Das ist eine Vermutung aus einer kleinen Stichprobe, keine bewiesene Tatsache.

---

## Wiederholung am 13.10. 14:35 UTC (Rohdaten neu, Version 4 live) und Vorschlag

**Quelle:** Workflow `scout_gegenprobe.yml`, Lauf 38414268797 (Rohdaten 14:33 UTC, 0 Fehler, 1619 Helius-Aufrufe), Tabelle in `auswertungen/2026-10-13_scout_bewertung_neu.md`. Die Zahlen weichen von der Morgen-Tabelle ab, weil sich die letzten 60 Transaktionen und die Kurse bewegt haben. Nicht vom `daten-pruefer` nachgerechnet (Summen und Zählungen mit eigenem Skript aus der Tabelle gerechnet).

**Frage: Hätte Version 4 die Verlierer abgelehnt?**
- **Dior, C7bF, 6ANG:** Ja, aber das hätte schon die alte Rechnung getan (Dior zu wenig Coins; C7bF −30,4 und 6ANG −4,2 Punkte, alt und neu gleich). Version 4 ändert an ihnen nichts.
- **Die 15 seit 09.10. Aufgenommenen** (Copy-Ergebnis zusammen −2,41 SOL, 13 noch aktiv, 4fy8 und FBXi schon entfernt): Mit heutigen Daten würden nur **9zWb und EToT** wieder aufgenommen (alt und neu). Version 4 fängt **3tgb** zusätzlich ab (alt +0,7 → neu −26,2). Alle anderen werden alt wie neu abgelehnt, 5ixS, FZb6, 7DFZ, HMHv nur wegen „letzte Aktivität nicht unter 24 h“ (gute Punkte, aber still).
- **Grenze:** Das sind die Daten von **heute**, nicht die vom Aufnahmetag. Dass heute abgelehnt würde, heißt nicht, dass am Aufnahmetag abgelehnt worden wäre.

**Rangkorrelation (Spearman, Punkte gegen unser Copy-Ergebnis):** mindestens 5 geschlossene Positionen (n = 12): alt 0,06, neu 0,27; alle mit Copy-Konto (n = 24): alt 0,44, neu 0,46. Am Morgen waren es 0,45 und 0,53 (n = 12). Ergebnis schwankt stark zwischen zwei Messungen, bei n = 12 **nicht belastbar**. Version 4 liegt beide Male etwas besser als Version 3, ohne dass man das beweisen kann.

**Einordnung (Claude, Vermutung):** Die Rechenfehler waren real, erklären aber nur einen kleinen Teil der Verluste. Ein gutes 7-Tage-Bild sagt wenig über die folgenden Tage voraus.

**Vorschlag `AUTO_AUFNAHME` (Entscheidung beim Betreiber):** **Aus lassen.** Gründe: (1) Version 4 ist erst zu 23 von 53 Prüflisten-Wallets bewertet und läuft noch an; (2) die Aufnahme der 15 hat bisher −2,41 SOL gekostet; (3) kein Nachweis, dass die Punkte die nächsten Tage vorhersagen. Erst wieder einschalten, wenn die Prüfliste komplett mit Version 4 bewertet ist und die Kriterien (z. B. Pflicht „nicht still“, Mindest-Kaufgröße) angeschaut wurden. Bis dahin: Aufnahme von Hand über die Prüfliste.

**Vorschlag Wallets raus (von den 13 aktiven der 15), nichts ist entfernt:**
- **Raus empfohlen:** 3tgb und 4u9a (Version 4 sagt klar nein: −26,2 und −30,2; noch kein kopierter Trade, kostet nichts außer Abfragen), **DPQX** (−76,7, Copy −0,44) und **7LnP** (−46,0, Copy −0,37, 6 überwiesene Coins).
- **Beobachten:** 28ez (53 Positionen, −0,42), DuEo (−0,02), EoZs (−0,50): kleiner Verlust, die Wallet-Regel (30 Positionen und über 1 SOL Verlust) greift selbst.
- **Behalten:** 9zWb, EToT (heute noch aufgenommen), 5ixS, FZb6, 7DFZ, HMHv (gute Punkte, derzeit still; die 72-Stunden-Regel greift selbst).

**Betrieb (Nebenfund):** Der erste Scout-Lauf mit Version 4 brach nach 45 Minuten ab, weil alle 53 Prüflisten-Wallets in einem Lauf neu bewertet werden sollten. Behoben mit einem Zeitbudget von 20 Minuten je Lauf (Commit nach diesem Bericht, Codex Sol freigegeben); danach lief der Scout grün, Versionswechsel erledigt (577 gespeicherte Bewertungen gesperrt, 14 Wartelisten-Einträge zur Neuprüfung), `copy_wallets.txt` unverändert.

## Entscheidung des Betreibers (13.10.2026)

- `AUTO_AUFNAHME` bleibt aus.
- Keine der 13 aktiven Wallets (aus den 15 seit 09.10.) wird entfernt. Grund: Die Scout-Punkte sagen unser Ergebnis nachweislich nicht voraus (Rangkorrelation 0,06 bis 0,53 bei n = 12). Die Entscheidung über Copy fällt im Strategie-Review. Meine Vorschläge „raus/beobachten“ oben sind damit nicht umgesetzt.
