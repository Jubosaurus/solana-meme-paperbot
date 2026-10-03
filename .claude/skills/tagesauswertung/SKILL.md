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

Für alle Berechnungen kurze Python-Skripte verwenden, keine großen Dateien komplett lesen.

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
- Hauptstrategie gegen die **Kontrollgruppe** (Ø je Trade).
- Experimente mit mindestens 200 Trades ausdrücklich bewerten (gegen Kontrollgruppe, ohne die 3 besten Trades) und Beenden oder Weiterführen vorschlagen.
- Regel-Beobachtung: Wie liefen die als `FOMO_SPRUNG` (Tag 17) abgelehnten Coins in `knapp_abgelehnt.csv`? Hätten wir mit ihnen gewonnen oder verloren?

**Messung der Ausführungskosten (seit 03.10., nur Beobachtung):** `messung.csv` (Hauptbot und Experimente, Spalte `konto`) und `copy/messung.csv` (Copy, je Trader), Spalte `abweichung_pct` (+ = 2 s später schlechter), getrennt nach KAUF/VERKAUF. Die 0,95-Notlösung steht in der Journal-Spalte `notloesung` (Hauptbot und Experimente). Je Bot und getrennt nach Kauf und Verkauf zeigen:
- Median und den Wert, den jeder zehnte Trade überschreitet
- wie oft die 0,95-Notlösung gegriffen hat

Daraus grob schätzen, wie viel Verzögerung die Ergebnisse real kosten würde (Abweichung × 0,2 SOL × Anzahl Trades). Das ist eine Schätzung: Sandwich-Angriffe und gescheiterte Transaktionen sind darin nicht enthalten.

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
