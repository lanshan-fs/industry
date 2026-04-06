#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

from company_tag_rule_engine import evaluate_logic, find_conflicts, load_rules, load_tag_catalog


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGION_DIMENSION_ID = 5
SCENE_DIMENSION_ID = 6
HEURISTIC_RULE_TYPE = "heuristic_rule"
TEXT_SOURCE_LABELS = {
    "company_name": "企业名称",
    "business_scope": "经营范围",
    "qualification_label": "企业资质",
    "industry_belong": "所属行业",
    "subdistrict": "所属街道/地区",
    "register_address": "注册地址",
    "register_address_detail": "地址明细",
}

SCENE_PROFILES: List[Dict[str, Any]] = [
    {"tag_name": "健康管理", "keywords": ["健康管理", "慢病管理", "远程健康管理", "健康监测", "健康档案", "养生保健"]},
    {"tag_name": "患者社区", "keywords": ["患者社区", "病友社区", "患者管理社区", "患教社区", "患者交流"]},
    {"tag_name": "健康和疾病咨询", "keywords": ["健康咨询", "疾病咨询", "医疗咨询", "问诊咨询", "健康和疾病咨询"]},
    {"tag_name": "就诊挂号", "keywords": ["预约挂号", "挂号服务", "挂号", "导诊", "分诊"]},
    {"tag_name": "就诊服务", "keywords": ["医疗服务", "门诊服务", "诊所服务", "互联网医院", "医院服务", "就诊服务"]},
    {"tag_name": "转诊服务", "keywords": ["转诊", "双向转诊", "会诊转诊"]},
    {"tag_name": "诊后服务", "keywords": ["诊后服务", "诊后管理", "院后管理", "复诊管理", "随访服务", "患者随访"]},
    {"tag_name": "疾病诊断", "keywords": ["疾病诊断", "医学检验", "检验检测", "体外诊断", "影像诊断", "病理诊断", "基因检测", "分子诊断"]},
    {"tag_name": "疾病治疗", "keywords": ["疾病治疗", "诊疗服务", "治疗服务", "手术治疗", "药物治疗", "临床治疗"]},
    {"tag_name": "康复治疗", "keywords": ["康复治疗", "康复训练", "康复服务", "术后康复", "康复护理"]},
]

DEFAULT_RECORD = {
    "company_name": "",
    "credit_code": "",
    "establish_date": None,
    "register_capital": None,
    "paid_capital": None,
    "employee_count": 0,
    "insured_count": 0,
    "contact_phone": "",
    "email_business": "",
    "register_address": "",
    "register_address_detail": "",
    "business_scope": "",
    "qualification_label": "",
    "industry_belong": "",
    "subdistrict": "",
    "is_micro_enterprise": False,
    "is_general_taxpayer": False,
    "has_recruitment": False,
    "has_patent": False,
    "has_work_copyright": False,
    "has_software_copyright": False,
    "is_high_tech_enterprise": False,
    "has_dishonest_execution": False,
    "has_chattel_mortgage": False,
    "has_business_abnormal": False,
    "has_legal_document": False,
    "has_admin_penalty": False,
    "has_bankruptcy_overlap": False,
    "has_env_penalty": False,
    "has_equity_freeze": False,
    "has_executed_person": False,
    "branch_count": 0,
    "recruit_count": 0,
    "patent_count": 0,
    "work_copyright_count": 0,
    "software_copyright_count": 0,
    "dishonest_execution_count": 0,
    "chattel_mortgage_count": 0,
    "business_abnormal_count": 0,
    "legal_doc_all_count": 0,
    "admin_penalty_count": 0,
    "bankruptcy_overlap_count": 0,
    "env_penalty_count": 0,
    "equity_freeze_count": 0,
    "executed_person_count": 0,
}


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def to_number(value: Any) -> float | None:
    if value in (None, "", "NULL"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def to_int(value: Any) -> int:
    number = to_number(value)
    return int(number or 0)


def to_bool(value: Any) -> bool:
    text = normalize_text(value).lower()
    return text in {"1", "true", "yes", "y", "是", "有"}


def filter_rules(
    rules: List[Dict[str, Any]],
    *,
    dimension_ids: List[int] | None = None,
) -> List[Dict[str, Any]]:
    allowed_dimension_ids = set(dimension_ids or [])
    if not allowed_dimension_ids:
      return rules

    catalog = load_tag_catalog()
    subdimensions_by_id = {int(row["company_tag_subdimension_id"]): row for row in catalog["subdimensions"]}
    filtered: List[Dict[str, Any]] = []
    for rule in rules:
        company_tag_id = int(rule["company_tag_id"])
        tag_row = catalog["tags_by_id"].get(company_tag_id)
        if tag_row is None:
            continue
        subdimension = subdimensions_by_id.get(int(tag_row["company_tag_subdimension_id"]))
        if subdimension is None:
            continue
        if int(subdimension["company_tag_dimension_id"]) not in allowed_dimension_ids:
            continue
        filtered.append(rule)
    return filtered


def make_heuristic_rule(*, company_tag_id: int, company_tag_name: str, subdimension_name: str, description: str) -> Dict[str, Any]:
    return {
        "company_tag_id": int(company_tag_id),
        "company_tag_name": company_tag_name,
        "company_tag_subdimension_name": subdimension_name,
        "company_tag_auto_rule_type": HEURISTIC_RULE_TYPE,
        "rule_definition": {
            "version": 1,
            "tag_name": company_tag_name,
            "subdimension_name": subdimension_name,
            "exclusive_group": None,
            "description": description,
            "logic": {"op": "heuristic"},
        },
        "is_enabled": 1,
    }


def tags_for_dimension(catalog: Dict[str, Any], dimension_id: int) -> List[Dict[str, Any]]:
    subdimension_ids = {
        int(row["company_tag_subdimension_id"])
        for row in catalog["subdimensions"]
        if int(row["company_tag_dimension_id"]) == dimension_id
    }
    return [row for row in catalog["tags"] if int(row["company_tag_subdimension_id"]) in subdimension_ids]


def build_heuristic_rules(catalog: Dict[str, Any], selected_dimension_ids: List[int]) -> List[Dict[str, Any]]:
    selected = set(selected_dimension_ids or [REGION_DIMENSION_ID, SCENE_DIMENSION_ID])
    rules: List[Dict[str, Any]] = []
    if REGION_DIMENSION_ID in selected:
        for row in tags_for_dimension(catalog, REGION_DIMENSION_ID):
            subdimension_name = next(
                sub["company_tag_subdimension_name"]
                for sub in catalog["subdimensions"]
                if int(sub["company_tag_subdimension_id"]) == int(row["company_tag_subdimension_id"])
            )
            rules.append(
                make_heuristic_rule(
                    company_tag_id=int(row["company_tag_id"]),
                    company_tag_name=str(row["company_tag_name"]),
                    subdimension_name=str(subdimension_name),
                    description="基于所属街道/地区与地址文本的启发式匹配",
                )
            )
    if SCENE_DIMENSION_ID in selected:
        scene_tags = {str(row["company_tag_name"]): row for row in tags_for_dimension(catalog, SCENE_DIMENSION_ID)}
        for profile in SCENE_PROFILES:
            row = scene_tags.get(profile["tag_name"])
            if row is None:
                continue
            rules.append(
                make_heuristic_rule(
                    company_tag_id=int(row["company_tag_id"]),
                    company_tag_name=str(row["company_tag_name"]),
                    subdimension_name="应用场景",
                    description="基于经营范围、所属行业、企业名称与资质文本的关键词评分",
                )
            )
    return rules


def clone_rule_assignment(rule: Dict[str, Any], *, confidence: float, evidence: str) -> Dict[str, Any]:
    assignment = dict(rule)
    assignment["assigned_confidence"] = round(confidence, 2)
    assignment["assigned_evidence"] = evidence
    return assignment


def match_region_assignment(record: Dict[str, Any], region_rules_by_name: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | None:
    field_weights = [("subdistrict", 12), ("register_address_detail", 7), ("register_address", 6)]
    best_match: Dict[str, Any] | None = None
    for tag_name, rule in region_rules_by_name.items():
        for field_name, base_score in field_weights:
            text = normalize_text(record.get(field_name))
            if not text:
                continue
            if text == tag_name:
                score = base_score + 6
            elif tag_name in text:
                score = base_score
            else:
                continue
            if best_match is None or score > best_match["score"]:
                best_match = {
                    "score": score,
                    "assignment": clone_rule_assignment(
                        rule,
                        confidence=0.95 if field_name == "subdistrict" else 0.82,
                        evidence=f"{TEXT_SOURCE_LABELS.get(field_name, field_name)}命中“{tag_name}”",
                    ),
                }
    return best_match["assignment"] if best_match else None


def collect_scene_texts(record: Dict[str, Any]) -> List[Tuple[str, str, int]]:
    return [
        ("company_name", normalize_text(record.get("company_name")), 6),
        ("industry_belong", normalize_text(record.get("industry_belong")), 5),
        ("qualification_label", normalize_text(record.get("qualification_label")), 4),
        ("business_scope", normalize_text(record.get("business_scope")), 3),
    ]


def match_scene_assignments(record: Dict[str, Any], scene_rules_by_name: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    texts = collect_scene_texts(record)
    ranked: List[Dict[str, Any]] = []
    for profile in SCENE_PROFILES:
        rule = scene_rules_by_name.get(profile["tag_name"])
        if rule is None:
            continue
        score = 0
        evidences: List[str] = []
        for keyword in profile["keywords"]:
            lowered_keyword = keyword.lower()
            keyword_bonus = 2 if len(keyword) >= 4 else 0
            for field_name, text, weight in texts:
                if not text or lowered_keyword not in text.lower():
                    continue
                score += weight + keyword_bonus
                evidences.append(f"{TEXT_SOURCE_LABELS.get(field_name, field_name)}包含“{keyword}”")
                break
            if len(evidences) >= 3:
                break
        if score < 6:
            continue
        confidence = min(0.95, 0.45 + score / 30.0)
        ranked.append(
            {
                "score": score,
                "assignment": clone_rule_assignment(rule, confidence=confidence, evidence="；".join(evidences[:3])),
            }
        )
    ranked.sort(key=lambda item: (-item["score"], int(item["assignment"]["company_tag_id"])))
    return [item["assignment"] for item in ranked[:3]]


def compute_heuristic_assignments(
    heuristic_rules: List[Dict[str, Any]],
    records: Dict[int, Dict[str, Any]],
) -> Dict[int, List[Dict[str, Any]]]:
    assignments: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    region_rules_by_name = {
        rule["company_tag_name"]: rule
        for rule in heuristic_rules
        if rule["company_tag_subdimension_name"] in ("街道", "地区")
    }
    scene_rules_by_name = {
        rule["company_tag_name"]: rule
        for rule in heuristic_rules
        if rule["company_tag_subdimension_name"] == "应用场景"
    }
    for company_id, record in records.items():
        if region_rules_by_name:
            region_assignment = match_region_assignment(record, region_rules_by_name)
            if region_assignment is not None:
                assignments[company_id].append(region_assignment)
        if scene_rules_by_name:
            assignments[company_id].extend(match_scene_assignments(record, scene_rules_by_name))
    return assignments


def build_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    record = dict(DEFAULT_RECORD)
    record.update(
        {
            "company_name": normalize_text(raw.get("company_name")),
            "credit_code": normalize_text(raw.get("credit_code")),
            "establish_date": normalize_text(raw.get("establish_date")) or None,
            "register_capital": to_number(raw.get("register_capital")),
            "paid_capital": to_number(raw.get("paid_capital")),
            "employee_count": to_int(raw.get("employee_count")),
            "insured_count": to_int(raw.get("insured_count")),
            "contact_phone": normalize_text(raw.get("contact_phone")),
            "email_business": normalize_text(raw.get("email_business")),
            "register_address": normalize_text(raw.get("register_address")),
            "register_address_detail": normalize_text(raw.get("register_address_detail")),
            "business_scope": normalize_text(raw.get("business_scope")),
            "qualification_label": normalize_text(raw.get("qualification_label")),
            "industry_belong": normalize_text(raw.get("industry_belong")),
            "subdistrict": normalize_text(raw.get("subdistrict")),
            "is_micro_enterprise": to_bool(raw.get("is_micro_enterprise")),
            "is_general_taxpayer": to_bool(raw.get("is_general_taxpayer")),
            "is_high_tech_enterprise": to_bool(raw.get("is_high_tech_enterprise")),
        }
    )
    record["contact_phone_combined"] = record["contact_phone"]
    record["has_address"] = bool(record["register_address"] or record["register_address_detail"])
    record["_today"] = date.today()
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate auto tag rules for imported candidate companies.")
    parser.add_argument("--input-json", required=True, help="Path to JSON payload file")
    args = parser.parse_args()

    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    raw_records: List[Dict[str, Any]] = payload.get("records") or []
    dimension_ids: List[int] = [int(item) for item in payload.get("dimension_ids") or []]

    catalog = load_tag_catalog()
    base_rules = filter_rules(load_rules(), dimension_ids=dimension_ids)
    heuristic_rules = build_heuristic_rules(catalog, dimension_ids)

    records = {index + 1: build_record(raw) for index, raw in enumerate(raw_records)}
    static_assignments: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for company_id, record in records.items():
        for rule in base_rules:
            if int(rule.get("is_enabled", 0)) != 1:
                continue
            if evaluate_logic(rule["rule_definition"]["logic"], record):
                static_assignments[company_id].append(rule)

    heuristic_assignments = compute_heuristic_assignments(heuristic_rules, records)
    conflicts = find_conflicts(static_assignments)

    results = []
    for company_id, raw in enumerate(raw_records, start=1):
        assignments = []
        if static_assignments.get(company_id):
            assignments.extend(static_assignments[company_id])
        if heuristic_assignments.get(company_id):
            assignments.extend(heuristic_assignments[company_id])

        tags = []
        for rule in assignments:
            tags.append(
                {
                    "company_tag_id": int(rule["company_tag_id"]),
                    "company_tag_name": str(rule["company_tag_name"]),
                    "company_tag_dimension_name": next(
                        dim["company_tag_dimension_name"]
                        for dim in catalog["dimensions"]
                        for sub in catalog["subdimensions"]
                        if int(sub["company_tag_subdimension_id"]) == int(catalog["tags_by_id"][int(rule["company_tag_id"])]["company_tag_subdimension_id"])
                        and int(sub["company_tag_dimension_id"]) == int(dim["company_tag_dimension_id"])
                    ),
                    "company_tag_subdimension_name": str(rule["company_tag_subdimension_name"]),
                    "confidence": float(rule.get("assigned_confidence", 1.0)),
                    "evidence": str(rule.get("assigned_evidence", rule["company_tag_auto_rule_type"])),
                }
            )

        results.append(
            {
                "company_name": normalize_text(raw.get("company_name")),
                "credit_code": normalize_text(raw.get("credit_code")),
                "row_index": raw.get("row_index", company_id),
                "tag_count": len(tags),
                "tags": tags,
                "error_message": "",
            }
        )

    output = {
        "company_count": len(raw_records),
        "rule_count": len(base_rules) + len(heuristic_rules),
        "assignment_count": sum(item["tag_count"] for item in results),
        "conflicted_company_count": len({item["company_id"] for item in conflicts}),
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
