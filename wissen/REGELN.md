# REGELN für das Wiki

**Bereich:** Wissen aus unserem Paper-Trading-Projekt: Strategien, Experimente, Regeln (Tag N), Copy-Trader, Rug- und Manipulationsmuster, Werkzeuge/Datenquellen, Lehren aus Fehlern, Entscheidungen. Werbung (Empfehlungslinks, beworbene Coins, Kurse) nur als Markierung, nie als Wissen.

**Verbindlich** bleiben `STRATEGIE.md` (Regeln) und `CLAUDE.md` (Arbeitsweise). Das Wiki sammelt Wissen und beschließt nichts.

**Rohquellen:** `auswertungen/*.md`, `STRATEGIE.md` (Änderungsprotokoll), `videos/regeln.md`, `korrekturen.md` (liegt in `auswertungen/`), `CLAUDE.md` (Lehren), `copy_wallets.txt` (Adressen, Aufnahme-/Entfernungsgründe; offiziell seit 04.10.), `wissen/notizen/`. Für volle Adressen darf zusätzlich `scout/kandidaten.csv` per Skript gelesen werden (nur Adressen). Sie werden verlinkt, nie kopiert oder verändert. Video-Transkripte (`videos/transkripte/`, lokal) dürfen gelesen, aber nie zitiert oder ins Repo gelegt werden.

## Beim Einspeisen

1. Datum und Quelle vorhanden? Fehlt etwas: nicht verarbeiten, in `log.md` unter „Rückfragen“.
2. Aussagen extrahieren, nicht zusammenfassen. Eine Aussage = ein Satz, der für sich stimmt, mit Zahl und Datum. Unsicheres bleibt als unsicher markiert („geschätzt“, „nicht nachgerechnet“).
3. Jede Aussage einer Seite zuordnen. Entitäten (Trader/Wallets, Experimente, Regeln, Werkzeuge, Coins mit Besonderheit) sofort als Seite. Muster-Seiten (z. B. „Exit-Liquidität“, „Rug-Vorzeichen“, „Ausreißer verzerren Ergebnis“) ab 2 Quellen, beim ersten Durchlauf ohne Schwelle.
4. Jede Aussage bekommt `[[Quelle]]` als Link (Quellen-Seiten in `wiki/quellen/`, sie nennen den echten Pfad der Rohquelle).
5. Widerspricht eine neue Aussage einer alten: nicht überschreiben, mit Datum anhängen und markieren. Drei getrennte Zeichen:
   - ⚠️ **echter Widerspruch**: gleicher Zeitpunkt/Stand, beide Aussagen können nicht wahr sein. Bleibt stehen, bis es geklärt ist.
   - 🕒 **überholt**: alter Stand, der neuere gilt (Entwicklung über die Zeit, kein Fehler).
   - ✅ **geklärt**: ein früherer Widerspruch wurde aufgelöst (mit Verweis, wie).
   Kein Zeichen: Meinungsunterschiede und Gegenbefunde, bei denen beide Aussagen stimmen (kurz als „Abweichung“ bzw. „Gegenbefund“ benennen).
6. `index.md` und `log.md` aktualisieren.

**Entitäten:** eine Sache, ein Name, eine Seite. Wallets mit Kurzname und voller Adresse. Vor jeder neuen Seite in `index.md` prüfen, ob es sie schon gibt.

## Bei Fragen

Erst `index.md`, dann 1–3 passende Seiten, nur daraus antworten, mit Quelle. Nichts gefunden: „steht nicht im Wiki“.

## Verboten

Zusammenfassungen von Zusammenfassungen, Aussagen ohne Quelle, Änderungen an Rohquellen und an `wissen/notizen/`, Schlüssel/Secrets.

## Dateinamen und Ordner (technische Festlegung beim ersten Durchlauf)

- `wiki/` hat Unterordner `experimente/`, `regeln/`, `trader/`, `muster/`, `werkzeuge/`, `coins/`, `themen/`, `quellen/`; Seitennamen sind eindeutig (ASCII, ohne Leerzeichen), damit `[[Name]]` in Obsidian überall funktioniert.
- Quellen-Seiten beginnen mit `Q-`.
