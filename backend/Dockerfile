# 后端 Dockerfile
# docker build -t litread-backend .
# docker run -d -p 8000:8000 --env-file .env litread-backend

FROM python:3.11-slim

WORKDIR /app

# 依赖先装，利用 Docker 缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ChromaDB 默认把 ONNX 模型下载到 ~/.cache/chroma
ENV CHROMA_PERSIST_DIRECTORY=/app/data/chroma

COPY app ./app
COPY .env ./

# 数据卷
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
