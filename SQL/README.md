# SQL 目录说明

本目录用于承接新数据库设计、建表 SQL 和导数脚本，当前以 `SQL/mysql-design/design-2026-3-16.csv` 为基础，`SQL/sql/init.sql` 与 `SQL/mysql-design/design-2026-3-20-V2.csv` 反映当前可执行版本。

## 目录结构

- `mysql-design/`: 原始 MySQL 设计文件
- `mysql-design/mod/`: 建表时对设计做的可执行映射说明
- `mysql-design/design-2026-3-20-V2.csv`: 按当前可执行 DDL 回写的 V2 设计
- `sql/init.sql`: 初始化数据库与建表文件
- `sql/raw_import_staging.sql`: `raw_import_*` 中转表建表文件，仅用于导入阶段
- `sql/`: 后续数据库初始化与运维 SQL
- `scripts/`: Excel/JSON -> MySQL 导数脚本
- `data/`: 按表拆分后的待导入 JSON 数据
- `suggestions/`: 对原始设计的待确认建议

## 当前状态

- 已生成可执行建表文件：
  - [init.sql](/Users/bluem/Projects/Web/industrial_chain/SQL/sql/init.sql)
- 已将 `raw_import_*` 从最终初始化 DDL 中拆出：
  - 最终库结构只保留设计中的业务表
  - 导入阶段通过 [raw_import_staging.sql](/Users/bluem/Projects/Web/industrial_chain/SQL/sql/raw_import_staging.sql) 临时创建中转表
- 用户体系已合并到单表：
  - `users` 同时承担认证与资料职责
  - `user_basic` 已从最终初始化设计中移除
- 智能助手历史会话已按用户隔离：
  - `rag_chat_session.user_id -> users.user_id`
  - 同一登录用户只能看到和操作自己的会话
- 已生成可执行 schema 对应的 V2 设计文件：
  - [design-2026-3-20-V2.csv](/Users/bluem/Projects/Web/industrial_chain/SQL/mysql-design/design-2026-3-20-V2.csv)
- 已生成建表映射说明：
  - [design-2026-3-16-init-mapping.md](/Users/bluem/Projects/Web/industrial_chain/SQL/mysql-design/mod/design-2026-3-16-init-mapping.md)
- 已整理设计待确认问题：
  - [design-2026-3-16-open-issues.md](/Users/bluem/Projects/Web/industrial_chain/SQL/suggestions/design-2026-3-16-open-issues.md)

## 使用方式

如果本机已安装 MySQL，可直接执行：

```bash
mysql -u <user> -p < /Users/bluem/Projects/Web/industrial_chain/SQL/sql/init.sql
```

如果数据库不叫 `industrial_chain`，先修改 `init.sql` 顶部的库名再执行。

如果本地数据库是 2026-03-20 之前已经建好的旧版本，需要补一次用户与会话归并迁移：

- 给 `users` 增加原先位于 `user_basic` 的资料字段
- 按 `user_basic.source_user_id` 或 `user_name` 将历史资料回填到 `users`
- 将 `password_hash` 扩展为适配 Django 的长度
- 删除 `user_basic`
- 给 `rag_chat_session` 增加 `user_id`
- 再补外键约束

生成当前 DDL 对应的 V2 设计文件：

```bash
python3 /Users/bluem/Projects/Web/industrial_chain/SQL/scripts/export_design_v2.py
```

将 `data/unclean/前4800家企业数据汇总.xlsx` 直接写入 `raw_import_*`：

```bash
python3 /Users/bluem/Projects/Web/industrial_chain/SQL/scripts/import_xlsx_to_raw.py --apply-init
```

说明：

- `--apply-init` 先应用最终 `init.sql`
- 脚本随后会自动应用 `raw_import_staging.sql`，创建中转表再导入 Excel
- 不再要求 `init.sql` 自身携带 `raw_import_*`

将 `raw_import_*` 清洗同步到结构化业务表：

```bash
python3 /Users/bluem/Projects/Web/industrial_chain/SQL/scripts/sync_raw_to_business.py --drop-raw-after-sync
```

说明：

- `company_basic_count` 中的 `*_count` 字段表示结构化明细数量
- 对应的 `*_count_raw` 字段保留 Excel 原始聚合值，避免原始值覆盖清洗后的明细计数
- 同步完成后可使用 `--drop-raw-after-sync` 删除 `raw_import_*` 中转表

执行同步校验并生成报告：

```bash
python3 /Users/bluem/Projects/Web/industrial_chain/SQL/scripts/validate_sync.py
```

校验报告输出到：

```text
/Users/bluem/Projects/Web/industrial_chain/SQL/validation-sync-report.md
```

## 后续顺序

1. 先应用最终 `init.sql`，再通过 `raw_import_staging.sql` 创建中转表并导入 Excel。
2. 再按业务需要，把 `raw_import_*` 清洗同步到结构化业务表，并在成功后删除中转表。
3. 人工确认 `suggestions/` 中的歧义项是否要回写到设计 CSV。
