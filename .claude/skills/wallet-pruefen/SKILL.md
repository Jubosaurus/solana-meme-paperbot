---
name: wallet-pruefen
description: Neue Wallets für das Copy Trading prüfen und aufnehmen. Verwenden, wenn der Betreiber Wallet-Adressen schickt (als Text, Liste oder Screenshot von GMGN, Kolscan o. Ä.), eine Prüfliste befüllen will oder fragt, welche Wallets ersetzt werden sollen.
---

# Wallets prüfen

Ablauf: Adressen sammeln → Prüfliste → Scout prüft → Ergebnis erklären → nach Zustimmung in die Copy-Liste. Antworten auf Deutsch, einfach.

## 1. Adressen vorbereiten

1. `git pull`.
2. Adressen aus der Nachricht des Betreibers übernehmen. Gültig sind Base58-Adressen mit 32 bis 44 Zeichen (ohne 0, O, I, l). Bei Screenshots sind Adressen oft abgekürzt (`54cb…XQhj`): dann um die vollständigen Adressen bitten, sie stehen hinter dem Kopier-Symbol neben dem Namen.
3. Mit `copy_wallets.txt` abgleichen, **auch mit den auskommentierten Zeilen**. Bereits bekannte Wallets mit ihrem Status nennen, z. B. „HSeC wurde am 30.09. als Bot entfernt“.
4. Namen vergeben: den Namen von der Plattform, sonst Anfang und Ende der Adresse (`54cb…XQhj`).

## 2. Prüfliste und Scout

1. `scout/pruefen.txt` mit den neuen Wallets **überschreiben** (alte Einträge raus, damit sie nicht erneut geprüft werden). Format je Zeile `Name: Adresse`, darüber eine Kommentarzeile mit Datum und Herkunft.
2. Nur diese Datei committen und pushen (Commit-Nachricht auf Deutsch).
3. Scout starten: `gh workflow run scout_runner.yml -f modus=normal`. Den Lauf mit `gh run list --workflow scout_runner.yml --limit 1` finden und mit `gh run watch <id>` abwarten (einige Minuten).
4. `git pull` und die neuen Zeilen mit `quelle = liste` aus `scout/kandidaten.csv` lesen.

## 3. Ergebnis erklären

Tabelle: Wallet | Urteil (✅ für uns im Plus / ➖ nach Reibung im Minus / ❔ zu wenig Coins / ❌ raus) | wichtigste Gründe (Rendite des Traders, ohne besten Coin, Haltedauer, Kaufgröße, Trades pro Tag, Fehleranteil).

Einordnen, was der Scout kann und was nicht:
- Er schaut auf 7 Tage und höchstens 150 Transaktionen. Bei wenigen Coins ist das Urteil unsicher.
- Seit 04.10. (Bewertung 3): Wallets mit Median-Kauf unter 0,05 SOL werden nicht bewertet („Kleinstkäufe“). Sonst blähen Kleinstbeträge die Rendite in % auf (Beispiel: 0,002 SOL → 472.633 %).
- Das Kriterium „20–700 Transaktionen“ wird vorerst **nicht geprüft**: Stufe 1 liest höchstens 1.000 Signaturen, `tx = 1000` heißt also nur „mindestens 1.000“.
- Gehaltene Coins zählen zum aktuellen Kurs; ein einzelner großer Gewinner wird zur Kontrolle abgezogen.
- Echte Copy-Daten sind aussagekräftiger als jede Schätzung. Plausible Kandidaten (kein Bot, aktiv, Kaufgröße ab 0,1 SOL) können auch bei ➖ oder ❔ live getestet werden, wenn der Betreiber das möchte.

## 4. In die Copy-Liste aufnehmen (nur nach Zustimmung)

1. In `copy_wallets.txt` neue Wallets unten anfügen, mit Kommentarzeile `# neu <Datum>: <Herkunft>`.
2. Zu ersetzende Wallets **auskommentieren, nicht löschen**: `# Name: Adresse   <- entfernt <Datum>: <Grund>`. Ihre Daten in `copy/` bleiben erhalten; offene Positionen laufen über Nachholen und Bestandsabgleich weiter.
3. Prüfen: keine doppelten Namen oder Adressen, Anzahl aktiver Wallets nennen (Ziel um 20, mehr ist möglich).
4. Subagent **code-pruefer** prüfen lassen, dann nur `copy_wallets.txt` committen und pushen.
5. Copy-Bot neu starten (laufenden Lauf von `copy_runner.yml` mit `gh run cancel` abbrechen, dann `gh workflow run copy_runner.yml -f modus=normal`) und nach etwa 2 Minuten im Log prüfen, dass alle Wallets angemeldet wurden („verbunden, X von X Wallets angemeldet“).
6. Eintrag im Änderungsprotokoll von `STRATEGIE.md`.
