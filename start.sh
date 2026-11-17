#!/bin/bash
echo "============================================"
echo "  LitRead AI - 启动脚本 (macOS/Linux)"
echo "============================================"

# ---- 检查并复制 .env ----
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "[提示] 已自动生成 backend/.env，请填入你的 LLM_API_KEY"
fi

# ---- 启动后端 ----
echo ""
echo "[1/2] 启动后端 FastAPI (端口 8000)..."
cd backend
if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

sleep 5

# ---- 启动前端 ----
echo ""
echo "[2/2] 启动前端 Streamlit (端口 8501)..."
cd frontend
if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
streamlit run app.py --server.port 8501 &

wait
