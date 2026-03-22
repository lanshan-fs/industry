USE `industrial_chain`;

-- raw_import_* 仅作为 Excel 导入阶段的中转表。
-- 最终设计以 init.sql 中的业务表为准；导入完成后应删除这些 staging tables。

DROP TABLE IF EXISTS `raw_import_company_recruit`;
DROP TABLE IF EXISTS `raw_import_company_subdistrict`;
DROP TABLE IF EXISTS `raw_import_company_risk`;
DROP TABLE IF EXISTS `raw_import_company_patent`;
DROP TABLE IF EXISTS `raw_import_company_work_copyright`;
DROP TABLE IF EXISTS `raw_import_company_customer`;
DROP TABLE IF EXISTS `raw_import_company_ranking`;
DROP TABLE IF EXISTS `raw_import_software_copyright`;
DROP TABLE IF EXISTS `raw_import_company_ip_overview`;
DROP TABLE IF EXISTS `raw_import_company_operation`;
DROP TABLE IF EXISTS `raw_import_company_basic`;
