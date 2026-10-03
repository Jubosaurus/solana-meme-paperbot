# Herkunft

- **Quelle:** offizielle Streamlit-Skills, mitgeliefert im Paket `streamlit==1.65.0` (Ordner `streamlit/.agents/skills/developing-with-streamlit`), eingerichtet mit `streamlit skills --yes`.
- **Lizenz:** Apache-2.0 (wie Streamlit).
- **Übernommen:** 03.10.2026, unverändert kopiert. Die Projekt-Installation nutzt Verknüpfungen (Symlinks), und die gehen unter Windows ohne Entwicklermodus nicht. Der Installer wich deshalb auf eine globale Installation aus. Diese wurde wieder entfernt, damit der Skill nur im Projekt liegt.
- **Aktualisieren:** Nach einem Streamlit-Update in `dashboard/requirements.txt` den Ordner aus `dashboard/.venv/Lib/site-packages/streamlit/.agents/skills/` neu kopieren.
