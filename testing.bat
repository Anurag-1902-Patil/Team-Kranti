@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem SIH26122 local test runner for Windows.
rem Starts infrastructure, seeds synthetic data, runs regression tests,
rem then opens separate API and Celery worker terminals.

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv-codex"
set "PYTHON=%VENV%\Scripts\python.exe"
set "CELERY=%VENV%\Scripts\celery.exe"
set "MODEL=qwen3:8b"

cd /d "%ROOT%"

echo.
echo === SIH26122 local test runner ===

where docker >nul 2>nul
if errorlevel 1 (
    echo ERROR: Docker is not available on PATH. Start Docker Desktop and reopen PowerShell or Command Prompt.
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo ERROR: Docker Desktop is installed but its Linux container engine is not running.
    echo Open Docker Desktop, wait until it reports "Engine running", then run this file again.
    echo If Docker Desktop is already open, use its menu to switch to Linux containers and wait for it to restart.
    exit /b 1
)

where ollama >nul 2>nul
if errorlevel 1 (
    echo ERROR: Ollama is not available on PATH. Start/install Ollama and reopen PowerShell or Command Prompt.
    exit /b 1
)

if not exist "%PYTHON%" (
    echo Creating the local Python environment...
    where python >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Python was not found. Install Python 3.11 or 3.12 and add it to PATH.
        exit /b 1
    )
    python -m venv "%VENV%"
    if errorlevel 1 exit /b 1
    "%PYTHON%" -m pip install --upgrade pip
    "%PYTHON%" -m pip install -r backend\requirements.txt
    if errorlevel 1 exit /b 1
)

if not exist ".env" (
    echo Creating .env from .env.example...
    copy /y .env.example .env >nul
)

echo Starting PostgreSQL, Redis, MinIO, and Qdrant...
docker compose up -d postgres redis minio qdrant
if errorlevel 1 exit /b 1

echo Waiting for Docker services to become healthy...
set /a WAIT_SECONDS=0
:wait_for_services
for /f "delims=" %%S in ('docker inspect -f "{{.State.Health.Status}}" sih26122-postgres 2^>nul') do set "POSTGRES_STATUS=%%S"
for /f "delims=" %%S in ('docker inspect -f "{{.State.Health.Status}}" sih26122-redis 2^>nul') do set "REDIS_STATUS=%%S"
for /f "delims=" %%S in ('docker inspect -f "{{.State.Health.Status}}" sih26122-minio 2^>nul') do set "MINIO_STATUS=%%S"
for /f "delims=" %%S in ('docker inspect -f "{{.State.Health.Status}}" sih26122-qdrant 2^>nul') do set "QDRANT_STATUS=%%S"
if /i "!POSTGRES_STATUS!"=="healthy" if /i "!REDIS_STATUS!"=="healthy" if /i "!MINIO_STATUS!"=="healthy" if /i "!QDRANT_STATUS!"=="healthy" goto services_ready
set /a WAIT_SECONDS+=2
if !WAIT_SECONDS! GEQ 60 (
    echo ERROR: Docker services did not become ready within 60 seconds.
    docker compose ps
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto wait_for_services

:services_ready
echo Docker services are running.

ollama list | findstr /C:"%MODEL%" >nul
if errorlevel 1 (
    echo Downloading Ollama model %MODEL%...
    ollama pull %MODEL%
    if errorlevel 1 exit /b 1
)

echo Seeding synthetic schedule, sender profiles, and Qdrant activity index...
"%PYTHON%" scripts\seed_schedule.py
if errorlevel 1 exit /b 1

echo Running regression tests...
"%PYTHON%" -m pytest tests\test_qdrant_store.py tests\test_review_schema.py tests\test_webhook_security.py tests\test_extraction_normalizer.py -q
if errorlevel 1 exit /b 1

echo Starting FastAPI and Celery in separate windows...
start "SIH26122 API" /D "%ROOT%" cmd /k ""%PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
start "SIH26122 Worker" /D "%ROOT%" cmd /k ""%CELERY%" -A backend.workers.celery_app worker --loglevel=info --pool=solo"

echo.
echo Ready.
echo Prototype UI: http://127.0.0.1:8000/prototype
echo API docs: http://127.0.0.1:8000/docs
echo Health:   http://127.0.0.1:8000/health
echo.
echo To exercise extraction and matching directly, run this in another terminal:
echo   "%PYTHON%" scripts\run_demo.py
echo.
pause
