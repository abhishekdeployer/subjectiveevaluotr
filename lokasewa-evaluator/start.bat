@echo off
REM Kill any processes using port 7860 and start the app

echo.
echo ====================================
echo  Lokasewa Evaluator - Quick Start
echo ====================================
echo.

echo [1/3] Checking for running instances on port 7860...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860 ^| findstr LISTENING') do (
    echo Found process %%a using port 7860
    echo Killing process...
    taskkill /PID %%a /F >nul 2>&1
    echo Process killed!
)

echo.
echo [2/3] Waiting 2 seconds...
timeout /t 2 /nobreak >nul

echo.
echo [3/3] Starting Lokasewa Evaluator...
echo.
python app.py

pause
