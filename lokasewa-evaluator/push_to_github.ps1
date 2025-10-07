# Quick script to push your code to GitHub
# Run this in PowerShell

Write-Host "🚀 Pushing to GitHub..." -ForegroundColor Green

# Initialize git if needed
if (-not (Test-Path .git)) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
}

# Stage all changes
Write-Host "Staging files..." -ForegroundColor Yellow
git add .

# Commit
$commitMessage = Read-Host "Enter commit message (or press Enter for default)"
if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    $commitMessage = "Update: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}
git commit -m $commitMessage

# Check if remote exists
$remoteExists = git remote | Select-String -Pattern "origin" -Quiet
if (-not $remoteExists) {
    Write-Host "`n⚠️  No remote repository configured!" -ForegroundColor Red
    Write-Host "Please create a repository on GitHub first, then run:" -ForegroundColor Yellow
    Write-Host "git remote add origin https://github.com/YOUR_USERNAME/lokasewa-evaluator.git" -ForegroundColor Cyan
    Write-Host "git push -u origin main" -ForegroundColor Cyan
} else {
    # Push to GitHub
    Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
    git push
    Write-Host "`n✅ Successfully pushed to GitHub!" -ForegroundColor Green
}

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Go to https://huggingface.co/spaces" -ForegroundColor White
Write-Host "2. Create new Space (Gradio SDK)" -ForegroundColor White
Write-Host "3. Link to your GitHub repo" -ForegroundColor White
Write-Host "4. Add API key secrets" -ForegroundColor White
Write-Host "5. Wait for build (2-5 minutes)" -ForegroundColor White
Write-Host "6. Your app is live! 🎉" -ForegroundColor White
