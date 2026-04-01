# 企业标签自动打标执行报告

- 生成日期: 2026-03-30
- 规则文件: `/Users/bluem/Projects/Web/industrial_chain/SQL/data/company_tag_auto_rule.json`
- 企业总数: 1
- 启用规则数: 42
- `direct_match`: 12
- `derived_rule`: 30
- 至少命中 1 个标签的企业数: 1
- 总打标条数: 14
- 互斥冲突数: 0

## 标签命中数

| 标签ID | 子维度 | 标签 | 规则类型 | 企业数 |
| --- | --- | --- | --- | --- |
| 1 | 成立年限 | 1 年内 | derived_rule | 0 |
| 2 | 成立年限 | 1-5 年 | derived_rule | 0 |
| 3 | 成立年限 | 5-10 年 | derived_rule | 0 |
| 4 | 成立年限 | 10-15 年 | derived_rule | 1 |
| 5 | 成立年限 | 15 年以上 | derived_rule | 0 |
| 6 | 注册资本 | 注册资本:0 万-100 万 | derived_rule | 1 |
| 7 | 注册资本 | 注册资本:100 万-200 万 | derived_rule | 0 |
| 8 | 注册资本 | 200 万- 500 万 | derived_rule | 0 |
| 9 | 注册资本 | 500 万- 1000 万 | derived_rule | 0 |
| 10 | 注册资本 | 1000 万以上 | derived_rule | 0 |
| 11 | 实缴资本 | 有实缴资本 | derived_rule | 0 |
| 12 | 实缴资本 | 无实缴资本 | derived_rule | 1 |
| 13 | 实缴资本 | 实缴资本:0 万-100 万 | derived_rule | 0 |
| 14 | 实缴资本 | 实缴资本:100 万-200 万 | derived_rule | 0 |
| 15 | 实缴资本 | 200 万-500 万 | derived_rule | 0 |
| 16 | 实缴资本 | 500 万-1000 万 | derived_rule | 0 |
| 17 | 实缴资本 | 1000 万-5000 万 | derived_rule | 0 |
| 18 | 实缴资本 | 5000 万以上 | derived_rule | 0 |
| 50 | 分支机构数量 | 有分支机构 | direct_match | 1 |
| 51 | 分支机构数量 | 无分支机构 | direct_match | 0 |
| 52 | 地址信息 | 有企业地址 | direct_match | 1 |
| 53 | 地址信息 | 无企业地址 | direct_match | 0 |
| 64 | 员工人数 | 员工人数:小于 50 人 | derived_rule | 1 |
| 65 | 员工人数 | 员工人数:50-99 人 | derived_rule | 0 |
| 66 | 员工人数 | 员工人数:100-499 人 | derived_rule | 0 |
| 67 | 员工人数 | 员工人数:500 人以上 | derived_rule | 0 |
| 68 | 员工人数 | 未披露 | derived_rule | 0 |
| 69 | 社保人数 | 社保人数:小于 50 人 | derived_rule | 1 |
| 70 | 社保人数 | 社保人数:50-99 人 | derived_rule | 0 |
| 71 | 社保人数 | 社保人数:100-499 人 | derived_rule | 0 |
| 72 | 社保人数 | 社保人数:500 人以上 | derived_rule | 0 |
| 78 | 联系方式 | 有联系电话 | derived_rule | 1 |
| 79 | 联系方式 | 有固定电话 | derived_rule | 1 |
| 80 | 联系方式 | 有手机号 | derived_rule | 1 |
| 81 | 工商信息邮箱 | 有工商信息邮箱 | direct_match | 1 |
| 82 | 工商信息邮箱 | 无工商信息邮箱 | direct_match | 0 |
| 83 | 小微企业 | 是小微企业 | direct_match | 1 |
| 84 | 小微企业 | 非小微企业 | direct_match | 0 |
| 87 | 一般纳税人 | 一般纳税人 | direct_match | 0 |
| 88 | 一般纳税人 | 非一般纳税人 | direct_match | 1 |
| 93 | 招聘信息 | 有招聘 | direct_match | 0 |
| 94 | 招聘信息 | 无招聘 | direct_match | 1 |

## 互斥冲突

无冲突。
