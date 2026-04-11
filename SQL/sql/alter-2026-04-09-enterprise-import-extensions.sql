SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

USE `industrial_chain`;

CREATE TABLE IF NOT EXISTS `raw_import_company_supplier` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `supplier_name` VARCHAR(255) DEFAULT NULL COMMENT '供应商名称',
  `purchase_ratio_raw` VARCHAR(64) DEFAULT NULL COMMENT '采购占比原值',
  `purchase_amount_raw` VARCHAR(255) DEFAULT NULL COMMENT '采购金额原值',
  `report_period_raw` VARCHAR(64) DEFAULT NULL COMMENT '报告期原值',
  `data_source` VARCHAR(255) DEFAULT NULL COMMENT '数据来源',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_supplier_company_name` (`company_name`),
  KEY `idx_raw_import_company_supplier_supplier_name` (`supplier_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-供应商';

CREATE TABLE IF NOT EXISTS `raw_import_company_bidding` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `bidding_title` VARCHAR(512) DEFAULT NULL COMMENT '招标项目名称',
  `publish_date_raw` VARCHAR(64) DEFAULT NULL COMMENT '发布日期原值',
  `bidding_role_raw` VARCHAR(128) DEFAULT NULL COMMENT '角色/公告类型原值',
  `purchaser_name` TEXT COMMENT '招采单位',
  `winner_name` TEXT COMMENT '中标单位',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_bidding_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-招投标';

ALTER TABLE `raw_import_company_bidding`
  MODIFY COLUMN `bidding_title` VARCHAR(512) DEFAULT NULL COMMENT '招标项目名称',
  MODIFY COLUMN `purchaser_name` TEXT COMMENT '招采单位',
  MODIFY COLUMN `winner_name` TEXT COMMENT '中标单位';

SET FOREIGN_KEY_CHECKS = 1;
