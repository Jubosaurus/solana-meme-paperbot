# Brand & Design Guidelines: NEXUS CORE

> **Claim:** Centralized Intelligence. Algorithmic Precision.

---

## 1. Brand Strategy & Kernbotschaft

NEXUS CORE transformiert das Dashboard von einem funktionalen Entwickler-Tool zu einem hochpräzisen, institutionellen Krypto-Trading-Terminal. Es steht als zentraler Knotenpunkt für alle Bots, Listings, Strategietests und Kennzahlen.

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
* **Header:** Linksbündiges NEXUS CORE Logo (geometrischer Konvergenz-Knoten + Wortmarke).
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