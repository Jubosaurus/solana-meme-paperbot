# Große Überprüfung – 03.10.2026

Stand der Daten: 03.10.2026, ca. 20:20 UTC (22:20 deutsche Zeit). Alle Zahlen sind mit `dashboard/rechnung.py` gerechnet und vom Daten-Prüfer unabhängig nachgerechnet.

**Datenbasis**
- Die Korrekturen aus `auswertungen/korrekturen.csv` sind herausgerechnet.
- Copy-Daten vor den Reparaturen vom 03.10. (vor 12:31 UTC) sind unsicher. Die Spalte „vor Rep.“ zeigt, wie viele Positionen das betrifft.
- Große Verkäufe im Verhältnis zur Liquidität (über 2 % des Pools) sind als **Obergrenze, real unsicher** gekennzeichnet.

Es wurde nichts an Code oder Listen geändert. Alle Vorschläge warten auf dein OK.

---

## Kurzfassung (das Wichtigste zuerst)

1. **Keine Strategie verdient bisher Geld.**
   - Die einzige mit fälligem Urteil (Endspurt ohne Filter, 266 Trades) ist **besser als Zufall, aber im Minus**.
   - Das gilt für beide Zeithälften.
   - **Vorschlag: beenden.**
2. **Neue Strategie-Ideen:** Von 5 Ideen besteht nur eine (**Notbremse bei −25 %**), und auch die nur knapp. Die Kontrollgruppe spricht dagegen. Sie wäre höchstens ein Experiment mit geringer Erwartung.
3. **Copy Trading:**
   - **Seit Start:** −42,2 SOL über alle Wallets und Runden. Davon gehen −38,2 SOL auf 922M, der schon entfernt ist.
   - **Die 21 aktiven Wallets** liegen zusammen bei +0,7 SOL. Das hängt aber fast ganz an HEBO und dort an einem einzigen Coin (PIGEON). Ohne PIGEON stünde HEBO bei −8,8 SOL.
4. **Austausch:**
   - **Raus nach den Wallet-Regeln:** Zrool, Putrick und Cooker.
   - **Raus mangels Aktivität:** die 5 stillen Wallets haru, 43Nu, Eshi, 42wu und koko (nach 72 h ohne Trade, also ab 05.10. 12:12 UTC).
   - **Rein:** Ich habe **keinen Kandidaten, der unsere Kriterien erfüllt**. Vorschlag: die Plätze vorerst frei lassen (spart Helius) und die Kandidatensuche verbessern (Teil D).
5. **Soziale Medien:** Am sinnvollsten ist **DexScreener** (kostenlos, offiziell, ohne Schlüssel). Damit ließe sich „bezahlte Sichtbarkeit“ (Profil, Boosts, Werbung) als Beobachtung mitlaufen lassen. X/Twitter wäre das eigentliche Signal, kostet aber pro gelesenem Beitrag Geld und braucht ein Entwickler-Konto (nur nach Rückfrage).
6. **Neue Erkenntnis zur Messgenauigkeit:**
   - „Ohne Limit“ hat 60 von 60 Coins genauso gekauft wie die Hauptstrategie.
   - Trotzdem liegt es auf denselben Coins 0,48 SOL schlechter (−0,008 SOL je Trade), allein durch andere Verkaufszeitpunkte.
   - **Unterschiede unter etwa 0,01 SOL je Trade sind also vom Zufall der Ausführung kaum zu trennen.**

---

## Teil A – Strategien bewerten

Vergleich mit der Kontrollgruppe (sie kauft zufällig) **im selben Zeitraum**: Gezählt werden nur Trades, die nach dem späteren der beiden Starts geschlossen wurden. „Ohne 3 beste“ = SOL je Trade ohne die 3 besten Trades. Die Hälften sind die erste und zweite Hälfte der eigenen Trades nach Zeit.

| Konto | Trades | Summe SOL | SOL/Trade | ohne 3 beste | 1. Hälfte | 2. Hälfte | gegen Kontrollgruppe (gleicher Zeitraum) | Status |
|---|---|---|---|---|---|---|---|---|
| Hauptstrategie | 108 | ▼ −0,109 | −0,0010 | −0,0132 | +0,0028 | −0,0048 | 61 Trades: −0,0091 gegen −0,0214; ohne 3 beste −0,0304 gegen −0,0285 | noch zu früh · Tendenz gemischt |
| Zweite Welle | 12 | ▲ +0,240 | +0,0200 | −0,0517 | +0,0032 | +0,0367 | +0,0200 gegen −0,0214; ohne 3 beste −0,0517 gegen −0,0285 | noch zu früh · gemischt (nur 12 Trades in 4,5 Tagen) |
| Heisse Coins | 81 | ▼ −2,394 | −0,0296 | −0,0581 | −0,0595 | −0,0003 | −0,0296 gegen −0,0214; ohne 3 beste −0,0581 gegen −0,0285 | noch zu früh · Tendenz schlechter als Zufall |
| Ohne Limit | 60 | ▼ −1,205 | −0,0201 | −0,0420 | −0,0292 | −0,0110 | −0,0201 gegen −0,0214; ohne 3 beste −0,0420 gegen −0,0285 | noch zu früh · gemischt (siehe Hinweis) |
| Endspurt viele Trades | 118 | ▼ −1,949 | −0,0165 | −0,0202 | −0,0146 | −0,0184 | −0,0165 gegen −0,0242; ohne 3 beste −0,0202 gegen −0,0330 | noch zu früh · Tendenz besser als Zufall, im Minus |
| **Endspurt ohne Filter** | **266** | ▼ −2,724 | −0,0102 | −0,0127 | −0,0144 | −0,0061 | −0,0102 gegen −0,0242; ohne 3 beste −0,0127 gegen −0,0330 | **Urteil fällig: besser als Zufall, aber im Minus** |
| Kontrollgruppe | 213 | ▼ −4,561 | −0,0214 | −0,0285 | −0,0157 | −0,0270 | – | bleibt immer |

**Realistische Kosten**

Die Simulation kauft und verkauft zum Kurs der Quote, ohne Verzögerung. Die Messung „Quote 2 s später“ läuft erst seit etwa 18:20 UTC. Bisher gibt es diese Daten:

| Bot | Aktion | Messungen | Mittel | Median | jeder zehnte schlechter als | tatsächlicher Abstand (Median) |
|---|---|---|---|---|---|---|
| Hauptbot + Experimente | Kauf | 18 | −4,7 % | −0,8 % | +15,5 % | 5,5 s |
| Hauptbot + Experimente | Verkauf | 20 | −0,4 % | −0,1 % | +6,6 % | 2,8 s |
| Copy | Kauf | 50 | +1,8 % | +0,6 % | +6,1 % | 6,5 s |
| Copy | Verkauf | 85 | −0,6 % | 0,0 % | +3,6 % | 3,8 s |

(+ = später schlechter für uns.)

- **Zu wenig Daten für ein Urteil.**
  - Bei Copy-Käufen kostet Verzögerung im Mittel etwa 1,8 %.
  - Bei Hauptbot-Käufen streut es stark: meist nichts, aber einzelne Ausreißer über 15 %.
- **Der Abstand ist länger als geplant.** Wegen des Jupiter-Takts kommt die zweite Quote meist erst nach 3–6 s, nicht nach 2 s. Das ist eher realistischer, denn echte Transaktionen brauchen auch einige Sekunden.
- **Schätzung bis genug Daten da sind** (1–3 % je Seite, wie im Prüfbericht): Jede Strategie verliert zusätzlich etwa 0,004–0,012 SOL je Trade. Das betrifft alle Konten gleich, auch die Kontrollgruppe. **An den Vergleichen ändert es nichts, aber kein Konto käme damit ins Plus.**
- **Neue Prüfung** mit echten Kosten nach etwa 1 Woche Messung, also ab rund 10.10.

**Hinweis „Ohne Limit“ (Daten-Prüfer bestätigt)**
- Alle 60 Coins hat auch die Hauptstrategie gekauft. Das fehlende Positionslimit hat also nie gegriffen, und das Experiment misst seine Idee bisher nicht.
- Auf denselben 60 Coins: Hauptstrategie −0,728 SOL, Ohne Limit −1,205 SOL.
- Die Ursache sind andere Verkaufszeitpunkte. Beispiele:
  - einmal „Gewinn geschützt“ statt „Story abgekühlt“, 17–23 min später
  - einmal Notbremse statt Gewinnschutz
- Das ist kein Code-Fehler, aber eine wichtige Zahl: **Allein der Zufall der Ausführung erzeugt etwa 0,008 SOL je Trade Unterschied.**

### Empfehlungen Teil A

| Konto | Empfehlung | Begründung |
|---|---|---|
| **Endspurt ohne Filter** | **beenden** | Ab 266 Trades ist das Urteil fällig. Es ist besser als Zufall (−0,0102 gegen −0,0242, auch ohne 3 beste), aber in beiden Hälften im Minus. Mit realistischen Kosten wäre es noch tiefer im Minus. Die Hypothese (kurz vor der Graduation kaufen, raus bei der Graduation) bringt kein Geld. Das passt zu offenem Punkt 3 in CLAUDE.md. |
| Endspurt viele Trades | weiterlaufen bis 200 (bei ~40 Trades am Tag etwa 2 Tage) | noch zu früh. Tendenz wie bei „ohne Filter“: besser als Zufall, im Minus. Vermutlich gleiches Ergebnis. |
| Heisse Coins | weiterlaufen | noch zu früh. Tendenz schlechter als Zufall, auch ohne 3 beste. In der 2. Hälfte fast ausgeglichen. |
| Zweite Welle | weiterlaufen, aber beachten | Mit 12 Trades in 4,5 Tagen würde es etwa 70 Tage bis 200 Trades dauern. Das Ergebnis (+0,24) hängt an wenigen Trades (ohne 3 beste −0,05). |
| Ohne Limit | **zur Entscheidung** | Unter 200 Trades und kein Code-Defekt, nach der Regel also kein Beenden. Die Bedingung, die es prüfen soll, tritt aber nie ein. Möglichkeiten: weiterlaufen lassen (zeigt das Rauschen der Ausführung) oder als Ausnahme beenden und den Platz für ein neues Experiment nutzen. |
| Hauptstrategie | weiter | Im Vergleichszeitraum etwas besser als Zufall (−0,0091 gegen −0,0214). Ohne 3 beste aber leicht schlechter, also hängt es an wenigen Treffern. |
| Kontrollgruppe | bleibt | Vergleichsbasis. |

---

## Teil B – Neue Strategie-Ideen (Strategie-Tester)

**Vorgehen**
- Alle 5 Hypothesen wurden **vor** der Rechnung aufgeschrieben.
- Hälfte 1 (27.–30.09.) zum Finden, Hälfte 2 (01.–03.10.) zum Bestätigen.
- Kosten: Gebühr 0,0015 SOL je Kauf und Verkauf, „Stress“ = zusätzlich 2 % je Seite.
- Der Simulator der Verkaufsregeln stimmt auf den 33 Verläufen der Regressionsprobe exakt mit dem Bot überein.

**Datenmenge**
- 43 bzw. 46 Verläufe der Hauptstrategie mit Nachlauf (Hälfte 1 / Hälfte 2)
- 81 bzw. 132 Trades der Kontrollgruppe
- 134 bzw. 173 knapp abgelehnte Coins („zu alt“)

| # | Idee | Begründung, erwarteter Effekt | Hälfte 1 (Variante gegen heute) | Hälfte 2 | Urteil |
|---|---|---|---|---|---|
| H1 | Notbremse −25 % statt −40 % | Wer 25 % fällt, erholt sich selten; erwartet + 0,005–0,01 je Trade | −0,0115 gegen −0,0163; ohne 3 beste besser; Stress besser | +0,0165 gegen +0,0090; ohne 3 beste besser; Stress besser | **formal bestanden**, aber Kontrollgruppe dagegen (in beiden Hälften schlechter) |
| H2 | Hälfte schon bei 1,5x verkaufen statt 2x | Viele erreichen 1,5x, aber nicht 2x | −0,0143 gegen −0,0163 | +0,0051 gegen +0,0090 | nicht bestanden |
| H3 | Zeitstopp: nach 60 min unter Einstand raus | Coins, die nicht anspringen, laufen aus | gleich | +0,0054 gegen +0,0090 | nicht bestanden |
| H4 | Mindestliquidität 10–50k USD statt 5k | Dünne Pools = mehr Rugs | jede Schwelle schlechter | schlechter | nicht bestanden (Effekt umgekehrt) |
| H5 | „zu alte“ Coins (über 6 h) doch kaufen | Ältere Coins mit Wachstum laufen noch | −0,030 gegen −0,005 | −0,012 gegen −0,010 | nicht bestanden, die 6-h-Regel ist bestätigt |

**H1 genauer**
- **Kosten:** 3 spätere Gewinner wären vorher verkauft worden (PUNCH 3,4x, CASHED, AGENTS).
- **Ersparnis:** 46 Notbremsen-Trades verlieren je 0,01–0,08 SOL weniger.
- **Kontrollgruppe (Gegenprobe):** In beiden Hälften schlechter. Dort kostet die Regel große Läufer wie MASHUP 7,7x.
- **Fazit des Testers:** Sicherheit gering.
- **Ersatz-Vorschlag**, falls „Endspurt ohne Filter“ endet: Experiment **„Notbremse 25“**.
  - eigenes 10-SOL-Konto, kauft dieselben Signale wie die Hauptstrategie, nur Notbremse −25 %
  - Urteil nach 200 Trades (etwa 2 Wochen)
- **Günstigere Alternative ohne Code:** Die Hauptstrategie zeichnet 6 h nach jedem Verkauf weiter auf. Deshalb lässt sich H1 jede Woche auf neuen Tagen nachrechnen. Das Experiment bringt nur eines dazu: echte Verkaufskurse bei −25 %.

**Nebenbefunde**
- **Tag 17 (FOMO_SPRUNG, offener Punkt 4):**
  - Die 65 abgelehnten Coins hätten −0,042 SOL je Trade gebracht, zusammen −2,75 SOL. Die Hauptstrategie lag bei −0,010.
  - **Die Regel hat bisher gespart** (nur 2 Tage Daten).
- **Liquidität:** In der Kontrollgruppe liefen Coins unter 10k USD Liquidität besser. Das wurde erst hinterher gefunden, ist also nur ein Hinweis.
- **Simulation zu optimistisch:** Sie ist absolut zu gut (Verkauf ohne Slippage), der Vergleich zweier Varianten bleibt aber fair.

---

## Teil C – Copy-Wallets bewerten

**Seit Start** = alle Runden: geschlossene Positionen plus offene zum letzten Kurs. **Ohne besten Coin** = ohne das Ergebnis des besten Coins (alle Positionen derselben Mint). **Wir/Trader** = Median je geschlossener Position (nur gültige Vergleiche). **Reibung** = Gebühren ÷ Einsatz. **vor Rep.** = Positionen vor den Reparaturen vom 03.10. (Daten unsicher).

| Wallet | seit | seit Start | ohne besten Coin | bester Coin | Pos. | wir / Trader % | Haltedauer | Reibung | letzter Trade | vor Rep. | Einteilung |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HEBO | alt | ▲ +23,16 | ▼ −8,84 | PIGEON +32,00 ⚠️ | 91 | −28 / −14 | 4 min | 1,4 % | 0,7 h | 70 | **beobachten** – das Plus ist eine Obergrenze (PIGEON-Verkauf ≈ 21 % der Pool-Liquidität) |
| 4DOV | alt | ▲ +2,18 | ▲ +0,38 | PUMPE +1,80 | 34 | −8 / −7 | 38 min | 0,1 % | 0,1 h | 32 | **behalten** – auch ohne besten Coin im Plus, wir nah am Trader |
| 6ANG | alt | ▼ −0,37 | ▼ −0,97 | FIX6900 +0,60 | 55 | −13 / −8 | 1 min | 1,7 % | 0,6 h | 52 | **beobachten** (≥ 30 Pos., aber < 1 SOL Verlust) |
| Gake | alt | ▼ −0,13 | ▼ −0,15 | – | 4 | – | – | 0,1 % | 13,3 h | 4 | beobachten (wenig Aktivität) |
| Troupe | alt | ▼ −0,68 | ▼ −1,01 | PANDORA +0,33 | 14 | −34 / −46 | 19 min | 0,2 % | 11,7 h | 14 | beobachten (schwächster Kandidat zum Tausch) |
| Loopierr | alt | ▼ −0,71 | ▼ −0,75 | – | 6 | −35 / −34 | 92 min | 1,2 % | 0,1 h | 6 | beobachten (wenige Trades) |
| Putrick | alt | ▼ −2,14 | ▼ −6,73 | HOTBOT +4,59 | 229 | −23 / −13 | 1 min | 1,9 % | 6,5 h | 225 | **ersetzen** (Regel: ≥ 30 Pos. und > 1 SOL Verlust) |
| Cooker | alt | ▼ −2,67 | ▼ −2,96 | – | 73 | −6 / **+5** | 0 min | 0,2 % | 0,6 h | 70 | **ersetzen** (Regel). Auffällig: Der Trader verdient, wir nicht. Haltedauer ~0 min, also nicht kopierbar. |
| Zrool | alt | ▼ −15,63 | ▼ −17,12 | FIX6900 +1,49 | 126 | −30 / −14 | 1 min | 0,5 % | 13,5 h | 126 | **ersetzen** (Regel; Konto schon einmal aufgebraucht) |
| 3zsr | neu | ▲ +0,04 | ▼ −0,15 | – | 18 | −3 / +5 | 64 min | 0,0 % | 0,0 h | 13 | zu früh |
| Dior | neu | ▼ −0,06 | ▼ −0,58 | COCKROACH +0,52 | 8 | −50 / −39 | 267 min | 1,0 % | 1,0 h | 8 | zu früh |
| C7bF | neu | ▼ −0,09 | ▼ −0,09 | – | 2 | −19 / −14 | 1 min | 0,2 % | 0,1 h | 1 | zu früh |
| Pikalosi | neu | ▼ −0,40 | ▼ −0,69 | – | 7 | −26 / −2 | 3 min | 0,1 % | 0,5 h | 4 | zu früh |
| 77n6 | neu | ▼ −1,84 | ▼ −1,84 | – | 4 | −85 / −84 | 286 min | 0,0 % | 2,9 h | 2 | zu früh (4 Positionen, alle schlecht – der Trader selbst auch) |
| 2FPk | neu | 0 | 0 | – | 0 | – | – | – | 1,4 h | 0 | zu früh (handelt, aber bisher alles über der Preisgrenze → nur Schattenpositionen) |
| 54cb | neu | 0 | 0 | – | 0 | – | – | – | – | 0 | zu früh (2 Transaktionen, ungeprüft) |
| haru, 43Nu, koko, Eshi, 42wu | neu | 0 | 0 | – | 0 | – | – | – | kein Trade seit Start | 0 | **still** → Teil E |

**Summen**
- Die 21 aktiven Wallets liegen bei **+0,67 SOL**.
- Alle 36 Wallets seit Start, mit entfernten, liegen bei **−42,21 SOL**. 922M allein: −38,17 SOL in 5 Runden.
- Zum Vergleich: Am Nachmittag (16:45 UTC) zeigte das Dashboard noch −37,0 SOL. Seither sind vor allem die offenen Positionen von HEBO und 922M gefallen.

**Wallet-Regeln (vom Daten-Prüfer bestätigt)**
- **„≥ 30 Positionen und > 1 SOL Verlust“** trifft auf Zrool, Putrick und Cooker zu (und auf 922M, der schon entfernt ist).
- **72 h ohne Trade:** derzeit keine aktive Wallet.
- **Bot-Verdacht:** kein Flutschutz-Fall.

**Die 8 ungeprüften Transaktionen (2FPk, 54cb)**
- **Über Helius konnte ich sie nicht prüfen:** Der Schlüssel liegt nur auf GitHub, und eine einmalige Prüfung dort bräuchte Code oder einen neuen Workflow.
- **Ersatz-Weg:** Ich habe es über den kostenlosen öffentlichen Solana-Zugang versucht, aber der hat fast alle Anfragen abgelehnt.
- **Bisher geprüft** (aus der früheren Stichprobe):
  - 2FPk 02.10. 19:44 UTC: Token-Eingang ohne SOL, also kein Trade
  - koko: 2× SOL-Überweisung, kein Trade
- **Indiz:** Inzwischen handelt 2FPk sichtbar. Der Bot hat am 03.10. um 18:57 UTC einen Kauf erkannt (wegen +29 % Preisabstand nur als Schatten). Die Erkennung funktioniert also bei dieser Wallet.
- **Ergebnis: offen.**
- **Vorschlag:** ein kleiner Prüf-Modus im Copy-Bot (`--probe` mit Signaturliste), der über Helius die Transaktionen auswertet. Das ist eine Code-Änderung und braucht dein OK.

---

## Teil D – Neue Wallets suchen

**Quellen**
- **Scout-Rangliste:** 30 bewertete Wallets, davon 3 aus einem zusätzlichen Scout-Lauf heute um 20:15 UTC.
- **Gewinner-Coins der letzten 7 Tage:** Darin enthalten, denn der Scout prüft bei jedem Lauf frühe Käufer und Birdeye-Top-Trader der Gewinner-Coins.
- **Öffentliche Quellen:** Für Wallets gibt es keine, die erlaubt und ohne Konto nutzbar wäre.
  - Kolscan und GMGN gingen nur per Scraping, und das ist ausgeschlossen.
  - DexScreener liefert keine Trader.

**Kriterien:** PnL ≥ +50 %, Haltezeit ≥ 15 min, 20–700 Transaktionen, Kaufgröße 60–600 $ (SOL = 120 $ laut DexScreener), Gewinnrate ≥ 35 %, aktiv < 24 h, kein Bot, mindestens 5 abgeschlossene Coins, und **auch ohne besten Coin im Plus**. „Wenig Verfolger“ ist mit unseren Daten nicht messbar.

**Ergebnis: Kein neuer Kandidat erfüllt die Kriterien.** Die besten 10 (alle bewerteten Wallets nach erfüllten Kriterien):

| # | Wallet | Quelle | erfüllt | PnL | ohne besten | Haltezeit | Kauf | Gewinnrate | abgeschl. Coins | Bemerkung |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | C7bF…V2fF | Liste | 8/9 | +120 % | +25 % | 124 min | 155 $ | 45 % | 9 | **schon im Copy** – bester Kandidat, bei uns erst 2 Positionen |
| 2 | haru…o55N | Liste | 7/9 | +326 % | +13 % | 7 min | 152 $ | 80 % | 5 | schon im Copy, aber still |
| 3 | koko…PCaC | Liste | 7/9 | +402 % | +6 % | 7 min | 138 $ | 80 % | 5 | schon im Copy, aber still |
| 4 | Deh9…x7R5 | Birdeye | 6/9 | +57 % | +34 % | 41 min | 60 $ | 100 % | 4 | **neu**, aber 1.120 Trades am Tag (Bot-Verdacht) und nur 4 Coins |
| 5 | 2FPk…YR4e | Liste | 6/9 | +98 % | +26 % | 7 min | 119 $ | 75 % | 5 | schon im Copy |
| 6 | FuKH…vpri | Birdeye | 6/9 | +22 % | −17 % | 22 min | 72 $ | 44 % | 9 | neu, ohne besten Coin im Minus |
| 7 | 54cb…XQhj | Liste | 5/9 | +1055 % | +8 % | 8 min | 240 $ | 38 % | 12 | schon im Copy |
| 8 | 8zkg…sNsZ | Birdeye | 5/9 | +8 % | +5 % | 12 min | 218 $ | 62 % | 8 | neu, zu wenig PnL, Bot-Verdacht |
| 9 | 8p6F…R3t8 | früh | 5/9 | −18 % | −20 % | 0,5 min | 169 $ | 37 % | 19 | Sniper |
| 10 | 42wu…VEYm | Liste | 4/9 | +31 % | +4 % | 22 min | 96 $ | 71 % | 4 | schon im Copy, still |

**Bewertungsfehler des Scouts (2 Wallets)**
- **Die Wallets:** H2Ag…ByLV (84.602 Punkte) und CPi4…gmNy (455 Punkte).
- **Was dort passiert:** Sie kaufen Kleinstbeträge (Median 0,002 SOL) und haben kaum abgeschlossene Coins. Das bläht die Rendite in % auf.
- **Folge:** Sie gehören nicht oben in die Rangliste.

**„20–700 Transaktionen“ ist nicht prüfbar:** Der Scout liest höchstens 1.000 Signaturen. Fast alle Wallets stehen auf genau 1.000, also auf „mindestens 1.000“.

**Vorschläge (je Code-Änderung am Scout, nur mit OK; `SCORING_VERSION` erhöhen)**
1. Wallets mit Median-Kauf unter 0,05 SOL oder weniger als 5 abgeschlossenen Coins nicht bewerten.
2. Transaktionen im 7-Tage-Fenster zählen statt auf 1.000 zu kappen.
3. Weitere Kandidaten von dir: GMGN-/Kolscan-Listen wie am 02.10. als Text oder Bildschirmfoto → Prüfliste.

**Verbrauch dieser Überprüfung**
- **Birdeye:** 210 CUs (ein Scout-Lauf; Monat jetzt 2.730 von 28.000).
- **Helius:** nur der eine Scout-Lauf. Lokal nicht ablesbar, geschätzt unter 3.000 Credits. Bitte im Helius-Dashboard nachsehen.
- **Kostenloser öffentlicher Solana-Zugang:** rund 30 Anfragen, ohne Kosten.
- Budget eingehalten (60.000 Credits / 5.000 CUs).

---

## Teil E – Austauschvorschlag

**Raus**

| Wallet | Grund | Wann |
|---|---|---|
| Zrool | Regel: 126 Positionen, −15,63 SOL (Konto schon einmal aufgebraucht) | sofort |
| Putrick | Regel: 229 Positionen, −2,14 SOL; ohne HOTBOT −6,73 | sofort |
| Cooker | Regel: 73 Positionen, −2,67 SOL; Trader im Plus, wir nicht (Haltedauer ~0 min, nicht kopierbar) | sofort |
| haru, 43Nu, Eshi, 42wu, koko | still: seit Start 02.10. 12:12 UTC kein Trade (koko nur SOL-Überweisungen) | gemeinsam ab 05.10. 12:12 UTC (14:12 dt. Zeit), falls bis dahin kein Trade |

**Rein:** keine Empfehlung. Kein Kandidat aus Teil D erfüllt die Kriterien. Der nächstbeste neue (Deh9…x7R5) hat Bot-Verdacht und nur 4 Coins.

**Ergebnis:** 21 − 3 − 5 = **13 aktive Wallets** (Grenze 22). Freie Plätze sparen Helius-Credits.

**Weitere Tauschkandidaten**, falls später gute Kandidaten kommen (nach Regeln dürften sie noch bleiben):
1. **Troupe:** −0,68, ohne besten Coin −1,01; wir −34 % je Position, nur 14 Positionen.
2. **Loopierr:** −0,71; wir −35 %, nur 6 Positionen.

**Umsetzung erst nach deinem OK auf die fertige Liste:**
- Zeilen in `copy_wallets.txt` mit Datum und Grund auskommentieren, Daten bleiben.
- Offene Positionen laufen über den stündlichen Abgleich weiter.

---

## Teil F – Soziale Medien als Signal (nur Recherche)

Ziel: Tag 5 („früh rein, solange es sich verbreitet“) besser messen. Heute sehen wir nur die On-Chain-Spur und ob ein Coin Links hat (`social`).

| Quelle | Was messbar | Zugang | Kosten / Limits | Erlaubt? | Bot-/Kauf-Anfälligkeit | Historische Daten | Empfehlung |
|---|---|---|---|---|---|---|---|
| **X / Twitter** | Erwähnungen von Ticker/Mint, Wachstum, Accounts, Zeitpunkt | offizielle API (Entwickler-Konto nötig) | seit 2026 Abrechnung je Nutzung: 0,005 $ je gelesenem Beitrag (bis 2 Mio./Monat); alte Pakete (Basic 200 $/Monat) für Neue nicht mehr; Suche nur letzte 7 Tage | ja, mit Konto | hoch (Bot-Netze, bezahlte Posts) | nur 7 Tage | **zu teuer / Konto nötig** – inhaltlich das beste Signal; nur nach deiner Zustimmung (Konto + Kosten) |
| **Telegram** | Beiträge/Aufrufe in öffentlichen Kanälen | Bot-API liest Kanäle nur als Admin; sonst Client-API (MTProto) mit Konto | kostenlos | Client-API mit eigenem Konto erlaubt, aber Konto nötig | hoch (Call-Kanäle werden bezahlt) | nur ab Beitritt | **nicht ohne Konto** |
| **Reddit** | Beiträge/Kommentare in Subreddits | offizielle API mit Freischaltung | kostenlos nur nicht-kommerziell (100 Abfragen/min), Freischaltung 2–4 Wochen | nur nach Freischaltung | mittel | ja (Suche) | **zu unzuverlässig** – Meme-Coins entstehen auf X/Telegram, Reddit hinkt hinterher |
| **TikTok** | Videos/Hashtags | Research-API nur für Hochschulen und gemeinnützige Forschung | – | **nein** (kommerziell ausgeschlossen) | hoch | – | **nicht erlaubt** |
| **Pump.fun-Kommentare** | Antworten je Coin, Zeitpunkt | keine offizielle API (nur von Dritten dokumentierte Schnittstellen) | – | unklar, eher nein | sehr hoch (Bot-Kommentare) | ja | **nicht erlaubt / unzuverlässig** |
| **DexScreener** | Profil bezahlt (Links, Beschreibung), Boosts (bezahlte Sichtbarkeit), Werbung („orders“ je Token mit Zeitpunkt), Community-Übernahmen | offizielle API **ohne Schlüssel** | kostenlos, 60 Abfragen/min für Profil/Boost | ja | misst **bezahlte** Aufmerksamkeit, nicht echte – das ist gerade das Interessante (Marketing vor oder nach dem Kauf?) | nein, nur ab jetzt | **lohnt sich (als Beobachtung)** |
| **LunarCrush** | Social-Kennzahlen (Erwähnungen, „Galaxy Score“) aus X, Reddit, YouTube, TikTok | API mit Konto | Gratis begrenzt; API ab 24–240 $/Monat | ja, mit Konto | mittel | ja | **zu teuer**, deckt frische Pump.fun-Coins kaum ab |
| **Moni** | „Smart Follower“ von X-Accounts | API auf Anfrage | Preis auf Anfrage | ja, mit Vertrag | mittel | ja | zu teuer / unklar |
| **CoinGecko Trending** | Suchtrends | API (Demo-Schlüssel kostenlos, ohne Schlüssel sehr knapp) | 30/min, 10.000/Monat | ja | gering | nein | zu spät: nur etablierte Coins |
| **Solana Tracker** (vorhanden) | Social-Links/Filter je Token | vorhandener Schlüssel | 70 Abfragen/Tag (schon verplant) | ja | – | nein | nur Links, kein Wachstum |

**Vorschlag: DexScreener als Beobachtung** (wie der Mitläufer-Verdacht, ändert keine Kaufentscheidung)
1. **Aufzeichnung:** Beim Kauf und bei knapp abgelehnten Coins notieren, ob ein bezahltes Profil existiert, wie viele Boosts es gibt und wann Werbung bezahlt wurde (`orders`: Zeitpunkt gegen Coin-Alter und gegen unseren Kauf).
   - Abfragen: 1–2 je Coin, kostenlos, kein Schlüssel.
   - Neue Spalten hinten im Journal bzw. in `knapp_abgelehnt.csv`.
2. **Ab wann auswerten:** nach **≥ 100 Käufen mit Aufzeichnung**, also etwa 1–2 Wochen über Hauptstrategie und Kontrollgruppe zusammen.
   - Frage: Unterscheiden sich Gewinner und Verlierer, z. B. „Werbung erst nach unserem Kauf“ gegen „schon vorher bezahlt“?
   - Gleiche Methode wie Teil B: erste Hälfte finden, zweite bestätigen, ohne 3 beste.
3. **Erst wenn das trennt:** über eine Kaufregel sprechen.
4. **X/Twitter** bleibt der zweite Schritt, nur mit deinem OK zu Konto und Kosten. Je Kaufkandidat ~50–100 gelesene Beiträge × 0,005 $ = 0,25–0,50 $; bei ~100 Kandidaten am Tag wären das 25–50 $ am Tag.

Quellen:
- [X API Pricing 2026](https://www.postproxy.dev/blog/x-api-pricing-2026/)
- [X API Pricing 2026: All Tiers Compared](https://zernio.com/blog/twitter-api-pricing)
- [Reddit API Key, Limits, and Pricing 2026](https://www.socialcrawl.dev/blog/reddit-api-key-limits-alternatives-2026)
- [TikTok Research API limits](https://www.xpoz.ai/blog/guides/tiktok-research-api-limits-access-and-alternatives/)
- [DexScreener API](https://www.mintlify.com/ikhwanhsn/syra_agent/api/dexscreener)
- [pumpfun-apis (Drittanbieter-Doku)](https://github.com/BankkRoll/pumpfun-apis)
- [Telegram Bot API und Kanäle](https://community.make.com/t/watching-telegram-messages/30045)
- [LunarCrush Pläne](https://www.toolmage.com/en/tool/lunarcrush/)
- [Moni API](https://moni-discover-api.readme.io/)
- [CoinGecko keyless API](https://docs.coingecko.com/docs/keyless-public-api.md)
- [Solana Tracker Data API](https://www.solanatracker.io/blog/solana-data-api-sdk)

---

## Deine Entscheidungen

| # | Frage | Mein Vorschlag |
|---|---|---|
| 1 | Endspurt ohne Filter beenden? | ja |
| 2 | Ersatz-Experiment „Notbremse 25“ oder die Alternative ohne Code (wöchentliche Nachrechnung)? | Alternative ohne Code; Experiment nur, wenn du einen echten Kurstest willst |
| 3 | „Ohne Limit“: weiterlaufen oder als Ausnahme beenden? | weiterlaufen bis 200 (es misst gerade das Rauschen der Ausführung) |
| 4 | Zrool, Putrick und Cooker entfernen? | ja |
| 5 | Stille Wallets ab 05.10. 12:12 UTC gemeinsam entfernen, falls weiter still? | ja |
| 6 | Neue Wallets: Plätze frei lassen, bis bessere Kandidaten da sind? | ja; dazu Scout-Bewertung verbessern (Vorschläge 1–2 in Teil D) und GMGN-/Kolscan-Listen von dir |
| 7 | Prüf-Modus für einzelne Transaktionen über Helius (Code)? | ja, klein (für 2FPk/54cb und künftige Fälle) |
| 8 | DexScreener-Beobachtung (Code, nur Aufzeichnung)? | ja |
