# 📚 LitRead AI

> 面向学习与科研的 AI 文献阅读与整理工具 —— 把「上传 · 速读 · 问答 · 对比 · 图谱 · 笔记 · 写作」串成一条完整链路。

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B?logo=streamlit&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-FF6B6B)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 一、项目简介

科研人员读一篇论文平均要 30–60 分钟，读完还容易忘；跨论文对比、整理综述、写 Related Work 更是重复劳动。

**LitRead AI** 把文献处理拆成 8 个可独立使用、也能串起来的模块，上传 PDF 后即可完成从「读懂单篇」到「串起多篇」的全过程。

### 核心亮点

- **Demo 模式可降级**：没有 LLM API Key 时自动切换到本地模板/检索模式，全链路依然可演示，现场不怕断网
- **不绑定模型供应商**：统一走 OpenAI 兼容协议，DeepSeek / 中转站 / 官方 API 只改 3 个环境变量
- **零外部服务依赖**：向量库、数据库、图谱全部本地化，单机即可跑通
- **中英文兼容**：PDF 解析、分块、追问均支持中英文混合文献

---

## 二、功能一览

| # | 模块 | 说明 | 是否依赖 LLM |
|---|------|------|:---:|
| 1 | 📄 **论文解析** | 上传 PDF，按字号启发式识别标题，抽取作者/摘要/关键词/章节结构 | ❌ |
| 2 | ⚡ **速读卡片** | 一键生成 TL;DR + 核心贡献 / 方法亮点 / 主要结论 / 局限性 | ✅ 可降级 |
| 3 | 💬 **文献问答** | 基于向量检索的 RAG 问答，回答带来源标注（论文 ID + 块序号 + 相关度） | ✅ 可降级 |
| 4 | ⚖️ **多论文对比** | 2+ 篇论文并排对比表，自动归纳共识点与分歧点，支持导出 Markdown | ✅ 可降级 |
| 5 | 🕸️ **知识图谱** | 基于语义相似度构建论文关系网络，pyvis 可拖拽交互 | ❌ |
| 6 | 📝 **阅读笔记** | 摘录批注 → AI 按「研究问题 / 方法 / 实验 / 结论」结构化整理 | ✅ 可降级 |
| 7 | ✍️ **Related Work** | 输入研究主题，基于库中论文生成综述段落草稿 | ✅ 可降级 |
| 8 | 📑 **BibTeX** | 从元数据生成标准 BibTeX，支持批量导出 `references.bib` | ❌ |

> 「可降级」= LLM 不可用时自动回退到基于摘要/关键词/检索结果的真实内容，不会报错也不会编造数据。

---

## 三、技术栈

### 后端

| 分类 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | **FastAPI** | 0.115.0 | REST API、自动 OpenAPI 文档 |
| ASGI 服务器 | **Uvicorn** | 0.30.6 | 生产级异步服务 |
| 数据校验 | **Pydantic v2** + pydantic-settings | 2.9.2 / 2.5.2 | 请求响应模型、配置管理 |
| ORM | **SQLAlchemy** | 2.0.35 | 论文/笔记持久化 |
| 数据库 | **SQLite** | 内置 | 零运维单文件存储 |
| PDF 解析 | **PyMuPDF (fitz)** | 1.24.10 | 文本抽取、字号/坐标分析 |
| LLM SDK | **OpenAI Python SDK** | 1.51.2 | OpenAI 兼容协议统一调用 |
| 向量数据库 | **ChromaDB** | 0.5.13 | 持久化向量检索 |
| Embedding | **ONNX MiniLM-L6-v2**（内置）/ BGE-small-zh（可选） | — | 免 PyTorch 的中英文向量化 |
| 图计算 | **NetworkX** | 3.3 | 相似度建边、连通分量 |
| 图可视化 | **PyVis** | 0.3.2 | 生成可交互 HTML 图谱 |
| 数值计算 | **NumPy** | <2.0 | 余弦相似度、矩阵运算 |

### 前端

| 分类 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 应用框架 | **Streamlit** | 1.38.0 | 8 Tab 单页应用、内嵌图谱 HTML |
| HTTP 客户端 | **Requests** | 2.32.3 | 调用后端 REST API |

### 部署

| 方式 | 说明 |
|------|------|
| 本地 | 一键 `start.bat`（Windows）/ `start.sh` |
| 容器 | 前后端各自 `Dockerfile`，数据目录挂载卷 |
| 公网 | Streamlit Community Cloud + Render（免费组合），详见 [DEPLOY.md](./DEPLOY.md) |

---

## 四、系统架构

```
┌──────────────────────────────────────────────────────────┐
│                    Streamlit 前端 (8501)                  │
│  解析 │ 速读 │ 问答 │ 对比 │ 图谱 │ 笔记 │ RW │ BibTeX    │
└───────────────────────────┬──────────────────────────────┘
                            │ HTTP / JSON
┌───────────────────────────▼──────────────────────────────┐
│                    FastAPI 后端 (8000)                    │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │
│  │ pdf_parser │  │ summarizer │  │   comparison     │    │
│  │  PyMuPDF   │  │  LLM/降级  │  │     LLM/降级     │    │
│  └────────────┘  └────────────┘  └──────────────────┘    │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │
│  │    rag     │  │   graph    │  │ notes / bibtex   │    │
│  │ 检索+问答  │  │ NX + PyVis │  │ SQLite + LLM     │    │
│  └────────────┘  └────────────┘  └──────────────────┘    │
│                                                          │
│  ┌──────────────────┐  ┌────────────────────────────┐    │
│  │  vector_store    │  │       llm_client           │    │
│  │    ChromaDB      │  │  OpenAI 兼容 + is_llm_ready│    │
│  └──────────────────┘  └────────────────────────────┘    │
└───────────────────────────┬──────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌───────────┐      ┌────────────┐      ┌────────────┐
  │  SQLite   │      │  ChromaDB  │      │  PDF 存储  │
  │ papers /  │      │  向量持久化 │      │  data/     │
  │  notes    │      │            │      │  papers/   │
  └───────────┘      └────────────┘      └────────────┘
```

### 关键设计

**1. LLM 可插拔 + 优雅降级**

`llm_client.is_llm_ready()` 决定走哪条路径，业务代码不关心供应商：

```python
if is_llm_ready():
    try:
        return get_llm().chat_json(...)     # 真实模型
    except Exception as e:
        log.warning("LLM 失败，回退 demo：%s", e)
return demo.demo_summary(title, abstract)  # 本地模板
```

**2. Embedding 双通道**

优先 `sentence-transformers + BGE`（效果好），未安装时自动回退到 ChromaDB 内置 ONNX MiniLM（免 PyTorch、开箱即用），两条路径产出同维度归一化向量，集合不会串味。

**3. 分块策略**

按空行切段落 → 合并至 800 字符 → 超长段落按 120 字符重叠硬切，兼顾语义完整性与检索粒度。

**4. PDF 结构化提取**

基于字号分布（最大字号 = 标题）+ 坐标排序 + 正则关键词匹配（Abstract / Introduction / References）做启发式识别，不依赖 ML 模型，冷启动零延迟。

---

## 五、快速开始

### 环境要求

- Python 3.11+
- 无需 GPU、无需 Docker、无需外网数据库

### 方式一：一键启动（Windows）

```bat
git clone <your-repo-url>
cd litread-ai
start.bat
```

打开 http://localhost:8501

### 方式二：手动启动

```bash
# 1. 后端
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. 前端（新终端）
cd frontend
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

### 配置 LLM（可选）

复制 `backend/.env.example` → `backend/.env`，填入三行即可，**不填则自动进入 Demo 模式**：

```env
LLM_BASE_URL=https://api.deepseek.com/v1   # 任意 OpenAI 兼容端点
LLM_API_KEY=sk-xxxxxxxx
LLM_MODEL=deepseek-chat
```

> 已验证兼容 DeepSeek 官方 API 与标准 OpenAI 协议中转站。

---

## 六、配置项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM 端点（OpenAI 兼容） |
| `LLM_API_KEY` | 空 | 空 → 自动 Demo 模式 |
| `LLM_MODEL` | `deepseek-chat` | 模型名 |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 安装了 sentence-transformers 时生效 |
| `EMBEDDING_DEVICE` | `cpu` | 有 GPU 可改 `cuda` |
| `RAG_CHUNK_SIZE` | 800 | 分块字符数 |
| `RAG_CHUNK_OVERLAP` | 120 | 分块重叠字符数 |
| `RAG_TOP_K` | 6 | 检索返回条数 |
| `GRAPH_SIMILARITY_THRESHOLD` | 0.55 | 图谱连边阈值（越低边越多） |
| `SUMMARY_MAX_CHARS` | 15000 | 送入 LLM 的最大字符数 |

---

## 七、API 一览

后端启动后访问 **http://localhost:8000/docs** 可查看交互式文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 + LLM 就绪状态 |
| GET | `/api/library/stats` | 论文数 / 向量块数 |
| POST | `/api/papers/upload` | 上传并解析 PDF |
| GET | `/api/papers` | 论文列表 |
| DELETE | `/api/papers/{id}` | 删除论文（含向量与文件） |
| POST | `/api/papers/{id}/parse` | 获取完整结构化内容 |
| POST | `/api/papers/{id}/summary` | 生成速读卡片 |
| POST | `/api/papers/{id}/index` | 建立向量索引 |
| POST | `/api/ask` | 文献库问答 |
| POST | `/api/compare` | 多论文对比 |
| POST | `/api/compare/export` | 对比表导出 Markdown |
| GET | `/api/graph` | 生成知识图谱 |
| POST | `/api/papers/{id}/notes` | 添加笔记 |
| GET | `/api/notes` | 查询笔记 |
| DELETE | `/api/notes/{id}` | 删除笔记 |
| POST | `/api/papers/{id}/notes/organize` | AI 结构化整理笔记 |
| GET | `/api/papers/{id}/bibtex` | 单篇 BibTeX |
| POST | `/api/bibtex/export` | 批量导出 BibTeX |
| POST | `/api/related-work` | 生成 Related Work 草稿 |

---

## 八、项目结构

```
litread-ai/
├── DEPLOY.md                    # 部署 + 比赛交付 + Demo 脚本
├── start.bat / start.sh         # 一键启动
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt         # 轻量依赖（不含 PyTorch）
│   ├── requirements-embedding.txt  # 可选：BGE 高质量向量
│   ├── .env.example
│   └── app/
│       ├── main.py              # 应用入口
│       ├── api.py               # 全部路由
│       ├── config.py            # 配置（pydantic-settings）
│       ├── models.py            # 请求/响应模型
│       ├── database.py          # SQLAlchemy 引擎与会话
│       ├── db_models.py         # Paper / Note 表
│       └── services/
│           ├── pdf_parser.py    # 字号启发式解析
│           ├── embeddings.py    # BGE / ONNX 双通道
│           ├── vector_store.py  # ChromaDB 封装
│           ├── rag.py           # 分块 + 检索 + 问答
│           ├── summarizer.py    # 速读卡片
│           ├── comparison.py    # 多论文对比
│           ├── graph.py         # 相似度图谱
│           ├── notes.py         # 笔记管理
│           ├── bibtex.py        # BibTeX 生成
│           ├── related_work.py  # 综述草稿
│           ├── llm_client.py    # OpenAI 兼容封装
│           ├── demo.py          # Demo 模式全部实现
│           └── paper_store.py   # 论文注册表
├── frontend/
│   ├── Dockerfile
│   ├── app.py                   # Streamlit 8 Tab
│   └── requirements.txt
└── data/                        # 运行时生成（已 gitignore）
    ├── papers/
    ├── chroma/
    └── litread.db
```

---

## 九、Demo 模式说明

**为什么需要**：黑客松现场网络不稳定，API 可能超时或余额不足；评审也需要立刻看到完整功能。

**怎么工作**：`backend/.env` 中 `LLM_API_KEY` 为空，或首次调用失败时，自动切换到 Demo 路径。

| 功能 | Demo 模式输出 |
|------|---------------|
| 速读卡片 | 从摘要中抽取首句/中句/末句，分别填充核心贡献、方法、结论 |
| 问答 | 返回向量检索 top-k 真实片段 + 相关度 + 来源标注 |
| 对比 | 关键词集合交集/差集计算共识与分歧 |
| Related Work | 关键词匹配排序，生成关联清单 |
| 笔记整理 | 关键词分类到「研究问题/方法/实验/结论」 |

`GET /api/health` 会返回 `{"llm_ready": false, "demo_mode": true}`，前端顶部显示黄色提示条。

---

## 十、已知限制与后续规划

**当前限制**

- PDF 解析基于字号启发式，扫描版（图片型）PDF 尚不支持 OCR
- 关键词提取偶有把正文首句带入的情况
- 默认 ONNX MiniLM 偏英文，中文语义效果弱于 BGE
- 暂无用户体系，多人共用同一实例会共享文献库

**规划**

- [ ] 接入 PaddleOCR / Marker 支持扫描版与公式图表理解
- [ ] 支持 Zotero / arXiv / Semantic Scholar 直接导入
- [ ] 增加多用户隔离与分享链接
- [ ] 引入文献引用网络（而非仅语义相似度）构建图谱
- [ ] 支持综述长文自动生成（多段 Related Work）

---

## 十一、License

MIT License — 可自由用于学习、科研与商业项目，请保留版权声明。

---

<p align="center">
  <sub>Built for AI for Learning & Research · Hackathon 2026</sub>
</p>
