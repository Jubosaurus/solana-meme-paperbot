@echo off
rem Paperbot-Dashboard im Heimnetz starten (fuer das Handy). Doppelklick genuegt.
rem Am Handy nur Anschauen; das Absenden von Wallets geht nur am PC (localhost).
title Paperbot-Dashboard (Handy)
cd /d "%~dp0"

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

rem Laeuft das Dashboard schon, aber nur fuer diesen PC (127.0.0.1)? Dann geht das Handy nicht.
netstat -ano | findstr /c:"127.0.0.1:8501" | findstr /c:"0.0.0.0:0" >nul 2>nul
if not errorlevel 1 (
  echo Das Dashboard laeuft schon, aber nur fuer diesen PC.
  echo Bitte das alte schwarze Dashboard-Fenster schliessen und start_handy.bat nochmal starten.
  pause
  exit /b 1
)
rem Laeuft es schon fuer das Heimnetz (0.0.0.0)? Dann nur Adresse und QR-Code zeigen.
netstat -ano | findstr /c:"0.0.0.0:8501" | findstr /c:"0.0.0.0:0" >nul 2>nul
if not errorlevel 1 (
  ".venv\Scripts\python.exe" handy_info.py
  start "" http://localhost:8501
  pause
  exit /b 0
)

rem Firewall-Regel: nur Port 8501, nur private Netzwerke. Einmalig; Windows fragt dann nach Administrator-Erlaubnis.
netsh advfirewall firewall show rule name=Paperbot-Dashboard-8501 >nul 2>nul
if errorlevel 1 (
  echo.
  echo Einmalig: Windows fragt gleich, ob "netsh" etwas aendern darf. Bitte mit JA bestaetigen.
  echo Es wird nur der Port 8501 und nur fuer PRIVATE Netzwerke, also das Heimnetz, freigegeben.
  echo.
  powershell -NoProfile -Command "Start-Process netsh -Verb RunAs -Wait -ArgumentList 'advfirewall','firewall','add','rule','name=Paperbot-Dashboard-8501','dir=in','action=allow','protocol=TCP','localport=8501','profile=private'"
  netsh advfirewall firewall show rule name=Paperbot-Dashboard-8501 >nul 2>nul
  if errorlevel 1 (
    echo Die Firewall-Regel wurde nicht angelegt. Ohne sie erreicht das Handy das Dashboard nicht.
    pause
  )
)

".venv\Scripts\python.exe" handy_info.py
echo.
echo Dashboard startet. Am PC: http://localhost:8501
echo Zum Beenden dieses Fenster schliessen.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0
pause
