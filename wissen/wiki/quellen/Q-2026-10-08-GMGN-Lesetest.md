# Quelle: GMGN-Lesetest (08.10.2026)

- Rohquelle: `auswertungen/2026-10-08_gmgn_lesetest.md`.
- Ergänzender Plan: `auswertungen/2026-10-08_gmgn_plan.md`.
- Datum der Quelle: 08.10.2026.
- Alle getesteten Lese-Endpunkte lieferten Daten; Guthaben, IP und Signatur führten beim Test zu keiner Ablehnung. Der Test belegt nicht, dass spätere Abfragen oder andere Laufumgebungen dieselben Ergebnisse liefern. [[Q-2026-10-08-GMGN-Lesetest]]
- Es gab nach zu schnellen Abfragen eine HTTP-429-Antwort und eine kurzzeitige IP-Sperre; beim späteren Lauf mit Abstand trat das nicht auf. Die Sperrdauer wurde nicht bestimmt. [[Q-2026-10-08-GMGN-Lesetest]]
- Beim Einlesen einer Adresse aus `copy_wallets.txt` muss das Format `Name: Adresse` berücksichtigt und die Adresse nach dem Doppelpunkt gelesen werden. [[Q-2026-10-08-GMGN-Lesetest]]
- Die Betreiberentscheidung lautet: GMGN-Wallet nur als Zugang, kein Handel; Schlüssel ausschließlich als GitHub-Secret und keine GMGN-Werte im Repository. [[Q-2026-10-08-GMGN-Lesetest]]
- GMGN wird nur als zusätzliche Kandidatenquelle eingebaut. Der Betreiber hat den Einbau am 08.10. freigegeben; die Umsetzung läuft. [[Q-2026-10-08-GMGN-Lesetest]]
