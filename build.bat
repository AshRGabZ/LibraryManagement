@echo off
REM ===========================================================================
REM  Build the GHCC Library Management desktop app (.exe) on Windows.
REM
REM  Usage (from the project root):
REM      double-click build.bat   --  or, in a terminal:   build.bat
REM
REM  Optional: use a specific interpreter ->  set PYTHON=py -3.13 & build.bat
REM ===========================================================================
setlocal

set "APP_NAME=GHCC Library"
set "ENTRY=main.py"
if "%PYTHON%"=="" set "PYTHON=python"

cd /d "%~dp0"

echo ==^> Python version:
"%PYTHON%" --version
if errorlevel 1 (
    echo.
    echo Python was not found on PATH. Install Python 3 from python.org and
    echo tick "Add Python to PATH" during setup, then run this again.
    pause
    exit /b 1
)

echo ==^> Installing build dependencies ^(pyinstaller, openpyxl, Pillow^)...
"%PYTHON%" -m pip install --upgrade pyinstaller openpyxl Pillow
if errorlevel 1 ( echo. & echo pip install failed. & pause & exit /b 1 )

echo ==^> Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"

echo ==^> Building "%APP_NAME%.exe"...
"%PYTHON%" -m PyInstaller --noconfirm --windowed --onefile --name "%APP_NAME%" --add-data "library_app\assets;library_app\assets" "%ENTRY%"
if errorlevel 1 ( echo. & echo Build failed. & pause & exit /b 1 )

echo.
echo ==^> Done.  Executable:  dist\%APP_NAME%.exe
echo     Double-click it, or run:  "dist\%APP_NAME%.exe"
echo.
pause
endlocal
