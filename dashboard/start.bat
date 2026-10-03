@echo off
rem Paperbot-Dashboard starten (nur Anschauen). Doppelklick genuegt.
title Paperbot-Dashboard
cd /d "%~dp0"

rem Laeuft es schon? Dann nur den Browser oeffnen.
rem (sprachunabhaengig: ein offener Port hat die Gegenstelle 0.0.0.0:0, auch auf deutschem Windows "ABHOEREN")
netstat -ano | findstr /c:"127.0.0.1:8501" | findstr /c:"0.0.0.0:0" >nul 2>nul
if not errorlevel 1 (
  start "" http://localhost:8501
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python wurde nicht gefunden. Bitte Python 3.11 installieren.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Einmalige Einrichtung, das dauert 1-2 Minuten ...
  python -m venv .venv
  if errorlevel 1 (
    echo Einrichtung fehlgeschlagen.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Installation der Pakete fehlgeschlagen.
  pause
  exit /b 1
)

echo.
echo Dashboard startet, der Browser oeffnet sich gleich (http://localhost:8501).
echo Zum Beenden dieses Fenster schliessen.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
