# 企业数据管理导入模板说明

说明：
- `company_basic.csv` 对应企业主表导入模板。
- 其余 `company_*.csv` 对应企业数据管理子表模板，字段名与 Django 企业数据管理导入口径保持一致。
- CSV 文件均为 `UTF-8 with BOM` 编码，建议直接用 Excel/WPS 打开整理后再保存。
- 只有模板中的列可以直接导入；系统主键、自增字段、审计字段未写入模板。

## company_address

- 中文名称：企业地址信息表
- 模板文件：`company_address.csv`
- 必填字段：企业唯一标识, 企业地址
- 可导入字段数：7

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 地址类型 | `address_type` | `varchar(64)` | 否 | 地址类型 |
| 企业地址 | `address_text` | `varchar(255)` | 是 | 企业地址 |
| 省 | `province` | `varchar(255)` | 否 | 省 |
| 市 | `city` | `varchar(255)` | 否 | 市 |
| 区县 | `district` | `varchar(255)` | 否 | 区县 |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |

## company_ai_model_filing

- 中文名称：企业算法备案医疗大模型表
- 模板文件：`company_ai_model_filing.csv`
- 必填字段：企业唯一标识, 模型名称
- 可导入字段数：10

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业名称原值 | `company_name_raw` | `varchar(255)` | 否 | 企业名称原值 |
| 模型名称 | `model_name` | `varchar(255)` | 是 | 模型名称 |
| 备案编号 | `filing_no` | `varchar(255)` | 否 | 备案编号 |
| 备案类型 | `filing_type` | `varchar(64)` | 否 | 备案类型 |
| 属地 | `territory` | `varchar(255)` | 否 | 属地 |
| 备案时间 | `filed_at` | `date` | 否 | 备案时间 |
| 时期原值 | `source_period_raw` | `varchar(64)` | 否 | 时期原值 |
| 来源文件 | `source_file` | `varchar(255)` | 否 | 来源文件 |
| 来源工作表 | `source_sheet` | `varchar(128)` | 否 | 来源工作表 |

## company_basic

- 中文名称：企业基础信息表
- 模板文件：`company_basic.csv`
- 必填字段：统一社会信用代码
- 可导入字段数：79

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业名称 | `company_name` | `varchar(255)` | 否 | 企业名称 |
| 企业英文名称 | `company_name_en` | `varchar(255)` | 否 | 企业英文名称 |
| 企业曾用名（最新） | `former_name_latest` | `varchar(255)` | 否 | 企业曾用名（最新） |
| 统一社会信用代码 | `credit_code` | `char(18)` | 是 | 统一社会信用代码 |
| 法定代表人 | `legal_representative` | `varchar(255)` | 否 | 法定代表人 |
| 注册号（工商注册号，旧版企业登记编号） | `register_number` | `char(15)` | 否 | 注册号（工商注册号，旧版企业登记编号） |
| 核准日期（工商信息最后核准更新日期） | `approved_date` | `date` | 否 | 核准日期（工商信息最后核准更新日期） |
| 组织机构代码 | `org_code` | `char(9)` | 否 | 组织机构代码 |
| 成立日期 | `establish_date` | `date` | 否 | 成立日期 |
| 经营期限 | `business_term` | `varchar(255)` | 否 | 经营期限 |
| 经营范围 | `business_scope` | `text` | 否 | 经营范围 |
| 经营状态 | `company_status` | `varchar(255)` | 否 | 经营状态 |
| 企业邮箱（工商信息） | `email_business` | `varchar(255)` | 否 | 企业邮箱（工商信息） |
| 企业邮箱（认证） | `email_auth` | `varchar(255)` | 否 | 企业邮箱（认证） |
| 企业网站 URL | `website` | `varchar(255)` | 否 | 企业网站 URL |
| 联系电话 | `contact_phone` | `varchar(255)` | 否 | 联系电话 |
| 联系方式 | `contact_info` | `varchar(255)` | 否 | 联系方式 |
| 推荐电话 | `recommended_phone` | `varchar(255)` | 否 | 推荐电话 |
| 股东（最新） | `latest_shareholder_name` | `varchar(255)` | 否 | 股东（最新） |
| 注册地（省） | `register_sheng` | `varchar(255)` | 否 | 注册地（省） |
| 注册地（市） | `register_shi` | `varchar(255)` | 否 | 注册地（市） |
| 注册地（区县） | `register_xian` | `varchar(255)` | 否 | 注册地（区县） |
| 所属街道/地区 | `subdistrict` | `varchar(255)` | 否 | 所属街道/地区 |
| 注册资本（万元） | `register_capital` | `decimal(18,4)` | 否 | 注册资本（万元） |
| 实缴资本（万元） | `paid_capital` | `decimal(18,4)` | 否 | 实缴资本（万元） |
| 企业类型 | `company_type` | `varchar(255)` | 否 | 企业类型 |
| 组织类型（暂时保留） | `org_type` | `varchar(255)` | 否 | 组织类型（暂时保留） |
| 投资类型 | `investment_type` | `varchar(255)` | 否 | 投资类型 |
| 企业规模 | `company_scale` | `varchar(255)` | 否 | 企业规模 |
| 员工人数（最新） | `employee_count` | `int` | 否 | 员工人数（最新） |
| 参保人数 | `insured_count` | `int` | 否 | 参保人数 |
| 所属行业（国标） | `industry_belong` | `varchar(255)` | 否 | 所属行业（国标） |
| 所属行业代码（国标） | `industry_belong_code` | `varchar(255)` | 否 | 所属行业代码（国标） |
| 是否为分支机构（1:是，0:否） | `is_branch` | `tinyint` | 否 | 是否为分支机构（1:是，0:否） |
| 分支机构唯一标识 | `branch_id` | `bigint` | 否 | 分支机构唯一标识 |
| 分支机构名称（最新） | `branch_name` | `varchar(255)` | 否 | 分支机构名称（最新） |
| 企业地址（工商信息） | `register_address` | `varchar(255)` | 否 | 企业地址（工商信息） |
| 企业地址（详细，最新） | `register_address_detail` | `varchar(255)` | 否 | 企业地址（详细，最新） |
| 企业资质/企业科技属性（最新） | `qualification_label` | `varchar(255)` | 否 | 企业资质/企业科技属性（最新） |
| 是否为一般纳税人（1:是，0:否） | `is_general_taxpayer` | `tinyint` | 否 | 是否为一般纳税人（1:是，0:否） |
| 纳税人资质 | `taxpayer_qualifications` | `varchar(255)` | 否 | 纳税人资质 |
| 纳税人信用等级：ABCDM | `taxpayer_credit_rating` | `varchar(16)` | 否 | 纳税人信用等级：ABCDM |
| 投融资轮次（最新） | `financing_round` | `varchar(255)` | 否 | 投融资轮次（最新） |
| 投融资轮次核准时间（最新） | `financing_round_verify_time` | `date` | 否 | 投融资轮次核准时间（最新） |
| 投融资轮次信息（最新） | `financing_info` | `varchar(255)` | 否 | 投融资轮次信息（最新） |
| 股票代码 | `stock_code` | `varchar(32)` | 否 | 股票代码 |
| 所属领域（1:数字医疗，2:康养） | `field_belong` | `tinyint` | 否 | 所属领域（1:数字医疗，2:康养） |
| 是否为高新技术企业（1:是，0:否） | `is_high_tech_enterprise` | `tinyint` | 否 | 是否为高新技术企业（1:是，0:否） |
| 高新技术企业认证日期 | `is_high_tech_enterprise_verify_time` | `date` | 否 | 高新技术企业认证日期 |
| 是否为小微企业（1:是，0:否） | `is_micro_enterprise` | `tinyint` | 否 | 是否为小微企业（1:是，0:否） |
| 是否有变更信息（1:是，0:否） | `has_changed_info` | `tinyint` | 否 | 是否有变更信息（1:是，0:否） |
| 是否有招投标信息（1:是，0:否） | `has_bidding` | `tinyint` | 否 | 是否有招投标信息（1:是，0:否） |
| 是否有招聘信息（1:是，0:否） | `has_recruitment` | `tinyint` | 否 | 是否有招聘信息（1:是，0:否） |
| 产业链环节（1:上游，2:中游，3:下游） | `industry_chain_link` | `tinyint` | 否 | 产业链环节（1:上游，2:中游，3:下游） |
| 有无软件著作权 | `has_software_copyright` | `tinyint` | 否 | 有无软件著作权 |
| 有无作品著作权 | `has_work_copyright` | `tinyint` | 否 | 有无作品著作权 |
| 上市状态（2:终止上市，1:正常上市，0:未上市） | `listing_status` | `tinyint` | 否 | 上市状态（2:终止上市，1:正常上市，0:未上市） |
| 同企业电话数量 | `same_phone_company_count` | `int` | 否 | 同企业电话数量 |
| 是否为专精特新中小企业 | `is_srdi_sme` | `tinyint` | 否 | 是否为专精特新中小企业 |
| 是否为瞪羚企业 | `is_gazelle_company` | `tinyint` | 否 | 是否为瞪羚企业 |
| 是否为科技型中小企业 | `is_tech_sme` | `tinyint` | 否 | 是否为科技型中小企业 |
| 是否为雏鹰企业 | `is_egalet_company` | `tinyint` | 否 | 是否为雏鹰企业 |
| 是否为专精特新小巨人 | `is_srdi_little_giant` | `tinyint` | 否 | 是否为专精特新小巨人 |
| 是否为创新型中小企业 | `is_innovative_sme` | `tinyint` | 否 | 是否为创新型中小企业 |
| 有无专利 | `has_patent` | `tinyint` | 否 | 有无专利 |
| 有无商标 | `has_trademark` | `tinyint` | 否 | 有无商标 |
| 有无法律文书 | `has_legal_document` | `tinyint` | 否 | 有无法律文书 |
| 有无失信被执行 | `has_dishonest_execution` | `tinyint` | 否 | 有无失信被执行 |
| 有无动产抵押 | `has_chattel_mortgage` | `tinyint` | 否 | 有无动产抵押 |
| 有无经营异常 | `has_business_abnormal` | `tinyint` | 否 | 有无经营异常 |
| 有无行政处罚 | `has_admin_penalty` | `tinyint` | 否 | 有无行政处罚 |
| 有无破产重叠 | `has_bankruptcy_overlap` | `tinyint` | 否 | 有无破产重叠 |
| 有无清算信息 | `has_liquidation_info` | `tinyint` | 否 | 有无清算信息 |
| 有无环保处罚 | `has_env_penalty` | `tinyint` | 否 | 有无环保处罚 |
| 有无股权冻结 | `has_equity_freeze` | `tinyint` | 否 | 有无股权冻结 |
| 有无被执行人 | `has_executed_person` | `tinyint` | 否 | 有无被执行人 |
| 有无限制高消费 | `has_consumption_restriction` | `tinyint` | 否 | 有无限制高消费 |
| 限制高消费数量 | `consumption_restriction_count` | `int` | 否 | 限制高消费数量 |
| 是否是朝阳区企业 | `is_chaoyang_company` | `tinyint` | 否 | 是否是朝阳区企业 |

## company_bidding

- 中文名称：企业招投标信息表
- 模板文件：`company_bidding.csv`
- 必填字段：企业唯一标识
- 可导入字段数：5

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 招投标项目名称 | `bidding_title` | `varchar(255)` | 否 | 招投标项目名称 |
| 企业角色 | `bidding_role` | `varchar(64)` | 否 | 企业角色 |
| 发布日期 | `publish_date` | `date` | 否 | 发布日期 |
| 招投标金额（万元） | `bidding_amount` | `decimal(18,4)` | 否 | 招投标金额（万元） |

## company_branch

- 中文名称：企业分支机构表
- 模板文件：`company_branch.csv`
- 必填字段：企业唯一标识, 企业分支机构名称
- 可导入字段数：9

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业分支机构名称 | `company_branch_name` | `varchar(255)` | 是 | 企业分支机构名称 |
| 企业分支机构（注册）地址 | `company_branch_address` | `varchar(255)` | 否 | 企业分支机构（注册）地址 |
| 企业分支机构地区原始文本 | `company_branch_region` | `varchar(255)` | 否 | 企业分支机构地区原始文本 |
| 企业分支机构状态文本（如存续、注销、吊销） | `company_branch_status` | `varchar(64)` | 否 | 企业分支机构状态文本（如存续、注销、吊销） |
| 企业分支机构成立日期 | `company_branch_establish_date` | `date` | 否 | 企业分支机构成立日期 |
| 企业分支机构法定代表人 | `company_branch_legal_representative` | `varchar(255)` | 否 | 企业分支机构法定代表人 |
| 企业分支机构经营范围 | `company_branch_business_scope` | `text` | 否 | 企业分支机构经营范围 |
| 企业分支机构纳税人信用等级 | `company_branch_taxpayer_credit_rating` | `varchar(16)` | 否 | 企业分支机构纳税人信用等级 |

## company_change

- 中文名称：企业变更信息表
- 模板文件：`company_change.csv`
- 必填字段：企业唯一标识, 变更事项
- 可导入字段数：5

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 变更事项 | `change_item` | `varchar(255)` | 是 | 变更事项 |
| 变更前内容 | `before_change` | `text` | 否 | 变更前内容 |
| 变更后内容 | `after_change` | `text` | 否 | 变更后内容 |
| 变更日期 | `change_date` | `date` | 否 | 变更日期 |

## company_consumption_restriction

- 中文名称：限制高消费表
- 模板文件：`company_consumption_restriction.csv`
- 必填字段：企业唯一标识
- 可导入字段数：5

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 案号 | `case_no` | `varchar(255)` | 否 | 案号 |
| 限制对象 | `restricted_subject` | `varchar(255)` | 否 | 限制对象 |
| 立案日期 | `filing_date` | `date` | 否 | 立案日期 |
| 发布日期 | `publish_date` | `date` | 否 | 发布日期 |

## company_contact_info

- 中文名称：企业联系方式表
- 模板文件：`company_contact_info.csv`
- 必填字段：企业唯一标识, 联系方式
- 可导入字段数：4

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 联系方式 | `contact_info` | `varchar(255)` | 是 | 联系方式 |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |
| 抓取/核准时间 | `captured_at` | `datetime` | 否 | 抓取/核准时间 |

## company_contact_phone

- 中文名称：企业联系电话表
- 模板文件：`company_contact_phone.csv`
- 必填字段：企业唯一标识, 联系电话
- 可导入字段数：4

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 联系电话 | `contact_phone` | `varchar(255)` | 是 | 联系电话 |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |
| 抓取/核准时间 | `captured_at` | `datetime` | 否 | 抓取/核准时间 |

## company_customer

- 中文名称：企业客户信息表
- 模板文件：`company_customer.csv`
- 必填字段：企业客户名称, 企业唯一标识
- 可导入字段数：7

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业客户名称 | `company_customer_name` | `varchar(255)` | 是 | 企业客户名称 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 客户企业 ID | `customer_company_id` | `bigint` | 否 | 客户企业 ID |
| 企业客户销售金额（万元） | `company_customer_sales_amount` | `decimal(20,2)` | 否 | 企业客户销售金额（万元） |
| 企业客户销售占比 | `company_customer_sales_ratio` | `decimal(5,2)` | 否 | 企业客户销售占比 |
| 报告时间 | `company_customer_report_date` | `date` | 否 | 报告时间 |
| 数据来源 | `data_source` | `varchar(255)` | 否 | 数据来源 |

## company_employee_count

- 中文名称：企业员工人数表
- 模板文件：`company_employee_count.csv`
- 必填字段：企业唯一标识, 统计年份, 员工人数
- 可导入字段数：3

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 统计年份 | `stat_year` | `smallint` | 是 | 统计年份 |
| 员工人数 | `employee_count` | `int` | 是 | 员工人数 |

## company_financing

- 中文名称：企业投融资轮次信息表
- 模板文件：`company_financing.csv`
- 必填字段：企业唯一标识, 投融资轮次
- 可导入字段数：6

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 投融资轮次 | `financing_round` | `varchar(255)` | 是 | 投融资轮次 |
| 核准时间 | `verify_time` | `date` | 否 | 核准时间 |
| 融资金额（万元） | `financing_amount` | `decimal(18,4)` | 否 | 融资金额（万元） |
| 投资方名称 | `investor_name` | `varchar(255)` | 否 | 投资方名称 |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |

## company_former_name

- 中文名称：企业曾用名表
- 模板文件：`company_former_name.csv`
- 必填字段：企业唯一标识, 企业曾用名
- 可导入字段数：5

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业曾用名 | `former_name` | `varchar(255)` | 是 | 企业曾用名 |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |
| 生效时间 | `effective_date` | `date` | 否 | 生效时间 |
| 排序序号 | `sort_order` | `int` | 否 | 排序序号 |

## company_high_quality_dataset

- 中文名称：企业高质量数据集表
- 模板文件：`company_high_quality_dataset.csv`
- 必填字段：企业唯一标识, 案例/数据集名称
- 可导入字段数：8

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业名称原值 | `company_name_raw` | `varchar(255)` | 否 | 企业名称原值 |
| 案例/数据集名称 | `dataset_name` | `varchar(255)` | 是 | 案例/数据集名称 |
| 申报单位原值 | `applicant_unit_raw` | `text` | 否 | 申报单位原值 |
| 推荐单位 | `recommender_unit` | `varchar(255)` | 否 | 推荐单位 |
| 公布日期 | `announced_at` | `date` | 否 | 公布日期 |
| 来源文件 | `source_file` | `varchar(255)` | 否 | 来源文件 |
| 来源工作表 | `source_sheet` | `varchar(128)` | 否 | 来源工作表 |

## company_innovation_notice

- 中文名称：企业创新性公示表
- 模板文件：`company_innovation_notice.csv`
- 必填字段：企业唯一标识, 公示类型
- 可导入字段数：14

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业名称原值 | `company_name_raw` | `varchar(255)` | 否 | 企业名称原值 |
| 公示类型 | `notice_type` | `varchar(64)` | 是 | 公示类型 |
| 公示标题 | `notice_title` | `varchar(255)` | 否 | 公示标题 |
| 公示类别 | `notice_category` | `varchar(255)` | 否 | 公示类别 |
| 产品/事项名称 | `product_name` | `varchar(255)` | 否 | 产品/事项名称 |
| 注册证号/登记号 | `reg_no` | `varchar(255)` | 否 | 注册证号/登记号 |
| 受理号 | `acceptance_no` | `varchar(255)` | 否 | 受理号 |
| 所有者名称 | `owner_name` | `varchar(255)` | 否 | 所有者名称 |
| 公示日期 | `public_date` | `date` | 否 | 公示日期 |
| 公示截止日期 | `public_end_date` | `date` | 否 | 公示截止日期 |
| 是否为罕见病药物 | `rare_disease_flag` | `tinyint` | 否 | 是否为罕见病药物 |
| 来源文件 | `source_file` | `varchar(255)` | 否 | 来源文件 |
| 来源工作表 | `source_sheet` | `varchar(128)` | 否 | 来源工作表 |

## company_listing_status

- 中文名称：企业上市状态表
- 模板文件：`company_listing_status.csv`
- 必填字段：企业唯一标识, 上市状态（2:终止上市，1:正常上市，0:未上市）
- 可导入字段数：7

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 上市状态（2:终止上市，1:正常上市，0:未上市） | `listing_status` | `tinyint` | 是 | 上市状态（2:终止上市，1:正常上市，0:未上市） |
| 股票代码 | `stock_code` | `varchar(32)` | 否 | 股票代码 |
| 上市市场 | `market_name` | `varchar(255)` | 否 | 上市市场 |
| 上市日期 | `listed_at` | `date` | 否 | 上市日期 |
| 终止上市日期 | `delisted_at` | `date` | 否 | 终止上市日期 |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |

## company_patent

- 中文名称：企业专利表
- 模板文件：`company_patent.csv`
- 必填字段：专利号, 专利名称, 企业唯一标识
- 可导入字段数：8

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 专利号 | `company_patent_number` | `varchar(255)` | 是 | 专利号 |
| 专利名称 | `company_patent_name` | `varchar(255)` | 是 | 专利名称 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 专利申请日期 | `application_date` | `date` | 否 | 专利申请日期 |
| 专利授权日期 | `auth_date` | `date` | 否 | 专利授权日期 |
| 专利申请公布日 | `publication_date` | `date` | 否 | 专利申请公布日 |
| 科技属性标签 | `tech_attribute_label` | `varchar(255)` | 否 | 科技属性标签 |
| 排序序号 | `sort_order` | `int` | 否 | 排序序号 |

## company_patent_company_map

- 中文名称：企业与专利映射表
- 模板文件：`company_patent_company_map.csv`
- 必填字段：专利唯一标识, 企业唯一标识
- 可导入字段数：2

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 专利唯一标识 | `company_patent_id` | `bigint` | 是 | 专利唯一标识 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |

## company_patent_patent_type_map

- 中文名称：企业专利与专利类型映射表
- 模板文件：`company_patent_patent_type_map.csv`
- 必填字段：专利唯一标识, 专利类型唯一标识
- 可导入字段数：2

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 专利唯一标识 | `company_patent_id` | `bigint` | 是 | 专利唯一标识 |
| 专利类型唯一标识 | `company_patent_type_id` | `bigint` | 是 | 专利类型唯一标识 |

## company_patent_type

- 中文名称：专利类型表
- 模板文件：`company_patent_type.csv`
- 必填字段：专利类型名称
- 可导入字段数：1

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 专利类型名称 | `company_patent_type_name` | `varchar(255)` | 是 | 专利类型名称 |

## company_qualification

- 中文名称：企业资质表
- 模板文件：`company_qualification.csv`
- 必填字段：企业唯一标识, 企业资质/科技属性名称
- 可导入字段数：14

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 记录类型（qualification/license） | `record_kind` | `varchar(32)` | 否 | 记录类型（qualification/license） |
| 企业资质/科技属性名称 | `qualification_name` | `varchar(255)` | 是 | 企业资质/科技属性名称 |
| 证书/许可编号 | `qualification_number` | `varchar(255)` | 否 | 证书/许可编号 |
| 证书/许可状态 | `qualification_status` | `varchar(64)` | 否 | 证书/许可状态 |
| 资质等级 | `qualification_level` | `tinyint` | 否 | 资质等级 |
| 资质类型 | `qualification_type` | `varchar(255)` | 否 | 资质类型 |
| 数据来源 | `data_source` | `varchar(255)` | 否 | 数据来源 |
| 认定日期 | `issued_at` | `date` | 否 | 认定日期 |
| 有效期开始日期 | `valid_from` | `date` | 否 | 有效期开始日期 |
| 失效日期 | `expires_at` | `date` | 否 | 失效日期 |
| 有效期原始文本 | `validity_period_text` | `varchar(255)` | 否 | 有效期原始文本 |
| 发证/许可机关 | `issuing_authority` | `varchar(255)` | 否 | 发证/许可机关 |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |

## company_ranking

- 中文名称：企业榜单表
- 模板文件：`company_ranking.csv`
- 必填字段：企业榜单名称, 企业唯一标识
- 可导入字段数：7

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业榜单名称 | `company_ranking_name` | `varchar(255)` | 是 | 企业榜单名称 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业榜单类型 | `company_ranking_type` | `varchar(255)` | 否 | 企业榜单类型 |
| 企业榜单来源 | `company_ranking_source` | `varchar(255)` | 否 | 企业榜单来源 |
| 榜内位置（数字） | `company_ranking_position` | `int` | 否 | 榜内位置（数字） |
| 榜内名称 | `company_ranking_alias` | `varchar(255)` | 否 | 榜内名称 |
| 榜单发布年份 | `company_ranking_publish_year` | `int` | 否 | 榜单发布年份 |

## company_recommended_phone

- 中文名称：企业推荐电话表
- 模板文件：`company_recommended_phone.csv`
- 必填字段：企业唯一标识, 推荐电话
- 可导入字段数：4

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 推荐电话 | `recommended_phone` | `varchar(255)` | 是 | 推荐电话 |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |
| 抓取/核准时间 | `captured_at` | `datetime` | 否 | 抓取/核准时间 |

## company_recruit

- 中文名称：企业招聘信息表
- 模板文件：`company_recruit.csv`
- 必填字段：企业招聘岗位, 企业唯一标识
- 可导入字段数：7

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业招聘岗位 | `company_recruit_position` | `varchar(255)` | 是 | 企业招聘岗位 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业招聘薪资 | `company_recruit_salary` | `varchar(255)` | 否 | 企业招聘薪资 |
| 企业招聘工作年限要求 | `company_recruit_work_year_req` | `varchar(255)` | 否 | 企业招聘工作年限要求 |
| 企业招聘工作地点 | `company_recruit_work_place` | `varchar(255)` | 否 | 企业招聘工作地点 |
| 企业招聘学历要求 | `company_recruit_edu_req` | `varchar(255)` | 否 | 企业招聘学历要求 |
| 企业招聘时间 | `company_recruit_time` | `date` | 否 | 企业招聘时间 |

## company_risk

- 中文名称：企业风险统计表
- 模板文件：`company_risk.csv`
- 必填字段：企业唯一标识, 企业风险种类名称
- 可导入字段数：3

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业风险种类名称 | `company_risk_category_name` | `varchar(255)` | 是 | 企业风险种类名称 |
| 企业风险数量 | `company_risk_category_count` | `int` | 否 | 企业风险数量 |

## company_shareholder

- 中文名称：企业股东信息表
- 模板文件：`company_shareholder.csv`
- 必填字段：企业唯一标识, 股东名称
- 可导入字段数：8

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 股东名称 | `shareholder_name` | `varchar(255)` | 是 | 股东名称 |
| 股东类型 | `shareholder_type` | `varchar(64)` | 否 | 股东类型 |
| 持股比例 | `holding_ratio` | `decimal(5,2)` | 否 | 持股比例 |
| 认缴出资额（万元） | `subscribed_amount` | `decimal(18,4)` | 否 | 认缴出资额（万元） |
| 实缴出资额（万元） | `paid_amount` | `decimal(18,4)` | 否 | 实缴出资额（万元） |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |
| 抓取/核准时间 | `captured_at` | `datetime` | 否 | 抓取/核准时间 |

## company_software_copyright

- 中文名称：企业软件著作权表
- 模板文件：`company_software_copyright.csv`
- 必填字段：软件著作名称, 企业唯一标识, 软件著作登记号
- 可导入字段数：7

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 软件著作名称 | `company_software_copyright_name` | `varchar(255)` | 是 | 软件著作名称 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 软件著作登记号 | `company_software_copyright_register_number` | `varchar(255)` | 是 | 软件著作登记号 |
| 软件著作登记批准日期 | `company_software_copyright_register_date` | `date` | 否 | 软件著作登记批准日期 |
| 软件著作简称 | `company_software_copyright_for_short` | `varchar(255)` | 否 | 软件著作简称 |
| 软件著作状态 | `company_software_copyright_status` | `varchar(255)` | 否 | 软件著作状态 |
| 软件著作取得方式 | `company_software_copyright_obtain` | `varchar(255)` | 否 | 软件著作取得方式 |

## company_subdistrict

- 中文名称：企业街道/地区映射表
- 模板文件：`company_subdistrict.csv`
- 必填字段：街道/地区名称, 企业唯一标识
- 可导入字段数：2

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 街道/地区名称 | `company_subdistrict_name` | `varchar(255)` | 是 | 街道/地区名称 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |

## company_supplier

- 中文名称：企业供应商信息表
- 模板文件：`company_supplier.csv`
- 必填字段：企业供应商名称, 企业唯一标识
- 可导入字段数：6

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业供应商名称 | `company_supplier_name` | `varchar(255)` | 是 | 企业供应商名称 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 供应商企业 ID | `supplier_company_id` | `bigint` | 否 | 供应商企业 ID |
| 企业供应商采购金额（万元） | `company_supplier_purchase_amount` | `decimal(20,2)` | 否 | 企业供应商采购金额（万元） |
| 企业供应商采购占比 | `company_supplier_purchase_ratio` | `decimal(5,2)` | 否 | 企业供应商采购占比 |
| 报告时间 | `company_supplier_report_date` | `date` | 否 | 报告时间 |

## company_trademark

- 中文名称：企业商标表
- 模板文件：`company_trademark.csv`
- 必填字段：企业商标名称, 企业唯一标识, 企业商标注册号
- 可导入字段数：4

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业商标名称 | `company_trademark_name` | `varchar(255)` | 是 | 企业商标名称 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业商标注册号 | `company_trademark_register_number` | `varchar(255)` | 是 | 企业商标注册号 |
| 企业商标申请日期 | `company_trademark_application_date` | `date` | 否 | 企业商标申请日期 |

## company_website

- 中文名称：企业网站表
- 模板文件：`company_website.csv`
- 必填字段：企业唯一标识, 企业网站 URL
- 可导入字段数：4

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 企业网站 URL | `website` | `varchar(255)` | 是 | 企业网站 URL |
| 是否为最新记录 | `is_latest` | `tinyint` | 否 | 是否为最新记录 |
| 抓取/核准时间 | `captured_at` | `datetime` | 否 | 抓取/核准时间 |

## company_work_copyright

- 中文名称：企业作品著作权表
- 模板文件：`company_work_copyright.csv`
- 必填字段：作品著作名称, 企业唯一标识, 作品著作登记号
- 可导入字段数：7

| 导入列名 | 字段名 | 类型 | 必填 | 备注 |
| --- | --- | --- | --- | --- |
| 作品著作名称 | `company_work_copyright_name` | `varchar(255)` | 是 | 作品著作名称 |
| 企业唯一标识 | `company_id` | `bigint` | 是 | 企业唯一标识 |
| 作品著作登记号 | `company_work_copyright_register_number` | `varchar(255)` | 是 | 作品著作登记号 |
| 作品著作类别 | `company_work_copyright_type` | `varchar(255)` | 否 | 作品著作类别 |
| 作品著作首次发布日期 | `company_work_copyright_publish_date` | `date` | 否 | 作品著作首次发布日期 |
| 作品著作登记日期 | `company_work_copyright_register_date` | `date` | 否 | 作品著作登记日期 |
| 作品著作状态 | `company_work_copyright_status` | `varchar(255)` | 否 | 作品著作状态 |
