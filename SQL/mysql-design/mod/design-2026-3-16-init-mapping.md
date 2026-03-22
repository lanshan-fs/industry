# `design-2026-3-16.csv` 建表映射说明

本文档记录 `SQL/sql/init.sql` 为了把 `SQL/mysql-design/design-2026-3-16.csv` 落成可执行 MySQL DDL 时做的映射与补全。

## 总体原则

- 本版优先保证 `data/unclean/前4800家企业数据汇总.xlsx` 可无损导入。
- 保留 CSV 中已经明确出现的主表、评分表、用户权限表。
- 对 `字段名` 里直接写成“某某表”“最新记录作为该字段值”的条目，拆成：
  - `company_basic` 中的当前快照字段；
  - 对应的历史子表。
- 对空字段名、空数据类型、明显拼写错误、无法直接执行的类型，按最保守可执行方式修正。
- 所有主键型 `BIGINT/INT` 标识默认补成 `AUTO_INCREMENT`。

## 导入优先策略

为避免原始 Excel 因字段类型不稳定而卡住导入，`init.sql` 额外补了一组 `raw_import_*` 原始导入表，与 Excel 的 11 个工作表一一对应。

- 这些表以“原值落库”为目标，字段类型以 `VARCHAR/TEXT` 为主。
- 导入脚本可以先把 Excel 无损写入 `raw_import_*`。
- 后续再从 `raw_import_*` 清洗同步到 `company_basic`、`company_patent`、`company_recruit` 等结构化业务表。

当前新增的原始导入表包括：

- `raw_import_company_basic`
- `raw_import_company_operation`
- `raw_import_company_ip_overview`
- `raw_import_software_copyright`
- `raw_import_company_ranking`
- `raw_import_company_customer`
- `raw_import_company_work_copyright`
- `raw_import_company_patent`
- `raw_import_company_risk`
- `raw_import_company_subdistrict`
- `raw_import_company_recruit`

## 主要字段映射

### `company_basic`

- `company_former_name（企业曾用名表）` 映射为：
  - `company_basic.former_name_latest`
  - 子表 `company_former_name`
- `website（企业网站表，最新的记录作为该字段的值）` 映射为：
  - `company_basic.website`
  - 子表 `company_website`
- `contact_phone（联系电话表，最新的记录作为该字段的值）` 映射为：
  - `company_basic.contact_phone`
  - 子表 `company_contact_phone`
- `contact_info（联系方式表，最新的记录作为该字段的值）` 映射为：
  - `company_basic.contact_info`
  - 子表 `company_contact_info`
- `recommanded_phone（推荐电话表，最新的记录作为该字段的值）` 统一修正为：
  - `company_basic.recommended_phone`
  - 子表 `company_recommended_phone`
- `（股东信息表，最新的记录作为该字段的值）` 映射为：
  - `company_basic.latest_shareholder_name`
  - 子表 `company_shareholder`
- `（员工人数表，不同年份，不同人数）` 映射为：
  - `company_basic.employee_count`
  - 子表 `company_employee_count`
- `（分支机构表，最新的记录作为该字段的值）` 映射为：
  - `company_basic.branch_name`
  - 子表 `company_branch`
- `（企业地址信息表，最新的地址作为该字段的值）` 映射为：
  - `company_basic.register_address_detail`
  - 子表 `company_address`
- `（企业资质表，最新的记录作为该字段的值）` 映射为：
  - `company_basic.qualification_label`
  - 子表 `company_qualification`
- `（投融资轮次信息表）` 映射为：
  - `company_basic.financing_info`
  - 子表 `company_financing`
- `（变更信息表）` 仅建子表 `company_change`
- `（招投标信息表）` 仅建子表 `company_bidding`
- `listing_status（上市状态表）` 映射为：
  - `company_basic.listing_status`
  - 子表 `company_listing_status`

### `company_basic` 中空字段或不可执行字段

- `核准日期（工商信息最后核准更新日期）` 补名为 `approved_date DATE`
- `经营期限（如长期，2020-2050）` 补名为 `business_term VARCHAR(255)`
- `组织类型（暂时保留）` 补名为 `org_type TINYINT`
- `投资类型` 补名为 `investment_type VARCHAR(255)`
- `股票代码 CHAR()` 修正为 `stock_code VARCHAR(32)`
- `taxpayer_qualifications` 空类型补为 `VARCHAR(255)`
- `financing_round` 空类型补为 `VARCHAR(255)`
- `financing_round_verify_time` 空类型补为 `DATE`
- `field_belong` 空类型补为 `TINYINT`
- `is_high_tech_enterprise_verify_time` 空类型补为 `DATE`
- `同企业电话` 映射为 `same_phone_company_count INT DEFAULT 0`
- `限制高消费` 映射为：
  - `company_basic.consumption_restriction_count`
  - 子表 `company_consumption_restriction`
- `is_chaoyao_company` 统一修正为 `is_chaoyang_company`

### 类型修正

- 所有 `DEMICAL(...)` 统一修正为 `DECIMAL(...)`
- `TINYINT/VARCHAR(255)` 一类冲突类型，优先按实际语义落地：
  - 枚举标记用 `TINYINT`
  - 行业名/编码一类文本用 `VARCHAR(255)`
- 为适配 xlsx 原始值并支持 `raw_import_* -> 业务表` 同步，以下结构化字段进一步放宽为文本：
  - `company_basic.company_type` -> `VARCHAR(255)`
  - `company_basic.org_type` -> `VARCHAR(255)`
  - `company_basic.company_scale` -> `VARCHAR(255)`
  - `company_software_copyright.company_software_copyright_status` -> `VARCHAR(255)`
  - `company_software_copyright.company_software_copyright_obtain` -> `VARCHAR(255)`
  - `company_recruit.company_recruit_edu_req` -> `VARCHAR(255)`
- `company_work_copyright_` 修正为 `company_work_copyright_publish_date`
- `company_ranking.company_ranking_name` 从 `BIGINT` 修正为 `VARCHAR(255)`
- `company_ranking.company_id` 从 `VARCHAR(255)` 修正为 `BIGINT`
- `company_branch.company_branch_id（是否可以）` 统一修正为 `company_branch_id`
- `company_branch_taxpayer_credit_rating` 空类型补为 `VARCHAR(16)`

## 补建的子表

为承接 CSV 中“某某表”的占位说明，新增以下表：

- `company_former_name`
- `company_website`
- `company_contact_phone`
- `company_contact_info`
- `company_recommended_phone`
- `company_shareholder`
- `company_employee_count`
- `company_address`
- `company_qualification`
- `company_financing`
- `company_change`
- `company_listing_status`
- `company_consumption_restriction`

## 关系补全

- 所有明显的一对多明细表均增加对 `company_basic.company_id` 的外键。
- `company_tag_subdimension` -> `company_tag_dimension`
- `company_tag_library` -> `company_tag_subdimension`
- `company_tag_map` -> `company_basic` / `company_tag_library`
- `company_tag_auto_rule` -> `company_tag_library`
- `category_industry_company_map` -> `category_industry` / `company_basic`
- `chain_industry_category_industry_map` -> `chain_industry` / `category_industry`
- `users` -> `user_domains`
- `user_and_roles` -> `users` / `user_roles`
- `user_operation_logs` -> `users`

## 当前未进一步抽象的部分

- `company_tag_auto_rule` 中的 `……` 落成了 `rule_definition JSON`
- `company_tag_dimension_library_map` 中缺失的映射字段补成了 `company_tag_id`
- `company_customer` 中的“客户id？”补成 `customer_company_id`
- `company_supplier` 中的“供应商id”补成 `supplier_company_id`

这些都已经写入建表文件，但仍建议后续由人确认并回写设计 CSV。
