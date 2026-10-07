@echo off
setlocal
REM Muse Bridge installer (Windows). Run by double-clicking.
REM Requires: Python 3 (python.org) and Muse Code CLI logged in.

REM Resolve repo root = parent of this install\ folder
for %%I in ("%~dp0..") do set "REPO=%%~fI"
set "BRIDGE=%REPO%\muse_bridge.py"

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python not found. Install Python 3 from https://python.org
  echo        and tick "Add python.exe to PATH", then re-run this file.
  pause
  exit /b 1
)

REM Create autostart entry (runs the bridge after every login)
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "AUTOSTART=%STARTUP%\muse-bridge.bat"
python "%REPO%\install\windows_autostart.py" "%BRIDGE%" > "%AUTOSTART%"
if errorlevel 1 (
  echo ERROR: failed to create the Windows autostart command.
  pause
  exit /b 1
)
echo OK: autostart created:
echo     %AUTOSTART%

REM Start the bridge now
start "" /min pythonw "%BRIDGE%"
echo OK: bridge started.
echo Test it in a browser:  http://127.0.0.1:11471/health
echo.
echo Next: open PI-Desktop and select the "Meta Muse" provider.
pause
