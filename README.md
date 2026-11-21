# LitRead · AI 研究思维训练

> 不是替你读论文，而是训练你像作者一样想。

**12 步研究流 · 作者路径逆向 · 先写后揭晓 · 红队/反例 · 思路对比 · 成长曲线**

[在线体验](https://litread.yogdunana.cn) · [竞品与相关工作](docs/competitive-landscape.md) · [部署说明](DEPLOY.md) · [3 分钟演示脚本](LitRead-Viz-Demo-Script.md)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 一、项目简介

科研训练里最缺的往往不是「再读一篇」，而是「自己推演一次」。

我们习惯了看别人总结好的方法、结论和局限，于是读完一篇论文，很容易产生一种错觉：这个方法本来就该这么想。但真正的研究能力，发生在**方法出现之前**——面对同样的背景和限制，你能提出什么假设？你会走哪条路？你会放弃什么？

**LitRead 是一个 12 步研究思维训练工作台。** 它把一篇论文拆成 6 个阶段、12 个研究动作：先建立背景，再只凭方法出现前的知识推演作者路径；然后拆解方法、审视证据、做红队攻击、设计反例，最后提出自己的 follow-up。

它不替用户读论文，也不替用户写论文。它把原本不可见的思考过程画出来，让用户先写、再对照、再改进。

> 一句话：**其他工具帮你更快地读，LitRead 帮你更像一个研究者那样想。**

### 适合谁

- 想从「读论文」过渡到「做研究」的本科生、研究生
- 准备组会、开题、审稿，需要快速建立判断的人
- 想训练学生研究思维的高校老师、实验室
- 对某个方向感兴趣，但不想只停留在「看懂摘要」的人

### 不适合谁

- 只想快速摘要、翻译、PDF 问答：ChatPDF、Scholarcy 更合适
- 想做大规模系统性综述：Elicit、SciSpace 更合适
- 想自动生成论文/自动做实验：AI Scientist、Agent Laboratory 更合适
- 想要「一键出结果」：LitRead 会刻意保留认知摩擦

---

## 二、五个页面

导航顺序固定为：**研究流 → 概述图 → 对比 → 笔记 → 论文库**。

| 页面 | 你在这里做什么 | 核心产出 |
|---|---|---|
| **研究流** | 按 6 阶段、12 步读一篇论文；第 3 步先写作者路径，再揭晓对照 | 一篇论文的完整研究拆解 + 4 张思维可视化 |
| **概述图** | 把论文压成一张竖版网页笔记 | 一句话总结、研究问题、方法直觉、关键结果、局限、takeaway；可下载 PNG |
| **对比** | 把 2 篇以上论文的「思路」并排，而不是比摘要相似度 | 8 个思维阶段并排、思维模式标签、没走的路、完整作者路径 |
| **笔记** | 写自己的想法、疑问或反思；留空时自动写入研究流 12 步 | 可展开/删除的笔记列表；可下载 PDF |
| **论文库** | 上传 PDF、解析元数据、管理文献架 | 标题、作者、年份、摘要、章节结构；可删除论文 |

---

## 三、12 步研究流

| 阶段 | 步 | 研究动作 | 用户要做什么 |
|---|---:|---|---|
| 一 · 背景与前史 | 1 | 研究问题：它为什么值得做 | 读背景，判断问题价值 |
|  | 2 | 前史：前人为什么不够 | 看时间线，找真正的缺口 |
| 二 · 作者路径（核心） | 3 | 作者最可能的思考路径 | **先写自己的推演，再揭晓 AI 的重建** |
| 三 · 方法与数学 | 4 | Intuition：核心 idea 的本质 | 用自己的话解释，而不是复述 |
|  | 5 | 具体方法：一个真实样本的 pipeline | 跟一遍数据流，找到关键设计 |
|  | 6 | 数学推导：从零开始 | 补预备概念，逐行推导 |
| 四 · 实验证据 | 7 | 问题 → 实验 → 答案 | 看每个实验到底回答了哪个问题 |
|  | 8 | Take-aways | 提炼可复用的结论 |
| 五 · 红队审稿 | 9 | 最脆弱的假设 | 找最可能被攻击的假设 |
|  | 10 | 一周最小复现 | 设计最小验证，而不是复现整篇 |
|  | 11 | 如果我反对它：反例设计 | 设计一个能推翻它的反例 |
| 六 · 我的 idea | 12 | Follow-up idea：从缺陷到新问题 | **先写自己的 idea，再对照 AI 的方向** |

### 第 3 步为什么是核心

第 3 步只给「方法出现前」的知识：当时的背景、已知工作、限制和矛盾。用户先写自己认为作者会怎么想，提交后才看到 AI 重建的作者路径。

这一步刻意制造信息隔离：

- 不提前给方法、实验结果和结论
- 用户必须先产出自己的路径
- 提交后才出现「你的路径」与「作者路径」的对照
- 对照是确定性文字重合计算，不调用 LLM

---

## 四、六个可视化

### 先看这条完整的构成条

研究流页最顶部有一条 **100% 堆叠色带**，把 12 步按信息来源分成四类：

| 类别 | 怎么判断 |
|---|---|
| **论文事实** | 能直接回到论文原文的依据 |
| **背景 / 外部** | 领域背景、前人工作、常识；不是本文结论 |
| **AI 推断** | 研究流里的合理推演，需要回原文核对 |
| **事实 + 推断** | 两者混用，不能简单归到一边 |

色带下方会直接写一句：「X% 是论文事实，Y% 是背景/外部知识，Z% 是 AI 推断……」。
这条色带只统计 12 步的依据来源，不包含用户路径和红队标记。

| 可视化 | 位置 | 它回答什么 |
|---|---|---|
| **研究流构成（可信度光谱）** | 研究流页顶 | 论文事实、背景/外部、AI 推断、事实+推断各占多少？ |
| **前史时间线** | 阶段一 | 这个想法出现前，世界已经知道了什么？哪些年份有明确节点？ |
| **思维分叉图** | 阶段二（第 3 步） | 作者从哪个世界出发、在哪一步跳跃、有哪些备选路线、你的路径在哪分叉？ |
| **论证结构图** | 阶段五顶部 | 主张靠哪些实验支撑？哪些主张被红队攻击、连线断在哪？ |
| **成长曲线** | 侧栏 | 已训练几篇？平均接近度多少？最近几次推演是进步还是波动？ |
| **思路对比** | 对比页 | 多篇论文的起点、转折、关键跳跃、设计取舍、最脆弱假设、没走的路有什么不同？ |

**思路对比的 8 个阶段**：起点 → 转折 → 关键跳跃 → 设计取舍 → 证据策略 → 最脆弱假设 → 没走的路 → 留下的问题。

### 思维分叉图怎么读

- 左侧：**方法出现前的世界**——作者当时知道什么、被什么卡住
- 中间：**作者路径**——每一步包含已知、疑问、跳跃、诱惑
- 右侧：**论文设计**——想法最终落成了什么方法（没有 design mapping 时省略）
- 小三角：**诱惑**——最容易走错的那一步
- 虚线：**备选路线**——作者没走的路，以及为什么放弃
- 高亮路径：**你的推演**——只在提交后出现；hit 实心环、partial 半环、miss 空心
- 分叉点：你的路径第一次偏离作者路径的位置；如果你更像某条备选路线，会在对应分支处亮起

---

## 五、和现有工具的区别

现有 AI 科研工具大致分四类：

| 类型 | 代表 | 它们给你 | LitRead 给你 |
|---|---|---|---|
| 答案引擎 | Elicit、Consensus、SciSpace、PaperQA2、ChatPaper | 答案、摘要、综述、提取表 | 先推演、再对照的训练 |
| 文献关系图 | Connected Papers、Litmaps、ResearchRabbit | 谁和谁相关/相似 | 谁的思路、起点、跳跃、取舍不同 |
| 研究自动化 Agent | AI Scientist、Agent Laboratory、STORM、GPT Researcher | 替你做检索、综述、实验、写作 | 训练你自己做研究 |
| 阅读/审稿辅助 | Explainpaper、Scholarcy、ReadPaper、OpenReviewer | 解释难句、速读卡、自动审稿 | 作者路径 + 红队 + 反例 + follow-up |

详细的项目对比、能力矩阵和答辩话术见：[docs/competitive-landscape.md](docs/competitive-landscape.md)。

> 我们刻意不做：论文问答、引文图谱、Related Work 生成、BibTeX 导出。

---

## 六、核心设计原则

### 1. 信息隔离

第 3 步只给方法出现前的知识。用户看不到方法、实验和结论，避免「看完答案觉得理所当然」。

### 2. 先写后揭晓

第 3 步和第 12 步都要求用户先写自己的版本，提交后才揭晓 AI 的版本。顺序不能反。

### 3. 用户路径只在提交后出现

分叉图里的用户路径、命中/半命中/未命中，只在用户提交推演后渲染。

### 4. 确定性对照，不调 LLM

第 3 步的路径对照、成长分数、思路对比都基于已有研究流字段做确定性计算：

- 字符 bigram / 英文词 / 数字 token
- Dice + coverage
- 不调用 LLM，不引入随机性

「接近度」是启发式指标。

### 5. 独立缓存，互不污染

- 研究流缓存：`data/research/{paper_id}.json`，版本 `rf-4`
- 可视化缓存：`data/research/{paper_id}.viz.json`，版本 `vz-4`
- 概述图缓存：`data/overview/{paper_id}.json` + `.png`，版本 `on-1`

可视化升级不会让研究流缓存失效；研究流变化会通过指纹触发可视化重建。

### 6. 原生 SVG/HTML，不引 Plotly

- 静态图直接内联在页面流里，高度随内容自适应
- 分叉图用固定高度 iframe + 响应式布局，避免内部滚动条
- 支持键盘聚焦与 `prefers-reduced-motion`
- 每张图都有：标题 + 一句话结论 + 可展开数据表

---

## 七、技术架构

```text
┌─────────────────────────────────────────────────────┐
│ Streamlit 前端（单文件 app.py）                      │
│ 研究流 · 概述图 · 思路对比 · 笔记 · 论文库           │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP / JSON
┌──────────────────────────▼──────────────────────────┐
│ FastAPI 后端                                         │
│ PDF 解析 · 研究流生成 · 可视化构建 · 思路对比         │
│ 概述图 · 笔记 · 成长记录                              │
└──────────────────────────┬──────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
      SQLite          data/research      data/papers
   论文/笔记/成长     rf-4 / vz-4 缓存     PDF 原文
```

| 层 | 技术 | 作用 |
|---|---|---|
| 前端 | Streamlit 1.38 | 5 页单文件应用、自定义 CSS、原生 SVG/HTML |
| 后端 | FastAPI 0.115 + Uvicorn | REST API、OpenAPI 文档 |
| 模型 | OpenAI 兼容协议 | 默认 DeepSeek；可替换任意兼容端点 |
| PDF | PyMuPDF | 标题/作者/摘要/章节结构解析 |
| 数据库 | SQLite + SQLAlchemy | 论文、笔记、成长记录 |
| 缓存 | 本地 JSON | 研究流、可视化、概述图；独立版本号 |
| 对照 | 字符 bigram + Dice/coverage | 作者路径接近度、思路对比，不调 LLM |
| 可视化 | 原生 SVG/HTML/CSS | 光谱、时间线、分叉图、论证图、成长曲线、思路对比 |

> 仓库中仍保留早期 RAG/图谱服务与依赖，用于兼容旧数据和旧接口；当前 5 页主流程只使用 PDF 解析、研究流、可视化、思路对比、概述图和笔记。

---

## 八、快速开始

### 环境要求

- Python 3.10+
- 无需 GPU、无需 Docker、无需外部数据库
- 可选：一个 OpenAI 兼容 API Key（不填则进入 Demo 模式）

### 方式一：一键启动

**Windows**

1. 将便携版 Python 解压到项目根目录的 `.python/`（确保存在 `.python\python.exe`）
2. 双击 `start.bat`
3. 打开 http://localhost:8501

**macOS / Linux**

```bash
chmod +x start.sh
./start.sh
```

`start.sh` 会自动创建后端/前端 venv、安装依赖并启动两个服务。

### 方式二：手动启动

```bash
# 1. 后端
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# 2. 前端（新终端）
cd frontend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

打开 http://localhost:8501。后端交互式 API 文档在 http://localhost:8000/docs。

### 配置 LLM

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

```env
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-xxxxxxxx
LLM_MODEL=deepseek-chat
```

> 任意 OpenAI 兼容端点均可。不填 Key 时，在线演示的预置论文仍可完整体验；上传新论文并生成深度研究流需要配置 Key。

### 在线演示

- 地址：https://litread.yogdunana.cn
- 预置 3 篇真实论文：Attention Is All You Need（2017）、Mastering the Game of Go with Self-play Experience Replay（2026）、Beyond Visual Evidence: Relational Privacy Leakage in Document MLLMs（2026）
- 每个 IP 有 30 次 LLM 调用试用；粘贴自己的 Key 后不限量
- Key 只在当前会话内存中使用，不写入磁盘

---

## 九、配置项

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI 兼容端点 |
| `LLM_API_KEY` | 空 | 空 → Demo 模式 |
| `LLM_MODEL` | `deepseek-chat` | 模型名 |
| `BACKEND_HOST` | `0.0.0.0` | 后端监听地址 |
| `BACKEND_PORT` | `8000` | 后端端口 |
| `DATA_DIR` | `../data` | 数据根目录 |
| `PAPERS_DIR` | `../data/papers` | PDF 存储目录 |
| `DB_PATH` | `../data/litread.db` | SQLite 路径 |

> `.env.example` 中仍保留旧版 RAG/图谱变量；当前 5 页主流程不依赖它们。

---

## 十、API 一览

后端启动后访问 **http://localhost:8000/docs** 查看交互式文档。核心接口：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 + LLM 就绪状态 |
| GET | `/api/rate-status` | 当前 IP 试用次数 |
| POST | `/api/verify-key` | 验证用户自配 Key |
| POST | `/api/papers/upload` | 上传并解析 PDF |
| GET | `/api/papers` | 论文列表 |
| DELETE | `/api/papers/{id}` | 删除论文及缓存 |
| POST | `/api/papers/{id}/parse` | 获取完整结构化内容 |
| GET | `/api/papers/{id}/research` | 获取研究流缓存 |
| POST | `/api/papers/{id}/research/{stage}` | 生成指定阶段（context/author/method/evidence/critique/idea） |
| POST | `/api/papers/{id}/research/{stage}/compare` | 对照用户推演 |
| POST | `/api/papers/{id}/research/author/compare-structured` | 第 3 步结构化对照（分叉图/成长） |
| GET | `/api/papers/{id}/research/viz` | 获取可视化数据（独立 `vz-4` 缓存） |
| GET | `/api/papers/{id}/research/markdown` | 导出研究流 Markdown |
| GET | `/api/research/growth?session_id=...` | 成长曲线数据 |
| POST | `/api/compare` | 多论文思路对比 |
| POST | `/api/compare/export` | 思路对比 Markdown 导出 |
| GET | `/api/papers/{id}/overview` | 概述图结构化数据 |
| GET | `/api/papers/{id}/overview.png` | 概述图 PNG |
| POST | `/api/papers/{id}/notes` | 添加笔记 |
| GET | `/api/notes?paper_id=...` | 查询笔记 |
| DELETE | `/api/notes/{id}` | 删除笔记 |
| GET | `/api/papers/{id}/notes/pdf` | 笔记 PDF 导出 |

---

## 十一、项目结构

```text
litread/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── api.py                  # 路由与中间件
│   │   ├── config.py               # pydantic-settings 配置
│   │   ├── models.py               # 请求/响应模型
│   │   ├── db_models.py            # Paper / Note / CompareScore
│   │   ├── database.py             # SQLAlchemy 引擎与会话
│   │   ├── rate_limit.py           # IP 限流
│   │   ├── context.py              # 用户 Key 的请求上下文
│   │   └── services/
│   │       ├── pdf_parser.py       # 字号启发式 PDF 解析
│   │       ├── paper_store.py      # 论文注册表
│   │       ├── research_flow.py    # 6 阶段 / 12 步研究流
│   │       ├── research_viz.py     # 光谱/分叉/论证/时间线/成长/思路对比
│   │       ├── comparison.py       # 多论文思路对比
│   │       ├── overview_note.py    # 概述图生成与缓存
│   │       ├── notes.py            # 笔记管理
│   │       ├── note_pdf.py         # 笔记 PDF
│   │       ├── llm_client.py       # OpenAI 兼容封装
│   │       └── demo.py             # Demo 模板
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app.py                      # 单文件 Streamlit 应用（5 页）
│   └── requirements.txt
├── docs/
│   └── competitive-landscape.md    # 竞品与相关工作
├── data/                           # 运行时生成（gitignore）
├── start.bat
├── start.sh
├── DEPLOY.md
└── README.md
```

---

## 十二、数据与缓存

| 路径 | 内容 | 说明 |
|---|---|---|
| `data/papers/` | 上传的 PDF 原文 | 本地存储；生成研究流时论文文本会发送到你配置的 LLM 端点 |
| `data/litread.db` | 论文、笔记、成长记录 | SQLite，单文件 |
| `data/research/{id}.json` | 研究流缓存 | `rf-4`；6 阶段 / 12 步 |
| `data/research/{id}.viz.json` | 可视化缓存 | `vz-4`；独立于研究流，不互相失效 |
| `data/overview/{id}.json` | 概述图结构化数据 | `on-1` |
| `data/overview/{id}.png` | 概述图 PNG | 可下载 |

---

## 十三、Demo 模式与演示论文

- **无 Key 时**：在线演示的 3 篇预置论文已有完整研究流与可视化缓存，可以直接体验；上传新论文并生成深度研究流需要配置 LLM Key。
- **有 Key 时**：在侧栏粘贴自己的 Key，验证后即可生成新论文的研究流；Key 只在当前会话内存中使用，刷新即清空。
- **演示脚本**：[LitRead-Viz-Demo-Script.md](LitRead-Viz-Demo-Script.md)，覆盖「选论文 → 光谱 → 现场写推演 → 揭晓 → 分叉图 → 论证图 → 成长曲线 → 思路对比」。

---

## 十四、已知限制

- PDF 解析基于字号/坐标/关键词启发式，扫描版（图片型）PDF 暂不支持 OCR。
- 作者路径是 **AI 重建**，不是作者本人的真实心理过程；页面会明确标注，并保留作者原文、证据和备选路线供用户判断。
- 成长曲线的「接近度」是确定性文字重合指标。
- 思路对比要求论文已经生成研究流；未生成的论文会提示先完成 12 步。
- 当前没有用户体系；多人共用同一实例会共享论文库和笔记。
- 生成研究流时，论文文本会发送到你配置的 LLM 端点；对隐私敏感的场景请使用本地或可信模型。
- 主要面向 ML/CS 论文；其他领域的术语和实验范式可能需要调整。

---

## 十五、Roadmap

- [ ] 扫描版 PDF / 公式 / 图表的 OCR 与结构化理解
- [ ] Zotero / arXiv / Semantic Scholar 直接导入
- [ ] 多用户隔离、分享链接与团队文献架
- [ ] 更细的研究思维评估：不只接近度，还能看到「起点/跳跃/取舍」的进步
- [ ] 英文界面与英文研究流

---

## 十六、License 与致谢

MIT License。

演示论文：

- *Attention Is All You Need*（Vaswani et al., 2017）
- *Mastering the Game of Go with Self-play Experience Replay*
- *Beyond Visual Evidence: Revealing and Mitigating Relational Privacy Leakage in Document MLLMs*

竞品与相关工作调研：[docs/competitive-landscape.md](docs/competitive-landscape.md)

<p align="center">
  <sub>Built for AI for Learning & Research · Hackathon 2026</sub>
</p>
