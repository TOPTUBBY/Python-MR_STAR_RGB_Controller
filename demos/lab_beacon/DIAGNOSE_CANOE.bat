@echo off
setlocal
cd /d "%~dp0"
call CHECK_ENV.bat
if errorlevel 1 goto fail
".venv\Scripts\python.exe" diagnose_canoe.py
set "BEACON_RESULT=%ERRORLEVEL%"
pause
exit /b %BEACON_RESULT%
:fail
pause
exit /b 1
