@echo off
REM ==============================================================================
REM OTT DIALECT PLATFORM — AUTONOMOUS TRAILER DIRECTOR
REM Interactive Demonstration Script for Hiring Evaluator
REM ==============================================================================

echo ==============================================================================
echo [1/4] Running Automated Test Suite (17 Tests)...
echo ==============================================================================
.venv\Scripts\pytest -v
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Test suite failed!
    exit /b %ERRORLEVEL%
)

echo.
echo ==============================================================================
echo [2/4] Generating Baseline Multi-Audience Trailers (Replay Mode)...
echo ==============================================================================
.venv\Scripts\python -m src.main --input sample_data --output sample_run --mode replay

echo.
echo ==============================================================================
echo [3/4] Triggering Surprise Event: Music Rights Expiration ^& Selective Replanning...
echo ==============================================================================
.venv\Scripts\python -m src.main --scenario contract_change --mode replay

echo.
echo ==============================================================================
echo [4/4] Triggering Adversarial Event: Climax Twist Spoiler Interception ^& Repair...
echo ==============================================================================
.venv\Scripts\python -m src.main --scenario spoiler --mode replay

echo.
echo ==============================================================================
echo Demonstration Completed Successfully!
echo Generated Artifacts in: .\sample_run\
echo ==============================================================================
pause
