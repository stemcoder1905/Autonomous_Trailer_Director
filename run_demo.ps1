# ==============================================================================
# OTT DIALECT PLATFORM — AUTONOMOUS TRAILER DIRECTOR
# PowerShell Interactive Demonstration Script for Hiring Evaluator
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "[1/4] Running Automated Test Suite (17 Tests)..." -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan
& .venv\Scripts\pytest -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Test suite failed!"
    exit $LASTEXITCODE
}

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host "[2/4] Generating Baseline Multi-Audience Trailers (Replay Mode)..." -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan
& .venv\Scripts\python -m src.main --input sample_data --output sample_run --mode replay

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host "[3/4] Triggering Surprise Event: Music Rights Expiration & Selective Replanning..." -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan
& .venv\Scripts\python -m src.main --scenario contract_change --mode replay

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host "[4/4] Triggering Adversarial Event: Climax Twist Spoiler Interception & Repair..." -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan
& .venv\Scripts\python -m src.main --scenario spoiler --mode replay

Write-Host "`n==============================================================================" -ForegroundColor Green
Write-Host "Demonstration Completed Successfully!" -ForegroundColor Green
Write-Host "Generated Artifacts located in: .\sample_run\" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
