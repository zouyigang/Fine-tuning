@echo off
setlocal
chcp 65001 >nul

REM ============================================================
REM  Fine-tuning host launcher: MySQL84 + backend(8000) + frontend(5180)
REM  - Starts MySQL service (elevates only for that step)
REM  - Runs `alembic upgrade head` (idempotent; keeps schema in sync)
REM  - Launches backend and frontend in their own windows
REM  Edit PY / MYSQL_SVC below if your paths differ.
REM ============================================================

set "PY=D:\anaconda3\python.exe"
set "MYSQL_SVC=MySQL84"
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo ============================================
echo  Fine-tuning host launcher
echo ============================================

REM ---- 1) MySQL ----
sc query "%MYSQL_SVC%" | find "RUNNING" >nul
if errorlevel 1 (
  echo [1/4] Starting service %MYSQL_SVC% ... ^(a UAC prompt may appear^)
  powershell -NoProfile -Command "Start-Process net -ArgumentList 'start','%MYSQL_SVC%' -Verb RunAs -Wait"
  timeout /t 4 /nobreak >nul
) else (
  echo [1/4] %MYSQL_SVC% already running.
)

REM ---- 2) Alembic (schema migrations; safe to run every time) ----
echo [2/4] alembic upgrade head ...
pushd "%ROOT%\server"
set "PYTHONUTF8=1"
"%PY%" -m alembic upgrade head
if errorlevel 1 (
  echo.
  echo [ERROR] alembic upgrade failed - is MySQL up? See message above.
  popd
  pause
  exit /b 1
)
popd

REM ---- 3) Backend (own window, UTF-8) ----
echo [3/4] starting backend  -> http://localhost:8000/docs
start "Fine-tuning Backend :8000" /d "%ROOT%\server" cmd /k "chcp 65001 >nul && set PYTHONUTF8=1&& %PY% -m uvicorn app.main:app --port 8000"

REM ---- 4) Frontend (own window) ----
echo [4/4] starting frontend -> http://localhost:5180
start "Fine-tuning Frontend :5180" /d "%ROOT%" cmd /k "npm run dev"

echo.
echo Launched. Login: admin / admin123
echo Close the two opened windows to stop backend/frontend.
timeout /t 6 /nobreak >nul
endlocal
