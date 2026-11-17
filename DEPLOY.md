# LitRead AI — 黑客松交付指南

## 一、最终交付物（比赛时必须有）

你需要交付的不是代码本身，而是 **一个可以公开访问的 URL + 一个 3 分钟 Demo 视频 + 一页技术栈说明**。评审不会跑你的代码，他们打开链接就得看到功能。

| 交付物 | 形式 | 优先级 |
|--------|------|--------|
| 🔗 公网 URL | `https://xxx.streamlit.app` 或 `https://litread.yourdomain.com` | **必做** |
| 📼 Demo 视频（2-3 分钟） | 录屏：上传论文 → 速读卡片 → 对比 → 图谱 → 问答 → BibTeX 导出 | **必做** |
| 📄 README | 功能清单 + 架构图 + 技术栈 | 必做 |
| 🧾 技术栈说明 | 一页表格 | 加分 |
| 🏷️ GitHub Repo | 代码 + README + Demo GIF | 加分 |

## 二、最快拿公网 URL（推荐）

**Streamlit Community Cloud** 免费、2 分钟上线、自带 `*.streamlit.app` 域名。

### 步骤

```
1. 在 GitHub 创建一个新仓库，推上去（包含 litread-ai 整个目录）
2. 访问 https://streamlit.io/cloud，用 GitHub 登录
3. New App → 选你的 Repo → 主分支 → Main file path 填 frontend/app.py
4. 点击 Advanced settings，把 backend/.env 里的变量（LLM_BASE_URL / LLM_API_KEY / LLM_MODEL）逐个加进去
5. Deploy → 等 2 分钟 → 拿到 https://xxx.streamlit.app
```

⚠️ **关键**：Streamlit Cloud 会自动检测到 `backend/app.py`？不会。它只知道 frontend/app.py。你需要让 Streamlit 能访问后端 API。最简单的办法——**把后端部署到另一处**（Render / Fly.io / Railway，都是免费），然后 `frontend/app.py` 里的 `BACKEND_URL` 用那个地址。

### 更简单的替代：把后端 embed 进 Streamlit（单文件方案）

把后端核心逻辑（pdf_parser / rag / summary）改成 Streamlit 里直接调用，不再起独立 FastAPI。但这样改动大，你现在时间紧，**不推荐**。

### 推荐组合：Streamlit Cloud + Render（两个免费）

```
Render（https://render.com）：
  - New → Web Service
  - Build Command: cd litread-ai/backend && pip install -r requirements.txt
  - Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
  - 环境变量里填 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
  - 拿到 https://litread-backend.onrender.com

Streamlit Cloud：
  - 环境变量 BACKEND_URL = https://litread-backend.onrender.com
```

## 三、自托管（如果你有服务器）

### Docker 方案

```bash
# 构建并启动后端
docker build -t litread-backend ./backend
docker run -d --name litread-backend -p 8000:8000 \
  -e LLM_BASE_URL=... -e LLM_API_KEY=... -e LLM_MODEL=... \
  -v ./data:/app/data \
  litread-backend

# 构建并启动前端
docker build -t litread-frontend ./frontend
docker run -d --name litread-frontend -p 8501:8501 \
  -e BACKEND_URL=http://host.docker.internal:8000 \
  litread-frontend
```

### Nginx 反代（可选，绑域名）

```nginx
server {
  listen 443 ssl;
  server_name litread.yourdomain.com;

  location / {
    proxy_pass http://127.0.0.1:8501;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
  }

  location /api/ {
    proxy_pass http://127.0.0.1:8000;
  }
}
```

## 四、比赛 Demo 脚本（3 分钟）

按这个顺序演示，评审印象最深：

```
0:00 - 开场：一句话说清做了什么
  "我们做了 LitRead AI —— 一个面向学习和科研的文献阅读助手，
   把上传、速读、问答、对比、图谱整理串成一条完整链路。"

0:15 - 上传论文（2-3 篇），展示解析后的结构化信息（标题/摘要/章节）
0:45 - 速读卡片：3 秒出 TL;DR 和四维卡片，突出"三句话让外行也看懂"
1:15 - 多论文对比：2 篇论文 → 并排对比表 + 共识/分歧，演示导出 Markdown
1:45 - 文献图谱：点击按钮 → 拖拽交互图
2:10 - 问答："这些论文用了什么方法？" → 回答 + 引用来源
2:35 - BibTeX 导出 → 下载 references.bib
2:50 - 结束：一句话总结 "Demo 模式下不依赖外部 LLM 也能跑通全链路"
```

## 五、技术栈说明（放进 README 或 PPT）

| 层 | 技术 | 理由 |
|----|------|------|
| 前端 | Streamlit | 快速出可交互 Demo，黑客松首选 |
| 后端 | FastAPI | 类型安全 + 自动文档 + 易部署 |
| LLM | OpenAI 兼容协议 | 不绑定供应商，DeepSeek/中转/官方都能换 |
| 解析 | PyMuPDF | 按字号启发式识别标题 |
| 向量 | ChromaDB + ONNX MiniLM | 零服务器依赖、持久化、中文可用 |
| 图谱 | networkx + pyvis | 语义相似度连边 + 可拖拽交互图 |
| 存储 | SQLite + SQLAlchemy | 单机零运维 |

## 六、Demo 模式说明（重点加分项）

评审现场网络不稳或 API 挂了怎么办？**我们有 Demo 模式**：

- `backend/.env` 留空时自动进入 Demo 模式
- 所有功能都能跑：上传/索引/速读（从摘要生成）/问答（返回检索片段）/对比（从关键词重叠）/图谱/笔记/BibTeX/Related Work
- 健康接口会显式返回 `{"demo_mode": true}`，前端会显示黄色横幅
- 真正的 LLM 可用时，自动切到真实模式（无需改代码）

这个设计在评审时是一个亮点：**"我们考虑了现场网络不稳的情况，系统能优雅降级"**。
