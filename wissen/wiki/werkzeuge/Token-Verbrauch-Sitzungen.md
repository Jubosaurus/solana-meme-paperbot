# Token-Verbrauch der Claude-Sitzungen

- 02.10. 13:44 bis 04.10. 05:31 UTC: 288 Mio. Token in 40 Sitzungen, 97,5 % aus dem Cache; 03.10. allein 271,7 Mio. [[Q-2026-10-04-Tokenverbrauch]]
- Hauptursache: fast alles am 03.10. in einer einzigen Sitzung (Verlauf bis ~950.000 Token); die 5 teuersten Aufgaben machten zusammen 73 % aus. [[Q-2026-10-04-Tokenverbrauch]]
- Subagenten: 32 Aufrufe, zusammen 11,3 Mio. Token (knapp 4 %), im Schnitt ~350.000 je Aufruf. [[Q-2026-10-04-Tokenverbrauch]]
- Größter Hebel: nach jeder Aufgabe `/clear`; nach langen Pausen (> 1 h) verfällt der Cache und der Verlauf wird teuer neu eingelesen. [[Q-2026-10-04-Tokenverbrauch]]
