@echo off
echo.
echo ========================================
echo   Lokasewa Evaluator - Fresh Start
echo ========================================
echo.

echo [1/4] Killing any running Python instances...
taskkill /F /IM python.exe 2>nul
if %errorlevel%==0 (
    echo    ✓ Killed existing processes
    timeout /t 2 /nobreak >nul
) else (
    echo    ✓ No existing processes found
)

echo.
echo [2/4] Clearing Python cache...
if exist __pycache__ rd /s /q __pycache__
if exist agents\__pycache__ rd /s /q agents\__pycache__
if exist utils\__pycache__ rd /s /q utils\__pycache__
echo    ✓ Cache cleared

echo.
echo [3/4] Testing API connections...
python test_fixes.py
if %errorlevel% neq 0 (
    echo.
    echo    ✗ API test failed! Check your .env file
    echo.
    pause
    exit /b 1
)

echo.
echo [4/4] Starting Lokasewa Evaluator...
echo    → The app will open in your browser
echo    → Press Ctrl+C to stop the server
echo.
python app.py

pause
