@echo off
REM Fitness Challenge: one-click start for Windows.
REM   start.bat       -> only this computer   (http://localhost:8000)
REM   start.bat lan   -> also phones/laptops on the same Wi-Fi
setlocal
cd /d "%~dp0backend"

set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer is required.
  echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo First run: creating a virtual environment...
  %PY% -m venv .venv || goto :fail
)
echo Installing dependencies (first run takes a minute)...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || goto :fail

set "HOST=127.0.0.1"
if /I "%~1"=="lan" (
  set "HOST=0.0.0.0"
  echo Other devices on your Wi-Fi can open http://YOUR-PC-IP:8000  ^(find it with: ipconfig^)
)
echo.
echo   Fitness Challenge is starting at http://localhost:8000
echo   API docs: http://localhost:8000/docs     Stop: Ctrl+C
echo.
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host %HOST% --port 8000
goto :eof

:fail
echo Setup failed. Check your internet connection and try again.
pause
exit /b 1
