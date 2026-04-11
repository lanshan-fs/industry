SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

USE `industrial_chain`;

SET @ddl = IF (
  EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'company_basic_count'
      AND column_name = 'ai_model_filing_count'
  ),
  'SELECT 1',
  "ALTER TABLE `company_basic_count` ADD COLUMN `ai_model_filing_count` int NOT NULL DEFAULT '0' COMMENT '算法备案医疗大模型数量' AFTER `executed_person_count`"
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = IF (
  EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'company_basic_count'
      AND column_name = 'high_quality_dataset_count'
  ),
  'SELECT 1',
  "ALTER TABLE `company_basic_count` ADD COLUMN `high_quality_dataset_count` int NOT NULL DEFAULT '0' COMMENT '高质量数据集数量' AFTER `ai_model_filing_count`"
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = IF (
  EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'company_basic_count'
      AND column_name = 'innovation_notice_count'
  ),
  'SELECT 1',
  "ALTER TABLE `company_basic_count` ADD COLUMN `innovation_notice_count` int NOT NULL DEFAULT '0' COMMENT '创新性公示数量' AFTER `high_quality_dataset_count`"
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS `company_ai_model_filing` (
  `company_ai_model_filing_id` bigint NOT NULL AUTO_INCREMENT COMMENT '算法备案医疗大模型记录唯一标识',
  `company_id` bigint NOT NULL COMMENT '企业唯一标识',
  `company_name_raw` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业名称原值',
  `model_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模型名称',
  `filing_no` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '备案编号',
  `filing_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '备案类型',
  `territory` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '属地',
  `filed_at` date DEFAULT NULL COMMENT '备案时间',
  `source_period_raw` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '时期原值',
  `source_file` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源文件',
  `source_sheet` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源工作表',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_ai_model_filing_id`),
  UNIQUE KEY `uk_company_ai_model_filing_company_no` (`company_id`,`filing_no`),
  KEY `idx_company_ai_model_filing_company_id` (`company_id`),
  KEY `idx_company_ai_model_filing_model_name` (`model_name`),
  CONSTRAINT `fk_company_ai_model_filing_company` FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业算法备案医疗大模型表';

CREATE TABLE IF NOT EXISTS `company_high_quality_dataset` (
  `company_high_quality_dataset_id` bigint NOT NULL AUTO_INCREMENT COMMENT '高质量数据集记录唯一标识',
  `company_id` bigint NOT NULL COMMENT '企业唯一标识',
  `company_name_raw` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业名称原值',
  `dataset_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '案例/数据集名称',
  `applicant_unit_raw` text COLLATE utf8mb4_unicode_ci COMMENT '申报单位原值',
  `recommender_unit` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '推荐单位',
  `announced_at` date DEFAULT NULL COMMENT '公布日期',
  `source_file` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源文件',
  `source_sheet` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源工作表',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_high_quality_dataset_id`),
  UNIQUE KEY `uk_company_high_quality_dataset_company_name` (`company_id`,`dataset_name`),
  KEY `idx_company_high_quality_dataset_company_id` (`company_id`),
  CONSTRAINT `fk_company_high_quality_dataset_company` FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业高质量数据集表';

CREATE TABLE IF NOT EXISTS `company_innovation_notice` (
  `company_innovation_notice_id` bigint NOT NULL AUTO_INCREMENT COMMENT '创新性公示记录唯一标识',
  `company_id` bigint NOT NULL COMMENT '企业唯一标识',
  `company_name_raw` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业名称原值',
  `notice_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '公示类型',
  `notice_title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公示标题',
  `notice_category` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公示类别',
  `product_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '产品/事项名称',
  `reg_no` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '注册证号/登记号',
  `acceptance_no` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '受理号',
  `owner_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '所有者名称',
  `public_date` date DEFAULT NULL COMMENT '公示日期',
  `public_end_date` date DEFAULT NULL COMMENT '公示截止日期',
  `rare_disease_flag` tinyint NOT NULL DEFAULT '0' COMMENT '是否为罕见病药物',
  `source_file` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源文件',
  `source_sheet` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源工作表',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_innovation_notice_id`),
  KEY `idx_company_innovation_notice_company_id` (`company_id`),
  KEY `idx_company_innovation_notice_type` (`notice_type`),
  KEY `idx_company_innovation_notice_public_date` (`public_date`),
  CONSTRAINT `fk_company_innovation_notice_company` FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_innovation_notice_rare_disease` CHECK ((`rare_disease_flag` in (0,1)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业创新性公示表';

CREATE TABLE IF NOT EXISTS `raw_import_company_ai_model_filing` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `source_file` VARCHAR(255) DEFAULT NULL COMMENT '来源文件名',
  `source_sheet` VARCHAR(128) DEFAULT NULL COMMENT '来源工作表',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `period_raw` VARCHAR(64) DEFAULT NULL COMMENT '时期原值',
  `filing_type` VARCHAR(64) DEFAULT NULL COMMENT '类型',
  `source_order_raw` VARCHAR(64) DEFAULT NULL COMMENT '原序号',
  `territory` VARCHAR(255) DEFAULT NULL COMMENT '属地',
  `model_name` VARCHAR(255) DEFAULT NULL COMMENT '模型名称',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '单位/企业名称',
  `filing_number` VARCHAR(255) DEFAULT NULL COMMENT '备案编号',
  `filed_at_raw` VARCHAR(64) DEFAULT NULL COMMENT '备案时间原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_ai_model_filing_company_name` (`company_name`),
  KEY `idx_raw_import_company_ai_model_filing_filing_number` (`filing_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-算法备案医疗大模型';

CREATE TABLE IF NOT EXISTS `raw_import_company_high_quality_dataset` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `source_file` VARCHAR(255) DEFAULT NULL COMMENT '来源文件名',
  `source_sheet` VARCHAR(128) DEFAULT NULL COMMENT '来源工作表',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `source_order_raw` VARCHAR(64) DEFAULT NULL COMMENT '原序号',
  `dataset_name` VARCHAR(255) DEFAULT NULL COMMENT '案例/数据集名称',
  `applicant_unit` TEXT COMMENT '申报单位原值',
  `recommender_unit` VARCHAR(255) DEFAULT NULL COMMENT '推荐单位',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_high_quality_dataset_dataset_name` (`dataset_name`),
  KEY `idx_raw_import_company_high_quality_dataset_recommender_unit` (`recommender_unit`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-高质量数据集';

CREATE TABLE IF NOT EXISTS `raw_import_company_innovation_notice` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `source_file` VARCHAR(255) DEFAULT NULL COMMENT '来源文件名',
  `source_sheet` VARCHAR(128) DEFAULT NULL COMMENT '来源工作表',
  `notice_type` VARCHAR(64) DEFAULT NULL COMMENT '公示类型',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `source_order_raw` VARCHAR(64) DEFAULT NULL COMMENT '原序号',
  `notice_title` VARCHAR(255) DEFAULT NULL COMMENT '公示标题',
  `notice_category` VARCHAR(255) DEFAULT NULL COMMENT '类别',
  `company_name` VARCHAR(512) DEFAULT NULL COMMENT '企业名称/申请人',
  `owner_name` VARCHAR(255) DEFAULT NULL COMMENT '所有者名称',
  `product_name` VARCHAR(255) DEFAULT NULL COMMENT '产品/事项名称',
  `reg_no` VARCHAR(255) DEFAULT NULL COMMENT '注册证号/登记号',
  `acceptance_no` VARCHAR(255) DEFAULT NULL COMMENT '受理号',
  `public_date_raw` VARCHAR(64) DEFAULT NULL COMMENT '公示日期原值',
  `public_end_date_raw` VARCHAR(64) DEFAULT NULL COMMENT '公示截止日期原值',
  `rare_disease_flag_raw` VARCHAR(64) DEFAULT NULL COMMENT '是否为罕见病药物原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_innovation_notice_company_name` (`company_name`),
  KEY `idx_raw_import_company_innovation_notice_owner_name` (`owner_name`),
  KEY `idx_raw_import_company_innovation_notice_notice_type` (`notice_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-创新性公示';

SET FOREIGN_KEY_CHECKS = 1;
