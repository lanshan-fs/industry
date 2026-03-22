# Django 认证重构与用户单表合并说明（2026-03-20）

本文档记录本次对认证层和数据库设计的联合收口。目标有两个：

- 用 Django 接管 `/api/auth/*`
- 将原本分散在 `users` 与 `user_basic` 的用户信息合并回 `users`

## 1. 为什么要删除 `user_basic`

此前的用户设计存在两个问题：

- 认证字段与资料字段分散在两张表里
- 运行时代码经常靠 `user_name` 做弱关联

这会导致：

- 登录、注册、重置密码都需要双写
- 一旦两表数据不同步，认证状态和展示资料会分裂
- Django 重构时无法建立清晰的单一用户模型

因此本次设计改为：

- `users` 是唯一用户主表
- `user_basic` 从最终 schema 中删除

## 2. 并入 `users` 的字段

以下字段从 `user_basic` 合并到 `users`：

- `user_nickname`
- `user_avatar`
- `user_type`
- `is_superuser`
- `user_role`
- `date_joined`
- `last_login_time`
- `last_login_ip`
- `password_update_time`
- `user_real_name`
- `org_name`
- `org_id`
- `dept_name`
- `dept_id`
- `user_status`

保留 `users` 原有字段：

- `user_name`
- `password_hash`
- `email`
- `phone`
- `organization`
- `position`
- `domain_id`
- `registered_at`
- `last_login_at`
- `updated_at`

这样做的原则是：

- 先消灭双表写入
- 再保留少量语义相近字段，避免一次性破坏过多历史代码

## 3. 为 Django 认证做的配套调整

为了让 Django 能稳定接管认证：

- `password_hash` 从 `CHAR(60)` 扩成 `VARCHAR(255)`
- 允许存放 Django 默认的 `pbkdf2_sha256` 哈希
- 仍兼容历史 bcrypt 哈希

对应实现上：

- Django 新注册和重置密码默认写 `pbkdf2_sha256`
- Express 侧保留兼容校验，避免迁移窗口期出现旧接口直接失效

## 4. 智能助手会话不受影响，但继续依赖 `users`

`rag_chat_session` 仍保持：

- `rag_chat_session.user_id -> users.user_id`

因此删除 `user_basic` 后，会话隔离逻辑不需要再做额外调整。

## 5. 本次设计的最终边界

本次完成：

- Django 版认证后端落地
- 用户表单表化
- 会话继续按 `users.user_id` 隔离
- 最新设计回写到 `design-2026-3-20-V2.csv`

暂未完成：

- 其余 Express 业务接口迁移到 Django
- 基于 Django ORM 的全量业务模型重建
- 更完整的角色与权限体系改造
