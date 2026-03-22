# `design-2026-3-16.csv` 同步清洗回写说明（2026-03-20）

本文档记录“整理 MySQL 数据库”阶段对可执行设计做的回写，用于解释为什么最终 DDL、导入中转层和同步脚本不再是最初那种混合状态。

## 1. `raw_import_*` 不再属于最终初始化设计

- `SQL/sql/init.sql` 现在只保留最终业务表。
- `raw_import_*` 被移动到单独的 [raw_import_staging.sql](/Users/bluem/Projects/Web/industrial_chain/SQL/sql/raw_import_staging.sql)。
- 导入脚本会先应用最终 `init.sql`，再显式创建 staging tables。
- 同步完成后，可通过 `sync_raw_to_business.py --drop-raw-after-sync` 或 `SQL/sql/operate.sql` 删除 `raw_import_*`。

这样处理的原因是：

- 原始设计 CSV 中并没有 `raw_import_*`；
- 这些表只是为 Excel 无损落库准备的中转层，不应污染最终 schema。

## 2. `company_basic_count` 拆分了“结构化计数”和“原始聚合计数”

原始 Excel 中的聚合数量与明细表可实际落库的数量存在明显差异，典型包括：

- 专利数量
- 软件著作权数量
- 作品著作权数量
- 客户数量
- 上榜榜单数量

因此可执行设计中做了以下调整：

- `branch_count` / `recruit_count` / `software_copyright_count` / `work_copyright_count` / `patent_count` / `customer_count` / `ranking_count`
  - 含义统一为“结构化明细表中的实际数量”
- 新增对应的 `*_count_raw`
  - 用于保留 Excel 原始聚合值
- 新增 `bidding_count`
  - 用于保留经营信息工作表中的招投标聚合值

这样既保证了结构化表之间的一致性，也没有丢失原始统计字段。

## 3. 专利新增企业映射表

新增：

- `company_patent_company_map`

原因：

- 同一专利号在原始数据中可能对应多个企业/联合申请人；
- 若只保留 `company_patent.company_id`，会丢失其他企业与该专利的关系；
- `company_patent` 继续保留一个快照式 `company_id`，同时通过映射表保存完整企业-专利关系。

同步与校验已同步更新：

- `patent_count` 通过 `company_patent_company_map` 计算；
- 校验脚本会检查 `company_patent_company_map` 孤儿记录。

## 4. 同步脚本语义更新

`SQL/scripts/sync_raw_to_business.py` 当前语义：

- 先从 `raw_import_*` 读取数据
- 对明细表做去重和结构化清洗
- 将 `company_basic_count.*_count` 写为结构化实际值
- 将 `company_basic_count.*_count_raw` 写为原始聚合值
- 可选删除 `raw_import_*` staging tables

## 5. 对智能助手的收益

这次回写后，数据库可以同时支撑两类问答：

- 基于结构化明细的一致性统计
- 基于原始采集视角的聚合口径追溯

也就是说，后续 RAG/智能助手在做企业画像和产业分析时，可以明确区分：

- “系统实际收敛出的结构化事实”
- “原始采集文件给出的统计口径”
