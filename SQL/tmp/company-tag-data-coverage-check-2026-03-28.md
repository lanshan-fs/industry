# 企业标签与真实数据对应性检查

检查时间：2026-03-28

检查范围：

- 标签设计来源：`SQL/data/企业标签.mm`
- 数据库结构来源：`SQL/sql/init.sql`
- 实际数据来源：本地 `industrial_chain` MySQL

判定口径：

- `可直接对应`：已有明确字段或明细表，且当前数据可直接支撑标签判断。
- `可规则推导`：已有原始值，但需要数值分桶、正则或别名归并。
- `部分对应`：结构上能做，但当前标签集合和真实值不完全一致，或只能依赖弱规则/聚合字段。
- `当前不适合`：现有库中没有可靠数据源，或当前字段/数据质量不足以稳定打标。

## 总结

- 这套“配套标签”不能整体直接拿来做稳定打标。
- 可以直接或经简单规则落地的，主要集中在：数值分桶、布尔存在性、风险标签、部分知识产权标签。
- 当前明显不适合直接打标的，主要集中在：`经营状态`、`税务评级`、`开户行`、`微信公众号`、`标准制定`、`ICP备案`、`商业特许经营`、`应用场景`。
- 还有一批属于“结构有，但当前真实数据不够”，典型如：`商标信息`、`网址信息`、`招投标`、`变更信息`、`限制高消费`。这些字段多半只能依赖聚合布尔值，缺少明细支撑。

关键数据事实：

- `company_basic` 共 `5837` 家企业。
- `company_status` 非空 `0/5837`，所以当前无法稳定判断“存续”。
- `website` 非空 `0/5837`，`company_website` 也为 `0`。
- `taxpayer_credit_rating` 非空 `0/5837`。
- `company_change` 为 `0`，`company_bidding` 为 `0`，`company_trademark` 为 `0`，`company_consumption_restriction` 为 `0`。
- `company_financing` 仅 `62` 条，`company_listing_status` 仅 `6` 条。
- `company_risk` 有 `686` 条，风险类标签可用性最好。
- `company_qualification` 有 `5575` 条，但内容明显混杂了“资质/状态/融资/风险/曾用名”等多种语义，不能直接等价为标准化标签库。

## 逐项检查

### 基本信息

- `企业名称`：可直接对应。来源 `company_basic.company_name`，非空 `5837/5837`。当前 `mm` 中无配套标签，只有字段本体。
- `统一社会信用代码`：可直接对应。来源 `company_basic.credit_code`，非空 `5837/5837`。当前无配套标签。
- `成立年限`：可规则推导。来源 `company_basic.establish_date`，非空 `4785/5837`。`1 年内 / 1-5 年 / 5-10 年 / 10-15 年 / 15 年以上` 可按日期差分桶。
- `注册资本`：可规则推导。来源 `company_basic.register_capital`，非空 `4255/5837`。区间标签可直接按数值分桶。
- `实缴资本`：可规则推导。来源 `company_basic.paid_capital`，非空 `1992/5837`。`有实缴资本/无实缴资本` 与区间标签都可推导，但覆盖率一般。
- `经营状态`：当前不适合。设计里只有 `存续`，但 `company_basic.company_status` 当前非空为 `0/5837`，没有稳定源数据。
- `企业类型`：部分对应。来源 `company_basic.company_type`，非空 `4663/5837`。真实值是细粒度工商类型，如“有限责任公司(自然人投资或控股)”；`国有企业/民营企业/外商投资/港澳台投资` 等需做归并，有些能做，有些会失真。
- `组织类型`：部分对应。来源 `company_basic.org_type`，非空 `4800/5837`。真实值以“有限责任公司/合伙企业/股份有限公司”为主，与 `mm` 中“新三板/学校/香港企业/事业单位”不是同一维度。
- `投资类型`：可直接对应字段，但当前 `mm` 没有配套标签。来源 `company_basic.investment_type`，非空 `4800/5837`。
- `企业规模`：可直接对应。来源 `company_basic.company_scale`，非空 `4800/5837`。真实值已包含 `大型企业/中型企业/小型企业/微型企业`，另有“未明确企业规模/无法判定”。
- `分支机构数量`：可直接对应。来源 `company_basic_count.branch_count`，`>0` 的企业有 `4800` 家。`有分支机构/无分支机构` 可直接判断。
- `分支机构名称`：可直接对应字段，但当前 `mm` 没有配套标签。来源 `company_basic.branch_name`，非空 `4800/5837`。
- `地址信息`：可直接对应。来源 `company_basic.register_address`，非空 `4757/5837`。`有企业地址/无企业地址` 可直接判断。
- `投融资轮次`：部分对应。来源 `company_basic.financing_round` 与 `company_financing`，当前仅 `62` 家非空。正向轮次如 `天使轮/A轮/B轮/C轮/D轮及以上/战略融资` 可以做归并，但 `未融资/无融资` 不能简单用空值代替。

### 经营状况

- `员工人数`：可规则推导。来源 `company_basic.employee_count`，非空 `3039/5837`。分桶标签可做，`未披露` 也可用空值表达。
- `社保人数`：可规则推导。来源 `company_basic.insured_count`，非空 `4150/5837`。分桶标签可做。
- `上市状态`：部分对应。来源 `company_listing_status.market_name` 与 `company_basic.listing_status`。当前仅 `6` 家上市相关记录，真实市场值是 `A股(正常上市)`、`新三板(终止上市)`、`新四板`，与 `mm` 的 `港股/中概股/科创板` 不完全对齐。
- `国标行业`：可直接对应字段，但当前 `mm` 没有配套标签。来源 `company_basic.industry_belong`，非空 `4775/5837`。
- `联系方式`：可规则推导。来源 `company_basic.contact_phone`，非空 `4239/5837`。按正则可区分 `有联系电话/有固定电话/有手机号`；当前命中手机号约 `2761`，固定电话约 `938`。
- `同电话企业`：可直接对应字段，但当前 `mm` 没有配套标签。来源 `company_basic.same_phone_company_count`，`>0` 的企业有 `720` 家。
- `工商信息邮箱`：可直接对应。来源 `company_basic.email_business`，非空 `3998/5837`。`有工商信息邮箱/无工商信息邮箱` 可直接判断。
- `小微企业`：可直接对应。来源 `company_basic.is_micro_enterprise`，为 `1` 的有 `3020` 家。
- `变更信息`：部分对应。来源 `company_basic.has_changed_info`，为 `1` 的有 `2198` 家；但 `company_change` 明细表当前为 `0`。也就是说只适合做“有/无变更信息”，不适合做更细粒度标签。
- `一般纳税人`：可直接对应。来源 `company_basic.is_general_taxpayer`，为 `1` 的有 `1203` 家。
- `融资信息`：部分对应。来源 `company_basic.financing_info`，非空 `62/5837`。`有融资` 可判断，但 `无融资` 与“未采集到融资信息”目前不可严格区分。
- `招投标数量`：部分对应。来源 `company_basic_count.bidding_count`，`>0` 的企业有 `826` 家；但 `company_bidding` 明细表为 `0`，当前只能依赖聚合值。
- `招投标`：部分对应。来源 `company_basic.has_bidding`，为 `1` 的企业有 `826` 家；同样缺少明细表验证。
- `招聘信息数量`：可直接对应。来源 `company_basic_count.recruit_count`，`>0` 的企业有 `16` 家；`company_recruit` 明细表有 `332` 条。
- `招聘信息`：可直接对应。来源 `company_basic.has_recruitment` 或 `company_basic_count.recruit_count`。当前有招聘的企业较少，但可稳定判断。
- `税务评级`：当前不适合。理论字段是 `company_basic.taxpayer_credit_rating`，但非空 `0/5837`。
- `开户行`：当前不适合。当前库中没有开户行/银行类别字段，也没有对应明细表。

### 知识产权

- `专利类型`：部分对应。来源 `company_patent_type` + `company_patent_patent_type_map`。当前真实值为 `实用新型/发明公开/发明授权/外观设计`；`mm` 中写的是 `发明公布`，与库中 `发明公开` 存在命名不一致，需要别名归并。
- `企业科技属性`：部分对应。可以由两类来源组合：一类是 `company_basic` 里的布尔字段，如 `is_high_tech_enterprise=11`、`is_srdi_sme=5`、`is_gazelle_company=2`、`is_tech_sme=5`、`is_egalet_company=1`、`is_srdi_little_giant=1`；另一类是 `company_qualification.qualification_name`。但后者内容混杂，不能直接当标准标签用，只能做弱匹配。
- `资质证书`：可直接对应字段，但当前 `mm` 没有配套标签。来源 `company_qualification`，有 `5575` 条。
- `商标信息`：当前不适合直接打标。结构上有 `has_trademark`、`company_basic_count.trademark_count`、`company_trademark`，但当前 `has_trademark=1` 为 `0`，`company_trademark` 表也为 `0`。如果现在强行打，会全部落成“无商标”。
- `专利信息`：可直接对应。来源 `company_basic.has_patent` 与 `company_basic_count.patent_count`。`has_patent=1` 为 `600`，`patent_count>0` 为 `429`。
- `作品著作权`：可直接对应。来源 `company_basic.has_work_copyright` 与 `company_basic_count.work_copyright_count`。正样本企业 `190` 家。
- `软件著作权`：可直接对应。来源 `company_basic.has_software_copyright` 与 `company_basic_count.software_copyright_count`。正样本企业 `241` 家。
- `高新技术企业`：可直接对应。来源 `company_basic.is_high_tech_enterprise`。正样本 `11` 家。
- `微信公众号`：当前不适合。当前库没有公众号字段，也没有公众号明细表。
- `标准制定`：当前不适合。当前库没有标准/标准制定相关字段或表。
- `网址信息`：当前不适合直接打标。结构上有 `company_basic.website` 和 `company_website`，但当前都为 `0`，所以只能全量落成“无网址信息”。
- `备案网站检测`：当前不适合。当前库没有 ICP/备案字段或表。
- `商业特许经营`：当前不适合。当前库没有商业特许经营字段或表。

### 风险信息

- `失信被执行`：可直接对应。来源 `company_basic.has_dishonest_execution` 与 `company_basic_count.dishonest_execution_count`。正样本 `27` 家。
- `动产抵押`：可直接对应。来源 `company_basic.has_chattel_mortgage` 与 `company_basic_count.chattel_mortgage_count`。正样本 `30` 家。
- `经营异常`：可直接对应。来源 `company_basic.has_business_abnormal` 与 `company_basic_count.business_abnormal_count`。正样本 `101` 家。
- `法律文书`：可直接对应。来源 `company_basic.has_legal_document` 与 `company_basic_count.legal_doc_all_count`。正样本 `295` 家。
- `行政处罚`：可直接对应。来源 `company_basic.has_admin_penalty` 与 `company_basic_count.admin_penalty_count`。正样本 `360` 家。
- `破产重叠`：可直接对应。来源 `company_basic.has_bankruptcy_overlap` 与 `company_basic_count.bankruptcy_overlap_count`。正样本 `5` 家。
- `清算信息`：部分对应。结构字段存在，但当前 `has_liquidation_info=1` 为 `0`，`liquidation_info_count>0` 也为 `0`。现在只能稳定打出“无清算信息”。
- `环保处罚`：可直接对应。来源 `company_basic.has_env_penalty` 与 `company_basic_count.env_penalty_count`。正样本 `88` 家。
- `股权冻结`：可直接对应。来源 `company_basic.has_equity_freeze` 与 `company_basic_count.equity_freeze_count`。正样本 `51` 家。
- `被执行人`：可直接对应。来源 `company_basic.has_executed_person` 与 `company_basic_count.executed_person_count`。正样本 `21` 家。
- `限制高消费`：部分对应。来源 `company_basic.has_consumption_restriction` 与 `company_basic.consumption_restriction_count`。正样本仅 `3` 家，且 `company_consumption_restriction` 明细表当前为 `0`。

### 街道地区

- `街道`：部分对应。来源 `company_basic.subdistrict` 与 `company_subdistrict`。非空仅 `1395/5837`，说明覆盖率有限；但对已有值可以做精确匹配。当前命中较多的有 `望京街道`、`酒仙桥街道`、`八里庄街道` 等。
- `地区`：部分对应。来源同上。对已有值可以精确匹配，但整体覆盖率仍只有 `1395/5837`。当前命中较多的有 `豆各庄地区`、`高碑店地区`、`将台地区` 等。

### 应用场景

- `应用场景` 下的 `38` 个标签当前都不适合直接对应。当前库里没有“企业应用场景/场景标签”字段，也没有业务表能够直接落到 `健康管理/患者社区/疾病诊断/肿瘤/骨科` 这类标签。
- 如果要支持这一组标签，通常要新增以下之一：
  - 人工标注结果表
  - 基于企业简介/经营范围/NLP 分类的自动打标规则
  - 行业分类与应用场景之间的映射规则

## 结论建议

- 第一批可以直接做自动打标的，优先建议：`成立年限`、`注册资本`、`实缴资本`、`企业规模`、`分支机构数量`、`地址信息`、`员工人数`、`社保人数`、`联系方式`、`工商信息邮箱`、`小微企业`、`一般纳税人`、`专利信息`、`作品著作权`、`软件著作权`、`高新技术企业`、全部风险标签。
- 第二批可以做，但必须补规则或做别名归并的：`企业类型`、`组织类型`、`投融资轮次`、`上市状态`、`专利类型`、`企业科技属性`、`街道/地区`。
- 第三批不建议现在就做正式打标：`经营状态`、`税务评级`、`开户行`、`商标信息`、`网址信息`、`微信公众号`、`标准制定`、`ICP备案`、`商业特许经营`、`应用场景`。
- 如果后续要把这套 `mm` 真正落到 `company_tag_auto_rule`，应先把“可直接对应”和“可规则推导”的子集单独抽出来，形成第一版规则库；其余部分不要混入首批自动打标。
