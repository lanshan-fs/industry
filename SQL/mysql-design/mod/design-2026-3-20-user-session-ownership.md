# 用户主从与会话归属整理说明（2026-03-20）

> 该说明记录的是 2026-03-20 当天的中间态。
> 在随后同日完成的 Django 认证重构中，`user_basic` 已进一步并入 `users`。
> 最新结论以 [design-2026-3-20-django-auth-merge.md](/Users/bluem/Projects/Web/industrial_chain/SQL/mysql-design/mod/design-2026-3-20-django-auth-merge.md) 为准。

本文档记录“跑通用户注册、用户登录、忘记密码页面”之后，对数据库设计补做的收口。目标不是新增一套用户体系，而是把现有两套表的职责明确下来，并让智能助手历史会话真正按用户隔离。

## 1. 用户体系改为明确主从关系

最终约定：

- `users` 是认证主表
  - 负责登录账号、密码哈希、邮箱、手机号、所属领域、登录时间
- `user_basic` 是平台扩展资料表
  - 负责昵称、头像、组织、角色、状态等平台侧补充信息
  - 不再视为独立认证主表

为避免继续通过 `user_name` 做弱关联，新增：

- `user_basic.source_user_id -> users.user_id`

这样注册、登录、重置密码时都以 `users` 为准，再同步维护 `user_basic`。

## 2. 为什么不直接删除 `user_basic`

当前前端和历史设计里仍有若干字段只存在于 `user_basic`，例如：

- `user_role`
- `user_real_name`
- `org_name`
- `dept_name`
- `user_status`

因此本阶段不做“硬合表”，而是先改成主从结构：

- 认证字段收敛到 `users`
- 扩展画像保留在 `user_basic`
- 两者通过主键显式关联

这样既能先把登录链路跑通，也方便后续 Django 重构时再决定是否彻底并表。

## 3. 智能助手会话改为按用户归属

新增约束：

- `rag_chat_session.user_id -> users.user_id`

对应语义改为：

- 一个会话必须属于某个登录用户
- 历史列表、会话详情、重命名、置顶、删除、清空都必须按当前用户过滤
- 不再允许“全局共享历史池”

这次调整后，`rag_chat_message` 仍然只关联 `session_id`，用户归属由 `rag_chat_session` 统一控制。

## 4. 对实现层的影响

后端与 AGENT 侧同步采用以下规则：

- 前端访问 `/api/chat*` 时必须携带登录态
- Express 从 JWT 中解析 `user_id`
- 转发到 AGENT 时显式传入 `userId`
- AGENT 的 `/history*` 接口全部要求 `userId`
- 数据库层对会话的查询、更新、删除都按 `session_id + user_id` 双条件执行

## 5. 当前阶段的边界

本次整理只完成：

- 用户表职责明确
- 主从关联落库
- 智能助手会话按用户隔离

尚未完成：

- Django 版本的认证重构
- `user_basic` 向 `users` 的彻底字段并表
- 更细粒度的角色/权限体系重建
