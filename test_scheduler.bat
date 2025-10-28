@echo off
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"
echo ================================================== >> "%SCRIPT_DIR%\worker_scheduler.log"
echo [%date% %time%] 🧪 Test Scheduler Run start >> "%SCRIPT_DIR%\worker_scheduler.log"

REM ✅ 1) Aktiviraj virtualno okruženje (.venv)
if exist "%SCRIPT_DIR%\.venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"
    echo [VENV] Aktiviran virtualenv >> "%SCRIPT_DIR%\worker_scheduler.log"
) else (
    echo [VENV] ⚠️ Nije pronađen .venv unutar %SCRIPT_DIR% >> "%SCRIPT_DIR%\worker_scheduler.log"
)

REM ✅ 2) Pokreni worker modul
set PYTHONPATH=%SCRIPT_DIR%
python -m wizvod.worker --run >> "%SCRIPT_DIR%\worker_scheduler.log" 2>&1

echo [%date% %time%] 🧪 Test Scheduler Run finished >> "%SCRIPT_DIR%\worker_scheduler.log"
echo ================================================== >> "%SCRIPT_DIR%\worker_scheduler.log"
pause
