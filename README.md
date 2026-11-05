# 开店筹备与运营验收 · 业务核对助手智能体系统

面向连锁开店场景的 RAG 智能核对助手：员工基于报销制度库进行**带出处的问答**与**对话式发起报销**，管理员维护**知识库版本**并查看**全部记录与审计**。

> **与姊妹项目的区别**：同案例下另有一个仓库 [`qingshan-retail-demo`](https://github.com/infinty420/qingshan-retail-demo)（Node.js）——那是「新店开业筹备**数智化平台**」（三系统只读对接 + 实时协同看板）；本仓库是「业务**核对助手智能体**」（Python/FastAPI + RAG）：聚焦报销制度知识库问答、对话式报销发起与审计留痕。前者管"筹备业务流程"，后者管"制度问答与费用核对"。

## 快速启动（Demo，零外部依赖）

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8790
```

浏览器打开 http://127.0.0.1:8790 。首次启动自动建表并初始化种子数据（演示账号 + 3 份制度文档向量化入库）。

演示账号：

| 账号 | 密码 | 角色 | 能力 |
|---|---|---|---|
| employee | employee123 | 员工（林亦舟 · 店长） | 制度问答（流式 + 引用出处）、对话发起报销、查看我的报销单 |
| admin | admin123 | 管理员（李慧 · 制度管理员） | 知识库上传/版本/启停、全部问答记录、报销单、审计日志 |

Windows 可直接双击 `run_demo.bat`。

## 演示脚本（5 条验收用例）

1. 员工登录 → 问「装修费报销上限是多少」→ 返回带《开店筹备费用报销制度》出处的答案
2. 员工问「发票丢了怎么办」→ 返回发票遗失处理条款
3. 员工说「我要报销 3000 元装修押金」→ 意图识别 → 生成报销草稿卡片（类型/金额/日期/制度依据）→ 点击提交
4. 管理员登录 → 知识库管理 → 上传《xx 制度》新内容 → 员工再问 → 答案引用新文档
5. 管理员查看问答记录 / 报销单 / 审计日志，验证全量留痕

## LLM 供应商热替换

默认 `local_demo`（离线抽取式回答，保证 Demo 无 API Key 可跑）。切换真实供应商：

```bash
set LLM_PROVIDER=openai_compat
set LLM_BASE_URL=https://api.moonshot.cn/v1
set LLM_API_KEY=sk-xxx
set LLM_MODEL=kimi-k2
```

零代码改动。任何 OpenAI 兼容供应商（Kimi / DeepSeek / 通义 / OpenAI / 本地 vLLM）均可。

> 注意：`EMBEDDING_PROVIDER` 切换会改变向量空间，需全量重嵌入（删除 `data/` 下数据库后重启自动重建，生产环境提供 reindex 脚本）。

## 四层架构与代码映射

| 层 | 代码位置 |
|---|---|
| ① 入口层 | `app/api/v1/`（路由、JWT、RBAC）+ `app/schemas/`（Pydantic 契约） |
| ② 服务层 | `app/services/`（chat / reimbursement / kb / record，薄业务层） |
| ③ 智能体编排层 | `app/agent/`（intent 意图路由、rag/ 检索管道、llm/ 供应商适配器、orchestrator 编排、tools 结构化抽取） |
| ④ 数据模型层 | `app/models/`（7 张表）+ `app/db/`（引擎与种子） |

数据表：users / kb_documents / kb_chunks / chat_sessions / chat_messages / reimbursements / audit_logs（与架构方案一致）。

## 生产化路径（Demo → 生产）

- SQLite → PostgreSQL + pgvector：`DATABASE_URL` 切换，`kb_chunks.embedding` 改 `VECTOR` 列 + HNSW 索引，检索由内存余弦改为 SQL
- 结构化查询 → Alembic 迁移管理
- 本地 demo 供应商 → OpenAI 兼容真实供应商（仅改 env）
- 多品牌/门店行级隔离：加 `brand_id` / `store_id` + PostgreSQL RLS
- OCR 发票识别、税务验真、规则引擎判定（二期，见《一页纸需求清单》）

## 项目结构

```
verify-agent/
├── app/
│   ├── main.py              # FastAPI 入口 + 静态页
│   ├── core/                # config / security(JWT) / deps(RBAC)
│   ├── api/v1/              # auth / chat(SSE) / reimbursement / kb / records
│   ├── schemas/             # Pydantic 契约
│   ├── services/            # 业务服务层
│   ├── agent/               # 智能体编排层（核心）
│   │   ├── orchestrator.py  # 意图 → 检索 → 生成/抽取 → 留痕
│   │   ├── rag/             # chunker / embedder / retriever
│   │   ├── llm/             # base / local_demo / openai_compat / factory
│   │   ├── intent.py        # 意图路由
│   │   ├── tools.py         # 报销结构化抽取
│   │   └── prompts.py       # 提示词模板
│   ├── models/              # SQLAlchemy ORM（7 张表）
│   ├── db/                  # session / seed
│   └── static/index.html    # 前端 Demo（单文件）
├── knowledge_docs/          # 种子制度文档（Markdown）
├── data/                    # SQLite 数据库（运行时生成）
├── requirements.txt
└── run_demo.bat
```
