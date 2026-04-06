# 设计变更说明（2026-04-05）

## 1. 基线校对结论

- 旧版 `SQL/sql/init.sql` 不是干净的初始化脚本，内部存在重复 `CREATE TABLE` 片段，已不适合作为可信基线。
- 活库比 `SQL/mysql-design/design-2026-4-1-V1.csv` 多出完整的 `platform_notice` 表结构，因此 `design-2026-4-5-V1.csv` 已按本地 MySQL 重新校准。
- `SQL/data` 中的企业标签静态源数据落后于活库，已补齐 1 个维度、2 个子维度、51 个标签项，避免后续重建数据库时丢失“行业标签”能力。
- `chain_industry_seed.json` 含 `stage_key` / `stage_title` / `sort_order`，旧版 `chain_industry` 无法完整表达该源数据。

## 2. 最新 Excel 的主要结构冲突

- `分支机构`：最新数据提供文本状态和地区原始值，旧表 `company_branch.company_branch_status` 为 `TINYINT`，且没有地区字段。
- `许可`：最新数据是独立工作表，旧库没有单独承载许可元数据的字段集。
- `资质`：最新数据包含 `证书编号` 与 `证书状态`，旧表 `company_qualification` 无对应字段。
- `企业经营信息`：最新数据提供 `供应商数量`、`许可数量`、`资质数量`，旧表 `company_basic_count` 没有对应聚合字段。
- `客户信息`：最新数据提供 `数据来源`，旧表 `company_customer` 无对应字段。
- `专利信息`：最新数据提供 `申请公布日`，旧表 `company_patent` 只有 `auth_date`（专利授权日期），语义不匹配。

## 3. V2 设计调整

- `chain_industry`：新增 `stage_key`、`stage_title`、`sort_order`，使表结构与 `SQL/data/chain_industry_seed.json` 对齐。
- `company_branch`：将 `company_branch_status` 改为文本类型，并新增 `company_branch_region`。
- `company_qualification`：不新建 `company_license` 表，改为扩展现有证照表，新增 `record_kind`、`qualification_number`、`qualification_status`、`data_source`、`valid_from`、`validity_period_text`、`issuing_authority`，统一承载“许可/资质”两类记录。
- `company_basic_count`：新增 `supplier_count` / `supplier_count_raw`、`qualification_count` / `qualification_count_raw`、`license_count` / `license_count_raw`。
- `company_customer`：新增 `data_source`。
- `company_patent`：新增 `publication_date`，避免把“申请公布日”误写进“授权日期”。

## 4. 本次同步的静态源数据

- 企业标签维度总数：7
- 企业标签子维度总数：60
- 企业标签库总数：303
- 行业分类源：`SQL/data/category_industry.json`
- 产业链源：`SQL/data/chain_industry_seed.json`
- 企业标签源：`SQL/data/company_tag_dimension.json`、`SQL/data/company_tag_subdimension.json`、`SQL/data/company_tag_library.json`、`SQL/data/company_tag_auto_rule.json`

## 5. Excel 工作表概览

- `企业基本信息`：26674 行；字段：序号、企业名称、统一社会信用代码、成立年限、注册资本（万元）、实缴资本（万元）、企业类型、组织类型、企业规模、是否有分支机构、分支机构数量、地址信息、投融资轮次、法定代表人、社保人数、注册号、组织机构代码、所属行业、经营范围、邮箱（工商信息）、股东、联系电话、联系电话1、联系电话2、联系电话3、联系电话4、联系电话5
- `分支机构`：4466 行；字段：企业名称、分支机构企业名称、负责人、地区、成立日期、登记状态
- `企业经营信息`：39283 行；字段：序号、企业名称、员工人数、社保人数、上市状态、国标行业、联系方式、同企业电话、邮箱（工商信息）_y、是否小微企业、是否有变更信息、是否为一般纳税人、有无融资信息、有无招投标、招投标数量、有无供应商、供应商数量、有无招聘、招聘信息数量、是否有客户信息、客户数量、是否有上榜榜单、上榜榜单数量、是否有许可、许可数量、是否有资质、资质数量、税务评级
- `客户信息`：10026 行；字段：序号、公司名称、客户名称、销售占比、销售金额、报告期、数据来源
- `上榜榜单信息`：1451 行；字段：企业名称、榜单名称、榜单类型、来源、榜内位置、榜内名称、发布年份
- `招聘信息`：38391 行；字段：公司名称、招聘职位、薪资、地区、工作经验、学历、发布时间
- `许可`：39283 行；字段：企业名称、许可文件编号、许可文件名称、许可状态、来源、有效期、许可机关
- `资质`：18851 行；字段：企业名称、证书名称、证书编号、证书类型、证书状态、发证日期、截止日期
- `知识产权`：25972 行；字段：序号、企业名称、有无作品著作、作品著作权数量、有无软件著作、软件著作权数量、高新技术企业、专精特新中小企业、瞪羚企业、科技型中小企业、雏鹰企业、专精特新小巨人、创新型中小企业、有无专利、专利数量
- `软件著作权`：28099 行；字段：序号、软件名称、登记号、软件简称、登记批准日期、状态、取得方式、著作权人
- `作品著作权`：3888 行；字段：序号、作品名称、登记号、类别、首次发布日期、登记日期、状态、企业名称
- `专利信息`：3740 行；字段：序号、申请人、专利号、专利名称、专利类型、申请日、申请公布日
- `扣分项`：25972 行；字段：企业名称、严重违法、司法案件、合作风险、失信被执行人、破产案件、被执行人、限制高消费、经营异常、集群注册
- `街道信息`：25972 行；字段：序号、企业名称、地址、街道、地区

## 6. 产物清单

- `SQL/mysql-design/design-2026-4-5-V1.csv`：基于旧 MySQL 的校准设计
- `SQL/mysql-design/design-2026-4-5-V2.csv`：支持最新 Excel 与静态源数据的目标设计
- `SQL/sql/init-2026-4-5-V1.sql`：基于旧 MySQL 结构整理出的初始化脚本快照
- `SQL/sql/init.sql`：V2 目标初始化脚本（未导入最新企业数据）
- `SQL/reports/design-2026-4-5-V2-changes.md`：本说明文件
