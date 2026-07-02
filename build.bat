@echo off
REM ============================================================
REM  SDS Studio - one-click portable build (Windows)
REM
REM  Double-click this file. It will:
REM    1. Check Python 3.11 is installed
REM    2. Create a virtual env (.venv) if missing
REM    3. Install all dependencies from requirements.txt
REM    4. Run PyInstaller to build dist\SDSStudio\SDSStudio.exe
REM    5. Copy config + assets into the dist folder
REM    6. Open the dist folder in Explorer
REM
REM  Output:  dist\SDSStudio\SDSStudio.exe
REM  To ship: zip the entire dist\SDSStudio\ folder
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo.
echo ============================================================
echo  SDS Studio - portable build
echo  Working directory: %CD%
echo ============================================================
echo.

REM ---- Step 1: locate Python ----
echo [1/7] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Python not found in PATH.
    echo Install Python 3.11 from https://www.python.org/downloads/windows/
    echo Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
python --version
echo.

REM ---- Step 2: create venv if missing ----
echo [2/7] Checking virtual environment...
if not exist ".venv\Scripts\python.exe" (
    echo Creating .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: could not create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo .venv already exists.
)
echo.

REM ---- Step 3: activate venv ----
echo [3/7] Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: could not activate venv.
    pause
    exit /b 1
)
python --version
echo.

REM ---- Step 4: install dependencies ----
echo [4/7] Installing dependencies (first run takes ~2 minutes)...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet pyinstaller
pip install --quiet -e . --no-deps
if errorlevel 1 (
    echo.
    echo ERROR: dependency installation failed.
    echo Try running manually:  pip install -r requirements.txt & pip install -e .
    pause
    exit /b 1
)
echo Dependencies installed.
echo.

REM ---- Step 5: clean previous build ----
echo [5/7] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

REM ---- Step 6: run PyInstaller ----
echo [6/7] Running PyInstaller (onedir mode, no console window)...
echo This takes 1-3 minutes. Please wait...
echo.
pyinstaller sds_studio.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  BUILD FAILED
    echo  See error messages above.
    echo ============================================================
    pause
    exit /b 1
)
echo.

REM ---- Step 7: copy runtime files into dist ----
echo [7/7] Copying config + assets into dist\SDSStudio\...
if not exist dist\SDSStudio\config mkdir dist\SDSStudio\config
if not exist dist\SDSStudio\assets mkdir dist\SDSStudio\assets
if not exist dist\SDSStudio\assets\logos mkdir dist\SDSStudio\assets\logos
if not exist dist\SDSStudio\input mkdir dist\SDSStudio\input
if not exist dist\SDSStudio\output mkdir dist\SDSStudio\output
if not exist dist\SDSStudio\review_queue mkdir dist\SDSStudio\review_queue
if not exist dist\SDSStudio\logs mkdir dist\SDSStudio\logs

xcopy /e /i /y /q config dist\SDSStudio\config >nul
xcopy /e /i /y /q assets dist\SDSStudio\assets >nul
echo.

REM ---- Verify output ----
if not exist "dist\SDSStudio\SDSStudio.exe" (
    echo ERROR: SDSStudio.exe was not produced.
    pause
    exit /b 1
)

REM ---- Show output size ----
for %%I in (dist\SDSStudio\SDSStudio.exe) do set EXE_SIZE=%%~zI
set /a EXE_MB=!EXE_SIZE! / 1048576
echo ============================================================
echo  BUILD OK
echo.
echo  Executable:  dist\SDSStudio\SDSStudio.exe  (!EXE_MB! MB)
echo  Full folder: dist\SDSStudio\
echo.
echo  To ship: zip the entire dist\SDSStudio\ folder.
echo  To run:  double-click dist\SDSStudio\SDSStudio.exe
echo ============================================================
echo.
echo Opening dist folder in Explorer...
explorer "dist\SDSStudio"

pause
endlocal
