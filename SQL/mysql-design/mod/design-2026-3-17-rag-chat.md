# RAG Chat Tables Design

本文件记录通用数据库 RAG 改造新增的 chat 持久化表设计。该设计对应：

- `rag_chat_session`
- `rag_chat_message`

目标：

- 将原先落在本地 `chat_history.json` 的会话历史迁回 MySQL
- 让 `AGENT` 的历史查询、会话恢复、后续评估留痕都基于数据库
- 不绑定当前 demo 的业务规则，服务于未来通用 RAG

## `rag_chat_session`

用途：

- 记录一次聊天会话的元信息
- 按 `updated_at` 支持会话列表排序

字段：

- `session_id VARCHAR(64) PK`
  - RAG 对话会话唯一标识
- `title VARCHAR(255) NULL`
  - 会话标题，当前默认取首条用户问题截断
- `is_pinned TINYINT NOT NULL DEFAULT 0`
  - 是否置顶（`1=是, 0=否`）
- `created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - 创建时间
- `updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`
  - 最后更新时间

索引：

- `PRIMARY KEY (session_id)`
- `idx_rag_chat_session_updated_at (updated_at)`
- `idx_rag_chat_session_pin_updated_at (is_pinned, updated_at)`

## `rag_chat_message`

用途：

- 记录会话内的逐条消息
- 支持消息级检索元数据回放

字段：

- `message_id BIGINT PK AUTO_INCREMENT`
  - 消息主键
- `session_id VARCHAR(64) NOT NULL`
  - 所属会话 ID
- `role VARCHAR(16) NOT NULL`
  - 消息角色，当前使用 `user / assistant / system`
- `content LONGTEXT NOT NULL`
  - 消息正文
- `retrieval_metadata JSON NULL`
  - 检索元数据，主要用于保存：
  - `rewritten_query`
  - `indexed_sources`
  - `probed_sources`
  - `candidate_sources`
  - `retrieved_docs`
  - `live_rows_sources`
- `created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - 创建时间

索引与约束：

- `PRIMARY KEY (message_id)`
- `idx_rag_chat_message_session_created_at (session_id, created_at)`
- `fk_rag_chat_message_session`
  - `session_id -> rag_chat_session.session_id`
  - `ON DELETE CASCADE`

## 与通用 RAG 的关系

- 会话层：
  - `rag_chat_session`
- 消息层：
  - `rag_chat_message`
- 检索留痕层：
  - 先通过 `retrieval_metadata JSON` 承接
  - 后续若要做系统评估，可再拆出：
  - `rag_eval_run`
  - `rag_eval_case`
  - `rag_eval_metric`

## 当前不做的事

- 暂不绑定平台用户表 `user_basic/users`
  - 当前智能诊断页仍以匿名会话为主
  - 等登录态与 RAG 会话策略稳定后，再补 `user_id`
- 暂不把索引快照写入 MySQL
  - 当前索引快照仍落在 `AGENT/data/rag_index/documents.json`
  - 便于快速迭代通用 RAG 管线
