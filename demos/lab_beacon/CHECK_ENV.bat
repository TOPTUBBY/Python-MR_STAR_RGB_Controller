@echo off
rem This helper is called by launchers. It does not modify the environment.
if not exist ".venv\Scripts\python.exe" goto invalid
".venv\Scripts\python.exe" -c "import sys, struct, tkinter, bleak, pythoncom, win32com.client; assert sys.version_info >= (3,11); assert struct.calcsize('P') == 8" >nul 2>nul
if errorlevel 1 goto invalid
exit /b 0
:invalid
echo The Python environment is missing, broken, or missing dependencies.
echo Run INSTALL_WINDOWS.bat from this folder to repair it.
echo A broken environment will be backed up before it is replaced.
exit /b 1
