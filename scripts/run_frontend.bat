@echo off
setlocal

set "REPO_ROOT=%~dp0.."
set "FRONTEND=%REPO_ROOT%\frontend"

cd /d "%FRONTEND%"

if not exist "node_modules" (
    echo Installing npm dependencies...
    npm install
)

echo.
echo Frontend running at http://localhost:5173
echo (proxies /api/* -^> http://localhost:8000 -- start backend first)
echo.
npm run dev
