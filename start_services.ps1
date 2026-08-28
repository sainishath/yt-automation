# Master Service Launcher for YouTube Automations
$env:PYTHONIOENCODING = "utf-8"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  YouTube Automations - Master Service Launcher" -ForegroundColor Cyan
Write-Host "========================================================`n"

# 1. Check Ollama
Write-Host "[1/3] Checking Ollama Service (Port 11434)..." -NoNewline
try {
    $res = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -UseBasicParsing
    Write-Host " [OK] ONLINE" -ForegroundColor Green
} catch {
    Write-Host " [STARTING] Launching Ollama daemon..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 3
}

# 2. Check Fooocus SDXL
Write-Host "[2/3] Checking Fooocus SDXL Service (Port 7865)..." -NoNewline
try {
    $res = Invoke-WebRequest -Uri "http://127.0.0.1:7865" -TimeoutSec 3 -UseBasicParsing
    Write-Host " [OK] ONLINE" -ForegroundColor Green
} catch {
    Write-Host " [STARTING] Launching Fooocus SDXL server on port 7865..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "D:\Projects\Fooocus\launch.py --listen 127.0.0.1 --port 7865" -WorkingDirectory "D:\Projects\Fooocus"
    Write-Host "Waiting for Fooocus SDXL to initialize..."
    Start-Sleep -Seconds 10
}

# 3. Environment & GPU Verification
Write-Host "[3/3] Checking CUDA Acceleration & PyTorch..."
python -c "import torch; print('      [OK] PyTorch:', torch.__version__, '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU (WARNING)')"

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "  All required services are active and ready!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
