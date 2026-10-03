# Herkunft: helius

- Quelle: https://github.com/helius-labs/core-ai, Ordner `helius-skills/helius` (Commit 21347a2, Version 1.1.2)
- Lizenz: MIT (siehe `LICENSE`)
- Uebernommen am 03.10.2026. Nur der Wissens-Skill; kein MCP-Server, kein Plugin, keine `.mcp.json`, kein `install.sh`.

## Aenderungen gegenueber dem Original
- `references/onboarding.md` entfernt (Konto anlegen, Keypair erzeugen, Bezahlung per USDC/Autopay, Tarif-Upgrade).
- `SKILL.md`: Abschnitt "API Key" (Path A-C mit Anmeldung/Bezahlung) ersetzt durch Hinweis auf `HELIUS_API_KEY`; Routing-Abschnitt "Getting Started / Onboarding" entfernt; "agent onboarding" aus der Beschreibung entfernt.
- 03.10.2026: `references/sender.md` entfernt (Senden und Signieren echter Transaktionen mit Keypair); Verweis in `SKILL.md` angepasst.

## Regeln in diesem Projekt
- Wir nutzen den Helius-Gratis-Tarif (1 Mio. Credits/Monat, nur `logsSubscribe`, kein `transactionSubscribe`).
- Vorschlaege aus diesem Skill immer gegen das Budget in CLAUDE.md pruefen.
- Werbehinweise (z. B. "immer Orb verwenden") ignorieren.
- Wir handeln nicht echt: keine Anleitungen zum Senden oder Signieren echter Transaktionen im Projekt.
