@echo off
setlocal
cd /d "%~dp0"
rem Keep a working environment; recreate only when its interpreter is invalid.
if not exist ".venv\Scripts\python.exe" goto select_python
".venv\Scripts\python.exe" -c "import sys, tkinter, venv, struct; assert sys.version_info >= (3,11); assert struct.calcsize('P') == 8" >nul 2>nul
if errorlevel 1 goto select_python
goto install_dependencies

:select_python
set "BEACON_PY="
rem Prefer the Python 3.13 version present in the supplied lab diagnostic.
for %%V in (3.13 3.12 3.11 3.14) do call :try_version %%V
if defined BEACON_PY goto python_found
python -c "import sys, tkinter, venv, struct; assert sys.version_info >= (3,11); assert struct.calcsize('P') == 8" >nul 2>nul
if not errorlevel 1 set "BEACON_PY=python"
if defined BEACON_PY goto python_found
echo No working 64-bit Python 3.11+ with Tk was found.
echo Install Python 3.13 64-bit with Tcl/Tk and the Python Launcher, then retry.
echo Python versions known to the launcher:
py -0p
goto fail

:python_found
echo Using %BEACON_PY%
if not exist ".venv" goto create_environment
:choose_backup
set "BEACON_BACKUP=.venv_backup_%RANDOM%_%RANDOM%"
if exist "%BEACON_BACKUP%" goto choose_backup
ren ".venv" "%BEACON_BACKUP%"
if errorlevel 1 goto fail
echo Previous environment preserved in %BEACON_BACKUP%

:create_environment
%BEACON_PY% -m venv ".venv"
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -c "import sys, tkinter; print('Python:', sys.executable); print(sys.version)"
if errorlevel 1 goto fail

:install_dependencies
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -c "import tkinter, bleak, pythoncom, win32com.client"
if errorlevel 1 goto fail
echo Installation complete. Use RUN_WINDOWS.bat or RUN_SIMULATED_LED.bat.
pause
exit /b 0

:try_version
if defined BEACON_PY exit /b 0
py -%1 -c "import sys, tkinter, venv, struct; assert sys.version_info >= (3,11); assert struct.calcsize('P') == 8" >nul 2>nul
if not errorlevel 1 set "BEACON_PY=py -%1"
exit /b 0

:fail
echo Installation failed. Check the error above. Existing settings are retained.
pause
exit /b 1
