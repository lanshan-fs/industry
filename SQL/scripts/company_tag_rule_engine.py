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


def normalize_text(value: Optional[str]) -> str:
    return " ".join((value or "").split())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rules() -> List[Dict[str, Any]]:
    return load_json(RULES_JSON_PATH)


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

