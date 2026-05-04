@echo off
REM Setup script to configure automatic paper sync on Windows startup
REM Run this script as Administrator

echo ============================================================
echo Setting up Automatic Paper Sync on Windows Startup
echo ============================================================
echo.

REM Get the current directory
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%execution\auto_sync_papers.py

REM Find Python executable
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

REM Get Python path
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i
echo Found Python: %PYTHON_PATH%
echo.

REM Create VBS script for silent execution (no console window)
set VBS_SCRIPT=%SCRIPT_DIR%run_paper_sync_silent.vbs
echo Creating silent launcher: %VBS_SCRIPT%

(
echo Set objShell = CreateObject^("WScript.Shell"^)
echo objShell.Run """%PYTHON_PATH%"" ""%PYTHON_SCRIPT%""", 0, False
) > "%VBS_SCRIPT%"

echo Created: %VBS_SCRIPT%
echo.

REM Create shortcut in Startup folder
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT=%STARTUP_FOLDER%\ArxivPaperSync.lnk

echo Creating startup shortcut: %SHORTCUT%

powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUT%'); $SC.TargetPath = '%VBS_SCRIPT%'; $SC.WorkingDirectory = '%SCRIPT_DIR%'; $SC.Description = 'Arxiv Paper Auto Sync'; $SC.Save()"

if exist "%SHORTCUT%" (
    echo SUCCESS: Startup shortcut created!
    echo.
    echo The paper sync will run automatically when you log in to Windows.
    echo.
    echo Location: %SHORTCUT%
    echo Script: %PYTHON_SCRIPT%
    echo Logs: %SCRIPT_DIR%.tmp\sync_log_YYYYMMDD.txt
    echo.
) else (
    echo ERROR: Failed to create startup shortcut
    echo Please create a shortcut manually in:
    echo %STARTUP_FOLDER%
    echo Target: %VBS_SCRIPT%
)

echo.
echo ============================================================
echo To test the sync manually, run:
echo python "%PYTHON_SCRIPT%"
echo ============================================================
echo.

pause
