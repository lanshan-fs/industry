SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

USE `industrial_chain`;

CREATE TABLE IF NOT EXISTS `raw_import_company_basic` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `credit_code` VARCHAR(64) DEFAULT NULL COMMENT '统一社会信用代码',
  `establish_info` VARCHAR(64) DEFAULT NULL COMMENT '成立年限/成立日期原值',
  `register_capital_raw` VARCHAR(255) DEFAULT NULL COMMENT '注册资本原值',
  `paid_capital_raw` VARCHAR(255) DEFAULT NULL COMMENT '实缴资本原值',
  `company_type_raw` VARCHAR(255) DEFAULT NULL COMMENT '企业类型原值',
  `org_type_raw` VARCHAR(255) DEFAULT NULL COMMENT '组织类型原值',
  `investment_type_raw` VARCHAR(255) DEFAULT NULL COMMENT '投资类型原值',
  `company_scale_raw` VARCHAR(255) DEFAULT NULL COMMENT '企业规模原值',
  `branch_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '分支机构数量原值',
  `branch_names_raw` TEXT COMMENT '分支机构名称原值',
  `address_info_raw` TEXT COMMENT '地址信息原值',
  `financing_round_raw` VARCHAR(255) DEFAULT NULL COMMENT '投融资轮次原值',
  `qualification_raw` TEXT COMMENT '企业资质原值',
  `legal_representative` VARCHAR(255) DEFAULT NULL COMMENT '法定代表人',
  `register_number` VARCHAR(64) DEFAULT NULL COMMENT '注册号',
  `org_code` VARCHAR(64) DEFAULT NULL COMMENT '组织机构代码',
  `industry_name_raw` VARCHAR(255) DEFAULT NULL COMMENT '所属行业原值',
  `business_scope_raw` LONGTEXT COMMENT '经营范围原值',
  `email_business` VARCHAR(255) DEFAULT NULL COMMENT '邮箱（工商信息）',
  `email_auth` VARCHAR(255) DEFAULT NULL COMMENT '邮箱（企业认证信息）',
  `shareholder_raw` LONGTEXT COMMENT '股东原值',
  `contact_phone_1` VARCHAR(255) DEFAULT NULL COMMENT '联系电话',
  `contact_phone_2` VARCHAR(255) DEFAULT NULL COMMENT '联系电话2',
  `contact_phone_3` VARCHAR(255) DEFAULT NULL COMMENT '联系电话3',
  `contact_phone_4` VARCHAR(255) DEFAULT NULL COMMENT '联系电话4',
  `contact_phone_5` VARCHAR(255) DEFAULT NULL COMMENT '联系电话5',
  `recommended_phone` VARCHAR(255) DEFAULT NULL COMMENT '推荐电话',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_basic_company_name` (`company_name`),
  KEY `idx_raw_import_company_basic_credit_code` (`credit_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-企业基本信息';

CREATE TABLE IF NOT EXISTS `raw_import_company_operation` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `employee_count_raw` VARCHAR(255) DEFAULT NULL COMMENT '员工人数原值',
  `insured_count_raw` VARCHAR(255) DEFAULT NULL COMMENT '社保人数原值',
  `listing_status_raw` VARCHAR(255) DEFAULT NULL COMMENT '上市状态原值',
  `national_industry_raw` VARCHAR(255) DEFAULT NULL COMMENT '国标行业原值',
  `contact_info_raw` VARCHAR(255) DEFAULT NULL COMMENT '联系方式原值',
  `same_phone_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '同企业电话原值',
  `email_business` VARCHAR(255) DEFAULT NULL COMMENT '邮箱（工商信息）',
  `is_micro_enterprise_raw` VARCHAR(64) DEFAULT NULL COMMENT '是否小微企业原值',
  `changed_info_raw` VARCHAR(64) DEFAULT NULL COMMENT '是否有变更信息原值',
  `is_general_taxpayer_raw` VARCHAR(64) DEFAULT NULL COMMENT '是否为一般纳税人原值',
  `has_financing_info_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无融资信息原值',
  `has_bidding_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无招投标原值',
  `bidding_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '招投标数量原值',
  `has_recruitment_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无招聘原值',
  `recruit_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '招聘信息数量原值',
  `has_customer_info_raw` VARCHAR(64) DEFAULT NULL COMMENT '是否有客户信息原值',
  `customer_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '客户数量原值',
  `has_ranking_raw` VARCHAR(64) DEFAULT NULL COMMENT '是否有上榜榜单原值',
  `ranking_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '上榜榜单数量原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_operation_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-企业经营信息';

CREATE TABLE IF NOT EXISTS `raw_import_company_ip_overview` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `has_work_copyright_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无作品著作原值',
  `work_copyright_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '作品著作权数量原值',
  `has_software_copyright_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无软件著作原值',
  `software_copyright_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '软件著作权数量原值',
  `is_high_tech_enterprise_raw` VARCHAR(64) DEFAULT NULL COMMENT '高新技术企业原值',
  `is_srdi_sme_raw` VARCHAR(64) DEFAULT NULL COMMENT '专精特新中小企业原值',
  `is_gazelle_company_raw` VARCHAR(64) DEFAULT NULL COMMENT '瞪羚企业原值',
  `is_tech_sme_raw` VARCHAR(64) DEFAULT NULL COMMENT '科技型中小企业原值',
  `is_egalet_company_raw` VARCHAR(64) DEFAULT NULL COMMENT '雏鹰企业原值',
  `is_srdi_little_giant_raw` VARCHAR(64) DEFAULT NULL COMMENT '专精特新小巨人原值',
  `is_innovative_sme_raw` VARCHAR(64) DEFAULT NULL COMMENT '创新型中小企业原值',
  `has_patent_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无专利原值',
  `patent_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '专利数量原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_ip_overview_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-知识产权';

CREATE TABLE IF NOT EXISTS `raw_import_software_copyright` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '著作权人/企业名称',
  `software_name` VARCHAR(255) DEFAULT NULL COMMENT '软件名称',
  `register_number` VARCHAR(255) DEFAULT NULL COMMENT '登记号',
  `software_short_name` VARCHAR(255) DEFAULT NULL COMMENT '软件简称',
  `register_date_raw` VARCHAR(64) DEFAULT NULL COMMENT '登记批准日期原值',
  `status_raw` VARCHAR(255) DEFAULT NULL COMMENT '状态原值',
  `obtain_method_raw` VARCHAR(255) DEFAULT NULL COMMENT '取得方式原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_software_copyright_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-软件著作权';

CREATE TABLE IF NOT EXISTS `raw_import_company_ranking` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `ranking_name` VARCHAR(255) DEFAULT NULL COMMENT '榜单名称',
  `ranking_type` VARCHAR(255) DEFAULT NULL COMMENT '榜单类型',
  `ranking_source` VARCHAR(255) DEFAULT NULL COMMENT '来源',
  `ranking_position_raw` VARCHAR(255) DEFAULT NULL COMMENT '榜内位置原值',
  `ranking_alias` VARCHAR(255) DEFAULT NULL COMMENT '榜内名称',
  `publish_year_raw` VARCHAR(64) DEFAULT NULL COMMENT '发布年份原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_ranking_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-上榜榜单信息';

CREATE TABLE IF NOT EXISTS `raw_import_company_customer` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '公司名称',
  `customer_name` TEXT COMMENT '客户名称',
  `sales_ratio_raw` VARCHAR(255) DEFAULT NULL COMMENT '销售占比原值',
  `sales_amount_raw` VARCHAR(255) DEFAULT NULL COMMENT '销售金额原值',
  `report_period_raw` VARCHAR(64) DEFAULT NULL COMMENT '报告期原值',
  `data_source` VARCHAR(255) DEFAULT NULL COMMENT '数据来源',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_customer_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-客户信息';

CREATE TABLE IF NOT EXISTS `raw_import_company_work_copyright` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `work_name` VARCHAR(255) DEFAULT NULL COMMENT '作品名称',
  `register_number` VARCHAR(255) DEFAULT NULL COMMENT '登记号',
  `work_type_raw` VARCHAR(255) DEFAULT NULL COMMENT '类别原值',
  `first_publish_date_raw` VARCHAR(64) DEFAULT NULL COMMENT '首次发布日期原值',
  `register_date_raw` VARCHAR(64) DEFAULT NULL COMMENT '登记日期原值',
  `status_raw` VARCHAR(255) DEFAULT NULL COMMENT '状态原值',
  `author_raw` VARCHAR(255) DEFAULT NULL COMMENT '作者原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_work_copyright_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-作品著作权';

CREATE TABLE IF NOT EXISTS `raw_import_company_patent` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '申请人/企业名称',
  `patent_number` VARCHAR(255) DEFAULT NULL COMMENT '专利号',
  `patent_name` VARCHAR(255) DEFAULT NULL COMMENT '专利名称',
  `patent_type_raw` VARCHAR(255) DEFAULT NULL COMMENT '专利类型原值',
  `application_date_raw` VARCHAR(64) DEFAULT NULL COMMENT '申请日原值',
  `auth_publish_date_raw` VARCHAR(64) DEFAULT NULL COMMENT '申请公布日原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_patent_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-专利信息';

CREATE TABLE IF NOT EXISTS `raw_import_company_risk` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `source_row_no` INT DEFAULT NULL COMMENT '原始行号',
  `legal_doc_case_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '法律文书_司法案件数量原值',
  `legal_doc_judgement_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '法律文书_裁判文书原值',
  `has_legal_document_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无法律文书原值',
  `legal_doc_total_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '法律文书_合计原值',
  `has_dishonest_execution_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无失信被执行原值',
  `dishonest_execution_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '失信被执行原值',
  `has_chattel_mortgage_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无动产抵押原值',
  `chattel_mortgage_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '动产抵押数量原值',
  `has_business_abnormal_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无经营异常原值',
  `business_abnormal_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '经营异常数量原值',
  `has_admin_penalty_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无行政处罚原值',
  `admin_penalty_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '行政处罚原值',
  `has_bankruptcy_overlap_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无破产重叠原值',
  `bankruptcy_overlap_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '破产重叠原值',
  `has_liquidation_info_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无清算信息原值',
  `liquidation_info_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '清算信息原值',
  `has_env_penalty_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无环保处罚原值',
  `env_penalty_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '环保处罚原值',
  `has_equity_freeze_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无股权冻结原值',
  `equity_freeze_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '股权冻结原值',
  `has_executed_person_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无被执行人原值',
  `executed_person_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '被执行人原值',
  `has_consumption_restriction_raw` VARCHAR(64) DEFAULT NULL COMMENT '有无限制高消费原值',
  `consumption_restriction_count_raw` VARCHAR(64) DEFAULT NULL COMMENT '限制高消费原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_risk_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-经营风险';

CREATE TABLE IF NOT EXISTS `raw_import_company_subdistrict` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '企业名称',
  `street_name` VARCHAR(255) DEFAULT NULL COMMENT '街道',
  `region_name` VARCHAR(255) DEFAULT NULL COMMENT '地区',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_subdistrict_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-街道信息';

CREATE TABLE IF NOT EXISTS `raw_import_company_recruit` (
  `raw_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '原始导入记录 ID',
  `sheet_row_no` INT DEFAULT NULL COMMENT 'Excel 行号/序号',
  `company_name` VARCHAR(255) DEFAULT NULL COMMENT '公司',
  `position_name` VARCHAR(255) DEFAULT NULL COMMENT '职位',
  `salary_raw` VARCHAR(255) DEFAULT NULL COMMENT '薪资原值',
  `work_year_raw` VARCHAR(255) DEFAULT NULL COMMENT '工作年限原值',
  `work_place` VARCHAR(255) DEFAULT NULL COMMENT '工作地点',
  `edu_req_raw` VARCHAR(255) DEFAULT NULL COMMENT '学历原值',
  `recruit_time_raw` VARCHAR(64) DEFAULT NULL COMMENT '招聘时间原值',
  PRIMARY KEY (`raw_id`),
  KEY `idx_raw_import_company_recruit_company_name` (`company_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Excel 原始导入表-招聘信息';

SET FOREIGN_KEY_CHECKS = 1;
