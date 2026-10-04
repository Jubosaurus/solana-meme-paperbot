# Copy-Fehlbuchungen bis 03.10.

- 15 Verkäufe wurden doppelt ausgeführt (01.10. 19:15 – 02.10. 19:16 UTC): zusätzlich 1,014 SOL Erlös und 0,071 SOL Gebühren gebucht. [[Q-Korrekturen]]
- Ursache: Der stündliche Abgleich einer neuen Schicht holte Trades bis zur Positionseröffnung nach; gemerkt waren nur 60 Signaturen je Position. [[Q-Korrekturen]]
- Das Konto ist dadurch nicht um 1,01 SOL zu hoch (die Token der noch offenen Position wären sonst später zu anderem Kurs verkauft worden); sicher falsch sind zusätzliche Gebühren, Zeitpunkt und der Vergleich „wir gegen Trader“. [[Q-Korrekturen]]
- 279 von 632 `VERPASST_KAUF` waren falsch (188 gekauft, 32 Schatten, 59 bewusst ausgelassen); echte verpasste Käufe: 353. [[Q-Korrekturen]]
- 22 doppelt vorgemerkte Teilverkäufe ohne Geldfluss; eine 922M-Position (MODEL) doppelt geschlossen; eine Zrool-Position (DUGECOIN) verloren. [[Q-Korrekturen]]
- Behebung 03.10.: Der Copy-Bot liest beim Start aus `copy/journal.csv`, welche Trader-Signaturen schon verarbeitet sind. [[Q-STRATEGIE]]
- Alte Daten werden nicht umgeschrieben; die Auswertung rechnet die Zeilen aus `korrekturen.csv` heraus. [[Q-Korrekturen]]
