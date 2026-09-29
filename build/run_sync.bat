@echo off
rem Weekly upstream sync for the Pixel Composer CN pack.
rem Registered by build\install_weekly_task.ps1 (Windows Task Scheduler).
rem NOTE: kept ASCII-only on purpose - cmd decodes a BOM-less .bat as ANSI,
rem       so any CJK comment here would turn into mojibake.
setlocal

set "REPO=%~dp0.."
cd /d "%REPO%" || exit /b 1

rem Python: stdlib only, so any 3.9+ works. Override with the PYTHON env var.
if "%PYTHON%"=="" set "PYTHON=C:\Users\15657.DC-PC\AppData\Local\Python\pythoncore-3.12-64\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

rem Force UTF-8 IO: when stdout is redirected by Task Scheduler, Python would
rem otherwise fall back to the system ANSI codepage and corrupt CJK log output.
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not exist "build\_sync_logs" mkdir "build\_sync_logs"

"%PYTHON%" build\sync_upstream.py --push >> "build\_sync_logs\sync.log" 2>&1
exit /b %ERRORLEVEL%
