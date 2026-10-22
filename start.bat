@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ==========================================
echo    禾光商家中心 - 本地演示
echo  ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] 正在创建 Python 环境...
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo [2/4] 正在安装后端依赖...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

if not exist "frontend\node_modules\vue\package.json" (
  echo [3/4] 正在安装前端依赖...
  call npm --prefix frontend install
  if errorlevel 1 goto :error
)

echo [4/4] 正在构建并启动页面...
call npm --prefix frontend run build
if errorlevel 1 goto :error

start "" powershell -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000/login'"
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
goto :eof

:error
echo.
echo 启动失败，请检查上方错误信息。
pause
exit /b 1
