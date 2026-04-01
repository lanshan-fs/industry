SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `industrial_chain`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `industrial_chain`;

DROP TABLE IF EXISTS `user_operation_logs`;
DROP TABLE IF EXISTS `user_and_roles`;
DROP TABLE IF EXISTS `user_roles`;
DROP TABLE IF EXISTS `user_dinvite_codes`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `user_domains`;
DROP TABLE IF EXISTS `rag_chat_message`;
DROP TABLE IF EXISTS `rag_chat_session`;
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
DROP TABLE IF EXISTS `scoring_scorelog`;
DROP TABLE IF EXISTS `scoring_scoreresult`;
DROP TABLE IF EXISTS `score_model_professional_weight`;
DROP TABLE IF EXISTS `score_model_tech_weight`;
DROP TABLE IF EXISTS `score_model_basic_weight`;
DROP TABLE IF EXISTS `score_model_total_weight`;
DROP TABLE IF EXISTS `score_industry_path`;
DROP TABLE IF EXISTS `company_supplier`;
DROP TABLE IF EXISTS `company_customer`;
DROP TABLE IF EXISTS `category_industry_company_map`;
DROP TABLE IF EXISTS `chain_industry_category_industry_map`;
DROP TABLE IF EXISTS `company_patent_patent_type_map`;
DROP TABLE IF EXISTS `company_patent_company_map`;
DROP TABLE IF EXISTS `company_patent_type`;
DROP TABLE IF EXISTS `company_ranking`;
DROP TABLE IF EXISTS `company_work_copyright`;
DROP TABLE IF EXISTS `company_trademark`;
DROP TABLE IF EXISTS `company_basic_count`;
DROP TABLE IF EXISTS `company_tag_dimension_library_map`;
DROP TABLE IF EXISTS `company_tag_auto_rule`;
DROP TABLE IF EXISTS `company_tag_llm_candidate`;
DROP TABLE IF EXISTS `company_tag_llm_batch`;
DROP TABLE IF EXISTS `company_tag_batch_item`;
DROP TABLE IF EXISTS `company_tag_batch`;
DROP TABLE IF EXISTS `company_tag_map`;
DROP TABLE IF EXISTS `company_software_copyright`;
DROP TABLE IF EXISTS `company_subdistrict`;
DROP TABLE IF EXISTS `company_patent`;
DROP TABLE IF EXISTS `company_risk`;
DROP TABLE IF EXISTS `company_recruit`;
DROP TABLE IF EXISTS `company_bidding`;
DROP TABLE IF EXISTS `company_consumption_restriction`;
DROP TABLE IF EXISTS `company_listing_status`;
DROP TABLE IF EXISTS `company_change`;
DROP TABLE IF EXISTS `company_financing`;
DROP TABLE IF EXISTS `company_qualification`;
DROP TABLE IF EXISTS `company_address`;
DROP TABLE IF EXISTS `company_employee_count`;
DROP TABLE IF EXISTS `company_shareholder`;
DROP TABLE IF EXISTS `company_recommended_phone`;
DROP TABLE IF EXISTS `company_contact_info`;
DROP TABLE IF EXISTS `company_contact_phone`;
DROP TABLE IF EXISTS `company_website`;
DROP TABLE IF EXISTS `company_former_name`;
DROP TABLE IF EXISTS `company_branch`;
DROP TABLE IF EXISTS `company_tag_library`;
DROP TABLE IF EXISTS `company_tag_subdimension`;
DROP TABLE IF EXISTS `company_tag_dimension`;
DROP TABLE IF EXISTS `chain_industry`;
DROP TABLE IF EXISTS `category_industry`;
DROP TABLE IF EXISTS `company_basic`;

CREATE TABLE `rag_chat_session` (
  `session_id` VARCHAR(64) NOT NULL COMMENT 'RAG 对话会话 ID',
  `user_id` BIGINT NOT NULL COMMENT '所属用户 ID（users.user_id）',
  `title` VARCHAR(255) DEFAULT NULL COMMENT '会话标题',
  `is_pinned` TINYINT NOT NULL DEFAULT 0 COMMENT '是否置顶（1:是，0:否）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`session_id`),
  KEY `idx_rag_chat_session_user_updated_at` (`user_id`, `updated_at`),
  KEY `idx_rag_chat_session_updated_at` (`updated_at`),
  KEY `idx_rag_chat_session_pin_updated_at` (`is_pinned`, `updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG 对话会话表';

CREATE TABLE `rag_chat_message` (
  `message_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '消息主键',
  `session_id` VARCHAR(64) NOT NULL COMMENT '所属会话 ID',
  `role` VARCHAR(16) NOT NULL COMMENT '消息角色（user/assistant/system）',
  `content` LONGTEXT NOT NULL COMMENT '消息正文',
  `retrieval_metadata` JSON DEFAULT NULL COMMENT '检索元数据',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`message_id`),
  KEY `idx_rag_chat_message_session_created_at` (`session_id`, `created_at`),
  CONSTRAINT `fk_rag_chat_message_session`
    FOREIGN KEY (`session_id`) REFERENCES `rag_chat_session` (`session_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG 对话消息表';

CREATE TABLE `company_basic` (
  `company_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业唯一标识',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `company_name_en` VARCHAR(255) DEFAULT NULL COMMENT '企业英文名称',
  `former_name_latest` VARCHAR(255) DEFAULT NULL COMMENT '企业曾用名（最新）',
  `credit_code` CHAR(18) NOT NULL COMMENT '统一社会信用代码',
  `legal_representative` VARCHAR(255) DEFAULT NULL COMMENT '法定代表人',
  `register_number` CHAR(15) DEFAULT NULL COMMENT '注册号（工商注册号，旧版企业登记编号）',
  `approved_date` DATE DEFAULT NULL COMMENT '核准日期（工商信息最后核准更新日期）',
  `org_code` CHAR(9) DEFAULT NULL COMMENT '组织机构代码',
  `establish_date` DATE DEFAULT NULL COMMENT '成立日期',
  `business_term` VARCHAR(255) DEFAULT NULL COMMENT '经营期限',
  `business_scope` TEXT COMMENT '经营范围',
  `company_status` VARCHAR(255) DEFAULT NULL COMMENT '经营状态',
  `email_business` VARCHAR(255) DEFAULT NULL COMMENT '企业邮箱（工商信息）',
  `email_auth` VARCHAR(255) DEFAULT NULL COMMENT '企业邮箱（认证）',
  `website` VARCHAR(255) DEFAULT NULL COMMENT '企业网站 URL',
  `contact_phone` VARCHAR(255) DEFAULT NULL COMMENT '联系电话',
  `contact_info` VARCHAR(255) DEFAULT NULL COMMENT '联系方式',
  `recommended_phone` VARCHAR(255) DEFAULT NULL COMMENT '推荐电话',
  `latest_shareholder_name` VARCHAR(255) DEFAULT NULL COMMENT '股东（最新）',
  `register_sheng` VARCHAR(255) DEFAULT NULL COMMENT '注册地（省）',
  `register_shi` VARCHAR(255) DEFAULT NULL COMMENT '注册地（市）',
  `register_xian` VARCHAR(255) DEFAULT NULL COMMENT '注册地（区县）',
  `subdistrict` VARCHAR(255) DEFAULT NULL COMMENT '所属街道/地区',
  `register_capital` DECIMAL(18, 4) DEFAULT NULL COMMENT '注册资本（万元）',
  `paid_capital` DECIMAL(18, 4) DEFAULT NULL COMMENT '实缴资本（万元）',
  `company_type` VARCHAR(255) DEFAULT NULL COMMENT '企业类型',
  `org_type` VARCHAR(255) DEFAULT NULL COMMENT '组织类型（暂时保留）',
  `investment_type` VARCHAR(255) DEFAULT NULL COMMENT '投资类型',
  `company_scale` VARCHAR(255) DEFAULT NULL COMMENT '企业规模',
  `employee_count` INT DEFAULT NULL COMMENT '员工人数（最新）',
  `insured_count` INT DEFAULT NULL COMMENT '参保人数',
  `industry_belong` VARCHAR(255) DEFAULT NULL COMMENT '所属行业（国标）',
  `industry_belong_code` VARCHAR(255) DEFAULT NULL COMMENT '所属行业代码（国标）',
  `is_branch` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为分支机构（1:是，0:否）',
  `branch_id` BIGINT DEFAULT NULL COMMENT '分支机构唯一标识',
  `branch_name` VARCHAR(255) DEFAULT NULL COMMENT '分支机构名称（最新）',
  `register_address` VARCHAR(255) DEFAULT NULL COMMENT '企业地址（工商信息）',
  `register_address_detail` VARCHAR(255) DEFAULT NULL COMMENT '企业地址（详细，最新）',
  `qualification_label` VARCHAR(255) DEFAULT NULL COMMENT '企业资质/企业科技属性（最新）',
  `is_general_taxpayer` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为一般纳税人（1:是，0:否）',
  `taxpayer_qualifications` VARCHAR(255) DEFAULT NULL COMMENT '纳税人资质',
  `taxpayer_credit_rating` VARCHAR(16) DEFAULT NULL COMMENT '纳税人信用等级：ABCDM',
  `financing_round` VARCHAR(255) DEFAULT NULL COMMENT '投融资轮次（最新）',
  `financing_round_verify_time` DATE DEFAULT NULL COMMENT '投融资轮次核准时间（最新）',
  `financing_info` VARCHAR(255) DEFAULT NULL COMMENT '投融资轮次信息（最新）',
  `stock_code` VARCHAR(32) DEFAULT NULL COMMENT '股票代码',
  `field_belong` TINYINT DEFAULT NULL COMMENT '所属领域（1:数字医疗，2:康养）',
  `is_high_tech_enterprise` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为高新技术企业（1:是，0:否）',
  `is_high_tech_enterprise_verify_time` DATE DEFAULT NULL COMMENT '高新技术企业认证日期',
  `is_micro_enterprise` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为小微企业（1:是，0:否）',
  `has_changed_info` TINYINT NOT NULL DEFAULT 0 COMMENT '是否有变更信息（1:是，0:否）',
  `has_bidding` TINYINT NOT NULL DEFAULT 0 COMMENT '是否有招投标信息（1:是，0:否）',
  `has_recruitment` TINYINT NOT NULL DEFAULT 0 COMMENT '是否有招聘信息（1:是，0:否）',
  `industry_chain_link` TINYINT DEFAULT NULL COMMENT '产业链环节（1:上游，2:中游，3:下游）',
  `has_software_copyright` TINYINT NOT NULL DEFAULT 0 COMMENT '有无软件著作权',
  `has_work_copyright` TINYINT NOT NULL DEFAULT 0 COMMENT '有无作品著作权',
  `listing_status` TINYINT DEFAULT NULL COMMENT '上市状态（2:终止上市，1:正常上市，0:未上市）',
  `same_phone_company_count` INT NOT NULL DEFAULT 0 COMMENT '同企业电话数量',
  `is_srdi_sme` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为专精特新中小企业',
  `is_gazelle_company` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为瞪羚企业',
  `is_tech_sme` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为科技型中小企业',
  `is_egalet_company` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为雏鹰企业',
  `is_srdi_little_giant` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为专精特新小巨人',
  `is_innovative_sme` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为创新型中小企业',
  `has_patent` TINYINT NOT NULL DEFAULT 0 COMMENT '有无专利',
  `has_trademark` TINYINT NOT NULL DEFAULT 0 COMMENT '有无商标',
  `has_legal_document` TINYINT NOT NULL DEFAULT 0 COMMENT '有无法律文书',
  `has_dishonest_execution` TINYINT NOT NULL DEFAULT 0 COMMENT '有无失信被执行',
  `has_chattel_mortgage` TINYINT NOT NULL DEFAULT 0 COMMENT '有无动产抵押',
  `has_business_abnormal` TINYINT NOT NULL DEFAULT 0 COMMENT '有无经营异常',
  `has_admin_penalty` TINYINT NOT NULL DEFAULT 0 COMMENT '有无行政处罚',
  `has_bankruptcy_overlap` TINYINT NOT NULL DEFAULT 0 COMMENT '有无破产重叠',
  `has_liquidation_info` TINYINT NOT NULL DEFAULT 0 COMMENT '有无清算信息',
  `has_env_penalty` TINYINT NOT NULL DEFAULT 0 COMMENT '有无环保处罚',
  `has_equity_freeze` TINYINT NOT NULL DEFAULT 0 COMMENT '有无股权冻结',
  `has_executed_person` TINYINT NOT NULL DEFAULT 0 COMMENT '有无被执行人',
  `has_consumption_restriction` TINYINT NOT NULL DEFAULT 0 COMMENT '有无限制高消费',
  `consumption_restriction_count` INT NOT NULL DEFAULT 0 COMMENT '限制高消费数量',
  `is_chaoyang_company` TINYINT NOT NULL DEFAULT 0 COMMENT '是否是朝阳区企业',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_id`),
  UNIQUE KEY `uk_company_basic_credit_code` (`credit_code`),
  KEY `idx_company_basic_company_name` (`company_name`),
  KEY `idx_company_basic_field_belong` (`field_belong`),
  KEY `idx_company_basic_industry_code` (`industry_belong_code`),
  KEY `idx_company_basic_subdistrict` (`subdistrict`),
  KEY `idx_company_basic_chaoyang` (`is_chaoyang_company`),
  CONSTRAINT `chk_company_basic_is_branch` CHECK (`is_branch` IN (0, 1)),
  CONSTRAINT `chk_company_basic_general_taxpayer` CHECK (`is_general_taxpayer` IN (0, 1)),
  CONSTRAINT `chk_company_basic_field_belong` CHECK (`field_belong` IS NULL OR `field_belong` IN (1, 2)),
  CONSTRAINT `chk_company_basic_industry_chain_link` CHECK (`industry_chain_link` IS NULL OR `industry_chain_link` IN (1, 2, 3)),
  CONSTRAINT `chk_company_basic_listing_status` CHECK (`listing_status` IS NULL OR `listing_status` IN (0, 1, 2))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业基础信息表';

CREATE TABLE `category_industry` (
  `category_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '行业分类唯一标识',
  `category_name` VARCHAR(255) NOT NULL COMMENT '行业分类名称',
  `category_level` TINYINT NOT NULL COMMENT '行业分类层级（0-3 级）',
  `category_level_code` VARCHAR(255) NOT NULL COMMENT '行业分类层级编码',
  `category_level_code_parent` VARCHAR(255) DEFAULT NULL COMMENT '行业分类层级编码（父级）',
  `field_belong` TINYINT NOT NULL COMMENT '所属领域（1:数字医疗，2:康养）',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序序号',
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `uk_category_industry_level_code` (`category_level_code`),
  KEY `idx_category_industry_parent_code` (`category_level_code_parent`),
  KEY `idx_category_industry_field_belong` (`field_belong`),
  CONSTRAINT `chk_category_industry_level` CHECK (`category_level` BETWEEN 0 AND 3),
  CONSTRAINT `chk_category_industry_field_belong` CHECK (`field_belong` IN (1, 2)),
  CONSTRAINT `chk_category_industry_sort_order` CHECK (`sort_order` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='行业分类表';

CREATE TABLE `chain_industry` (
  `chain_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '产业链节点唯一标识',
  `chain_name` VARCHAR(255) NOT NULL COMMENT '产业链节点名称',
  `chain_des` VARCHAR(255) DEFAULT NULL COMMENT '产业链节点简述',
  PRIMARY KEY (`chain_id`),
  UNIQUE KEY `uk_chain_industry_name` (`chain_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='产业链节点表';

CREATE TABLE `company_tag_dimension` (
  `company_tag_dimension_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业标签维度唯一标识',
  `company_tag_dimension_name` VARCHAR(255) NOT NULL COMMENT '企业标签维度名称',
  `company_tag_dimension_color` VARCHAR(255) DEFAULT NULL COMMENT '增强前端表现力',
  `company_tag_dimension_icon` VARCHAR(255) DEFAULT NULL COMMENT '维度图标',
  `company_tag_dimension_des` VARCHAR(255) DEFAULT NULL COMMENT '维度描述',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序序号',
  PRIMARY KEY (`company_tag_dimension_id`),
  UNIQUE KEY `uk_company_tag_dimension_name` (`company_tag_dimension_name`),
  CONSTRAINT `chk_company_tag_dimension_sort_order` CHECK (`sort_order` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签维度表';

CREATE TABLE `company_tag_subdimension` (
  `company_tag_subdimension_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业标签子维度唯一标识',
  `company_tag_subdimension_name` VARCHAR(255) NOT NULL COMMENT '企业标签子维度名称',
  `company_tag_dimension_id` BIGINT NOT NULL COMMENT '企业标签维度唯一标识',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序序号',
  PRIMARY KEY (`company_tag_subdimension_id`),
  UNIQUE KEY `uk_company_tag_subdimension_name` (`company_tag_dimension_id`, `company_tag_subdimension_name`),
  CONSTRAINT `fk_company_tag_subdimension_dimension`
    FOREIGN KEY (`company_tag_dimension_id`) REFERENCES `company_tag_dimension` (`company_tag_dimension_id`),
  CONSTRAINT `chk_company_tag_subdimension_sort_order` CHECK (`sort_order` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签子维度表';

CREATE TABLE `company_tag_library` (
  `company_tag_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业标签唯一标识',
  `company_tag_name` VARCHAR(255) NOT NULL COMMENT '企业标签名称',
  `company_tag_subdimension_id` BIGINT DEFAULT NULL COMMENT '企业标签子维度唯一标识',
  `company_tag_level` TINYINT DEFAULT NULL COMMENT '企业标签等级（国家级、省级、市级）',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序序号',
  PRIMARY KEY (`company_tag_id`),
  UNIQUE KEY `uk_company_tag_library_name` (`company_tag_name`),
  KEY `idx_company_tag_library_subdimension` (`company_tag_subdimension_id`),
  CONSTRAINT `fk_company_tag_library_subdimension`
    FOREIGN KEY (`company_tag_subdimension_id`) REFERENCES `company_tag_subdimension` (`company_tag_subdimension_id`),
  CONSTRAINT `chk_company_tag_library_sort_order` CHECK (`sort_order` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签库表';

CREATE TABLE `company_branch` (
  `company_branch_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业分支机构唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_branch_name` VARCHAR(255) NOT NULL COMMENT '企业分支机构名称',
  `company_branch_address` VARCHAR(255) DEFAULT NULL COMMENT '企业分支机构（注册）地址',
  `company_branch_status` TINYINT DEFAULT NULL COMMENT '企业分支机构状态（存续、注销、吊销）',
  `company_branch_establish_date` DATE DEFAULT NULL COMMENT '企业分支机构成立日期',
  `company_branch_legal_representative` VARCHAR(255) DEFAULT NULL COMMENT '企业分支机构法定代表人',
  `company_branch_business_scope` TEXT COMMENT '企业分支机构经营范围',
  `company_branch_taxpayer_credit_rating` VARCHAR(16) DEFAULT NULL COMMENT '企业分支机构纳税人信用等级',
  PRIMARY KEY (`company_branch_id`),
  UNIQUE KEY `uk_company_branch_name` (`company_id`, `company_branch_name`),
  KEY `idx_company_branch_company_id` (`company_id`),
  CONSTRAINT `fk_company_branch_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业分支机构表';

CREATE TABLE `company_former_name` (
  `company_former_name_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业曾用名记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `former_name` VARCHAR(255) NOT NULL COMMENT '企业曾用名',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  `effective_date` DATE DEFAULT NULL COMMENT '生效时间',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序序号',
  PRIMARY KEY (`company_former_name_id`),
  KEY `idx_company_former_name_company_id` (`company_id`),
  CONSTRAINT `fk_company_former_name_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_former_name_is_latest` CHECK (`is_latest` IN (0, 1)),
  CONSTRAINT `chk_company_former_name_sort_order` CHECK (`sort_order` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业曾用名表';

CREATE TABLE `company_website` (
  `company_website_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业网站记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `website` VARCHAR(255) NOT NULL COMMENT '企业网站 URL',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  `captured_at` DATETIME DEFAULT NULL COMMENT '抓取/核准时间',
  PRIMARY KEY (`company_website_id`),
  UNIQUE KEY `uk_company_website` (`company_id`, `website`),
  CONSTRAINT `fk_company_website_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_website_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业网站表';

CREATE TABLE `company_contact_phone` (
  `company_contact_phone_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '联系电话记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `contact_phone` VARCHAR(255) NOT NULL COMMENT '联系电话',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  `captured_at` DATETIME DEFAULT NULL COMMENT '抓取/核准时间',
  PRIMARY KEY (`company_contact_phone_id`),
  UNIQUE KEY `uk_company_contact_phone` (`company_id`, `contact_phone`),
  CONSTRAINT `fk_company_contact_phone_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_contact_phone_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业联系电话表';

CREATE TABLE `company_contact_info` (
  `company_contact_info_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '联系方式记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `contact_info` VARCHAR(255) NOT NULL COMMENT '联系方式',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  `captured_at` DATETIME DEFAULT NULL COMMENT '抓取/核准时间',
  PRIMARY KEY (`company_contact_info_id`),
  UNIQUE KEY `uk_company_contact_info` (`company_id`, `contact_info`),
  CONSTRAINT `fk_company_contact_info_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_contact_info_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业联系方式表';

CREATE TABLE `company_recommended_phone` (
  `company_recommended_phone_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '推荐电话记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `recommended_phone` VARCHAR(255) NOT NULL COMMENT '推荐电话',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  `captured_at` DATETIME DEFAULT NULL COMMENT '抓取/核准时间',
  PRIMARY KEY (`company_recommended_phone_id`),
  UNIQUE KEY `uk_company_recommended_phone` (`company_id`, `recommended_phone`),
  CONSTRAINT `fk_company_recommended_phone_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_recommended_phone_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业推荐电话表';

CREATE TABLE `company_shareholder` (
  `company_shareholder_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业股东记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `shareholder_name` VARCHAR(255) NOT NULL COMMENT '股东名称',
  `shareholder_type` VARCHAR(64) DEFAULT NULL COMMENT '股东类型',
  `holding_ratio` DECIMAL(5, 2) DEFAULT NULL COMMENT '持股比例',
  `subscribed_amount` DECIMAL(18, 4) DEFAULT NULL COMMENT '认缴出资额（万元）',
  `paid_amount` DECIMAL(18, 4) DEFAULT NULL COMMENT '实缴出资额（万元）',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  `captured_at` DATETIME DEFAULT NULL COMMENT '抓取/核准时间',
  PRIMARY KEY (`company_shareholder_id`),
  KEY `idx_company_shareholder_company_id` (`company_id`),
  CONSTRAINT `fk_company_shareholder_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_shareholder_ratio` CHECK (`holding_ratio` IS NULL OR (`holding_ratio` >= 0 AND `holding_ratio` <= 100)),
  CONSTRAINT `chk_company_shareholder_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业股东信息表';

CREATE TABLE `company_employee_count` (
  `company_employee_count_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业员工人数记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `stat_year` SMALLINT NOT NULL COMMENT '统计年份',
  `employee_count` INT NOT NULL COMMENT '员工人数',
  PRIMARY KEY (`company_employee_count_id`),
  UNIQUE KEY `uk_company_employee_count_year` (`company_id`, `stat_year`),
  CONSTRAINT `fk_company_employee_count_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_employee_count_value` CHECK (`employee_count` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业员工人数表';

CREATE TABLE `company_address` (
  `company_address_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业地址记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `address_type` VARCHAR(64) NOT NULL DEFAULT 'registered' COMMENT '地址类型',
  `address_text` VARCHAR(255) NOT NULL COMMENT '企业地址',
  `province` VARCHAR(255) DEFAULT NULL COMMENT '省',
  `city` VARCHAR(255) DEFAULT NULL COMMENT '市',
  `district` VARCHAR(255) DEFAULT NULL COMMENT '区县',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  PRIMARY KEY (`company_address_id`),
  KEY `idx_company_address_company_id` (`company_id`),
  CONSTRAINT `fk_company_address_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_address_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业地址信息表';

CREATE TABLE `company_qualification` (
  `company_qualification_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业资质记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `qualification_name` VARCHAR(255) NOT NULL COMMENT '企业资质/科技属性名称',
  `qualification_level` TINYINT DEFAULT NULL COMMENT '资质等级',
  `qualification_type` VARCHAR(255) DEFAULT NULL COMMENT '资质类型',
  `issued_at` DATE DEFAULT NULL COMMENT '认定日期',
  `expires_at` DATE DEFAULT NULL COMMENT '失效日期',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  PRIMARY KEY (`company_qualification_id`),
  KEY `idx_company_qualification_company_id` (`company_id`),
  CONSTRAINT `fk_company_qualification_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_qualification_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业资质表';

CREATE TABLE `company_financing` (
  `company_financing_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业投融资记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `financing_round` VARCHAR(255) NOT NULL COMMENT '投融资轮次',
  `verify_time` DATE DEFAULT NULL COMMENT '核准时间',
  `financing_amount` DECIMAL(18, 4) DEFAULT NULL COMMENT '融资金额（万元）',
  `investor_name` VARCHAR(255) DEFAULT NULL COMMENT '投资方名称',
  `is_latest` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为最新记录',
  PRIMARY KEY (`company_financing_id`),
  KEY `idx_company_financing_company_id` (`company_id`),
  CONSTRAINT `fk_company_financing_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_financing_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业投融资轮次信息表';

CREATE TABLE `company_change` (
  `company_change_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业变更记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `change_item` VARCHAR(255) NOT NULL COMMENT '变更事项',
  `before_change` TEXT COMMENT '变更前内容',
  `after_change` TEXT COMMENT '变更后内容',
  `change_date` DATE DEFAULT NULL COMMENT '变更日期',
  PRIMARY KEY (`company_change_id`),
  KEY `idx_company_change_company_id` (`company_id`),
  CONSTRAINT `fk_company_change_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业变更信息表';

CREATE TABLE `company_listing_status` (
  `company_listing_status_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业上市状态记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `listing_status` TINYINT NOT NULL COMMENT '上市状态（2:终止上市，1:正常上市，0:未上市）',
  `stock_code` VARCHAR(32) DEFAULT NULL COMMENT '股票代码',
  `market_name` VARCHAR(255) DEFAULT NULL COMMENT '上市市场',
  `listed_at` DATE DEFAULT NULL COMMENT '上市日期',
  `delisted_at` DATE DEFAULT NULL COMMENT '终止上市日期',
  `is_latest` TINYINT NOT NULL DEFAULT 1 COMMENT '是否为最新记录',
  PRIMARY KEY (`company_listing_status_id`),
  KEY `idx_company_listing_status_company_id` (`company_id`),
  CONSTRAINT `fk_company_listing_status_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_listing_status_status` CHECK (`listing_status` IN (0, 1, 2)),
  CONSTRAINT `chk_company_listing_status_is_latest` CHECK (`is_latest` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业上市状态表';

CREATE TABLE `company_consumption_restriction` (
  `company_consumption_restriction_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '限制高消费记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `case_no` VARCHAR(255) DEFAULT NULL COMMENT '案号',
  `restricted_subject` VARCHAR(255) DEFAULT NULL COMMENT '限制对象',
  `filing_date` DATE DEFAULT NULL COMMENT '立案日期',
  `publish_date` DATE DEFAULT NULL COMMENT '发布日期',
  PRIMARY KEY (`company_consumption_restriction_id`),
  KEY `idx_company_consumption_restriction_company_id` (`company_id`),
  CONSTRAINT `fk_company_consumption_restriction_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='限制高消费表';

CREATE TABLE `company_bidding` (
  `company_bidding_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业招投标记录唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `bidding_title` VARCHAR(255) DEFAULT NULL COMMENT '招投标项目名称',
  `bidding_role` VARCHAR(64) DEFAULT NULL COMMENT '企业角色',
  `publish_date` DATE DEFAULT NULL COMMENT '发布日期',
  `bidding_amount` DECIMAL(18, 4) DEFAULT NULL COMMENT '招投标金额（万元）',
  PRIMARY KEY (`company_bidding_id`),
  KEY `idx_company_bidding_company_id` (`company_id`),
  CONSTRAINT `fk_company_bidding_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业招投标信息表';

CREATE TABLE `company_recruit` (
  `company_recruit_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业招聘记录唯一标识',
  `company_recruit_position` VARCHAR(255) NOT NULL COMMENT '企业招聘岗位',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_recruit_salary` VARCHAR(255) DEFAULT NULL COMMENT '企业招聘薪资',
  `company_recruit_work_year_req` VARCHAR(255) DEFAULT NULL COMMENT '企业招聘工作年限要求',
  `company_recruit_work_place` VARCHAR(255) DEFAULT NULL COMMENT '企业招聘工作地点',
  `company_recruit_edu_req` VARCHAR(255) DEFAULT NULL COMMENT '企业招聘学历要求',
  `company_recruit_time` DATE DEFAULT NULL COMMENT '企业招聘时间',
  PRIMARY KEY (`company_recruit_id`),
  KEY `idx_company_recruit_company_id` (`company_id`),
  CONSTRAINT `fk_company_recruit_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业招聘信息表';

CREATE TABLE `company_risk` (
  `company_risk_category_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业风险种类唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_risk_category_name` VARCHAR(255) NOT NULL COMMENT '企业风险种类名称',
  `company_risk_category_count` INT NOT NULL DEFAULT 0 COMMENT '企业风险数量',
  PRIMARY KEY (`company_risk_category_id`),
  UNIQUE KEY `uk_company_risk_name` (`company_id`, `company_risk_category_name`),
  CONSTRAINT `fk_company_risk_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_risk_count` CHECK (`company_risk_category_count` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业风险统计表';

CREATE TABLE `company_patent` (
  `company_patent_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '专利唯一标识',
  `company_patent_number` VARCHAR(255) NOT NULL COMMENT '专利号',
  `company_patent_name` VARCHAR(255) NOT NULL COMMENT '专利名称',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `application_date` DATE DEFAULT NULL COMMENT '专利申请日期',
  `auth_date` DATE DEFAULT NULL COMMENT '专利授权日期',
  `tech_attribute_label` VARCHAR(255) DEFAULT NULL COMMENT '科技属性标签',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序序号',
  PRIMARY KEY (`company_patent_id`),
  UNIQUE KEY `uk_company_patent_number` (`company_patent_number`),
  KEY `idx_company_patent_company_id` (`company_id`),
  CONSTRAINT `fk_company_patent_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_patent_sort_order` CHECK (`sort_order` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业专利表';

CREATE TABLE `company_subdistrict` (
  `company_subdistrict_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '街道/地区 ID',
  `company_subdistrict_name` VARCHAR(255) NOT NULL COMMENT '街道/地区名称',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  PRIMARY KEY (`company_subdistrict_id`),
  UNIQUE KEY `uk_company_subdistrict` (`company_id`, `company_subdistrict_name`),
  CONSTRAINT `fk_company_subdistrict_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业街道/地区映射表';

CREATE TABLE `company_software_copyright` (
  `company_software_copyright_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '软件著作唯一标识',
  `company_software_copyright_name` VARCHAR(255) NOT NULL COMMENT '软件著作名称',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_software_copyright_register_number` VARCHAR(255) NOT NULL COMMENT '软件著作登记号',
  `company_software_copyright_register_date` DATE DEFAULT NULL COMMENT '软件著作登记批准日期',
  `company_software_copyright_for_short` VARCHAR(255) DEFAULT NULL COMMENT '软件著作简称',
  `company_software_copyright_status` VARCHAR(255) DEFAULT NULL COMMENT '软件著作状态',
  `company_software_copyright_obtain` VARCHAR(255) DEFAULT NULL COMMENT '软件著作取得方式',
  PRIMARY KEY (`company_software_copyright_id`),
  UNIQUE KEY `uk_company_software_copyright_register_number` (`company_software_copyright_register_number`),
  KEY `idx_company_software_copyright_company_id` (`company_id`),
  CONSTRAINT `fk_company_software_copyright_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业软件著作权表';

CREATE TABLE `company_tag_map` (
  `company_tag_map_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业标签映射唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_tag_id` BIGINT NOT NULL COMMENT '企业标签唯一标识',
  `source` TINYINT DEFAULT NULL COMMENT '打标来源（1:手动，2:自动）',
  `confidence` DECIMAL(3, 2) DEFAULT NULL COMMENT '置信度',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '打标时间',
  `user_id` BIGINT DEFAULT NULL COMMENT '打标人',
  PRIMARY KEY (`company_tag_map_id`),
  UNIQUE KEY `uk_company_tag_map` (`company_id`, `company_tag_id`),
  KEY `idx_company_tag_map_tag_id` (`company_tag_id`),
  CONSTRAINT `fk_company_tag_map_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `fk_company_tag_map_tag`
    FOREIGN KEY (`company_tag_id`) REFERENCES `company_tag_library` (`company_tag_id`),
  CONSTRAINT `chk_company_tag_map_source` CHECK (`source` IS NULL OR `source` IN (1, 2)),
  CONSTRAINT `chk_company_tag_map_confidence` CHECK (`confidence` IS NULL OR (`confidence` >= 0 AND `confidence` <= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签映射表';

CREATE TABLE `company_tag_batch` (
  `company_tag_batch_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业标签批次唯一标识',
  `batch_code` VARCHAR(64) NOT NULL COMMENT '批次编码',
  `batch_name` VARCHAR(255) DEFAULT NULL COMMENT '批次名称',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '批次状态（pending/running/completed/failed）',
  `requested_by_user_id` BIGINT DEFAULT NULL COMMENT '发起用户 ID',
  `dimension_ids` JSON DEFAULT NULL COMMENT '本批次选择的标签维度 ID 列表',
  `dimension_names` JSON DEFAULT NULL COMMENT '本批次选择的标签维度名称列表',
  `requested_company_count` INT NOT NULL DEFAULT 0 COMMENT '本批次请求企业数',
  `success_company_count` INT NOT NULL DEFAULT 0 COMMENT '成功企业数',
  `failed_company_count` INT NOT NULL DEFAULT 0 COMMENT '失败企业数',
  `summary_json` JSON DEFAULT NULL COMMENT '批次执行摘要',
  `error_message` TEXT DEFAULT NULL COMMENT '批次错误信息',
  `started_at` DATETIME DEFAULT NULL COMMENT '开始时间',
  `finished_at` DATETIME DEFAULT NULL COMMENT '结束时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_tag_batch_id`),
  UNIQUE KEY `uk_company_tag_batch_code` (`batch_code`),
  KEY `idx_company_tag_batch_status_created` (`status`, `created_at`),
  KEY `idx_company_tag_batch_user_created` (`requested_by_user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签批次表';

CREATE TABLE `company_tag_batch_item` (
  `company_tag_batch_item_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业标签批次明细唯一标识',
  `company_tag_batch_id` BIGINT NOT NULL COMMENT '企业标签批次唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '明细状态（pending/success/failed）',
  `tag_count` INT NOT NULL DEFAULT 0 COMMENT '本次命中标签数',
  `result_json` JSON DEFAULT NULL COMMENT '明细执行结果',
  `error_message` TEXT DEFAULT NULL COMMENT '明细错误信息',
  `started_at` DATETIME DEFAULT NULL COMMENT '开始时间',
  `finished_at` DATETIME DEFAULT NULL COMMENT '结束时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_tag_batch_item_id`),
  UNIQUE KEY `uk_company_tag_batch_item` (`company_tag_batch_id`, `company_id`),
  KEY `idx_company_tag_batch_item_company` (`company_id`),
  KEY `idx_company_tag_batch_item_status` (`status`),
  CONSTRAINT `fk_company_tag_batch_item_batch`
    FOREIGN KEY (`company_tag_batch_id`) REFERENCES `company_tag_batch` (`company_tag_batch_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_company_tag_batch_item_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签批次明细表';

CREATE TABLE `company_tag_llm_batch` (
  `company_tag_llm_batch_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业标签 LLM 候选批次唯一标识',
  `batch_code` VARCHAR(64) NOT NULL COMMENT 'LLM 批次编码',
  `batch_name` VARCHAR(255) DEFAULT NULL COMMENT '批次名称',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '批次状态（pending/running/completed/failed）',
  `provider` VARCHAR(64) NOT NULL DEFAULT 'agent_chat' COMMENT '候选生成服务提供方',
  `model_name` VARCHAR(128) DEFAULT NULL COMMENT '模型名称',
  `company_tag_dimension_id` BIGINT NOT NULL COMMENT '对应的标签维度，当前固定为应用场景',
  `requested_by_user_id` BIGINT DEFAULT NULL COMMENT '发起用户 ID',
  `requested_company_count` INT NOT NULL DEFAULT 0 COMMENT '请求企业数',
  `success_company_count` INT NOT NULL DEFAULT 0 COMMENT '成功生成候选的企业数',
  `failed_company_count` INT NOT NULL DEFAULT 0 COMMENT '生成失败企业数',
  `summary_json` JSON DEFAULT NULL COMMENT '候选生成摘要',
  `error_message` TEXT DEFAULT NULL COMMENT '批次错误信息',
  `started_at` DATETIME DEFAULT NULL COMMENT '开始时间',
  `finished_at` DATETIME DEFAULT NULL COMMENT '结束时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_tag_llm_batch_id`),
  UNIQUE KEY `uk_company_tag_llm_batch_code` (`batch_code`),
  KEY `idx_company_tag_llm_batch_status_created` (`status`, `created_at`),
  CONSTRAINT `fk_company_tag_llm_batch_dimension`
    FOREIGN KEY (`company_tag_dimension_id`) REFERENCES `company_tag_dimension` (`company_tag_dimension_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签 LLM 候选批次表';

CREATE TABLE `company_tag_llm_candidate` (
  `company_tag_llm_candidate_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业标签 LLM 候选唯一标识',
  `company_tag_llm_batch_id` BIGINT NOT NULL COMMENT '所属 LLM 候选批次',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_tag_id` BIGINT DEFAULT NULL COMMENT '映射到正式标签库的标签 ID，可为空',
  `candidate_type` VARCHAR(32) NOT NULL COMMENT '候选类型（mapped_tag/unmapped_term）',
  `candidate_name` VARCHAR(255) NOT NULL COMMENT '候选标签名称或候选短语',
  `normalized_name` VARCHAR(255) DEFAULT NULL COMMENT '归一化后的标签名称',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '候选状态（pending/unmapped/applied/rejected）',
  `confidence` DECIMAL(3, 2) DEFAULT NULL COMMENT '候选置信度',
  `reason_text` TEXT DEFAULT NULL COMMENT '候选生成原因',
  `evidence_json` JSON DEFAULT NULL COMMENT '候选生成证据快照',
  `prompt_text` MEDIUMTEXT DEFAULT NULL COMMENT '发送给模型的提示词',
  `raw_response` MEDIUMTEXT DEFAULT NULL COMMENT '模型原始响应',
  `response_json` JSON DEFAULT NULL COMMENT '解析后的响应 JSON',
  `created_by_user_id` BIGINT DEFAULT NULL COMMENT '发起用户 ID',
  `reviewed_by_user_id` BIGINT DEFAULT NULL COMMENT '审核用户 ID',
  `reviewed_at` DATETIME DEFAULT NULL COMMENT '审核时间',
  `applied_at` DATETIME DEFAULT NULL COMMENT '采纳落库时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_tag_llm_candidate_id`),
  UNIQUE KEY `uk_company_tag_llm_candidate_batch_name` (`company_tag_llm_batch_id`, `company_id`, `candidate_type`, `candidate_name`),
  KEY `idx_company_tag_llm_candidate_company_status` (`company_id`, `status`),
  KEY `idx_company_tag_llm_candidate_tag_id` (`company_tag_id`),
  CONSTRAINT `fk_company_tag_llm_candidate_batch`
    FOREIGN KEY (`company_tag_llm_batch_id`) REFERENCES `company_tag_llm_batch` (`company_tag_llm_batch_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_company_tag_llm_candidate_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `fk_company_tag_llm_candidate_tag`
    FOREIGN KEY (`company_tag_id`) REFERENCES `company_tag_library` (`company_tag_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签 LLM 场景候选表';

CREATE TABLE `company_tag_auto_rule` (
  `company_tag_auto_rule_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '打标规则唯一标识',
  `company_tag_id` BIGINT NOT NULL COMMENT '企业标签唯一标识',
  `company_tag_auto_rule_type` VARCHAR(255) NOT NULL COMMENT '打标规则类型',
  `rule_definition` JSON DEFAULT NULL COMMENT '规则定义 JSON',
  `is_enabled` TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用规则',
  PRIMARY KEY (`company_tag_auto_rule_id`),
  KEY `idx_company_tag_auto_rule_tag_id` (`company_tag_id`),
  CONSTRAINT `fk_company_tag_auto_rule_tag`
    FOREIGN KEY (`company_tag_id`) REFERENCES `company_tag_library` (`company_tag_id`),
  CONSTRAINT `chk_company_tag_auto_rule_enabled` CHECK (`is_enabled` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签自动打标规则表';

CREATE TABLE `company_tag_dimension_library_map` (
  `company_tag_dimension_library_map_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '标签维度与标签库映射唯一标识',
  `company_tag_dimension_id` BIGINT NOT NULL COMMENT '企业标签维度唯一标识',
  `company_tag_id` BIGINT NOT NULL COMMENT '企业标签唯一标识',
  PRIMARY KEY (`company_tag_dimension_library_map_id`),
  UNIQUE KEY `uk_company_tag_dimension_library_map` (`company_tag_dimension_id`, `company_tag_id`),
  CONSTRAINT `fk_company_tag_dimension_library_map_dimension`
    FOREIGN KEY (`company_tag_dimension_id`) REFERENCES `company_tag_dimension` (`company_tag_dimension_id`),
  CONSTRAINT `fk_company_tag_dimension_library_map_tag`
    FOREIGN KEY (`company_tag_id`) REFERENCES `company_tag_library` (`company_tag_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业标签维度与标签库映射表';

CREATE TABLE `company_basic_count` (
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `branch_count` INT NOT NULL DEFAULT 0 COMMENT '分支机构数量（结构化明细）',
  `branch_count_raw` INT NOT NULL DEFAULT 0 COMMENT '分支机构数量（原始聚合值）',
  `recruit_count` INT NOT NULL DEFAULT 0 COMMENT '招聘信息数量（结构化明细）',
  `recruit_count_raw` INT NOT NULL DEFAULT 0 COMMENT '招聘信息数量（原始聚合值）',
  `software_copyright_count` INT NOT NULL DEFAULT 0 COMMENT '软件著作权数量（结构化明细）',
  `software_copyright_count_raw` INT NOT NULL DEFAULT 0 COMMENT '软件著作权数量（原始聚合值）',
  `work_copyright_count` INT NOT NULL DEFAULT 0 COMMENT '作品著作权数量（结构化明细）',
  `work_copyright_count_raw` INT NOT NULL DEFAULT 0 COMMENT '作品著作权数量（原始聚合值）',
  `patent_count` INT NOT NULL DEFAULT 0 COMMENT '专利数量（结构化明细）',
  `patent_count_raw` INT NOT NULL DEFAULT 0 COMMENT '专利数量（原始聚合值）',
  `trademark_count` INT NOT NULL DEFAULT 0 COMMENT '商标数量',
  `customer_count` INT NOT NULL DEFAULT 0 COMMENT '客户数量（结构化明细）',
  `customer_count_raw` INT NOT NULL DEFAULT 0 COMMENT '客户数量（原始聚合值）',
  `ranking_count` INT NOT NULL DEFAULT 0 COMMENT '上榜榜单数量（结构化明细）',
  `ranking_count_raw` INT NOT NULL DEFAULT 0 COMMENT '上榜榜单数量（原始聚合值）',
  `bidding_count` INT NOT NULL DEFAULT 0 COMMENT '招投标数量（原始聚合值）',
  `legal_doc_case_count` INT NOT NULL DEFAULT 0 COMMENT '法律文书（司法案件）数量',
  `legal_doc_judgement_count` INT NOT NULL DEFAULT 0 COMMENT '法律文书（裁判文书）数量',
  `legal_doc_all_count` INT NOT NULL DEFAULT 0 COMMENT '法律文书（全部）数量',
  `dishonest_execution_count` INT NOT NULL DEFAULT 0 COMMENT '失信被执行数量',
  `chattel_mortgage_count` INT NOT NULL DEFAULT 0 COMMENT '动产抵押数量',
  `business_abnormal_count` INT NOT NULL DEFAULT 0 COMMENT '经营异常数量',
  `admin_penalty_count` INT NOT NULL DEFAULT 0 COMMENT '行政处罚数量',
  `bankruptcy_overlap_count` INT NOT NULL DEFAULT 0 COMMENT '破产重叠数量',
  `liquidation_info_count` INT NOT NULL DEFAULT 0 COMMENT '清算信息数量',
  `env_penalty_count` INT NOT NULL DEFAULT 0 COMMENT '环保处罚数量',
  `equity_freeze_count` INT NOT NULL DEFAULT 0 COMMENT '股权冻结数量',
  `executed_person_count` INT NOT NULL DEFAULT 0 COMMENT '被执行人数量',
  PRIMARY KEY (`company_id`),
  CONSTRAINT `fk_company_basic_count_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业聚合计数表';

CREATE TABLE `company_trademark` (
  `company_trademark_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业商标唯一标识',
  `company_trademark_name` VARCHAR(255) NOT NULL COMMENT '企业商标名称',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_trademark_register_number` VARCHAR(255) NOT NULL COMMENT '企业商标注册号',
  `company_trademark_application_date` DATE DEFAULT NULL COMMENT '企业商标申请日期',
  PRIMARY KEY (`company_trademark_id`),
  UNIQUE KEY `uk_company_trademark_register_number` (`company_trademark_register_number`),
  KEY `idx_company_trademark_company_id` (`company_id`),
  CONSTRAINT `fk_company_trademark_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业商标表';

CREATE TABLE `company_work_copyright` (
  `company_work_copyright_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '作品著作唯一标识',
  `company_work_copyright_name` VARCHAR(255) NOT NULL COMMENT '作品著作名称',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_work_copyright_register_number` VARCHAR(255) NOT NULL COMMENT '作品著作登记号',
  `company_work_copyright_type` VARCHAR(255) DEFAULT NULL COMMENT '作品著作类别',
  `company_work_copyright_publish_date` DATE DEFAULT NULL COMMENT '作品著作首次发布日期',
  `company_work_copyright_register_date` DATE DEFAULT NULL COMMENT '作品著作登记日期',
  `company_work_copyright_status` VARCHAR(255) DEFAULT NULL COMMENT '作品著作状态',
  PRIMARY KEY (`company_work_copyright_id`),
  UNIQUE KEY `uk_company_work_copyright_register_number` (`company_work_copyright_register_number`),
  KEY `idx_company_work_copyright_company_id` (`company_id`),
  CONSTRAINT `fk_company_work_copyright_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业作品著作权表';

CREATE TABLE `company_ranking` (
  `company_ranking_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业榜单唯一标识',
  `company_ranking_name` VARCHAR(255) NOT NULL COMMENT '企业榜单名称',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `company_ranking_type` VARCHAR(255) DEFAULT NULL COMMENT '企业榜单类型',
  `company_ranking_source` VARCHAR(255) DEFAULT NULL COMMENT '企业榜单来源',
  `company_ranking_position` INT DEFAULT NULL COMMENT '榜内位置（数字）',
  `company_ranking_alias` VARCHAR(255) DEFAULT NULL COMMENT '榜内名称',
  `company_ranking_publish_year` INT DEFAULT NULL COMMENT '榜单发布年份',
  PRIMARY KEY (`company_ranking_id`),
  KEY `idx_company_ranking_company_id` (`company_id`),
  CONSTRAINT `fk_company_ranking_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业榜单表';

CREATE TABLE `company_patent_type` (
  `company_patent_type_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '专利类型唯一标识',
  `company_patent_type_name` VARCHAR(255) NOT NULL COMMENT '专利类型名称',
  PRIMARY KEY (`company_patent_type_id`),
  UNIQUE KEY `uk_company_patent_type_name` (`company_patent_type_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='专利类型表';

CREATE TABLE `company_patent_patent_type_map` (
  `company_patent_patent_type_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '映射唯一标识',
  `company_patent_id` BIGINT NOT NULL COMMENT '专利唯一标识',
  `company_patent_type_id` BIGINT NOT NULL COMMENT '专利类型唯一标识',
  PRIMARY KEY (`company_patent_patent_type_id`),
  UNIQUE KEY `uk_company_patent_type_map` (`company_patent_id`, `company_patent_type_id`),
  CONSTRAINT `fk_company_patent_type_map_patent`
    FOREIGN KEY (`company_patent_id`) REFERENCES `company_patent` (`company_patent_id`),
  CONSTRAINT `fk_company_patent_type_map_type`
    FOREIGN KEY (`company_patent_type_id`) REFERENCES `company_patent_type` (`company_patent_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业专利与专利类型映射表';

CREATE TABLE `company_patent_company_map` (
  `company_patent_company_map_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '映射唯一标识',
  `company_patent_id` BIGINT NOT NULL COMMENT '专利唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  PRIMARY KEY (`company_patent_company_map_id`),
  UNIQUE KEY `uk_company_patent_company_map` (`company_patent_id`, `company_id`),
  KEY `idx_company_patent_company_map_company_id` (`company_id`),
  CONSTRAINT `fk_company_patent_company_map_patent`
    FOREIGN KEY (`company_patent_id`) REFERENCES `company_patent` (`company_patent_id`),
  CONSTRAINT `fk_company_patent_company_map_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业与专利映射表';

CREATE TABLE `chain_industry_category_industry_map` (
  `chain_industry_category_industry_map_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '映射唯一标识',
  `chain_id` BIGINT NOT NULL COMMENT '产业链节点唯一标识',
  `category_id` BIGINT NOT NULL COMMENT '行业分类唯一标识',
  PRIMARY KEY (`chain_industry_category_industry_map_id`),
  UNIQUE KEY `uk_chain_industry_category_industry_map` (`chain_id`, `category_id`),
  CONSTRAINT `fk_chain_industry_category_industry_map_chain`
    FOREIGN KEY (`chain_id`) REFERENCES `chain_industry` (`chain_id`),
  CONSTRAINT `fk_chain_industry_category_industry_map_category`
    FOREIGN KEY (`category_id`) REFERENCES `category_industry` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='产业链节点与行业分类映射表';

CREATE TABLE `category_industry_company_map` (
  `category_industry_company_map_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '映射唯一标识',
  `category_id` BIGINT NOT NULL COMMENT '行业分类唯一标识',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  PRIMARY KEY (`category_industry_company_map_id`),
  UNIQUE KEY `uk_category_industry_company_map` (`category_id`, `company_id`),
  CONSTRAINT `fk_category_industry_company_map_category`
    FOREIGN KEY (`category_id`) REFERENCES `category_industry` (`category_id`),
  CONSTRAINT `fk_category_industry_company_map_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='行业分类与企业映射表';

CREATE TABLE `company_customer` (
  `company_customer_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业客户记录唯一标识',
  `company_customer_name` VARCHAR(255) NOT NULL COMMENT '企业客户名称',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `customer_company_id` BIGINT DEFAULT NULL COMMENT '客户企业 ID',
  `company_customer_sales_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '企业客户销售金额（万元）',
  `company_customer_sales_ratio` DECIMAL(5, 2) DEFAULT NULL COMMENT '企业客户销售占比',
  `company_customer_report_date` DATE DEFAULT NULL COMMENT '报告时间',
  PRIMARY KEY (`company_customer_id`),
  KEY `idx_company_customer_company_id` (`company_id`),
  KEY `idx_company_customer_customer_company_id` (`customer_company_id`),
  CONSTRAINT `fk_company_customer_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `fk_company_customer_customer_company`
    FOREIGN KEY (`customer_company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_customer_sales_ratio` CHECK (`company_customer_sales_ratio` IS NULL OR (`company_customer_sales_ratio` >= 0 AND `company_customer_sales_ratio` <= 100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业客户信息表';

CREATE TABLE `company_supplier` (
  `company_supplier_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '企业供应商记录唯一标识',
  `company_supplier_name` VARCHAR(255) NOT NULL COMMENT '企业供应商名称',
  `company_id` BIGINT NOT NULL COMMENT '企业唯一标识',
  `supplier_company_id` BIGINT DEFAULT NULL COMMENT '供应商企业 ID',
  `company_supplier_purchase_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '企业供应商采购金额（万元）',
  `company_supplier_purchase_ratio` DECIMAL(5, 2) DEFAULT NULL COMMENT '企业供应商采购占比',
  `company_supplier_report_date` DATE DEFAULT NULL COMMENT '报告时间',
  PRIMARY KEY (`company_supplier_id`),
  KEY `idx_company_supplier_company_id` (`company_id`),
  KEY `idx_company_supplier_supplier_company_id` (`supplier_company_id`),
  CONSTRAINT `fk_company_supplier_company`
    FOREIGN KEY (`company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `fk_company_supplier_supplier_company`
    FOREIGN KEY (`supplier_company_id`) REFERENCES `company_basic` (`company_id`),
  CONSTRAINT `chk_company_supplier_purchase_ratio` CHECK (`company_supplier_purchase_ratio` IS NULL OR (`company_supplier_purchase_ratio` >= 0 AND `company_supplier_purchase_ratio` <= 100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业供应商信息表';

CREATE TABLE `scoring_scoreresult` (
  `enterprise_id` BIGINT NOT NULL COMMENT '企业 ID',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `total_score` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '总得分',
  `basic_score` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '基础得分',
  `tech_score` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '科技属性得分',
  `professional_score` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '专业能力得分',
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
  PRIMARY KEY (`enterprise_id`),
  CONSTRAINT `fk_scoring_scoreresult_company`
    FOREIGN KEY (`enterprise_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业评分结果表';

CREATE TABLE `score_industry_path` (
  `industry_path` VARCHAR(255) NOT NULL COMMENT '行业路径名称',
  `path_level` SMALLINT DEFAULT NULL COMMENT '几级标签',
  `avg_score` DECIMAL(5, 2) DEFAULT NULL COMMENT '行业平均分',
  `company_count` INT DEFAULT NULL COMMENT '行业包含企业数量',
  PRIMARY KEY (`industry_path`),
  CONSTRAINT `chk_score_industry_path_company_count` CHECK (`company_count` IS NULL OR `company_count` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='行业路径评分统计表';

CREATE TABLE `scoring_scorelog` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '评分日志 ID',
  `enterprise_id` BIGINT NOT NULL COMMENT '企业 ID',
  `enterprise_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `score_type` VARCHAR(20) DEFAULT NULL COMMENT '得分类型',
  `score_value` DECIMAL(5, 2) DEFAULT NULL COMMENT '得分分值',
  `description` LONGTEXT COMMENT '得分依据描述',
  `created_at` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_scoring_scorelog_enterprise_id` (`enterprise_id`),
  CONSTRAINT `fk_scoring_scorelog_company`
    FOREIGN KEY (`enterprise_id`) REFERENCES `company_basic` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业评分日志表';

CREATE TABLE `score_model_total_weight` (
  `model_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '模型 ID',
  `model_name` VARCHAR(100) NOT NULL COMMENT '模型名称',
  `model_weight` DECIMAL(5, 2) NOT NULL COMMENT '模型权重',
  PRIMARY KEY (`model_id`),
  CONSTRAINT `chk_score_model_total_weight_range` CHECK (`model_weight` >= 0 AND `model_weight` <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='总评分模型权重表';

CREATE TABLE `score_model_basic_weight` (
  `model_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '基础评分模型 ID',
  `model_name` VARCHAR(100) NOT NULL COMMENT '基础评分模型名称',
  `established_year` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '成立年限',
  `registered_capital` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '注册资本',
  `actual_paid_capital` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '实缴资本',
  `company_type` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '公司类型',
  `enterprise_size_type` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '企业规模（分型）',
  `social_security_count` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '企业规模（社保人数）',
  `website` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '网址',
  `business_scope` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '经营范围',
  `tax_rating` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '纳税人等级',
  `tax_type` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '纳税人类型',
  `funding_round` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '投融资轮次',
  `patent_type` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '专利类型',
  `software_copyright` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '软件著作权',
  `technology_enterprise` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '科技型企业',
  PRIMARY KEY (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='基础评分模型权重表';

CREATE TABLE `score_model_tech_weight` (
  `model_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '科技属性评分模型 ID',
  `model_name` VARCHAR(100) NOT NULL COMMENT '科技属性评分模型名称',
  `tech_patent_type` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '专利类型',
  `patent_tech_attribute` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '专利科技属性',
  `tech_software_copyright` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '软件著作权',
  `software_copyright_tech_attribute` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '软著科技属性',
  `tech_technology_enterprise` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '科技型企业',
  `industry_university_research` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '产学研合作',
  `national_provincial_award` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '国家/省级奖励',
  PRIMARY KEY (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='科技属性评分模型权重表';

CREATE TABLE `score_model_professional_weight` (
  `model_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '专业能力评分模型 ID',
  `model_name` VARCHAR(100) NOT NULL COMMENT '专业能力评分模型名称',
  `industry_market_size` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '行业市场规模',
  `industry_heat` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '行业热度',
  `industry_profit_margin` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '行业利润率',
  `qualification` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '资质',
  `certificates` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '证书',
  `innovation` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '创新性',
  `partnership_score` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '合作上下游',
  `ranking` DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT '专业榜单入选',
  PRIMARY KEY (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='专业能力评分模型权重表';

CREATE TABLE `user_domains` (
  `domain_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '领域表 领域 ID 唯一标识',
  `domain_name` VARCHAR(50) NOT NULL COMMENT '领域名称',
  `domain_description` LONGTEXT COMMENT '领域描述',
  `created_at` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
  PRIMARY KEY (`domain_id`),
  UNIQUE KEY `uk_user_domains_name` (`domain_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户领域表';

CREATE TABLE `users` (
  `user_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户表 用户 ID 唯一标识',
  `user_name` VARCHAR(100) NOT NULL COMMENT '用户名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希值',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '联系方式（手机号）',
  `organization` VARCHAR(100) DEFAULT NULL COMMENT '单位',
  `position` VARCHAR(100) DEFAULT NULL COMMENT '职务',
  `user_nickname` VARCHAR(255) DEFAULT NULL COMMENT '用户显示昵称',
  `user_avatar` VARCHAR(255) DEFAULT NULL COMMENT '头像（文件 URL）',
  `user_type` TINYINT DEFAULT NULL COMMENT '所属领域（1:数字医疗，2:康养）',
  `is_superuser` TINYINT NOT NULL DEFAULT 0 COMMENT '是否为管理员（1:是，0:否）',
  `user_role` VARCHAR(255) DEFAULT NULL COMMENT '用户角色',
  `date_joined` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  `last_login_time` DATETIME DEFAULT NULL COMMENT '上次登录时间',
  `last_login_ip` VARCHAR(255) DEFAULT NULL COMMENT '上次登录 IP',
  `password_update_time` DATETIME DEFAULT NULL COMMENT '上次修改密码时间',
  `user_real_name` VARCHAR(255) DEFAULT NULL COMMENT '用户真实姓名',
  `org_name` VARCHAR(255) DEFAULT NULL COMMENT '用户所属组织名称',
  `org_id` VARCHAR(255) DEFAULT NULL COMMENT '用户所属组织 ID',
  `dept_name` VARCHAR(255) DEFAULT NULL COMMENT '用户所属部门名称',
  `dept_id` VARCHAR(255) DEFAULT NULL COMMENT '用户所属部门 ID',
  `user_status` TINYINT NOT NULL DEFAULT 2 COMMENT '用户状态（0:禁用，1:正常，2:待审核）',
  `domain_id` BIGINT DEFAULT NULL COMMENT '所属领域 ID',
  `registered_at` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '注册时间',
  `last_login_at` DATETIME(6) DEFAULT NULL COMMENT '最后登录时间',
  `updated_at` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_users_user_name` (`user_name`),
  UNIQUE KEY `uk_users_email` (`email`),
  UNIQUE KEY `uk_users_phone` (`phone`),
  KEY `idx_users_org_id` (`org_id`),
  KEY `idx_users_dept_id` (`dept_id`),
  CONSTRAINT `chk_users_is_superuser` CHECK (`is_superuser` IN (0, 1)),
  CONSTRAINT `chk_users_user_type` CHECK (`user_type` IS NULL OR `user_type` IN (1, 2)),
  CONSTRAINT `chk_users_status` CHECK (`user_status` IN (0, 1, 2)),
  CONSTRAINT `fk_users_domain`
    FOREIGN KEY (`domain_id`) REFERENCES `user_domains` (`domain_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='统一用户认证与资料表';

CREATE TABLE `user_dinvite_codes` (
  `invite_code` VARCHAR(50) NOT NULL COMMENT '邀请码',
  `is_used` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '使用状态：0-未使用，1-已使用',
  `created_at` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
  PRIMARY KEY (`invite_code`),
  CONSTRAINT `chk_user_dinvite_codes_used` CHECK (`is_used` IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邀请码表';

CREATE TABLE `user_roles` (
  `role_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '权限表 权限 ID 唯一标识',
  `role_name` VARCHAR(30) NOT NULL COMMENT '权限名称',
  `role_description` LONGTEXT COMMENT '权限描述',
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `uk_user_roles_role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色表';

CREATE TABLE `user_and_roles` (
  `association_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户权限关联表 关联 ID 唯一标识',
  `user_id` BIGINT NOT NULL COMMENT '用户 ID',
  `role_id` BIGINT NOT NULL COMMENT '权限 ID',
  `assigned_at` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '授权时间',
  PRIMARY KEY (`association_id`),
  UNIQUE KEY `uk_user_and_roles` (`user_id`, `role_id`),
  CONSTRAINT `fk_user_and_roles_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_user_and_roles_role`
    FOREIGN KEY (`role_id`) REFERENCES `user_roles` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户权限关联表';

CREATE TABLE `user_operation_logs` (
  `log_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '操作日志表 日志 ID 唯一标识',
  `user_id` BIGINT NOT NULL COMMENT '用户 ID',
  `operation_time` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '操作时间',
  `action` VARCHAR(50) NOT NULL COMMENT '操作内容',
  PRIMARY KEY (`log_id`),
  KEY `idx_user_operation_logs_user_id` (`user_id`),
  CONSTRAINT `fk_user_operation_logs_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户操作日志表';

ALTER TABLE `rag_chat_session`
  ADD CONSTRAINT `fk_rag_chat_session_user`
  FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
  ON DELETE CASCADE;

SET FOREIGN_KEY_CHECKS = 1;
