# Brand & Design Guidelines: NEXUS CORE

> **Leitsatz:** Nexus Core – Centralized Intelligence · Algorithmic Precision

---

## 1. Brand Strategy & Kernbotschaft

NEXUS CORE transformiert das Dashboard von einem funktionalen Entwickler-Tool zu einem hochpräzisen, institutionellen Krypto-Trading-Terminal. Es steht als zentraler Knotenpunkt für alle Bots, Listings, Strategietests und Kennzahlen.

### Marke und Logo (Stand 07.10., Nexus Core T3)

Die vorhandenen PNGs in `dashboard/static/` sind verbindlich: `nexus-core-logo-text.png` zeigt Zeichen und Wortmarke waagerecht, `nexus-core-bildzeichen.png` nur das quadratische Zeichen. Beide haben einen transparenten Hintergrund. `stil.logo_einbinden()` verwendet die Wortmarke mit `st.logo(..., icon_image=<Bildzeichen>, size="large")`. CSS setzt das Seitenleisten-Logo auf 56 px Höhe, den Seitenleisten-Kopf auf 76 px und das eingeklappte Bildzeichen am Desktop auf 44 px (sichtbares Zeichen wegen des transparenten Bildrands rund 36,5 px). Selektoren: `stSidebarLogo`/`stLogo` und `stHeaderLogo`. Die Fußzeile bettet ausschließlich `nexus-core-bildzeichen-klein.png` (96 × 96, rund 19 KB) ein. Das Favicon bleibt `favicon.png`.

Unter dem Logo steht zusätzlich der Leitsatz „Centralized Intelligence · Algorithmic Precision“ in Inter, 12 px, Großbuchstaben, `TEXT_LEISE`. Am Handy entfällt dieser zusätzliche Leitsatz. Die obere Streamlit-Leiste ist deckend, am Desktop 48 px und am Handy 56 px hoch, ohne Schatten. Bis 640 px ist das eingeklappte Bildzeichen fest 48 × 48 px groß (sichtbares Zeichen rund 40 px); seine Bildränder und Streamlit-Abstände sind eingerechnet. Öffnen- und Schließen-Knopf der Seitenleiste haben je 44 × 44 px Tippfläche (`stExpandSidebarButton`, `stSidebarCollapseButton`).

Neben dem Bildzeichen in der Fußzeile steht der vollständige Leitsatz in Inter, 12 px, `TEXT_LEISE`, Großbuchstaben und mit leichtem Buchstabenabstand. Bis 640 px Breite entfällt der Vorsatz „Nexus Core –“; „Centralized Intelligence · Algorithmic Precision“ darf umbrechen und wird nicht abgeschnitten.

Das Manifest referenziert `icon-192.png` (192 × 192) und `icon-512.png` (512 × 512); beide haben einen dunklen Hintergrund und halten die Schutzfläche für maskierbare Symbole ein. `background_color` und `theme_color` bleiben `#080B11`. `apple-touch-icon.png` (180 × 180) liegt bereit, wird aber nicht als Manifest-Icon ausgegeben: Streamlit bietet hier keine saubere Einbindung als `apple-touch-icon` im Dokumentkopf. Auch das Manifest wird weiterhin nicht per JavaScript eingebunden.

Die Bilder stammen aus `tools/logo_aus_vorlage.py`. Vorhandene PNGs verwenden; nur bei einer ausdrücklich beauftragten Logo-Änderung neu erzeugen.

### Kernwerte & Vermittlungsziel
1. **Souveräne Kontrolle & Systemintegrität (Cockpit-Effekt):**
   * *Aussage:* „Das System hat alles im Griff – kein Rauschen, keine unbemerkten Fehler.“
   * *Umsetzung:* Subtile Status-Dots für Bot-Zustände, klare Latenz-Indikatoren und handlungsorientierte Warnmeldungen statt optischem Alarmismus.
2. **Mathematische Präzision & Statistische Schärfe:**
   * *Aussage:* „Hier wird nicht spekuliert, sondern systematische Edge verwaltet.“
   * *Umsetzung:* Strikt tabellarische Typografie (Monospace-Ziffern) für SOL-Beträge und Trade-Counts, klare Trennung zwischen Test-, Kontroll- und Hauptstrategien.
3. **Technologischer Fortschritt ohne Ablenkung:**
   * *Aussage:* „Modernste Infrastruktur für anspruchsvolle automatisierte Execution.“
   * *Umsetzung:* Deep-Slate-Darkmode für lange Sessions, fokussierte Akzentfarben (Indigo) für Navigation und neutrale Fortschritte, während Signalrot und Smaragdgrün rein Performance-relevanten Daten vorbehalten bleiben.

---

## 2. Design System & Farbpalette

| Token | Hex-Code | Semantik & Verwendung |
| :--- | :--- | :--- |
| **Canvas Background** | `#080B11` | Extrem tiefes Schieferblau. Bildet das Fundament und schont die Augen. |
| **Card Surface** | `#0F172A` | Strukturierte Inhaltskarten mit dezentem 1px Border (`#1E293B`). |
| **Nexus Indigo (Brand Primary)** | `#6366F1` | Identitätsfarbe: Logo-Akzent, aktive Reiter, Fortschrittsringe, Fokusrahmen. |
| **Execution Emerald (Profit / OK)** | `#10B981` | Aktive Bot-Status, positive PnL-Entwicklung, erfolgreiche Runden. |
| **Risk Crimson (Loss / Drawdown)** | `#F43F5E` | Negative Renditen, Drawdowns, kritische Performance-Werte. |
| **Advisory Amber (Alert / Sync)** | `#F59E0B` | Verzögerte Scouts, Outlier-Warnungen, Listing-Benachrichtigungen. |

---

## 3. Typografie-Regeln

* **Headings / Logo:** `Space Grotesk` oder `Inter Tight`
  * *Einsatz:* Hauptnavigation, Seitenüberschriften („Übersicht“, „Strategie & Experimente“).
  * *Wirkung:* Technisch, markant, architektonisch.
* **Body / UI Labels:** `Inter`
  * *Einsatz:* Filterleisten, Statusbeschreibungen, Listing-Tags, Erklärtexte.
  * *Wirkung:* Neutrale Formgebung und maximale Lesbarkeit in kleinen Schriftgraden.
* **Finanzdaten & Zahlenreihen:** `JetBrains Mono` (mit `font-variant-numeric: tabular-nums`)
  * *Einsatz:* SOL-Beträge, Trade-Zähler, PnL-Prozente, Wallet-IDs, Latenzen.
  * *Wirkung:* Feste Zeichenbreite verhindert Layout-Sprünge bei Live-Datenupdates.

---

## 4. Komponenten & UI/UX-Spezifikationen

### A. Navigation & Systemstatus
* **Header:** Linksbündiges NEXUS CORE Logo (transparentes PNG mit Zeichen + Wortmarke).
* **Bot-Statusanzeigen:** Kompakte Status-Pills mit pulsierenden 6px-Indikatoren:
  * `[● Läuft] Hauptbot · 0m`
  * `[● Läuft] Copy-Bot · 1m`
  * `[▲ Verzögert] Scout · 11h`
* **Tabs:** Flache Struktur mit 2px Indigo-Unterstrich bei aktiven Modulen anstelle massiver Kasten-Hintergründe.

### B. KPI-Cards & Datenblöcke
* **Metriken:** Große, fette Zahlen (`24px`–`32px` in Monospace) für Hauptwerte (z. B. `9,91 SOL`).
* **Vergleichswerte:** Sekundäre Labels (z. B. `-0,092 SOL seit Start`) direkt darunter mit klarer Farbcodierung (Risk Crimson).
* **Sparklines:** Feine Vektorlinien mit leichtem Glow und weichem vertikalen Verlauf ins Transparente unter der Linie für Tiefenwirkung.

### C. Feeds & Tabellen (Listing & Copy Trading)
* **Listing-Karten:** Kompakte Badges für Exchange und Paar (`KRW-BR`, `KRW-POD`) mit dezentem Zeitstempel-Chip.
* **Warnhinweise / Outlier:** Schmale Infobars mit Amber-Border (`#F59E0B`) und direktem Aktionsbutton (z. B. „Ausreißer filtern“) statt überdimensionierter Textboxen.
* **Trader-Ranking:** Trader-IDs in Monospace kombiniert mit proportionalen horizontalen Mini-Balken für den schnellen visuellen PnL-Vergleich auf einen Blick.

### D. Qualitätsschleifen Runde 1 und 2 (07.10., Karten 20, 22 und 23)

* **Übersicht:** Seitenkopf und Status, Konten-Kennzahlen (Hauptstrategie, Kontrollgruppe, Copy seit Start, Copy ohne besten Trader), Ausreißer-Hinweise, „Läuft gut/schlecht“, Hauptstrategie und Experimente samt Tabelle und Vergleich, danach „Was ist neu?“ und „Für dich wichtig“. Berechnungen, Werte und ihre Beschriftungen bleiben unverändert.
* **Tabellen:** Volle Inhaltsbreite statt erzwungener Inhaltsbreite, 6 × 8 px Zellabstand, 12 px Kopfzeilen mit Wortumbruch; Zahlen bleiben ohne Umbruch in JetBrains Mono. Am Handy zeigen ab sechs Spalten ein rechter Indigo-Rand mit Schattenverlauf und ein Pfeil oberhalb die Wischrichtung. Bei 1280 px nutzen die Haupttabellen höchstens sieben Spalten: Testurteil steht in zwei sichtbaren Tabellen (alle Roh/Kosten-Werte samt Summen), Scout, Copy und Betrieb halten weitere Kennzahlen in schmalen Tabellen unter „Weitere Kennzahlen und Hinweise“ bereit. Es gibt keine leeren Trennzeilen für inaktive Trader oder Wallets ohne Ergebnis; jede Datenzeile gehört zu einem Trader. Text und Kopfzeilen dürfen umbrechen; nur Zahlen bleiben einzeilig. Lange Copy-Hinweise stehen mit dem letzten Trade in einer eigenen Detailtabelle. Am Handy ist die erste Textspalte höchstens 7 rem breit, damit „laufende Runde“ durch Wischen vollständig erreichbar bleibt. Tabellen mit mehr als zwölf Zeilen haben auf allen Bildschirmbreiten eine innere Scrollfläche: höchstens 70 vh und 480 px, auch bei zuvor gesetztem `hoehe=None`. Oberhalb steht „N Zeilen – in der Tabelle scrollen“; die Kopfzeile bleibt stehen. Native Tabellen über 200 Zeilen sind ebenfalls auf höchstens 480 px begrenzt und nennen die Zeilenzahl.
* **Wallet-Wächter:** Kompakte Liste mit Wallet, Symbol und Ampelwort, Grund und Hinweis; rote zuerst, gelbe danach, grüne zuletzt. Eine Zählerzeile nennt Gelb/Rot/Grün und erklärt die Vorschau einmal. „Aktuelle Scout-Prüfung fehlt“ erscheint einmal oberhalb der Liste, für alle betroffenen Wallets oder mit deren Namen. Die Spalte „Hinweis“ entfällt, wenn keine weiteren Hinweise je Wallet vorliegen; andere Datenlücken und Schonfristen bleiben sichtbar. Die zugrunde liegenden Ampeln und Daten bleiben unverändert. Auch lange Wächter-Listen scrollen innen bei höchstens 70 vh / 480 px. Am Handy stehen Wallet und Ampel oben, Grund und Hinweis darunter. Ein gemeinsamer aufklappbarer Bereich mit Wallet-Auswahl hält sämtliche Details erreichbar. Die belegte „automatisch“-Plakette bei historischen Entfernungen bleibt erhalten.
* **Kennzahlen-Raster auf allen Seiten:** Die tatsächliche Kartenanzahl bestimmt die Spalten (`spalten-1` bis `spalten-4`), unabhängig von `gross`, `breit` oder dem bisherigen `vierer`-Aufruf. Vier Karten: vier gleich breite Spalten am Desktop, zwei mal zwei am Handy. Fünf bis sechs Karten: drei Spalten am Desktop, zwei am Handy. Größere Raster haben drei Desktop-Spalten; bei Rest eins stehen die letzten vier Karten in zwei Paaren. Am Handy nimmt bei ungerader Anzahl ab fünf Karten die drittletzte Karte die volle Breite ein, danach folgt ein Abschluss-Paar. So bleibt die letzte Zeile besetzt. Ein bis drei Karten stehen am Handy untereinander. Die Übersicht mit Experimenten verwendet am Handy bewusst eine kompakte Liste mit einer Karte je Zeile. Roh/Kosten-Karten überspannen keine zusätzlichen Spalten mehr. Im Vierer-Raster erhalten ihre Zahlen 13–17 px Schrift und kleinere Abstände an der Trennlinie; Beträge dürfen zwischen Zahl und Einheit umbrechen, damit beide Werte in die schmalen Karten passen.
* **Handy-Übersicht:** Je Experiment eine kompakte Karte mit Name, Kostenhinweis und den unveränderten Roh/Kosten-Werten nebeneinander. Darunter stehen je ein Roh- und Kosten-Urteil, die Trade-Anzahl und ein 36 px kleiner Fortschrittsring. Sparklines sind hier nur am Desktop sichtbar. Abstände: 8 px zwischen Karten, 10 × 12 px Innenabstand, 3 px zwischen Urteilen. In „Läuft gut/schlecht“ stehen Name und Wert in derselben Zeile; Herkunft und Zusatzangaben bleiben sichtbar.
* **Schrift und Chips:** Karten- und Detailtexte am Handy mindestens 13 px, kleine Roh/Kosten-Labels 12 px. Chips überall mindestens 12 px; sie umbrechen nur zwischen Wörtern, ohne Worttrennung. „Zu früh“ verwendet ein Uhrsymbol statt eines führenden Auslassungszeichens; Urteilstexte bleiben unverändert. Allgemeine Handy-Chips sind mindestens 32 px hoch, Urteils-Chips 36 px. Nur die kompakte Experiment-Liste verwendet Chips mit 12 px Schrift und 3 × 7 px Innenabstand ohne erzwungene Mindesthöhe. Dort steht der Ring neben den Urteilen; andere Karten behalten die eigene Fortschrittszeile.

Die tatsächliche Darstellung bei 1280 px und 390 px wird nach dieser Runde durch Claudes neue Fotos geprüft. Quelltext- und Streamlit-Tests ersetzen diese Sichtprüfung nicht.

### E. Diagramme und Betrieb – Runde 2 (07.10., Karte 24)

* **Rennbahn:** Die Farblegende steht unter dem Diagramm, mit einem Konto je Zeile. Vollständige Namen werden nicht gekürzt (`labelLimit=0`); Linien und Legende verwenden dieselbe Farbskala. Kontrollgruppe und beendete Konten behalten ihre bisherigen Farben und Linienmerkmale. Die Rangtabelle hat drei Spalten: Konto, „roh“, „mit Kosten“. Beide Beträge behalten ihre bisherigen Werte, Vorzeichen und Einheiten; sämtliche Details bleiben aufklappbar.
* **Flugschreiber:** Jede linke Wertachse erhält `minExtent=72`, `maxExtent=72` und `titlePadding=10`. Die feste Achsenbreite steht direkt an der Y-Kodierung, damit das gemeinsame Diagramm-Thema sie nicht überschreibt. Alle Zeichenflächen beginnen bündig; gemeinsame Zeitbereiche, Werte, Referenzlinien und Verkaufsmarkierungen bleiben erhalten.
* **Betrieb:** Hauptbot und Copy-Bot verwenden Commit-Zeitpunkte aus der lokalen Git-Historie, der Scout seinen letzten Bewertungszeitpunkt. Der Fotomodus erlaubt `git log` ausdrücklich. Die lokale Historie ist lesbar und enthält beide Bots. Wenn das Lesen der Historie mit einem Prozessfehler scheitert, liefert die bestehende Rechnung `{}`; dadurch verschwanden bisher beide Karten. Fehlende Einträge erhalten nun eine sichtbare Karte „Datenstand fehlt“ mit neutralem Hinweis „nicht prüfbar“. Aktuelle Dateizeiten ersetzen keine Bot-Zeitpunkte. Ohne vollständige Zeitreihen erscheint „Lücken nicht prüfbar“ statt einer unbelegten Entwarnung. Vorhandene Status- und Lückenrechnungen sowie `rechnung.py` und `daten.py` bleiben unverändert. Ob genau dieser Prozessfehler die bisherigen Fotos verursachte, lässt sich ohne deren Laufprotokoll nicht bestätigen.

Streamlit-Tests prüfen die Legende auch beim Kostenwechsel und mit beendeten Konten, beide Rangspalten, feste Diagrammachsen mit und ohne Verkäufe sowie fehlende, teilweise, leere und vollständige Bot-Historien. Die Sichtprüfung bei 1280 px und 390 px übernimmt Claude mit neuen Fotos. Punkte 1–6 und 8 sind in Karte 24 nicht beschrieben und wurden hier nicht erneut geprüft.

### F. Rückschritte Runde 3 (07.10., Karte 25)

* **Tabellen:** Zellen und Köpfe verwenden `overflow-wrap: normal`, `word-break: normal` und `hyphens: none`; Umbrüche erfolgen nur zwischen Wörtern. Zahlenzellen bleiben einzeilig, auch ohne ausdrückliche Formatvorgabe. Die Tabelle nutzt `min-width: min-content`, Textspalten mindestens 10 ch: längste Wörter und Zahlen bestimmen die notwendige Breite, statt ganze mehrteilige Kopfzeilen auf eine Zeile zu zwingen. Damit bleiben die schmalen Desktop-Haupttabellen kompakt; bei Platzmangel scrollt der äußere Container waagerecht. Lange Tabellen und Wächter-Listen erhalten bis zu `min(75vh, 560px)` Höhe. Am Handy gilt diese Höhe auch bei kleineren übergebenen Tabellenhöhen. Native Tabellen über 200 Zeilen verwenden 560 px Standardhöhe und 48 px Zeilenhöhe, damit ungefähr zehn Zeilen sichtbar sind. Zeilenzahl-Hinweis und feststehende Tabellenköpfe bleiben erhalten. Diese Regeln ersetzen die Breiten- und Höhenvorgaben aus Abschnitt D.
* **Reiche Karten:** Raster mit Roh/Kosten-Karten oder Experimenten haben am Desktop maximal zwei Spalten. Bei ungerader Anzahl füllt die letzte Karte die gesamte Zeile. Der Strategie-Kopf zeigt Konto und SOL je Trade oben, Fortschritt und Gewinner darunter (2×2). Einfache Kennzahlen behalten ihre bisherigen drei bis vier Desktop-Spalten. Am Handy stehen reiche Karten einspaltig; die kompakte Experiment-Liste mit zwei Werten, Chips und kleinem Ring bleibt erhalten. Die Regeln ersetzen die Vierer-/Dreier-Vorgaben für reiche Karten aus Abschnitt D.
* **Tageszeit:** Die vier Tageszeiten stehen gemeinsam in vier Desktop-Spalten, die drei Marktphasen in drei. Zahl, Name, Trade-Anzahl und vollständige Zeitangaben bleiben in den Karten; die bisherigen Ergebnis-/Ausreißer-Details sind darunter aufklappbar. Zwischen 641 und 1000 px Bildschirmbreite wechselt dieses Raster auf zwei Spalten (letzte Marktphase bei ungerader Anzahl über die ganze Zeile), bis 640 px auf eine Spalte.

Neue Tests sichern Wortumbruch-Regeln, Mindestbreiten, Tabellenhöhen, numerische Zellen, Kartenraster und die vollständigen Tageszeit-Werte im Roh-/Kostenmodus. Die Sichtprüfung bei 1280 px und 390 px sowie die tatsächlich sichtbare Zeilenzahl übernimmt Claude mit neuen Fotos; hier stehen weder Browser noch Netzwerk zur Verfügung.


### G. Letzte Restpunkte Runde 4 (07.10., Karte 26)

* **Wallets prüfen:** Die Haupttabelle zeigt Name, Status, Ergebnis, Punkte, abgeschlossene Coins, Copy und geprüft. Haltedauer, Verkäufe unter 60 s, Rendite ohne besten Coin und vollständige Adressen stehen unverändert im aufklappbaren Detailbereich. Sieben feste Spalten teilen sich die Inhaltsbreite; 800 px Mindestbreite, 4 × 6 px Zellabstand und 64 px Mindestzeilenhöhe halten die Darstellung kompakt und gleichmäßig. Ergebnistext bricht ausschließlich an Wortgrenzen um; besonders lange Texte dürfen die Zeile erweitern, damit nichts verloren geht. Der vollständige Prüfzeitpunkt bleibt einzeilig. Am Handy scrollt die Tabelle waagerecht. Eingabe, Adressprüfung, Schreib- und Git-Funktionen bleiben unverändert.
* **Scout:** Die gekürzte Wallet-Adresse in der Rangliste und ihren Detailtabellen bleibt durch `white-space: nowrap` in einer Zeile. Alle Werte und die übrigen Spalten bleiben unverändert.
* **Tageszeit:** SOL-Zahlen erhalten eine eigene einzeilige Darstellung für Zahl, Vorzeichen/Pfeil und Einheit. Die kleinen Zahlen verwenden 16–20 px statt möglichem Umbruch. Die vier Tageszeiten und drei Marktphasen sowie alle Beschriftungen, Werte, Zeitangaben und Details bleiben erhalten.
* **Lernen:** Im Urteils-Kalender ist die Kontospalte mindestens 12 ch breit und auf 18 ch gewichtet, auch am Handy. Namen dürfen nur an Wortgrenzen umbrechen. Trade-Zähler, numerische Werte, Urteil und vollständiges voraussichtliches Datum bleiben einzeilig; auch „Tempo je Tag“ im Tabellenkopf bleibt zusammen. 56 px Mindestzeilenhöhe und mittige Ausrichtung gleichen ein- und zweizeilige Namen aus. Bei Platzmangel scrollt die Tabelle waagerecht, ohne Werte oder Spalten zu verlieren.

Nach jedem der vier Punkte laufen die Dashboard-Tests mit `dashboard/.venv`. Streamlit-Tests sichern unveränderte Werte und vollständige Details; die Prüfung der Wallet-Darstellung sperrt alle Eingabe-, Schreib- und Scout-Startfunktionen. Die fünf Wallet-Tests mit lokalem Git-Klon können in der Codex-Sandbox weiterhin an `Win32 error 5` scheitern. Die Sichtprüfung bei 1280 px und 390 px erfolgt anschließend durch Claude mit neuen Fotos.
