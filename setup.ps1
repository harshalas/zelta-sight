# ====================================================================
# Zelta Sight Backend Startup Automation
# ====================================================================

$BackendPath = "C:\git\zelta-sight\backend"
$UvicornPath = "C:\git\zelta-sight\backend\venv\Scripts\uvicorn.exe"

if (Test-Path $BackendPath) {
    Set-Location $BackendPath
    Write-Host "Shifted to backend directory." -ForegroundColor Green
    
    if (Test-Path $UvicornPath) {
        Write-Host "Launching Uvicorn server directly..." -ForegroundColor Magenta
        & $UvicornPath main:app --reload --host 0.0.0.0
    } else {
        Write-Host "Error: uvicorn executable not found at expected path." -ForegroundColor Red
    }
} else {
    Write-Host "Error: Directory path not found!" -ForegroundColor Red
}