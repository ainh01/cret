@echo off
REM Start mock server, backend, and run test

echo Starting mock server on port 5001...
start "Mock Server" cmd /c "cd /d C:\Users\Ainh\Desktop\dev\cret\backend && python mock_server.py"

echo Waiting for mock server to be ready...
timeout /t 3 /nobreak > nul

echo Starting backend on port 5000 with mock endpoint...
start "Backend Server" cmd /c "cd /d C:\Users\Ainh\Desktop\dev\cret && set ENDPOINT=http://127.0.0.1:5001/chat/completions && set TOKEN=mock-token && set STREAM=true && python app.py"

echo Waiting for backend server to be ready...
timeout /t 5 /nobreak > nul

echo Testing backend availability...
:wait_backend
curl -s http://127.0.0.1:5000/api/config > nul 2>&1
if errorlevel 1 (
    echo Backend not ready yet, waiting...
    timeout /t 2 /nobreak > nul
    goto wait_backend
)

echo Backend is ready!
echo.

echo Running test...
cd /d C:\Users\Ainh\Desktop\dev\cret\backend
python test_auto_mode.py

echo.
echo Test complete. Press any key to stop servers...
pause > nul

taskkill /FI "WindowTitle eq Mock Server*" /F > nul 2>&1
taskkill /FI "WindowTitle eq Backend Server*" /F > nul 2>&1
