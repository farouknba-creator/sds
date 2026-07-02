@echo off
REM ============================================================
REM SDS Studio - portable build script (Windows)
REM
REM Run on a Windows machine with Python 3.11 + pip deps installed:
REM     pip install -r requirements.txt
REM     build_portable.bat
REM
REM Output: dist\SDSStudio\   <- zip this folder and ship
REM ============================================================

setlocal

echo.
echo [1/4] Cleaning previous build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo [2/4] Ensuring config / asset folders exist in source tree...
if not exist sds_studio\config mkdir sds_studio\config
if not exist sds_studio\assets mkdir sds_studio\assets
if not exist sds_studio\assets\logos mkdir sds_studio\assets\logos

echo [3/4] Running PyInstaller (onedir, no console)...
pyinstaller sds_studio.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo BUILD FAILED. See output above.
    exit /b 1
)

echo [4/4] Copying runtime config + assets into dist folder...
xcopy /e /i /y sds_studio\config dist\SDSStudio\config >nul
xcopy /e /i /y sds_studio\assets dist\SDSStudio\assets >nul
if not exist dist\SDSStudio\input mkdir dist\SDSStudio\input
if not exist dist\SDSStudio\output mkdir dist\SDSStudio\output
if not exist dist\SDSStudio\review_queue mkdir dist\SDSStudio\review_queue
if not exist dist\SDSStudio\logs mkdir dist\SDSStudio\logs

echo.
echo ============================================================
echo  BUILD OK
echo  Portable app:  dist\SDSStudio\SDSStudio.exe
echo  Zip dist\SDSStudio\ and ship it.
echo ============================================================
echo.
pause
endlocal
