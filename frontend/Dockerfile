# 前端 Dockerfile
# 后端地址通过环境变量传入
# docker run -d -p 8501:8501 -e BACKEND_URL=http://host.docker.internal:8000 litread-frontend

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
