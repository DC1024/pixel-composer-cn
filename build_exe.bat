@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Pixel Composer 汉化工具 - 打包为单文件 EXE（PyInstaller）
echo ============================================================
echo.

rem 选择 Python（需 3.7+，且带 tkinter）
set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY (where python >nul 2>&1 && set "PY=python")
if not defined PY (
  echo [错误] 未找到 Python。请安装 Python 3.7+ 并勾选 "Add Python to PATH"。
  pause & exit /b 1
)

echo [1/3] 安装 / 升级 PyInstaller ...
%PY% -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 (
  echo [错误] PyInstaller 安装失败。
  pause & exit /b 1
)

set "WORK=%TEMP%\pc-cn-pyi"
if exist "%WORK%" rmdir /s /q "%WORK%"

echo [2/3] 开始打包（onefile / windowed / 内嵌 zh 汉化包）...
rem 注意：--add-data 必须用绝对路径。PyInstaller 会以 --specpath 目录为基准
rem 解析相对路径，用相对路径会报 "Unable to find ...\spec\zh"。
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "PixelComposer-CN-Patcher" ^
  --icon "%~dp0app_icon.ico" ^
  --add-data "%~dp0zh;zh" ^
  --add-data "%~dp0app_icon.ico;." ^
  --add-data "%~dp0translate_core.py;." ^
  --hidden-import translate_core ^
  --workpath "%WORK%\build" --specpath "%WORK%\spec" --distpath "%WORK%\dist" ^
  "%~dp0patch_tool.py"
if errorlevel 1 (
  echo [错误] 打包失败。
  pause & exit /b 1
)

echo [3/3] 复制为发布文件 ...
copy /y "%WORK%\dist\PixelComposer-CN-Patcher.exe" "PixelComposer一键汉化.exe" >nul
if errorlevel 1 (
  echo [错误] 复制失败。
  pause & exit /b 1
)

echo.
echo ============================================================
echo   完成！已生成：PixelComposer一键汉化.exe
echo ============================================================
pause
