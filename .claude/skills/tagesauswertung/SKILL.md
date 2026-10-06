---
name: tagesauswertung
description: Tägliche Auswertung aller drei Bots (Hauptstrategie mit Experimenten, Copy Trading, Wallet-Scout). Verwenden, wenn der Betreiber „Tagesauswertung“, „Auswertung“, „wie lief es“ oder Ähnliches schreibt.
---

# Tagesauswertung

Ziel: in wenigen Minuten ein ehrliches Bild, was seit der letzten Auswertung passiert ist, und klare Vorschläge. Antwort auf Deutsch, einfach, fürs Handy: kurze Tabellen, keine langen Listen.

## 1. Vorbereitung

1. `git pull` (die Bots pushen laufend Daten).
2. Letzte Auswertung lesen: neueste Datei in `auswertungen/` (Format `JJJJ-MM-TT.md`). Der Zeitraum dieser Auswertung beginnt dort, wo die letzte endete. Gibt es noch keine, die letzten 24 Stunden nehmen.
3. Den Betreiber nach dem aktuellen **Helius-Verbrauch** aus dem Dashboard fragen, falls er ihn nicht mitgeschickt hat. Nicht darauf warten, sondern mit dem Rest anfangen.

Für alle Berechnungen kurze Python-Skripte verwenden. **Große Dateien (`journal.csv`, `verlauf/`, `copy/`, `flugschreiber/`) nie direkt lesen, sondern per Python-Skript auswerten und nur das Ergebnis ausgeben. Subagenten bekommen nur die nötigen Zahlen, nicht ganze Dateien.**

**Gemeinsame Rechnung (seit 03.10.):** Kennzahlen mit `dashboard/rechnung.py` berechnen, nicht neu schreiben. Dann zeigen Auswertung, Dashboard und Discord dieselben Zahlen.

```python
import sys; sys.path.insert(0, "dashboard"); import rechnung as r
konten = r.alle_strategie_konten()                 # Hauptstrategie + Experimente: kontowert, trades, pro_trade, ohne_beste_pro_trade, offen, closed
kg = next(k for k in konten if k["key"] == r.KONTROLLE)
urteil = {k["label"]: r.vergleich_mit_kontrolle(k, kg) for k in konten}   # Testregel: 200 Trades, gleicher Zeitraum, ohne 3 beste
copy, gespeichert, journal = r.copy_konten()       # je Trader kontowert, vorsichtig, wartend, wir/trader_median_pct, verzoegerung; journal ohne Korrekturen
zeiten = r.commit_zeiten(); r.luecken(zeiten["Copy-Bot"], 20)   # Betrieb: Lücken über 20 min
r.messung()                                        # Quote 2 s später, 0,95-Notlösung
```

Fehlt eine Kennzahl, sie in `rechnung.py` ergänzen (mit Test), nicht nur im Auswertungsskript.

**Korrekturen herausrechnen (seit 03.10.):** Bevor `copy/journal.csv` ausgewertet wird, die Zeilen aus `auswertungen/korrekturen.csv` entfernen (gleiche `trader`, `trader_signatur`, `aktion` und `zeit`). Bei Zeilen ohne Signatur zählen nur `trader`, `aktion` und `zeit`. Was die einzelnen Arten bedeuten und wie sie zu behandeln sind, steht in `auswertungen/korrekturen.md`, unter anderem:
- Positionen mit `doppelter_verkauf` nicht in den Vergleich „wir gegen Trader“ nehmen.
- Den Kontowert aus `konten.json` bei 922M, HEBO und 4DOV mit dem Hinweis „enthält doppelte Verkäufe“ zeigen.

In der Auswertung kurz nennen, wie viele Zeilen herausgerechnet wurden. Kommen neue Fehlbuchungen dazu, dort nachtragen (alte Daten nie umschreiben).

## 2. Betrieb

- Lücken über 10 Minuten in `verlauf/` (Hauptbot) und über 45 Minuten in `copy/journal.csv` (Copy-Bot) im Zeitraum.
- `gh run list --limit 30` für alle drei Workflows: fehlgeschlagene oder abgebrochene Läufe? Bei Fehlern das Log mit `gh run view <id> --log-failed` lesen und die Ursache in einem Satz nennen.
- Lief der Scout seit der letzten Auswertung (Zeitstempel in `scout/kandidaten.csv`)?

## 3. Hauptstrategie und Experimente

Tabelle für den Zeitraum **und** seit Start: Konto | Trades | Gewinner | Summe SOL | Ø je Trade.
- **Immer beide Zahlen zeigen (Entscheidung 06.10.): roh und mit Kostenaufschlag** (2 % vom Einsatz je Rundlauf, Endspurt-Konten 4 %). `rechnung.py` liefert beide (`pro_trade`, `pro_trade_kosten`, `ohne_beste_pro_trade_kosten`, Urteil in `v['kosten']`, Text `rechnung.urteil_beide(v)`).
- Hauptstrategie gegen die **Kontrollgruppe** (Ø je Trade).
- Experimente mit mindestens 200 Trades ausdrücklich bewerten (gegen Kontrollgruppe, ohne die 3 besten Trades) und Beenden oder Weiterführen vorschlagen.
- **Paar-Experimente** (Notbremse 25, Drittel-Leiter: kaufen genau mit der Hauptstrategie) zusätzlich **Coin für Coin** gegen die Hauptstrategie: `rechnung.paarvergleich(exp_closed, haupt_closed)` (Anzahl Paare, besser/schlechter/gleich, Unterschied gesamt und ohne die 3 besten, größte Einzelunterschiede mit Verkaufsgrund). Dasselbe zeigt das Dashboard auf der Seite Strategie.
- Regel-Beobachtung: Wie liefen die als `FOMO_SPRUNG` (Tag 17) abgelehnten Coins in `knapp_abgelehnt.csv`? Hätten wir mit ihnen gewonnen oder verloren?

**Messung der Ausführungskosten (seit 03.10., nur Beobachtung):** `messung.csv` (Hauptbot und Experimente, Spalte `konto`) und `copy/messung.csv` (Copy, je Trader), Spalte `abweichung_pct` (+ = 2 s später schlechter), getrennt nach KAUF/VERKAUF. Die 0,95-Notlösung steht in der Journal-Spalte `notloesung` (Hauptbot und Experimente). Je Bot und getrennt nach Kauf und Verkauf zeigen:
- Median und den Wert, den jeder zehnte Trade überschreitet
- wie oft die 0,95-Notlösung gegriffen hat

Daraus grob schätzen, wie viel Verzögerung die Ergebnisse real kosten würde (Abweichung × 0,2 SOL × Anzahl Trades). Das ist eine Schätzung: Sandwich-Angriffe und gescheiterte Transaktionen sind darin nicht enthalten.

**DexScreener-Beobachtung (seit 04.10., nur Aufzeichnung):** `dexscreener.csv` je gekauftem bzw. knapp abgelehntem Coin: bezahltes Profil, Werbung, Community-Übernahme, Boosts, Zahlungszeitpunkte in Minuten vor dem Ereignis.
- Bis 100 Käufe aufgezeichnet sind, nur die Anzahl nennen.
- Danach prüfen, ob Gewinner und Verlierer sich unterscheiden (z. B. Werbung vor gegen nach unserem Kauf). Methode wie bei Strategie-Ideen: erste Hälfte finden, zweite bestätigen, ohne 3 beste.

## 4. Copy Trading

- Pro aktiver Wallet: Kontowert (frei + aktueller Wert der offenen Positionen, Kurse aus `copy/verlauf/`), Runde, geschlossene Positionen im Zeitraum, wir gegen Trader (Median je Position, nur gültige Trader-Vergleiche).
- Wartende Verkäufe (seit 03.10.): Positionen mit `verkauf_offen: true` in `copy/konten.json` (Jupiter-Ausfall beim Verkauf, Verkauf vorgemerkt) je Wallet auflisten (Coin, seit wann: erste `VERKAUF_GEMERKT`-Zeile mit „Ausfall“ im Hinweis in `copy/journal.csv` für Wallet und Coin). Kontowert dieser Wallets zusätzlich **vorsichtig** zeigen: diese Positionen mit Wert 0 gerechnet. Beide Werte nennen („Kontowert X SOL, vorsichtig Y SOL“). Wartet eine Position länger als 24 h, als Auffälligkeit melden.
- Verzögerung und Preisabstand beim Kauf (Median), Anteil blockierter Käufe, Ergebnis der Schattenpositionen. Seit 03.10. gibt es die Aktion `SCHATTEN_VERKAUF` (Teilverkauf einer Schattenposition, kein Geldfluss). Sie nicht als eigenen Verkauf zählen.
- Wallet-Regeln anwenden (Bot, 72 h still, nach 30 Positionen und mehr als 1 SOL Verlust prüfen) und Kandidaten zum Ersetzen nennen. Nichts selbst entfernen.

## 5. Scout

Neue Einträge in `scout/kandidaten.csv` im Zeitraum: Wie viele geprüft, wie viele mit positiven Punkten? Die besten mit Adresse nennen.

## 6. Helius

Verbrauch mit dem Wert aus der letzten Auswertung vergleichen, pro Tag und hochgerechnet auf den Monat (Budget 1 Mio.). Den größten Verursacher nennen, wenn erkennbar.

## 7. Nachprüfen und Abschluss

1. Die wichtigsten Zahlen vom Subagenten **daten-pruefer** nachrechnen lassen. Abweichungen korrigieren, bevor du antwortest.
2. Antwort an den Betreiber: erst das Wichtigste in drei Sätzen, dann die Tabellen, dann **Vorschläge** (nummeriert, je ein Satz Begründung). Auf Zustimmung warten, nichts davon selbst umsetzen.
3. Eine kurze Zusammenfassung als `auswertungen/JJJJ-MM-TT.md` speichern: Zeitraum, Kernzahlen je Konto, Helius-Stand, Vorschläge und was der Betreiber entschieden hat. Einspielen erst nach seinem OK, zusammen mit der nächsten freigegebenen Änderung oder einzeln.

## 8. Wiki einspeisen (nach dem Speichern des Berichts)

Erst nach Schritt 7.3, wenn der Bericht in `auswertungen/` liegt. Regeln stehen in `wissen/REGELN.md` – vorher lesen.

1. Neue Berichte in `auswertungen/` und neue Dateien in `wissen/notizen/` seit dem letzten Eintrag in `wissen/log.md` suchen (die Notizen nur lesen, nie ändern).
2. Je Quelle zuerst eine Quellen-Seite in `wissen/wiki/quellen/` anlegen (Pfad, Datum), dann Aussagen ausziehen (ein Satz, Zahl, Datum, `[[Quelle]]`), nicht zusammenfassen. Ohne Datum oder Quelle nicht verarbeiten, sondern in `log.md` unter „Rückfragen“.
3. Vor jeder neuen Seite `wissen/index.md` prüfen. Widerspruch zu einer alten Aussage: anhängen, mit Datum, nie überschreiben; ⚠️ nur für echte Widersprüche (gleicher Stand), 🕒 für überholt (neuerer Stand gilt), ✅ für geklärt (siehe `wissen/REGELN.md`).
4. `wissen/index.md` und `wissen/log.md` aktualisieren; am Ende Links prüfen (jede `[[...]]` hat eine Seite).
5. Nur Doku: einspielen wie andere Berichte, aber nichts aus `wissen/.obsidian/` (steht in `.gitignore`). Werbung nur als Markierung, keine Schlüssel, keine Transkripte.
