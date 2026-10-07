# DexScreener

- Offizielle API ohne Schlüssel, 60 Abfragen/min für Profil/Boost; misst bezahlte Sichtbarkeit (Profil, Boosts, Werbung, Community-Übernahmen), nicht echte Aufmerksamkeit; liefert keine Trader. [[Q-2026-10-03-Ueberpruefung]]
- Seit 04.10. Beobachtung (`dexscreener.csv`) je gekauftem und knapp abgelehntem Coin, höchstens alle 6 h je Coin und Art; Stand ~02:43 UTC: 48 Einträge, 0 Fehler. [[Q-STRATEGIE]] [[Q-2026-10-04-Nachtlauf]]
- Auswertung ab ≥ 100 Käufen mit Aufzeichnung; erst wenn das trennt, über eine Kaufregel sprechen. [[Q-2026-10-03-Ueberpruefung]]
- Im Video: ein frisch bezahltes DexScreener-Profil als Kaufsignal; ein Beitrag von Polymarket und DexTools auf X ließ einen Coin von 2,1 auf 6,4 Mio. steigen (Eigenangaben). [[Q-Videos-Regeln]]
- Metas (`/metas/trending/v1`) werden von Moderatoren/Community von Hand zugeordnet, Rangformel und Takt undokumentiert – als Narrativ-Signal eher spät; WebSocket-Folgeformat undokumentiert, Abfragen für unsere Schichten einfacher. `dexscreener.csv` speichert nur Kennzahlen, keine Texte/Bilder/Links. Nutzungsbedingungen: Rechte an Daten bleiben bei DexScreener, Weitergabe an Dritte untersagt. [[Q-2026-10-07-Backtest-Plan]]
