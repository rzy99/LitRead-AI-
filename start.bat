@echo off
chcp 65001 >nul
setlocal
set ROOT=%~dp0
set PY=%ROOT%.python\python.exe

echo ============================================
echo   LitRead AI - 启动脚本
echo ============================================

if not exist "%PY%" (
    echo [错误] 未找到便携版 Python: %PY%
    echo 请先把 python-3.11.9-embed-amd64 解压到 .python 目录。
    pause
    exit /b 1
)

if not exist "%ROOT%backend\.env" (
    copy "%ROOT%backend\.env.example" "%ROOT%backend\.env" >nul
    echo [提示] 已生成 backend\.env，请填入 LLM_API_KEY
)

echo.
echo [1/2] 启动后端 (http://127.0.0.1:8000) ...
start "LitRead-Backend" cmd /k "cd /d "%ROOT%backend" && "%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

timeout /t 6 /nobreak >nul

echo.
echo [2/2] 启动前端 (http://127.0.0.1:8501) ...
start "LitRead-Frontend" cmd /k "cd /d "%ROOT%frontend" && "%PY%" -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo 启动完成，浏览器打开 http://localhost:8501
endlocal
