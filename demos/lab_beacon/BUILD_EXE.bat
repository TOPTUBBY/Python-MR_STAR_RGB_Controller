@echo off
cd /d "%~dp0"
call CHECK_ENV.bat
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install pyinstaller
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name Lab_Beacon_Demo --hidden-import=pythoncom --hidden-import=pywintypes --collect-submodules=win32com --collect-submodules=bleak app.py
if errorlevel 1 goto fail
echo Built: dist\Lab_Beacon_Demo\Lab_Beacon_Demo.exe
echo Keep the entire dist\Lab_Beacon_Demo folder together.
pause
exit /b 0
:fail
echo Build failed. Check the error above.
pause
exit /b 1
