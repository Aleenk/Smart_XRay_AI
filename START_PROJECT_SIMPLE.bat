@echo off
title Smart X-Ray AI
cd /d "%~dp0"

echo ==========================================
echo          Smart X-Ray AI
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment was not found.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo ERROR: frontend\dist\index.html was not found.
    echo.
    echo Run these commands first:
    echo cd frontend
    echo npm run build
    echo.
    pause
    exit /b 1
)

echo Starting Smart X-Ray AI...
echo.
echo Website:
echo http://127.0.0.1:8000
echo.
echo Keep this window OPEN while using the project.
echo Press CTRL+C to stop the server.
echo.

REM Open the browser a few seconds after the server starts loading
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 6; Start-Process 'http://127.0.0.1:8000'"

".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo.
echo ==========================================
echo The server has stopped.
echo If you see an error above, take a screenshot.
echo ==========================================
echo.
pause
