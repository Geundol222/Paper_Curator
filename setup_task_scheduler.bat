@echo off
REM Setup Windows Task Scheduler to run paper sync daily
REM Run this script as Administrator

echo ============================================================
echo Setting up Daily Paper Sync with Task Scheduler
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
echo Script: %PYTHON_SCRIPT%
echo.

REM Create task
echo Creating scheduled task "ArxivPaperSync"...
echo This task will run daily at 9:00 AM
echo.

schtasks /Create /TN "ArxivPaperSync" /TR "\"%PYTHON_PATH%\" \"%PYTHON_SCRIPT%\"" /SC DAILY /ST 09:00 /RL HIGHEST /F

if %ERRORLEVEL% equ 0 (
    echo.
    echo SUCCESS: Task created successfully!
    echo.
    echo Task Name: ArxivPaperSync
    echo Schedule: Daily at 9:00 AM
    echo.
    echo To view the task:
    echo   schtasks /Query /TN "ArxivPaperSync" /V
    echo.
    echo To run the task manually:
    echo   schtasks /Run /TN "ArxivPaperSync"
    echo.
    echo To delete the task:
    echo   schtasks /Delete /TN "ArxivPaperSync" /F
    echo.
    echo Logs will be saved to: %SCRIPT_DIR%.tmp\sync_log_YYYYMMDD.txt
    echo.
) else (
    echo ERROR: Failed to create scheduled task
    echo Please run this script as Administrator
)

echo.
echo ============================================================
echo To test the sync manually, run:
echo python "%PYTHON_SCRIPT%"
echo ============================================================
echo.

pause
