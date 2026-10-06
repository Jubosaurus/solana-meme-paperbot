# Testsammlung und Regressionsprobe

- Seit 02.10. 145 automatische Tests (zuletzt 227 am 04.10.), ohne echte APIs; Start mit `python -m pytest`. [[Q-STRATEGIE]] [[Q-2026-10-04-Nachtlauf]]
- Regressionsprobe: 33 aufgezeichnete Verläufe laufen durch `manage_positions`; Ergebnis und Verkaufsgrund je Coin sind festgeschrieben. [[Q-CLAUDE]]
- Hooks: vor jedem `git push` laufen die Tests; vor jedem `git commit` wird abgebrochen, wenn Daten-Dateien gestaged sind. [[Q-CLAUDE]]
- Seit 06.10.: Der Push-Hook startet zusätzlich `tests/test_dashboard_wallets.py` mit `dashboard/.venv`, wenn der Push `dashboard/` betrifft (dauert ca. 18 s auf ca. 42 s Gesamttests; im normalen Python wird dieser Test übersprungen, weil `streamlit` fehlt). [[Q-2026-10-06-Entscheidungen]]
