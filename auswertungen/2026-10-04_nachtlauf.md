# Nachtlauf 03./04.10.2026 – Abschlussbericht

Zeitraum: 03.10. 22:30 UTC (00:30 deutsche Zeit) bis 04.10. 04:30 UTC (06:30 deutsche Zeit). Paper-Trading, kein echtes Geld.
Markierung vor dem Start: Tag `vor-nachtlauf-2026-10-03` (= Commit `70ca85788`).

## Kurzfassung

- Alles läuft: Hauptbot und Copy-Bot haben die ganze Nacht ohne Absturz Daten gepusht; kein Revert war nötig.
- Neu live: Flugschreiber, zwei mutige Experimente (Offene Tür, Serien-Devs), 4 neue Copy-Wallets (jetzt 22 aktiv), Exit-Liquidität im Dashboard.
- Videos: Nur 14 von 44 geplanten Transkripten kamen an (alle vom Kanal OrangieWEB3), danach hat YouTube die Abrufe gesperrt. Auswertung in `auswertungen/2026-10-04_videos.md`.
- Helius: Neue Funktionen zusammen geschätzt höchstens ~80.000 Credits/Monat (Grenze 150.000).
- Zwischen ca. 22:50 und 02:30 UTC war Pause wegen des Nutzungslimits von Claude.

## Schritt 1 (vor der Markierung erledigt)

Die 8 Entscheidungen und die Leitlinie wurden schon am 03.10. abends **vor** dem Tag eingespielt (sie fallen also nicht unter „zurücksetzen“):
Experimente Endspurt ohne Filter/Ohne Limit beendet + Notbremse 25 neu (`183eca937`), Leitlinie in CLAUDE.md (`a5f922441`), Zrool/Putrick/Cooker entfernt (`0b56ba81f`), Scout-Bewertung 3 (`7dc416ad6`), Scout-Prüf-Modus (`ffd658281`), DexScreener-Beobachtung (`ac31e323a`).

## Alle Commits seit der Markierung (je ein Satz)

Zeiten UTC (deutsche Zeit +2 h). Datencommits der Bots (`[skip ci]`) nicht aufgeführt.

| Commit | Zeit | Was |
|---|---|---|
| `7b300cb58` | 22:35 | Flugschreiber: je offene Position etwa jede Minute Liquidität, Holder, Top-10, Dev-Bestand, Handel 5 min und alle 10 min der Bestand der Bundler (Block 0) – nur Aufzeichnung, in `flugschreiber/`. |
| `fb2bfeafb` | 22:37 | `.gitignore`: Video-Transkripte bleiben nur auf dem PC. |
| `b5edee64f` | 22:39 | Zwei neue Experimente mit je 10 SOL: „Offene Tür“ (Story-Filter ohne Sicherheitsprüfungen) und „Serien-Devs“ (Devs, deren früherer Coin ≥ 300.000 $ erreichte). |
| `3c23c6c52` | 22:41 | Copy: 4 neue Wallets (G7b2, GeFg, 499R, 2Nxj), damit 22 aktive. |
| `982cb34d5` | 22:42 | Absicherung der neuen Experimente: ein Fehler bei einem Coin stoppt nie die Hauptstrategie. |
| `23811a5b7` | 02:33 | Dashboard: Exit-Liquidität je Copy-Trader (wie oft der Trader binnen 60 s bzw. schon vor unserem Kauf verkauft). |
| `4e9481661` | 02:47 | Video-Auswertung: 14 Videos von OrangieWEB3, Regeln, Widersprüche zu Tag 1–17, Tools-Tabelle, 4 Vorschläge (nur Doku). |
| (dieser Bericht) | | Abschlussbericht – nur Doku. |

Jede Änderung: Tests grün (zuletzt 227), Code-Prüfer „einspielbar“, Eintrag im Änderungsprotokoll von `STRATEGIE.md`, einzeln eingespielt. Hauptstrategie, Kontrollgruppe und Testregeln unverändert (Regressionsprobe gleich).

## Was jetzt live ist

| Funktion | Seit | Stand 04.10. ~02:43 UTC (vom Daten-Prüfer nachgerechnet) |
|---|---|---|
| Flugschreiber | Hauptschicht ab 00:33 UTC | 1.033 Zeilen, 111 davon (11 %) mit Bundler-Werten (nur Coins mit Block-0-Käufern) |
| DexScreener-Beobachtung | ab 00:33 UTC | 48 Einträge, 0 Fehler |
| Offene Tür | ab 00:33 UTC | 14 Käufe, 10 abgeschlossen (8 per Notbremse, je 1 Liquidität abgezogen / Story abgekühlt) – viel zu früh für ein Urteil |
| Serien-Devs | ab 00:33 UTC | 2 Käufe, 2 abgeschlossen (beide Notbremse) |
| Notbremse 25 | ab 00:33 UTC | 4 Käufe, 3 abgeschlossen (2 Notbremse, 1 Gewinn gesichert) |
| Copy: 22 Wallets inkl. 4 neue, neue Flugschreiber-Spalten in `copy/verlauf/` | Copy-Schicht ab 00:03 UTC | verbunden, Daten fließen |
| Scout-Prüf-Modus | nächster Scout-Lauf | Ergebnis 2FPk/54cb: alle Trades erkannt, nichts verpasst |
| Dashboard Exit-Liquidität | sofort (lokal, `start.bat`) | – |

Die Experimente urteilen erst nach 200 Trades gegen die Kontrollgruppe (unverändert).

## Helius-Schätzung je neuer Funktion

| Funktion | Credits/Monat (hochgerechnet) |
|---|---|
| Flugschreiber Bundler-Bestand (bis 8 Wallets je Coin alle 10 min, 1 Credit je Abfrage) | ≤ 69.000 |
| 4 neue Copy-Wallets | ~10.000 |
| Prüf-Modus (einmalig) | < 350 |
| DexScreener, Offene Tür, Serien-Devs, Copy-Spalten, Exit-Liquidität | 0 (andere Quellen bzw. vorhandene Daten) |
| **Zusammen** | **≤ ~80.000** (Grenze 150.000) |

Bitte im Helius-Dashboard nachsehen, ob der Verbrauch dazu passt (Stand vorher: ~520.000/Monat inkl. 922M, der inzwischen entfernt ist).

## Probleme und Reverts

- **Keine Reverts nötig.** Beide Bots liefen durchgehend (seit 22:30 UTC keine Datenlücke über 10 min; letzte Datencommits 02:42/02:43 UTC).
- **YouTube-Sperre:** Nach 14 Transkripten (nur OrangieWEB3) kam „IP blockiert“. Ein zweiter, langsamer Versuch brachte nichts Neues. Ich habe das respektiert und nichts umgangen. leensx100, TJRTrades und rasmrr fehlen deshalb ganz.
- **Nutzungslimit von Claude:** ca. 22:50–02:30 UTC Pause, danach weiter.
- Ein versehentlich getippter `git rebase -i` hatte keine Wirkung (geprüft: sauberer Stand).

## Videos in Kürze

Nur ein Trader (OrangieWEB3), 14 Videos. Seine Kernbotschaft ist Verhalten statt Filter: nicht dem Hype hinterher, nicht blind kopieren, Gewinne laufend mitnehmen. Er widerspricht sich selbst: In 8 Videos klagt er über „zu früh verkauft“, in 7 über „Gewinn wieder hergegeben“. **In allen 14 Beschreibungen steht Werbung mit Empfehlungslink** (Handels-App FOMO), in mehreren auch für Trading-Terminals und bezahlte Gruppen. Widersprüche zu uns: Wallet-Signale (Tag 8) und große Coins über 3 Mio. (Tag 7). Vorschläge (nichts umgesetzt): Wallet-Signal aus `copy/journal.csv` nachrechnen, Verkauf in Stücken an alten Verläufen nachrechnen, Konto „Große Coins“, Gebühren-Feld nur aufzeichnen. Details: `auswertungen/2026-10-04_videos.md`.

## Offene Fragen an dich

1. **Helius-Dashboard:** Passt der Verbrauch zur Schätzung?
2. **Wallet-Grenze:** 22 sind erreicht. Darf es mehr werden, oder erst stille Wallets (haru, 43Nu, Eshi, 42wu, koko) entfernen? Vorgemerkt: ab 05.10. 12:12 UTC entfernen, falls sie bis dahin nicht gehandelt haben.
3. **C7bF:** Bei 4 von 4 Käufen hat der Trader binnen 5 s wieder verkauft (Exit-Liquidität). Beobachten oder früh ersetzen?
4. **Videos:** Später noch einmal versuchen, die fehlenden 30 Transkripte zu holen (andere Tageszeit, langsamer)?
5. **Vorschläge aus den Videos** (siehe Video-Bericht): Nichts davon ist umgesetzt – nur nach deinem OK.

## Zurücksetzen im Notfall

Wenn du „zurücksetzen“ sagst, mache ich **nur** meine Code- und Doku-Commits seit der Markierung mit `git revert` rückgängig – Daten der Bots bleiben erhalten. **Niemals** `git reset --hard` oder Force-Push auf `main`.

Befehl (neueste zuerst, ein Revert-Commit je Änderung):

```
git pull
git revert --no-edit <Bericht-Commit> 4e9481661 23811a5b7 982cb34d5 3c23c6c52 b5edee64f fb2bfeafb 7b300cb58
python -m pytest
git push
```

Danach Hauptbot und Copy-Bot neu starten (sie nehmen den alten Code erst beim nächsten Start). Die neuen Datendateien (`flugschreiber/`, `experimente/offene_tuer/`, `experimente/serien_devs/`) bleiben liegen und stören den alten Code nicht.
