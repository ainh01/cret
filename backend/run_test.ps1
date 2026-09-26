# Script to run mock server, backend, and test

Write-Host "Starting mock LLM server on port 5001..." -ForegroundColor Cyan
$mockServer = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python mock_server.py" -PassThru

Write-Host "Waiting for mock server to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

Write-Host "Starting backend server on port 5000..." -ForegroundColor Cyan
$backendServer = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..'; $env:ENDPOINT='http://127.0.0.1:5001/chat/completions'; $env:TOKEN='mock-token'; $env:USE_PROXY='false'; python -m uvicorn app:app --host 127.0.0.1 --port 5000" -PassThru

Write-Host "Waiting for backend server to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "`nRunning test..." -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green

python "$PSScriptRoot\test_queue_mode.py"

Write-Host "`n" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "Test complete. Press any key to stop servers..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host "Stopping servers..." -ForegroundColor Red
Stop-Process -Id $mockServer.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $backendServer.Id -Force -ErrorAction SilentlyContinue

Write-Host "Done." -ForegroundColor Green
