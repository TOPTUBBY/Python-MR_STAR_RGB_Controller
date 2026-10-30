@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo MR STAR RGB Controller - First-time Setup
 echo ==========================================
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3 not found. Install Python 3.10+ from python.org first.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 (
  echo Failed to create Python virtual environment.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check Internet access.
  pause
  exit /b 1
)
echo Installation completed. Double click RUN_WINDOWS.bat.
pause
