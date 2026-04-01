@echo off
setlocal

set "REPO_ROOT=%~dp0.."
set "BACKEND=%REPO_ROOT%\backend"

REM ── .env check ───────────────────────────────────────────────────────────────
if not exist "%BACKEND%\.env" (
    echo ERROR: %BACKEND%\.env not found.
    echo        Copy and edit the example:
    echo          copy backend\.env.example backend\.env
    pause
    exit /b 1
)

REM ── start PostgreSQL via Docker Compose (only the db service) ────────────────
echo Starting PostgreSQL container...
docker compose -f "%REPO_ROOT%\docker-compose.yml" up -d db
if errorlevel 1 (
    echo ERROR: Failed to start the db container. Is Docker Desktop running?
    pause
    exit /b 1
)

REM ── wait for postgres to be ready ────────────────────────────────────────────
echo Waiting for PostgreSQL to be ready...
:wait_loop
docker compose -f "%REPO_ROOT%\docker-compose.yml" exec -T db pg_isready -U uran -d uran >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait_loop
)
echo PostgreSQL is ready.

REM ── override DATABASE_URL to match the Docker db service ─────────────────────
set "DATABASE_URL=postgresql+asyncpg://uran:uran@localhost:5432/uran"

REM ── virtualenv / dependencies ─────────────────────────────────────────────────
cd /d "%BACKEND%"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing / syncing dependencies...
pip install -e ".[dev]" -q

REM ── migrations + seed ─────────────────────────────────────────────────────────
echo Running migrations...
alembic upgrade head
if errorlevel 1 (
    echo ERROR: Migrations failed.
    pause
    exit /b 1
)

echo Seeding definitions...
python -m app.db.seed
if errorlevel 1 (
    echo ERROR: Seed failed.
    pause
    exit /b 1
)

REM ── start ─────────────────────────────────────────────────────────────────────
echo.
echo Backend running at http://localhost:8000
echo Swagger UI:         http://localhost:8000/docs
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
