@echo off
chcp 936 >nul 2>&1
setlocal EnableExtensions
cd /d "%~dp0"
title 禾光商家中心 - 本地演示

rem ============================================================
rem  禾光商家中心 本地演示启动脚本
rem  用法：双击 start.bat
rem         start.bat --check          仅检查环境，不启动服务
rem         set PORT=8001 && start.bat 指定端口
rem         set NO_BROWSER=1 && start.bat 不自动打开浏览器
rem  注意：本文件为 GBK 编码 + CRLF 换行，请勿存成 UTF-8，
rem        否则中文提示在 cmd 里会显示为乱码。
rem ============================================================

set "APP_PORT=8000"
set "CHECK_ONLY=0"
if defined PORT set "APP_PORT=%PORT%"
if /I "%~1"=="--check" set "CHECK_ONLY=1"

echo.
echo  ==========================================
echo     禾光商家中心 - 本地演示
echo  ==========================================
echo.

rem ==================== [1/4] 端口 ====================
echo [1/4] 检查端口 %APP_PORT% ...
call :port_pid %APP_PORT%
if not defined PORT_PID goto :port_ready

call :proc_name %PORT_PID%
echo       端口 %APP_PORT% 已被 %PROC_NAME% (PID %PORT_PID%) 占用
call :is_our_app %APP_PORT%
if not errorlevel 1 goto :already_running

echo       占用进程不是本演示服务，自动寻找空闲端口 ...
call :next_free_port
if not defined APP_PORT (
  echo  [X] 端口 8001-8010 均被占用，请先释放端口，或用 set PORT=xxxx 指定其他端口。
  goto :error
)
echo       已改用端口 %APP_PORT%
goto :port_ready

:already_running
if "%CHECK_ONLY%"=="1" (
  echo       本演示服务已在运行：http://127.0.0.1:%APP_PORT%/login
  echo  [--check] 无需启动。
  goto :done
)
echo       本演示服务已在运行，直接打开浏览器。
start "" "http://127.0.0.1:%APP_PORT%/login"
goto :done

:port_ready

rem ==================== [2/4] Python ====================
echo [2/4] 检查 Python 环境 ...
set "PY="
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,11) else 1)" >nul 2>&1
  if not errorlevel 1 set "PY=.venv\Scripts\python.exe"
)
if not defined PY if exist ".venv\Scripts\python.exe" (
  echo       已有 .venv 不可用（版本低于 3.11 或已损坏），删除后重建 ...
  rmdir /s /q ".venv" 2>nul
)

if not defined PY (
  for %%v in (3.12 3.11) do (
    if not defined PY (
      py -%%v -c "import sys" >nul 2>&1
      if not errorlevel 1 set "PY=py -%%v"
    )
  )
)
if not defined PY (
  for %%d in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
  ) do (
    if not defined PY if exist %%d set "PY=%%~d"
  )
)
if not defined PY (
  python -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo  [X] 未找到可用的 Python，需要 3.11 或 3.12：
  echo      https://www.python.org/downloads/
  echo      安装时请勾选 "Add python.exe to PATH"。
  goto :error
)

%PY% -c "import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo  [X] Python 版本低于 3.11，本项目需要 3.11 或 3.12。
  %PY% -V
  goto :error
)

if not exist ".venv\Scripts\python.exe" (
  echo       创建虚拟环境 .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo  [X] 创建虚拟环境失败，请检查磁盘权限或 Python 安装是否完整。
    goto :error
  )
)
set "PY=.venv\Scripts\python.exe"
for /f "delims=" %%v in ('%PY% -V 2^>^&1') do echo       使用 %%v

rem ==================== [3/4] 后端依赖 ====================
echo [3/4] 检查后端依赖 ...
%PY% -c "import fastapi, uvicorn, httpx" >nul 2>&1
if not errorlevel 1 goto :deps_ok
echo       安装 requirements.txt ...
rem pip 输出为 UTF-8，临时切换代码页，避免中文路径乱码
chcp 65001 >nul
%PY% -m pip install -q --disable-pip-version-check -r requirements.txt
set "PIP_RC=%errorlevel%"
chcp 936 >nul
if not "%PIP_RC%"=="0" (
  echo  [X] 后端依赖安装失败，请检查网络或 pip 源配置。
  goto :error
)
:deps_ok
echo       依赖已就绪

rem ==================== [4/4] 前端 ====================
echo [4/4] 检查前端环境 ...
where npm >nul 2>&1
if errorlevel 1 (
  echo  [X] 未找到 npm / Node.js，请安装 Node.js 18 或更高版本：
  echo      https://nodejs.org/
  goto :error
)

if exist "frontend\node_modules\vue\package.json" goto :fe_deps_ok
echo       安装前端依赖（首次运行较慢）...
rem npm / vite 的输出是 UTF-8，临时切到 65001 避免中文乱码
chcp 65001 >nul
call npm --prefix frontend install
set "NPM_RC=%errorlevel%"
chcp 936 >nul
if not "%NPM_RC%"=="0" (
  echo  [X] 前端依赖安装失败；可尝试：
  echo      npm --prefix frontend install --registry=https://registry.npmmirror.com
  goto :error
)
:fe_deps_ok

set "NEED_BUILD=0"
if not exist "frontend\dist\index.html" set "NEED_BUILD=1"
if "%NEED_BUILD%"=="1" goto :do_build
powershell -NoProfile -Command "$d=(Get-Item 'frontend\dist\index.html').LastWriteTime; $n=Get-ChildItem -Recurse -File 'frontend\src','frontend\index.html','frontend\vite.config.js','frontend\package.json' -ErrorAction SilentlyContinue | Where-Object {$_.LastWriteTime -gt $d}; if($n){exit 1}else{exit 0}" >nul 2>&1
if errorlevel 1 set "NEED_BUILD=1"
if "%NEED_BUILD%"=="0" goto :build_skip

:do_build
echo       构建 Vue 页面 ...
chcp 65001 >nul
call npm --prefix frontend run build
set "NPM_RC=%errorlevel%"
chcp 936 >nul
if not "%NPM_RC%"=="0" (
  echo  [X] 前端构建失败，请查看上方 Vite 输出。
  goto :error
)
goto :build_done
:build_skip
echo       构建产物已是最新，跳过构建
:build_done

rem ==================== 启动 ====================
echo.
echo  --------------------------------------------------
echo   访问地址: http://127.0.0.1:%APP_PORT%/login
echo   演示账号: admin / admin123
echo   咨询演示: http://127.0.0.1:%APP_PORT%/chat
echo  --------------------------------------------------
echo.

if "%CHECK_ONLY%"=="1" (
  echo  [--check] 环境检查全部通过，未启动服务。
  goto :done
)

if defined NO_BROWSER goto :no_browser
start "" powershell -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:%APP_PORT%/login'"
:no_browser
echo  正在启动服务，按 Ctrl+C 停止 ...
echo.
"%PY%" -m uvicorn backend.main:app --host 127.0.0.1 --port %APP_PORT%
echo.
echo  服务已停止。
goto :done

rem ==================== 子过程 ====================

:port_pid
rem %1 = 端口；结果写入 PORT_PID（未占用时为空）
set "PORT_PID="
for /f "tokens=5" %%p in ('netstat -ano -p tcp ^| findstr /C:":%~1 " ^| findstr /C:"LISTENING"') do set "PORT_PID=%%p"
exit /b 0

:proc_name
rem %1 = PID；结果写入 PROC_NAME
set "PROC_NAME=未知进程"
for /f "tokens=1 delims=," %%n in ('tasklist /FI "PID eq %~1" /FO CSV /NH 2^>nul') do set "PROC_NAME=%%~n"
exit /b 0

:is_our_app
rem %1 = 端口；是本演示服务（健康检查 ok）返回 0，否则返回 1
powershell -NoProfile -Command "try{$r=Invoke-RestMethod -Uri 'http://127.0.0.1:%~1/api/health' -TimeoutSec 2; if($r.status -eq 'ok'){exit 0}else{exit 1}}catch{exit 1}" >nul 2>&1
exit /b %errorlevel%

:next_free_port
rem 在 8001-8010 中找第一个空闲端口写入 APP_PORT；全部占用则置空
set "FOUND="
for /l %%p in (8001,1,8010) do (
  if not defined FOUND (
    call :port_pid %%p
    if not defined PORT_PID set "FOUND=%%p"
  )
)
set "APP_PORT=%FOUND%"
exit /b 0

:error
echo.
echo  启动失败，请根据上方提示处理后重试。
echo.
pause
endlocal
exit /b 1

:done
endlocal
exit /b 0
