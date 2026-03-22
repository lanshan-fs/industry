# `design-2026-3-16.csv` 待确认问题

下面这些问题来自原始 CSV 设计本身，不是建表 SQL 的语法问题。`SQL/sql/init.sql` 已做保守落地，但建议人工确认后再回写设计文件。

当前为了先接住 `data/unclean/前4800家企业数据汇总.xlsx`，`init.sql` 已增加一组 `raw_import_*` 原始导入表。也就是说，导入工作不会被这些设计问题阻塞，但结构化业务表仍建议后续统一收口。

## 1. 用户模型重复

CSV 同时存在两套用户体系：

- `user_basic`
- `users + user_domains + user_roles + user_and_roles + user_operation_logs`

这两套表都包含登录账号、邮箱、手机号、登录时间等重叠字段。当前建表时两套都保留了，避免遗漏设计项，但后续后端只能选一套作为权威模型。

建议：

- 若走 Django 自带权限体系，保留一套用户主表并明确角色、领域、组织字段归属。
- 尽快决定 `company_tag_map.user_id` 应该关联哪一套用户表。

## 2. `company_basic` 中存在大量“字段/子表混写”

例如：

- `company_former_name（企业曾用名表）`
- `website（企业网站表，最新的记录作为该字段的值）`
- `（股东信息表，最新的记录作为该字段的值）`
- `（企业资质表，最新的记录作为该字段的值）`

这类写法把“快照字段”和“历史明细表”写在同一行，不利于后续导数脚本与 ORM 建模。

建议：

- 在设计 CSV 中把“主表快照字段”和“历史子表字段”拆成两部分单独维护。
- 明确哪些字段要做冗余快照，哪些只存在于明细表。

## 3. 多个字段名缺失或拼写错误

典型问题：

- 空字段名：核准日期、经营期限、组织类型、投资类型、限制高消费、客户 id、供应商 id
- 类型拼写错误：`DEMICAL`
- 类型不完整：`CHAR()`
- 字段名残缺：`company_work_copyright_`
- 业务拼写错误：`recommanded_phone`、`is_chaoyao_company`
- 表名可疑：`user_dinvite_codes`

建议：

- 下一版 CSV 明确字段名、类型、枚举值，不要再在导入阶段二次猜测。

## 4. 类型定义与业务含义冲突

典型问题：

- `taxpayer_credit_rating` 被写成 `TINYINT`，但说明是 `ABCDM`
- `industry_belong` / `industry_belong_code` 被写成 `TINYINT/VARCHAR(255)`
- `company_ranking.company_ranking_name` 被写成 `BIGINT`
- `company_ranking.company_id` 被写成 `VARCHAR(255)`

建议：

- 所有带“代码/名称/等级文案”的字段统一给出确定类型。
- 涉及字典值时，明确是存枚举码、文本，还是外键。

## 5. 映射表定义不完整

典型问题：

- `company_tag_dimension_library_map` 只有 `company_tag_dimension_id`，缺失另一侧字段
- `company_tag_auto_rule` 只有 `……`
- `company_patent` 中“专利类型表”只是说明，没有对应字段

建议：

- 每张映射表至少明确：
  - 主键
  - 左右两侧外键
  - 是否允许重复

## 6. 评分模型表缺约束与版本策略

目前 `score_model_total_weight`、`score_model_basic_weight`、`score_model_tech_weight`、`score_model_professional_weight` 仅描述了一个模型行，但没有说明：

- 是否会有多个版本
- 是否有“当前启用”状态
- 四张表之间如何关联同一版本

建议：

- 增加 `version` / `is_active` / `created_at`
- 或者统一成“模型主表 + 指标明细表”

## 7. 朝阳区平台相关字段建议统一命名

平台面向朝阳区，但设计里出现了 `is_chaoyao_company`。

建议：

- 统一为 `is_chaoyang_company`
- 如未来可能扩区，改为 `region_scope` 或 `is_core_region_company`

## 8. 导数脚本前还需要最终确认的点

在开始做 `SQL/scripts/` 与 `SQL/data/` 前，至少要确认：

- 用户体系最终采用哪套表
- `company_basic` 哪些字段是快照，哪些只走历史子表
- 评分模型如何做版本化
- 行业、标签、企业资质是否走字典表或外键

不先确认这几项，后续 Excel -> JSON -> MySQL 的导数脚本会不断返工。
