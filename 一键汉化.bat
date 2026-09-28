@echo off
chcp 65001 >nul
setlocal
set "SCRIPT=%~dp0patch_tool.py"
set PY=
where py >nul 2>&1 && set PY=py
if not defined PY (where python >nul 2>&1 && set PY=python)
if not defined PY (where python3 >nul 2>&1 && set PY=python3)
if not defined PY (
  echo 未找到 Python。请先安装 Python 3.7+ 并勾选 “Add Python to PATH”。
  pause
  exit /b 1
)
"%PY%" "%SCRIPT%" %*
pause
