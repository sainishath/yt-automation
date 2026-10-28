# Start Local AI Infrastructure for Pipeline 1 (Fooocus SDXL + Ollama)
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Starting Chronos Shift AI Infrastructure..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Ollama (Port 11434)
$ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $ollamaRunning) {
    Write-Host "[1/2] Starting Ollama background server..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "[1/2] Ollama server is already running on port 11434." -ForegroundColor Green
}

# 2. Start Fooocus SDXL (Port 7865)
$fooocusDir = "D:\AI-Tools\Fooocus"
if (Test-Path $fooocusDir) {
    $fooocusPort = 7865
    $portActive = Get-NetTCPConnection -LocalPort $fooocusPort -State Listen -ErrorAction SilentlyContinue
    if (-not $portActive) {
        Write-Host "[2/2] Launching Fooocus SDXL (VRAM offload enabled)..." -ForegroundColor Yellow
        $pythonExe = Join-Path $fooocusDir "fooocus_env\Scripts\python.exe"
        $launchPy = Join-Path $fooocusDir "launch.py"
        Start-Process -FilePath $pythonExe -ArgumentList "$launchPy --listen 127.0.0.1 --port $fooocusPort --disable-in-browser --always-offload-from-vram" -WorkingDirectory $fooocusDir
        Write-Host "Fooocus launching in background on http://127.0.0.1:7865" -ForegroundColor Green
    } else {
        Write-Host "[2/2] Fooocus SDXL is already listening on port 7865." -ForegroundColor Green
    }
} else {
    Write-Host "[2/2] Fooocus directory not found at $fooocusDir" -ForegroundColor Red
}

Write-Host "Infrastructure check complete!" -ForegroundColor Cyan
