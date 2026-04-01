@echo off
setlocal

set "REPO_ROOT=%~dp0.."
set "BACKEND=%REPO_ROOT%\backend"

if not exist "%BACKEND%\.env" (
    echo ERROR: %BACKEND%\.env not found.
    echo        Copy and edit the example:
    echo          copy backend\.env.example backend\.env
    pause
    exit /b 1
)

cd /d "%BACKEND%"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing / syncing dependencies...
pip install -e ".[dev]" -q

echo Running migrations...
alembic upgrade head

echo Seeding definitions...
python -m app.db.seed

echo.
echo Backend running at http://localhost:8000
echo Swagger UI:         http://localhost:8000/docs
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
