# 评分口径与现库映射

目标：保留 `dcpt-f` 旧项目的评分口径和权重表语义，不采纳其旧数据库结构；全部取数改为当前本地库。

## 总体原则

- 权重表继续使用本地既有的：
  - `score_model_total_weight`
  - `score_model_basic_weight`
  - `score_model_tech_weight`
  - `score_model_professional_weight`
- 评分结果全部回写本地既有的派生表：
  - `scoring_scoreresult`
  - `scoring_scorelog`
  - `score_industry_path`
- 业务源表只读，不做结构变更。

## 旧口径到现库字段

### 基础维度

- `企业基本信息.成立年限` -> `company_basic.establish_date`
  - 现库没有独立“成立年限”列，改为按当前日期反推年限。
- `企业基本信息.注册资本` -> `company_basic.register_capital`
- `企业基本信息.实缴资本` -> `company_basic.paid_capital`
- `企业基本信息.企业类型` -> `company_basic.company_type`
- `企业基本信息.企业规模` -> `company_basic.company_scale`
  - `company_basic.employee_count` 作为兜底。
- `企业经营信息.社保人数` -> `company_basic.insured_count`
- `企业基本信息.网址` -> `company_basic.website`
- `企业基本信息.经营范围` -> `company_basic.business_scope`
- `企业经营信息.税务评级` -> `company_basic.taxpayer_credit_rating`
- `企业经营信息.是否为一般纳税人` -> `company_basic.is_general_taxpayer`
  - `company_basic.taxpayer_qualifications` 作为弱兜底。
- `企业基本信息.投融资轮次` -> `company_basic.financing_round`
- `专利信息.专利类型` -> `company_patent` + `company_patent_patent_type_map` + `company_patent_type`
- `软件著作权` -> `company_software_copyright`
- `知识产权.高新技术企业/专精特新/创新型` -> `company_basic`
  - `is_high_tech_enterprise`
  - `is_srdi_sme`
  - `is_srdi_little_giant`
  - `is_innovative_sme`
  - `is_tech_sme`
  - `is_gazelle_company`
  - `is_egalet_company`
- `风险信息` -> `company_basic` 风险布尔字段 + `company_risk`
  - `集群注册` 现库无直接对位字段，移除该扣分项。

### 科技维度

- `专利类型` -> 同上，来自 `company_patent*`
- `专利科技属性` -> `company_patent.company_patent_name` + `company_patent.tech_attribute_label`
- `软件著作权数量` -> `company_software_copyright`
- `软著科技属性` -> `company_software_copyright_name` + `company_software_copyright_for_short`
- `科技型企业` -> `company_basic` 科技属性布尔字段
- `产学研合作` -> `company_basic.business_scope` + `company_qualification`
  - 通过关键词兼容，现库无独立合作表。
- `国家/省级奖励` -> `company_ranking` + `company_qualification`
  - 同样走关键词兼容，现库无独立奖励表。

### 专业维度

- `行业分类` -> `category_industry_company_map` + `category_industry`
  - 按 `category_level_code` / `category_level_code_parent` 重建行业路径。
- `资质认证` -> `company_qualification`
  - 需要过滤掉“小微企业、曾用名、司法案件、正常经营”等脏状态标签。
- `客户信息` -> `company_customer`
- `供应商` -> `company_supplier`
  - 当前现库为 `0` 条，阶段内按真实现状计分。
- `上榜榜单` -> `company_ranking`

## 当前缺口与兼容策略

- `company_qualification` 混杂状态标签，不可直接当证书表使用。
  - 处理：先过滤噪声，再按旧口径关键词判定“资质”和“证书”。
- 旧库里的 `集群注册` 风险项无直接现库字段。
  - 处理：不保留该扣分项。
- 旧库 `产学研合作`、`国家/省级奖励` 曾有硬编码占位。
  - 处理：改为基于现库关键词兼容，不再写死固定满分。
- 行业类目名称不完全一致。
  - 处理：沿用旧项目的分档逻辑，但补充当前类目别名，如 `医药商业 / 流通`、`数字疗法`、`AI 药物研`、`第三方中心`。

## 落地边界

- 当前阶段只重建评分引擎和行业聚合。
- 不迁移旧项目的 Django 模型、旧表、旧 SQL。
- 不继续扩展 `project/server.js` 里的旧评分接口，评分统一由 Django 接管。
