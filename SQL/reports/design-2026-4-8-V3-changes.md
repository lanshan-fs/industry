# 设计变更说明（2026-04-08）

## 1. 本次目标

- 为评分新增字段补齐可落库的数据承接层，不再把“算法备案医疗大模型”“高质量数据集”“创新性公示”挤进 `company_qualification`。
- 保持与企业数据管理模块协同，新增业务表继续沿用 `company_` 前缀，保证后台可发现、可编辑、可删除。
- 完成 `mysql-design`、初始化 SQL、迁移脚本、导入脚本、同步脚本、Django 评分读取的同步回写。

## 2. 新增表结构

- 新增 3 张业务事实表：
  - `company_ai_model_filing`
  - `company_high_quality_dataset`
  - `company_innovation_notice`
- 新增 3 张原始导入表：
  - `raw_import_company_ai_model_filing`
  - `raw_import_company_high_quality_dataset`
  - `raw_import_company_innovation_notice`
- 扩展 `company_basic_count`：
  - `ai_model_filing_count`
  - `high_quality_dataset_count`
  - `innovation_notice_count`

## 3. 数据承接口径

- `算法备案的医疗大模型(1).xlsx`
  - `raw_import_company_ai_model_filing -> company_ai_model_filing`
  - 评分命中项：`算法备案的医疗大模型`
- `高质量数据集.xlsx`
  - `raw_import_company_high_quality_dataset -> company_high_quality_dataset`
  - 评分命中项：`高质量数据集`
- `专业能力评分-创新性.xlsx`
  - `raw_import_company_innovation_notice -> company_innovation_notice`
  - `notice_type` 统一收口：
    - `innovative_medical_device_beijing`
    - `innovative_medical_device_national`
    - `priority_review_candidate`
    - `breakthrough_therapy`
    - `master_file`
  - 评分命中项：`创新性`

## 4. 代码协同调整

- 新增脚本：
  - `SQL/scripts/import_auxiliary_xlsx_to_raw.py`
  - `SQL/scripts/sync_auxiliary_raw_to_business.py`
- `backend_django/system_api/views.py`
  - 新增业务表删除联动。
  - 补充中文 token，避免企业数据管理界面对新表名/字段名显示为生硬英文。
- `backend_django/scoring_api/engine.py`
  - 评分引擎优先读取 `company_ai_model_filing`、`company_high_quality_dataset`、`company_innovation_notice`。
  - 保留旧的文本兜底逻辑，但新增专表存在时优先使用结构化事实。

## 5. 产物清单

- `SQL/mysql-design/design-2026-4-8-V3.csv`
- `SQL/sql/init.sql`
- `SQL/sql/init-2026-4-5-V1.sql`
- `SQL/sql/raw_import_staging.sql`
- `SQL/sql/alter-2026-04-08-auxiliary-enterprise-data.sql`
- `SQL/scripts/import_auxiliary_xlsx_to_raw.py`
- `SQL/scripts/sync_auxiliary_raw_to_business.py`
- `backend_django/system_api/views.py`
- `backend_django/scoring_api/engine.py`

## 6. 说明

- 本次新增业务表以“源事实存储”为主，不再依赖 `company_tag_map` 或 `qualification_label` 承接原始事实。
- `company_tag_*` 仍可继续作为派生标签层，但不再作为这三类数据的唯一来源。
- 本说明文件仅覆盖 2026-04-08 这次辅助评分数据落地，旧版 V1/V2 设计说明仍保留作为历史快照。
