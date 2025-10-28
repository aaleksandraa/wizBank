@echo off
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo ================================================== >> "%SCRIPT_DIR%\worker_scheduler.log"
echo [%date% %time%] 🚀 Auto Worker Start >> "%SCRIPT_DIR%\worker_scheduler.log"

REM ✅ Aktiviraj virtualenv ako postoji
if exist "%SCRIPT_DIR%\.venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"
    echo [VENV] Aktiviran virtualenv >> "%SCRIPT_DIR%\worker_scheduler.log"
) else (
    echo [VENV] ⚠️ Nije pronađen .venv >> "%SCRIPT_DIR%\worker_scheduler.log"
)

REM ✅ Postavi PYTHONPATH na glavni folder projekta (ne na wizvod\)
set PYTHONPATH=%SCRIPT_DIR%

REM ✅ Pokreni worker kao modul
python -m wizvod.worker >> "%SCRIPT_DIR%\worker_scheduler.log" 2>&1

echo [%date% %time%] ✅ Auto Worker Finished >> "%SCRIPT_DIR%\worker_scheduler.log"
echo ================================================== >> "%SCRIPT_DIR%\worker_scheduler.log"
