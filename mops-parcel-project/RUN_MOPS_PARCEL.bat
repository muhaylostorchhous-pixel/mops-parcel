@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 is not installed. Install it from https://www.python.org/downloads/
  echo During installation, enable "Add Python to PATH".
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating the local Python environment...
  python -m venv .venv
  if errorlevel 1 goto failed
)
call ".venv\Scripts\activate.bat"
echo Installing project dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo If this is your first run, edit .env and set ADMIN_EMAIL and ADMIN_PASSWORD.
echo Then run this file again.
echo.
python app.py
pause
exit /b 0
:failed
echo Setup did not finish. Check your internet connection and Python installation.
pause
exit /b 1
