@echo off
setlocal
title Smart X-Ray AI

REM Always run from the folder where this BAT file is located
cd /d "%~dp0"

echo ==========================================
echo        Smart X-Ray AI - Starting...
echo ==========================================
echo.

REM Check Python virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment was not found.
    echo Expected: .venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

REM Build React automatically only if frontend/dist does not exist
if not exist "frontend\dist\index.html" (
    echo Frontend build was not found.
    echo Building React frontend...
    echo.

    where npm >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] npm was not found.
        echo Please install Node.js or run npm run build manually.
        echo.
        pause
        exit /b 1
    )

    pushd frontend
    call npm run build

    if errorlevel 1 (
        echo.
        echo [ERROR] Frontend build failed.
        popd
        pause
        exit /b 1
    )

    popd
    echo.
    echo Frontend build completed.
    echo.
)

REM Wait until FastAPI /health responds, then open the browser
start "" powershell -NoProfile -WindowStyle Hidden -Command ^
"$url='http://127.0.0.1:8000/health'; for($i=0;$i -lt 90;$i++){ try { $r=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 1; if($r.StatusCode -eq 200){ Start-Process 'http://127.0.0.1:8000'; exit } } catch {} ; Start-Sleep -Seconds 1 }"

echo Starting AI server...
echo.
echo Website: http://127.0.0.1:8000
echo Swagger: http://127.0.0.1:8000/docs
echo.
echo Keep this window open while using Smart X-Ray AI.
echo To stop the project, press CTRL+C.
echo.

".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo.
echo Smart X-Ray AI has stopped.
pause
