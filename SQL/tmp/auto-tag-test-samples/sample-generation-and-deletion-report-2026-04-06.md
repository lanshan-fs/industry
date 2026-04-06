# 自动打标签测试样本生成与删除记录

生成时间：2026-04-06

## 样本文件

- `auto-tag-test-sample-1.csv`：20 家
- `auto-tag-test-sample-2.csv`：20 家
- `auto-tag-test-sample-3.csv`：20 家
- `auto-tag-test-sample-4.csv`：20 家
- `auto-tag-test-sample-5.csv`：20 家
- `selected-100-with-ids.csv`：100 家，含 `company_id`
- `selected-company-ids.txt`：100 个 `company_id`

## 抽样口径

- 来源表：`company_basic`
- 排序：`updated_at DESC, company_id DESC`
- 条件：`company_name <> ''`、`business_scope <> ''`、`credit_code IS NOT NULL`、`credit_code <> ''`

## 删除结果

以下关联口径已回查为 0：

- `company_basic`
- `company_basic_count`
- `company_branch`
- `company_qualification`
- `company_recruit`
- `company_patent`
- `company_tag_map`
- `category_industry_company_map`
- `company_customer`
- `company_supplier`
- `scoring_scorelog`
- `scoring_scoreresult`

说明：这 100 家样本已从当前数据库及关键关联表中删除，可直接作为“待入库企业”测试自动打标签与预检查重流程。
