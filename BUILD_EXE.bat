@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install pyinstaller
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name "MR_STAR_RGB_Controller" --icon "assets\app.ico" --add-data "assets\app.ico;assets" --collect-all bleak app.py
if errorlevel 1 goto fail
echo.
echo Build completed: dist\MR_STAR_RGB_Controller.exe
pause
exit /b 0
:fail
echo Build failed. Review messages above.
pause
exit /b 1
