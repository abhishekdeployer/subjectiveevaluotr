# Lokasewa Evaluator - Quick Start Script
# This script kills any running instances and starts the app fresh

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host " Lokasewa Evaluator - Quick Start" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill any process using port 7860
Write-Host "[1/3] Checking for running instances on port 7860..." -ForegroundColor Yellow
$processIds = Get-NetTCPConnection -LocalPort 7860 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess

if ($processIds) {
    foreach ($pid in $processIds) {
        Write-Host "Found process $pid using port 7860" -ForegroundColor Yellow
        Write-Host "Killing process..." -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Host "Process killed!" -ForegroundColor Green
    }
} else {
    Write-Host "No processes found on port 7860" -ForegroundColor Green
}

# Step 2: Wait a moment
Write-Host ""
Write-Host "[2/3] Waiting 2 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Step 3: Start the app
Write-Host ""
Write-Host "[3/3] Starting Lokasewa Evaluator..." -ForegroundColor Yellow
Write-Host ""

# Activate venv if it exists
if (Test-Path "..\venv\Scripts\Activate.ps1") {
    & "..\venv\Scripts\Activate.ps1"
}

# Run the app
python app.py
