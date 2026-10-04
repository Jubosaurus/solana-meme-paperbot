# Testsammlung und Regressionsprobe

- Seit 02.10. 145 automatische Tests (zuletzt 227 am 04.10.), ohne echte APIs; Start mit `python -m pytest`. [[Q-STRATEGIE]] [[Q-2026-10-04-Nachtlauf]]
- Regressionsprobe: 33 aufgezeichnete Verläufe laufen durch `manage_positions`; Ergebnis und Verkaufsgrund je Coin sind festgeschrieben. [[Q-CLAUDE]]
- Hooks: vor jedem `git push` laufen die Tests; vor jedem `git commit` wird abgebrochen, wenn Daten-Dateien gestaged sind. [[Q-CLAUDE]]
