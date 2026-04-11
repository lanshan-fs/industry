# SQL Scripts README

## 脚本
- [generate_credit_code_schema.py](/Users/bluem/Projects/Web/industrial_chain/SQL/scripts/generate_credit_code_schema.py)
  - 作用
    - 从单一基线 [init.sql](/Users/bluem/Projects/Web/industrial_chain/SQL/sql/init.sql) 生成并回写 `credit_code` 版 schema
    - 生成 [init-2026-04-10-credit-code.sql](/Users/bluem/Projects/Web/industrial_chain/SQL/sql/init-2026-04-10-credit-code.sql)
    - 同步回写 [design-2026-4-10-V1.csv](/Users/bluem/Projects/Web/industrial_chain/SQL/mysql-design/design-2026-4-10-V1.csv)
- [reset_and_import_enterprise_credit_code.py](/Users/bluem/Projects/Web/industrial_chain/SQL/scripts/reset_and_import_enterprise_credit_code.py)
  - 作用
    - 校验 `SQL/data/company_*.json` 已经是 `credit_code` 版 business 数据
    - 删除并重建本地 `industrial_chain`
    - 基于 `credit_code` schema 全量重导企业事实表
- [refresh_industry_taxonomy_and_tags.py](/Users/bluem/Projects/Web/industrial_chain/SQL/scripts/refresh_industry_taxonomy_and_tags.py)
  - 作用
    - 读取 `data/unclean/上中下游分类（一二三级分类标签）.xlsx`
    - 重建 `category_industry` / `chain_industry` / `chain_industry_category_industry_map`
    - 读取 `data/unclean/打标标签拆分结果（完整）.xlsx`
    - 重建 `category_industry_company_map`
    - 同步重建行业维度 `company_tag_library` / `company_tag_map`
    - 输出核对报告到 `SQL/tmp/industry-taxonomy-refresh-report-2026-04-10.md`

## 运行前提
- 使用 `conda` 的 `ic` 环境执行
- 当前脚本依赖 `pymysql`
- 根目录 `.env` 需保持 LF 行尾，避免 shell 侧工具读取出错

## 依赖 SQL
- [alter-2026-04-08-auxiliary-enterprise-data.sql](/Users/bluem/Projects/Web/industrial_chain/SQL/sql/alter-2026-04-08-auxiliary-enterprise-data.sql)
- [alter-2026-04-09-enterprise-import-extensions.sql](/Users/bluem/Projects/Web/industrial_chain/SQL/sql/alter-2026-04-09-enterprise-import-extensions.sql)
- [init-2026-04-10-credit-code.sql](/Users/bluem/Projects/Web/industrial_chain/SQL/sql/init-2026-04-10-credit-code.sql)

## 导入顺序
1. 生成并确认 `credit_code` 版 `init.sql`
2. 预处理 Excel，直接产出 `company_*` business JSON
3. 删除并重建本地 `industrial_chain`
4. 应用 `credit_code` schema
5. 批量导入全部企业 business 表
6. 根据最新行业分类与打标 Excel 刷新行业树和行业标签映射

## 为什么这样设计
- 当前流程只保留一个正式落库路径
  - `credit_code` schema + `company_*` JSON + 全库重建导入
- `raw_import_*` 只作为历史实现保留在旧迁移文件中
  - 不再是现行运行链路的一部分

## 2026-04-10 credit_code 重构结果
- `company_basic` 主键已切换为 `credit_code`
- 全库引用 `company_basic` 的 38 处 FK 已改为引用 `credit_code`
- `raw_import_*` 表已从当前 `init.sql` 中移除
- 本地 `industrial_chain` 已按新 schema 清库重建并完成全量导入

## 本次落库结果
- `company_basic`: 25972
- `company_branch`: 4352
- `company_customer`: 9508
- `company_recruit`: 37171
- `company_supplier`: 1153
- `company_qualification`: 60475
- `company_software_copyright`: 28029
- `company_work_copyright`: 3879
- `company_patent`: 8694
- `company_bidding`: 17625
- `company_ai_model_filing`: 3
- `company_high_quality_dataset`: 0
- `company_innovation_notice`: 12

## 复跑命令
```bash
conda run -n ic python SQL/scripts/generate_credit_code_schema.py
conda run -n ic python SQL/scripts/reset_and_import_enterprise_credit_code.py
conda run -n ic python SQL/scripts/refresh_industry_taxonomy_and_tags.py
```
