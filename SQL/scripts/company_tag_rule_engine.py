#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = PROJECT_ROOT / "SQL"
DATA_ROOT = SQL_ROOT / "data"
RULES_JSON_PATH = DATA_ROOT / "company_tag_auto_rule.json"

TAG_DIMENSION_JSON_PATH = DATA_ROOT / "company_tag_dimension.json"
TAG_SUBDIMENSION_JSON_PATH = DATA_ROOT / "company_tag_subdimension.json"
TAG_LIBRARY_JSON_PATH = DATA_ROOT / "company_tag_library.json"


CONTACT_MOBILE_PATTERN = r"1[3-9][0-9]{9}"
CONTACT_LANDLINE_PATTERN = r"0[0-9]{2,3}-?[0-9]{7,8}"


def normalize_text(value: Optional[str]) -> str:
    return " ".join((value or "").split())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_tag_catalog() -> Dict[str, Any]:
    dimensions = load_json(TAG_DIMENSION_JSON_PATH)
    subdimensions = load_json(TAG_SUBDIMENSION_JSON_PATH)
    tags = load_json(TAG_LIBRARY_JSON_PATH)

    subdimensions_by_name = {row["company_tag_subdimension_name"]: row for row in subdimensions}
    tags_by_subdimension: Dict[int, Dict[str, Dict[str, Any]]] = {}
    tags_by_id: Dict[int, Dict[str, Any]] = {}

    for row in tags:
        tags_by_id[int(row["company_tag_id"])] = row
        tags_by_subdimension.setdefault(int(row["company_tag_subdimension_id"]), {})[row["company_tag_name"]] = row

    return {
        "dimensions": dimensions,
        "subdimensions": subdimensions,
        "tags": tags,
        "subdimensions_by_name": subdimensions_by_name,
        "tags_by_subdimension": tags_by_subdimension,
        "tags_by_id": tags_by_id,
    }


def tag_id_for(subdimension_name: str, tag_name: str, catalog: Dict[str, Any]) -> int:
    subdimension = catalog["subdimensions_by_name"].get(subdimension_name)
    if subdimension is None:
        raise KeyError(f"未找到子维度 {subdimension_name!r}")
    rows = catalog["tags_by_subdimension"].get(int(subdimension["company_tag_subdimension_id"]), {})
    tag_row = rows.get(tag_name)
    if tag_row is None:
        raise KeyError(f"未在子维度 {subdimension_name!r} 下找到标签 {tag_name!r}")
    return int(tag_row["company_tag_id"])


def make_rule(
    *,
    subdimension_name: str,
    tag_name: str,
    rule_type: str,
    logic: Dict[str, Any],
    exclusive_group: Optional[str],
    description: str,
    catalog: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "company_tag_id": tag_id_for(subdimension_name, tag_name, catalog),
        "company_tag_name": tag_name,
        "company_tag_subdimension_name": subdimension_name,
        "company_tag_auto_rule_type": rule_type,
        "rule_definition": {
            "version": 1,
            "tag_name": tag_name,
            "subdimension_name": subdimension_name,
            "exclusive_group": exclusive_group,
            "description": description,
            "logic": logic,
        },
        "is_enabled": 1,
    }


def build_rule_specs() -> List[Dict[str, Any]]:
    catalog = load_tag_catalog()
    rules: List[Dict[str, Any]] = []

    def add(
        subdimension_name: str,
        tag_name: str,
        *,
        rule_type: str,
        logic: Dict[str, Any],
        exclusive_group: Optional[str],
        description: str,
    ) -> None:
        rules.append(
            make_rule(
                subdimension_name=subdimension_name,
                tag_name=tag_name,
                rule_type=rule_type,
                logic=logic,
                exclusive_group=exclusive_group,
                description=description,
                catalog=catalog,
            )
        )

    add("成立年限", "1 年内", rule_type="derived_rule", exclusive_group="age_established_range", description="成立未满 1 年", logic={"op": "age_years_range", "field": "establish_date", "min": 0, "max": 1})
    add("成立年限", "1-5 年", rule_type="derived_rule", exclusive_group="age_established_range", description="成立 1 至 5 年", logic={"op": "age_years_range", "field": "establish_date", "min": 1, "max": 5})
    add("成立年限", "5-10 年", rule_type="derived_rule", exclusive_group="age_established_range", description="成立 5 至 10 年", logic={"op": "age_years_range", "field": "establish_date", "min": 5, "max": 10})
    add("成立年限", "10-15 年", rule_type="derived_rule", exclusive_group="age_established_range", description="成立 10 至 15 年", logic={"op": "age_years_range", "field": "establish_date", "min": 10, "max": 15})
    add("成立年限", "15 年以上", rule_type="derived_rule", exclusive_group="age_established_range", description="成立 15 年及以上", logic={"op": "age_years_range", "field": "establish_date", "min": 15})

    add("注册资本", "注册资本:0 万-100 万", rule_type="derived_rule", exclusive_group="register_capital_range", description="注册资本在 0 至 100 万之间", logic={"op": "numeric_range", "field": "register_capital", "min": 0, "max": 100})
    add("注册资本", "注册资本:100 万-200 万", rule_type="derived_rule", exclusive_group="register_capital_range", description="注册资本在 100 至 200 万之间", logic={"op": "numeric_range", "field": "register_capital", "min": 100, "max": 200})
    add("注册资本", "200 万- 500 万", rule_type="derived_rule", exclusive_group="register_capital_range", description="注册资本在 200 至 500 万之间", logic={"op": "numeric_range", "field": "register_capital", "min": 200, "max": 500})
    add("注册资本", "500 万- 1000 万", rule_type="derived_rule", exclusive_group="register_capital_range", description="注册资本在 500 至 1000 万之间", logic={"op": "numeric_range", "field": "register_capital", "min": 500, "max": 1000})
    add("注册资本", "1000 万以上", rule_type="derived_rule", exclusive_group="register_capital_range", description="注册资本在 1000 万及以上", logic={"op": "numeric_range", "field": "register_capital", "min": 1000})

    add("实缴资本", "有实缴资本", rule_type="derived_rule", exclusive_group="paid_capital_presence", description="实缴资本大于 0", logic={"op": "numeric_compare", "field": "paid_capital", "gt": 0})
    add("实缴资本", "无实缴资本", rule_type="derived_rule", exclusive_group="paid_capital_presence", description="实缴资本为空或小于等于 0", logic={"op": "not", "rule": {"op": "numeric_compare", "field": "paid_capital", "gt": 0}})
    add("实缴资本", "实缴资本:0 万-100 万", rule_type="derived_rule", exclusive_group="paid_capital_range", description="实缴资本在 0 至 100 万之间", logic={"op": "numeric_range", "field": "paid_capital", "min": 0, "max": 100})
    add("实缴资本", "实缴资本:100 万-200 万", rule_type="derived_rule", exclusive_group="paid_capital_range", description="实缴资本在 100 至 200 万之间", logic={"op": "numeric_range", "field": "paid_capital", "min": 100, "max": 200})
    add("实缴资本", "200 万-500 万", rule_type="derived_rule", exclusive_group="paid_capital_range", description="实缴资本在 200 至 500 万之间", logic={"op": "numeric_range", "field": "paid_capital", "min": 200, "max": 500})
    add("实缴资本", "500 万-1000 万", rule_type="derived_rule", exclusive_group="paid_capital_range", description="实缴资本在 500 至 1000 万之间", logic={"op": "numeric_range", "field": "paid_capital", "min": 500, "max": 1000})
    add("实缴资本", "1000 万-5000 万", rule_type="derived_rule", exclusive_group="paid_capital_range", description="实缴资本在 1000 至 5000 万之间", logic={"op": "numeric_range", "field": "paid_capital", "min": 1000, "max": 5000})
    add("实缴资本", "5000 万以上", rule_type="derived_rule", exclusive_group="paid_capital_range", description="实缴资本在 5000 万及以上", logic={"op": "numeric_range", "field": "paid_capital", "min": 5000})

    add("员工人数", "员工人数:小于 50 人", rule_type="derived_rule", exclusive_group="employee_count_range", description="员工人数小于 50", logic={"op": "numeric_range", "field": "employee_count", "min": 0, "max": 50})
    add("员工人数", "员工人数:50-99 人", rule_type="derived_rule", exclusive_group="employee_count_range", description="员工人数在 50 至 99", logic={"op": "numeric_range", "field": "employee_count", "min": 50, "max": 100})
    add("员工人数", "员工人数:100-499 人", rule_type="derived_rule", exclusive_group="employee_count_range", description="员工人数在 100 至 499", logic={"op": "numeric_range", "field": "employee_count", "min": 100, "max": 500})
    add("员工人数", "员工人数:500 人以上", rule_type="derived_rule", exclusive_group="employee_count_range", description="员工人数在 500 及以上", logic={"op": "numeric_range", "field": "employee_count", "min": 500})
    add("员工人数", "未披露", rule_type="derived_rule", exclusive_group="employee_count_range", description="员工人数未披露", logic={"op": "is_null", "field": "employee_count"})

    add("社保人数", "社保人数:小于 50 人", rule_type="derived_rule", exclusive_group="insured_count_range", description="社保人数小于 50", logic={"op": "numeric_range", "field": "insured_count", "min": 0, "max": 50})
    add("社保人数", "社保人数:50-99 人", rule_type="derived_rule", exclusive_group="insured_count_range", description="社保人数在 50 至 99", logic={"op": "numeric_range", "field": "insured_count", "min": 50, "max": 100})
    add("社保人数", "社保人数:100-499 人", rule_type="derived_rule", exclusive_group="insured_count_range", description="社保人数在 100 至 499", logic={"op": "numeric_range", "field": "insured_count", "min": 100, "max": 500})
    add("社保人数", "社保人数:500 人以上", rule_type="derived_rule", exclusive_group="insured_count_range", description="社保人数在 500 及以上", logic={"op": "numeric_range", "field": "insured_count", "min": 500})

    add("联系方式", "有联系电话", rule_type="derived_rule", exclusive_group=None, description="企业存在至少一个联系电话", logic={"op": "phone_any"})
    add("联系方式", "有固定电话", rule_type="derived_rule", exclusive_group=None, description="联系电话中命中固定电话模式", logic={"op": "phone_regex", "pattern": CONTACT_LANDLINE_PATTERN})
    add("联系方式", "有手机号", rule_type="derived_rule", exclusive_group=None, description="联系电话中命中手机号模式", logic={"op": "phone_regex", "pattern": CONTACT_MOBILE_PATTERN})

    add("分支机构数量", "有分支机构", rule_type="direct_match", exclusive_group="branch_presence", description="分支机构数量大于 0", logic={"op": "numeric_compare", "field": "branch_count", "gt": 0})
    add("分支机构数量", "无分支机构", rule_type="direct_match", exclusive_group="branch_presence", description="分支机构数量等于 0", logic={"op": "numeric_compare", "field": "branch_count", "eq": 0})

    add("地址信息", "有企业地址", rule_type="direct_match", exclusive_group="address_presence", description="存在注册地址或地址明细", logic={"op": "boolean_true", "field": "has_address"})
    add("地址信息", "无企业地址", rule_type="direct_match", exclusive_group="address_presence", description="不存在注册地址且无地址明细", logic={"op": "boolean_false", "field": "has_address"})

    add("工商信息邮箱", "有工商信息邮箱", rule_type="direct_match", exclusive_group="business_email_presence", description="工商邮箱非空", logic={"op": "non_empty", "field": "email_business"})
    add("工商信息邮箱", "无工商信息邮箱", rule_type="direct_match", exclusive_group="business_email_presence", description="工商邮箱为空", logic={"op": "is_empty", "field": "email_business"})

    add("小微企业", "是小微企业", rule_type="direct_match", exclusive_group="micro_enterprise", description="is_micro_enterprise = 1", logic={"op": "numeric_compare", "field": "is_micro_enterprise", "eq": 1})
    add("小微企业", "非小微企业", rule_type="direct_match", exclusive_group="micro_enterprise", description="is_micro_enterprise = 0", logic={"op": "numeric_compare", "field": "is_micro_enterprise", "eq": 0})

    add("一般纳税人", "一般纳税人", rule_type="direct_match", exclusive_group="general_taxpayer", description="is_general_taxpayer = 1", logic={"op": "numeric_compare", "field": "is_general_taxpayer", "eq": 1})
    add("一般纳税人", "非一般纳税人", rule_type="direct_match", exclusive_group="general_taxpayer", description="is_general_taxpayer = 0", logic={"op": "numeric_compare", "field": "is_general_taxpayer", "eq": 0})

    add("招聘信息", "有招聘", rule_type="direct_match", exclusive_group="recruitment_presence", description="招聘布尔标记为 1 或招聘数量大于 0", logic={"op": "or", "rules": [{"op": "numeric_compare", "field": "has_recruitment", "eq": 1}, {"op": "numeric_compare", "field": "recruit_count", "gt": 0}]})
    add("招聘信息", "无招聘", rule_type="direct_match", exclusive_group="recruitment_presence", description="招聘布尔标记为 0 且招聘数量为 0", logic={"op": "and", "rules": [{"op": "numeric_compare", "field": "has_recruitment", "eq": 0}, {"op": "numeric_compare", "field": "recruit_count", "eq": 0}]})

    add("专利信息", "有专利", rule_type="direct_match", exclusive_group="patent_presence", description="专利布尔标记为 1 或专利数量大于 0", logic={"op": "or", "rules": [{"op": "numeric_compare", "field": "has_patent", "eq": 1}, {"op": "numeric_compare", "field": "patent_count", "gt": 0}]})
    add("专利信息", "无专利", rule_type="direct_match", exclusive_group="patent_presence", description="专利布尔标记为 0 且专利数量为 0", logic={"op": "and", "rules": [{"op": "numeric_compare", "field": "has_patent", "eq": 0}, {"op": "numeric_compare", "field": "patent_count", "eq": 0}]})

    add("作品著作权", "有作品著作权", rule_type="direct_match", exclusive_group="work_copyright_presence", description="作品著作权布尔标记为 1 或数量大于 0", logic={"op": "or", "rules": [{"op": "numeric_compare", "field": "has_work_copyright", "eq": 1}, {"op": "numeric_compare", "field": "work_copyright_count", "gt": 0}]})
    add("作品著作权", "无作品著作权", rule_type="direct_match", exclusive_group="work_copyright_presence", description="作品著作权布尔标记为 0 且数量为 0", logic={"op": "and", "rules": [{"op": "numeric_compare", "field": "has_work_copyright", "eq": 0}, {"op": "numeric_compare", "field": "work_copyright_count", "eq": 0}]})

    add("软件著作权", "有软件著作权", rule_type="direct_match", exclusive_group="software_copyright_presence", description="软件著作权布尔标记为 1 或数量大于 0", logic={"op": "or", "rules": [{"op": "numeric_compare", "field": "has_software_copyright", "eq": 1}, {"op": "numeric_compare", "field": "software_copyright_count", "gt": 0}]})
    add("软件著作权", "无软件著作权", rule_type="direct_match", exclusive_group="software_copyright_presence", description="软件著作权布尔标记为 0 且数量为 0", logic={"op": "and", "rules": [{"op": "numeric_compare", "field": "has_software_copyright", "eq": 0}, {"op": "numeric_compare", "field": "software_copyright_count", "eq": 0}]})

    add("高新技术企业", "是高新技术企业", rule_type="direct_match", exclusive_group="high_tech_enterprise", description="is_high_tech_enterprise = 1", logic={"op": "numeric_compare", "field": "is_high_tech_enterprise", "eq": 1})
    add("高新技术企业", "不是高新技术企业", rule_type="direct_match", exclusive_group="high_tech_enterprise", description="is_high_tech_enterprise = 0", logic={"op": "numeric_compare", "field": "is_high_tech_enterprise", "eq": 0})

    risk_specs = [
        ("失信被执行", "has_dishonest_execution", "dishonest_execution_count", "risk_dishonest_execution"),
        ("动产抵押", "has_chattel_mortgage", "chattel_mortgage_count", "risk_chattel_mortgage"),
        ("经营异常", "has_business_abnormal", "business_abnormal_count", "risk_business_abnormal"),
        ("法律文书", "has_legal_document", "legal_doc_all_count", "risk_legal_document"),
        ("行政处罚", "has_admin_penalty", "admin_penalty_count", "risk_admin_penalty"),
        ("破产重叠", "has_bankruptcy_overlap", "bankruptcy_overlap_count", "risk_bankruptcy_overlap"),
        ("环保处罚", "has_env_penalty", "env_penalty_count", "risk_env_penalty"),
        ("股权冻结", "has_equity_freeze", "equity_freeze_count", "risk_equity_freeze"),
        ("被执行人", "has_executed_person", "executed_person_count", "risk_executed_person"),
    ]
    for subdimension_name, bool_field, count_field, group in risk_specs:
        add(subdimension_name, f"有{subdimension_name}", rule_type="direct_match", exclusive_group=group, description=f"{subdimension_name}布尔标记为 1 或数量大于 0", logic={"op": "or", "rules": [{"op": "numeric_compare", "field": bool_field, "eq": 1}, {"op": "numeric_compare", "field": count_field, "gt": 0}]})
        add(subdimension_name, f"无{subdimension_name}", rule_type="direct_match", exclusive_group=group, description=f"{subdimension_name}布尔标记为 0 且数量为 0", logic={"op": "and", "rules": [{"op": "numeric_compare", "field": bool_field, "eq": 0}, {"op": "numeric_compare", "field": count_field, "eq": 0}]})

    rules.sort(key=lambda row: int(row["company_tag_id"]))
    return rules


def dump_rules_json(path: Path = RULES_JSON_PATH) -> List[Dict[str, Any]]:
    rules = build_rule_specs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rules


def parse_date(value: Any) -> Optional[date]:
    if value in (None, "", "NULL"):
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def age_in_years(value: Any, today: Optional[date] = None) -> Optional[float]:
    establish_date = parse_date(value)
    if establish_date is None:
        return None
    today = today or date.today()
    return (today - establish_date).days / 365.2425


def regex_search(pattern: str, value: str) -> bool:
    return re.search(pattern, value or "") is not None


def to_number(value: Any) -> Optional[float]:
    if value in (None, "", "NULL"):
        return None
    return float(value)


def evaluate_logic(logic: Dict[str, Any], record: Dict[str, Any]) -> bool:
    op = logic["op"]

    if op == "and":
        return all(evaluate_logic(rule, record) for rule in logic["rules"])
    if op == "or":
        return any(evaluate_logic(rule, record) for rule in logic["rules"])
    if op == "not":
        return not evaluate_logic(logic["rule"], record)
    if op == "is_null":
        return record.get(logic["field"]) is None
    if op == "non_empty":
        return normalize_text(str(record.get(logic["field"]) or "")) != ""
    if op == "is_empty":
        return normalize_text(str(record.get(logic["field"]) or "")) == ""
    if op == "boolean_true":
        return bool(record.get(logic["field"]))
    if op == "boolean_false":
        return not bool(record.get(logic["field"]))
    if op == "numeric_compare":
        value = to_number(record.get(logic["field"]))
        if value is None:
            return False
        if "eq" in logic:
            return value == float(logic["eq"])
        if "gt" in logic:
            return value > float(logic["gt"])
        if "gte" in logic:
            return value >= float(logic["gte"])
        if "lt" in logic:
            return value < float(logic["lt"])
        if "lte" in logic:
            return value <= float(logic["lte"])
        raise ValueError(f"numeric_compare 缺少比较条件: {logic}")
    if op == "numeric_range":
        value = to_number(record.get(logic["field"]))
        if value is None:
            return False
        min_value = logic.get("min")
        max_value = logic.get("max")
        if min_value is not None and value < float(min_value):
            return False
        if max_value is not None and value >= float(max_value):
            return False
        return True
    if op == "age_years_range":
        age_value = age_in_years(record.get(logic["field"]), today=record.get("_today"))
        if age_value is None:
            return False
        min_value = logic.get("min")
        max_value = logic.get("max")
        if min_value is not None and age_value < float(min_value):
            return False
        if max_value is not None and age_value >= float(max_value):
            return False
        return True
    if op == "phone_any":
        return normalize_text(str(record.get("contact_phone_combined") or "")) != ""
    if op == "phone_regex":
        return regex_search(logic["pattern"], str(record.get("contact_phone_combined") or ""))

    raise ValueError(f"未知规则操作符: {op}")


def find_conflicts(assignments: Dict[int, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    for company_id, rows in assignments.items():
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            exclusive_group = row["rule_definition"].get("exclusive_group")
            if not exclusive_group:
                continue
            grouped.setdefault(exclusive_group, []).append(row)
        for exclusive_group, items in grouped.items():
            if len(items) > 1:
                conflicts.append(
                    {
                        "company_id": company_id,
                        "exclusive_group": exclusive_group,
                        "tag_ids": [int(item["company_tag_id"]) for item in items],
                        "tag_names": [str(item["company_tag_name"]) for item in items],
                    }
                )
    return conflicts


def managed_tag_ids(rules: Iterable[Dict[str, Any]]) -> List[int]:
    return sorted({int(rule["company_tag_id"]) for rule in rules})
