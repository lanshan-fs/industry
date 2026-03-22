# Qwen + LangGraph Task-Driven RAG

当前 `AGENT` 已重构为面向区域产业治理场景的任务驱动 RAG，而不是通用数据库问答骨架。

当前版本已经支持：

- 优先调用 AutoDL 上部署的微调模型 `Qwen3-14B_sft_merged`
- 当 AutoDL 实例关机、SSH 隧道未建立、远端 `vLLM` 未启动或调用失败时
- 自动回退到 DashScope 的 `Qwen` API

## 当前架构

- `AGENT/rag/rag_modules/data_preparation.py`
  - 从 `industrial_chain` 全库提取：
  - 任务边界知识文档
  - 数据库概览文档
  - 表结构文档
  - 精确模式文档（DDL 风格）
  - 关系文档
  - 行样本文档
- `AGENT/rag/rag_modules/index_construction.py`
  - 构建索引快照
  - 当前快照写入 `AGENT/data/rag_index/documents.json`
- `AGENT/rag/rag_modules/retrieval_optimization.py`
  - 通用词项检索
  - 候选表选择
  - 全库轻量探测
- `AGENT/rag/rag_modules/generation_integration.py`
  - 微调模型优先的查询改写
  - 任务路由：4 个一级任务 + 1 个支撑能力 + 通用接话
  - 基于精确模式、任务示例和实时证据的答案生成
  - Qwen API 自动回退
- `AGENT/rag/remote_vllm.py`
  - 本地到 AutoDL 的 SSH 隧道管理
- `AGENT/rag/system.py`
  - 用 `LangGraph` 组织 `rewrite -> route -> retrieve -> generate`
- `AGENT/app.py`
  - FastAPI 接口层

## 当前能力

- 面向区域产业链分析的 4 个一级任务：
  - 区域产业现状分析与链条诊断
  - 风险研判与预警
  - 补链延链强链建议
  - 招商引资与目标企业推荐
- 1 个支撑能力：
  - 重点企业识别与企业画像
- 以及通用接话能力：
  - 承接追问、澄清、解释、展开、比较
- 聊天历史写入 MySQL：
  - `rag_chat_session`
  - `rag_chat_message`
  - 会话按 `rag_chat_session.user_id` 与登录用户隔离
- 提供索引重建接口：
  - `POST /admin/rebuild-index`

## 运行前提

- 根目录 `.env` 已配置：
  - `DB_HOST`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_NAME`
  - `DASHSCOPE_API_KEY`
  - `SSH`
  - `PASSWORD`
- 本地 MySQL 中可访问 `industrial_chain`
- 建议使用 `ic` conda 环境

## 模型路由

默认按以下顺序调用模型：

1. `PRIMARY_LLM_BASE_URL` 指向的微调模型接口
2. 若失败，则回退到 `QWEN_BASE_URL` + `QWEN_MODEL`

默认配置下，主模型接口为：

- `PRIMARY_LLM_MODEL=Qwen3-14B_sft_merged`
- `PRIMARY_LLM_BASE_URL=http://127.0.0.1:6006/v1`

当检测到主模型地址是本地 `127.0.0.1:6006` 时，`AGENT` 会尝试根据 `.env` 中的 `SSH` 和 `PASSWORD` 自动建立到 AutoDL 的本地隧道，再访问远端 `vLLM`。

如果不希望自动建隧道，可以设置：

```bash
AUTODL_TUNNEL_ENABLED=false
```

## 安装依赖

```bash
conda run -n ic pip install -r AGENT/requirements.txt
```

## 启动服务

```bash
conda activate ic
uvicorn AGENT.app:app --host 127.0.0.1 --port 8001 --reload
```

## 接口

- `GET /health`
- `POST /chat`
- `POST /chat/stream`
- `GET /history`
- `GET /history/{session_id}`
- `PATCH /history/{session_id}`
- `DELETE /history/{session_id}`
- `DELETE /history`
- `POST /admin/rebuild-index`

说明：

- `POST /chat` / `POST /chat/stream` 请求体必须携带 `userId`
- 所有 `history` 接口都必须带 `userId` 查询参数
- `userId` 用于确保不同登录用户只访问自己的历史会话

## 已知限制

- 当前 embedding 侧暂未稳定跑通 DashScope 兼容层，`health.vector_enabled` 可能为 `false`
- 因此当前主检索仍以：
  - 索引文档词项召回
  - 全库实时行探测
  - 任务驱动生成整合
  为主
- 如果快照还是旧版本，服务首次启动会自动重建 `AGENT/data/rag_index/documents.json`
