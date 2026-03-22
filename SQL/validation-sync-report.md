# 同步校验报告

本报告用于校验 `raw_import_* -> 结构化业务表` 的同步结果。

## 总览

- `company_basic`: 5837
- `TMP*` 临时信用代码企业数: 1037
- `is_chaoyang_company = 1` 企业数: 4744
- `company_branch`: 14636
- `company_contact_phone`: 10035
- `company_software_copyright`: 2748
- `company_patent`: 3199
- `company_patent_company_map`: 3202
- `company_customer`: 4733
- `company_ranking`: 58
- `company_recruit`: 332
- `company_risk`: 686

## 关键检查

| 检查项 | 结果 |
| --- | --- |
| company_basic_null_credit_code | 0 |
| company_basic_duplicate_credit_code | 0 |
| company_basic_null_company_name | 0 |
| contact_phone_orphans | 0 |
| software_orphans | 0 |
| patent_type_map_orphans | 0 |
| patent_company_map_orphans | 0 |
| count_mismatch_branch | 0 |
| count_mismatch_recruit | 0 |
| count_mismatch_software | 0 |
| count_mismatch_work | 0 |
| count_mismatch_patent | 0 |
| count_mismatch_customer | 0 |
| count_mismatch_ranking | 0 |

## 原始聚合值与结构化明细差异

| 检查项 | 结果 |
| --- | --- |
| raw_delta_branch | 131 |
| raw_delta_recruit | 0 |
| raw_delta_software | 6 |
| raw_delta_work | 3 |
| raw_delta_patent | 204 |
| raw_delta_customer | 1 |
| raw_delta_ranking | 4 |

## 差异样本

### 软件著作权原始聚合值差异

| 企业名称 | 原始聚合计数 | 实际明细数 |
| --- | --- | --- |
| 北京环球医疗救援有限责任公司 | 47 | 0 |
| 北京知几未来医疗科技有限公司 | 10 | 0 |
| 北京缙铖医疗科技有限公司 | 5 | 0 |
| 京华民服（北京）康养产业中心（有限合伙） | 2 | 0 |
| 北京中科希莱医疗科技有限公司 | 8 | 9 |
| 惠每医疗管理咨询（北京）有限公司 | 1 | 0 |

### 作品著作权原始聚合值差异

| 企业名称 | 原始聚合计数 | 实际明细数 |
| --- | --- | --- |
| 首都医科大学附属北京朝阳医院 | 5 | 0 |
| 北京青华丛生医疗技术有限公司 | 1 | 0 |
| 壹舟健康医疗科技（北京）有限公司 | 1 | 0 |

### 专利原始聚合值差异

| 企业名称 | 原始聚合计数 | 实际明细数 |
| --- | --- | --- |
| 北京融尚智讯科技有限公司 | 414 | 0 |
| 首都医科大学附属北京朝阳医院 | 1445 | 1085 |
| 北京乌索普科技发展有限公司 | 73 | 3 |
| 北京本草丽格中医诊所有限公司 | 51 | 0 |
| 北京万东医疗科技股份有限公司 | 290 | 247 |
| 点奇生物医疗科技（北京）有限公司 | 38 | 0 |
| 北京中宸口腔诊所有限公司 | 37 | 3 |
| 北京京泰内科诊所（普通合伙） | 29 | 0 |
| 北京天助畅运医疗技术股份有限公司 | 113 | 84 |
| 北京瑞维塔中西医结合诊所有限公司 | 29 | 0 |

## 说明

- `count_mismatch_*` 为 0 说明结构化计数字段已经和对应明细表完全对齐。
- `raw_delta_*` 大于 0 说明 Excel 中的原始聚合值与可落到明细表的实际数量存在差异，这些原值已单独保留，不再覆盖结构化计数。
- `TMP*` 信用代码表示原始 Excel 中缺少统一社会信用代码，当前同步阶段为了满足主表唯一约束生成了临时值。
