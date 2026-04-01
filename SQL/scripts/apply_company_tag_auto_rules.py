#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from company_tag_rule_engine import (
    RULES_JSON_PATH,
    evaluate_logic,
    find_conflicts,
    load_tag_catalog,
    managed_tag_ids,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = PROJECT_ROOT / "SQL" / "tmp"


BASE_COLUMNS = [
    "company_id",
    "company_name",
    "establish_date",
    "register_capital",
    "paid_capital",
    "employee_count",
    "insured_count",
    "contact_phone",
    "email_business",
    "register_address",
    "register_address_detail",
    "business_scope",
    "qualification_label",
    "industry_belong",
    "subdistrict",
    "is_micro_enterprise",
    "is_general_taxpayer",
    "has_recruitment",
    "has_patent",
    "has_work_copyright",
    "has_software_copyright",
    "is_high_tech_enterprise",
    "has_dishonest_execution",
    "has_chattel_mortgage",
    "has_business_abnormal",
    "has_legal_document",
    "has_admin_penalty",
    "has_bankruptcy_overlap",
    "has_env_penalty",
    "has_equity_freeze",
    "has_executed_person",
    "branch_count",
    "recruit_count",
    "patent_count",
    "work_copyright_count",
    "software_copyright_count",
    "dishonest_execution_count",
    "chattel_mortgage_count",
    "business_abnormal_count",
    "legal_doc_all_count",
    "admin_penalty_count",
    "bankruptcy_overlap_count",
    "env_penalty_count",
    "equity_freeze_count",
    "executed_person_count",
]

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
    {"tag_name": "疾病预防", "keywords": ["疾病预防", "预防服务", "疾病筛查", "早筛", "疫苗", "免疫接种", "体检服务"]},
    {"tag_name": "中医科", "keywords": ["中医", "中药", "中西医", "国医", "针灸", "推拿", "艾灸", "中医诊所"]},
    {"tag_name": "口腔科", "keywords": ["口腔", "牙科", "种植牙", "正畸", "义齿", "口腔科"]},
    {"tag_name": "眼科", "keywords": ["眼科", "眼视光", "视光", "视力矫正", "屈光", "青光眼", "白内障"]},
    {"tag_name": "疼痛科", "keywords": ["疼痛科", "疼痛治疗", "疼痛管理", "镇痛", "止痛"]},
    {"tag_name": "辅助科室", "keywords": ["检验科", "影像科", "病理科", "药房", "供应室", "放射科", "辅助科室"]},
    {"tag_name": "精神科", "keywords": ["精神科", "心理科", "精神卫生", "精神健康", "心理治疗"]},
    {"tag_name": "行政管理", "keywords": ["医院管理", "医疗管理", "医保管理", "行政管理", "运营管理", "诊所管理"]},
    {"tag_name": "后勤支持", "keywords": ["后勤支持", "医用物流", "仓储服务", "供应链管理", "消毒服务", "保洁服务", "后勤保障"]},
    {"tag_name": "肿瘤", "keywords": ["肿瘤", "癌症", "放疗", "化疗", "肿瘤科", "肿瘤诊疗"]},
    {"tag_name": "心血管疾病", "keywords": ["心血管", "心脏", "冠脉", "高血压", "冠心病", "心律"]},
    {"tag_name": "感染性疾病", "keywords": ["感染性疾病", "感染控制", "传染病", "病原检测", "抗感染"]},
    {"tag_name": "内分泌系统疾病", "keywords": ["内分泌", "甲状腺", "激素", "内分泌系统疾病"]},
    {"tag_name": "代谢性疾病", "keywords": ["代谢性疾病", "代谢管理", "肥胖管理", "痛风", "糖脂代谢"]},
    {"tag_name": "精神类疾病", "keywords": ["精神类疾病", "抑郁", "焦虑", "精神障碍", "睡眠障碍"]},
    {"tag_name": "神经系统疾病", "keywords": ["神经系统疾病", "神经内科", "脑神经", "帕金森", "癫痫"]},
    {"tag_name": "呼吸系统疾病", "keywords": ["呼吸系统疾病", "呼吸科", "肺病", "哮喘", "呼吸机"]},
    {"tag_name": "血液系统疾病", "keywords": ["血液系统疾病", "血液科", "白血病", "淋巴瘤", "贫血"]},
    {"tag_name": "消化系统疾病", "keywords": ["消化系统疾病", "消化科", "胃肠", "肝胆", "胰腺"]},
    {"tag_name": "眼部疾病", "keywords": ["眼部疾病", "眼底病", "白内障", "青光眼", "干眼"]},
    {"tag_name": "皮肤疾病", "keywords": ["皮肤疾病", "皮肤科", "皮炎", "皮肤治疗", "医美皮肤"]},
    {"tag_name": "生殖系统疾病", "keywords": ["生殖系统疾病", "生殖医学", "男科", "妇科", "不孕不育"]},
    {"tag_name": "罕见病", "keywords": ["罕见病", "孤儿药", "罕见疾病"]},
    {"tag_name": "泌尿系统疾病", "keywords": ["泌尿系统疾病", "泌尿科", "肾病", "透析", "前列腺"]},
    {"tag_name": "慢性病", "keywords": ["慢性病", "慢病", "慢病管理", "高血压", "糖尿病"]},
    {"tag_name": "脑部疾病", "keywords": ["脑部疾病", "脑病", "脑卒中", "脑血管", "颅脑"]},
    {"tag_name": "运动系统疾病", "keywords": ["运动系统疾病", "运动医学", "肌骨", "关节康复", "脊柱"]},
    {"tag_name": "骨科", "keywords": ["骨科", "骨病", "骨折", "脊柱外科", "关节外科"]},
]


def parse_env(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def mysql_command(env: Dict[str, str]) -> Tuple[List[str], Dict[str, str]]:
    host = env.get("DB_HOST", "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    cmd = [
        "mysql",
        "-h",
        host,
        "-P",
        env.get("DB_PORT", "3306"),
        "-u",
        env.get("DB_USER", "root"),
        "-D",
        env.get("DB_NAME", "industrial_chain"),
        "--default-character-set=utf8mb4",
        "--batch",
        "--raw",
        "--skip-column-names",
    ]
    child_env = os.environ.copy()
    if env.get("DB_PASSWORD"):
        child_env["MYSQL_PWD"] = env["DB_PASSWORD"]
    return cmd, child_env


def query_rows(sql: str, env: Dict[str, str]) -> List[List[str]]:
    cmd, child_env = mysql_command(env)
    cmd.extend(["-e", sql])
    result = subprocess.run(cmd, text=True, capture_output=True, env=child_env, check=True)
    rows: List[List[str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def run_mysql_sql(sql: str, env: Dict[str, str]) -> None:
    cmd, child_env = mysql_command(env)
    result = subprocess.run(cmd, text=True, input=sql, capture_output=True, env=child_env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "mysql command failed")


def load_rules() -> List[Dict[str, Any]]:
    rules = json.loads(RULES_JSON_PATH.read_text(encoding="utf-8"))
    for rule in rules:
        rule["company_tag_id"] = int(rule["company_tag_id"])
    return rules


def parse_int_csv(value: str | None) -> List[int]:
    if not value:
        return []
    result: List[int] = []
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        result.append(int(part))
    return result


def filter_rules(
    rules: List[Dict[str, Any]],
    *,
    dimension_ids: List[int] | None = None,
    company_tag_ids: List[int] | None = None,
) -> List[Dict[str, Any]]:
    allowed_dimension_ids = set(dimension_ids or [])
    allowed_company_tag_ids = set(company_tag_ids or [])

    if not allowed_dimension_ids and not allowed_company_tag_ids:
        return rules

    catalog = load_tag_catalog()
    subdimensions_by_id = {
        int(row["company_tag_subdimension_id"]): row for row in catalog["subdimensions"]
    }

    filtered: List[Dict[str, Any]] = []
    for rule in rules:
        company_tag_id = int(rule["company_tag_id"])
        if allowed_company_tag_ids and company_tag_id not in allowed_company_tag_ids:
            continue

        if allowed_dimension_ids:
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


def normalize_scalar(value: str) -> Any:
    if value == "NULL" or value == "":
        return None
    return value


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def make_heuristic_rule(
    *,
    company_tag_id: int,
    company_tag_name: str,
    subdimension_name: str,
    description: str,
) -> Dict[str, Any]:
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


def to_int(value: Any) -> int:
    if value in (None, "", "NULL"):
        return 0
    return int(value)


def fetch_base_records(env: Dict[str, str]) -> Dict[int, Dict[str, Any]]:
    sql = """
    SELECT
      b.company_id,
      REPLACE(REPLACE(REPLACE(COALESCE(b.company_name, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
      b.establish_date,
      b.register_capital,
      b.paid_capital,
      b.employee_count,
      b.insured_count,
      b.contact_phone,
      b.email_business,
      REPLACE(REPLACE(REPLACE(COALESCE(b.register_address, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
      REPLACE(REPLACE(REPLACE(COALESCE(b.register_address_detail, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
      REPLACE(REPLACE(REPLACE(COALESCE(b.business_scope, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
      REPLACE(REPLACE(REPLACE(COALESCE(b.qualification_label, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
      REPLACE(REPLACE(REPLACE(COALESCE(b.industry_belong, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
      REPLACE(REPLACE(REPLACE(COALESCE(b.subdistrict, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
      b.is_micro_enterprise,
      b.is_general_taxpayer,
      b.has_recruitment,
      b.has_patent,
      b.has_work_copyright,
      b.has_software_copyright,
      b.is_high_tech_enterprise,
      b.has_dishonest_execution,
      b.has_chattel_mortgage,
      b.has_business_abnormal,
      b.has_legal_document,
      b.has_admin_penalty,
      b.has_bankruptcy_overlap,
      b.has_env_penalty,
      b.has_equity_freeze,
      b.has_executed_person,
      COALESCE(c.branch_count, 0),
      COALESCE(c.recruit_count, 0),
      COALESCE(c.patent_count, 0),
      COALESCE(c.work_copyright_count, 0),
      COALESCE(c.software_copyright_count, 0),
      COALESCE(c.dishonest_execution_count, 0),
      COALESCE(c.chattel_mortgage_count, 0),
      COALESCE(c.business_abnormal_count, 0),
      COALESCE(c.legal_doc_all_count, 0),
      COALESCE(c.admin_penalty_count, 0),
      COALESCE(c.bankruptcy_overlap_count, 0),
      COALESCE(c.env_penalty_count, 0),
      COALESCE(c.equity_freeze_count, 0),
      COALESCE(c.executed_person_count, 0)
    FROM company_basic b
    LEFT JOIN company_basic_count c ON b.company_id = c.company_id
    ORDER BY b.company_id;
    """
    rows = query_rows(sql, env)
    records: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        record = dict(zip(BASE_COLUMNS, row))
        company_id = int(record["company_id"])
        normalized: Dict[str, Any] = {}
        for key, value in record.items():
            normalized[key] = normalize_scalar(value)
        records[company_id] = normalized
    return records


def fetch_group_concat_map(sql: str, env: Dict[str, str]) -> Dict[int, str]:
    rows = query_rows(sql, env)
    result: Dict[int, str] = {}
    for row in rows:
        if len(row) < 2:
            continue
        result[int(row[0])] = row[1]
    return result


def enrich_records(records: Dict[int, Dict[str, Any]], env: Dict[str, str]) -> None:
    phone_map = fetch_group_concat_map(
        "SELECT company_id, GROUP_CONCAT(DISTINCT contact_phone SEPARATOR '||') FROM company_contact_phone GROUP BY company_id;",
        env,
    )
    address_map = fetch_group_concat_map(
        "SELECT company_id, CAST(COUNT(*) AS CHAR) FROM company_address GROUP BY company_id;",
        env,
    )

    today = date.today()
    for company_id, record in records.items():
        phones: List[str] = []
        basic_phone = str(record.get("contact_phone") or "").strip()
        if basic_phone:
            phones.append(basic_phone)
        contact_phone_rows = phone_map.get(company_id, "")
        if contact_phone_rows:
            phones.extend(part for part in contact_phone_rows.split("||") if part)
        record["contact_phone_combined"] = " || ".join(dict.fromkeys(phones))
        record["has_address"] = bool(str(record.get("register_address") or "").strip()) or to_int(address_map.get(company_id)) > 0
        record["_today"] = today


def tags_for_dimension(catalog: Dict[str, Any], dimension_id: int) -> List[Dict[str, Any]]:
    subdimension_ids = {
        int(row["company_tag_subdimension_id"])
        for row in catalog["subdimensions"]
        if int(row["company_tag_dimension_id"]) == dimension_id
    }
    return [
        row
        for row in catalog["tags"]
        if int(row["company_tag_subdimension_id"]) in subdimension_ids
    ]


def build_heuristic_rules(
    catalog: Dict[str, Any],
    selected_dimension_ids: List[int],
) -> List[Dict[str, Any]]:
    selected = set(selected_dimension_ids)
    rules: List[Dict[str, Any]] = []

    if REGION_DIMENSION_ID in selected:
        for row in tags_for_dimension(catalog, REGION_DIMENSION_ID):
            rules.append(
                make_heuristic_rule(
                    company_tag_id=int(row["company_tag_id"]),
                    company_tag_name=str(row["company_tag_name"]),
                    subdimension_name=str(
                        next(
                            sub["company_tag_subdimension_name"]
                            for sub in catalog["subdimensions"]
                            if int(sub["company_tag_subdimension_id"]) == int(row["company_tag_subdimension_id"])
                        )
                    ),
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


def clone_rule_assignment(
    rule: Dict[str, Any],
    *,
    confidence: float,
    evidence: str,
) -> Dict[str, Any]:
    assignment = dict(rule)
    assignment["assigned_confidence"] = round(confidence, 2)
    assignment["assigned_evidence"] = evidence
    return assignment


def match_region_assignment(
    record: Dict[str, Any],
    region_rules_by_name: Dict[str, Dict[str, Any]],
) -> Dict[str, Any] | None:
    field_weights = [
        ("subdistrict", 12),
        ("register_address_detail", 7),
        ("register_address", 6),
    ]
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
                label = TEXT_SOURCE_LABELS.get(field_name, field_name)
                best_match = {
                    "score": score,
                    "assignment": clone_rule_assignment(
                        rule,
                        confidence=0.95 if field_name == "subdistrict" else 0.82,
                        evidence=f"{label}命中“{tag_name}”",
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


def match_scene_assignments(
    record: Dict[str, Any],
    scene_rules_by_name: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    texts = collect_scene_texts(record)
    ranked: List[Dict[str, Any]] = []

    for profile in SCENE_PROFILES:
        rule = scene_rules_by_name.get(profile["tag_name"])
        if rule is None:
            continue

        score = 0
        evidences: List[str] = []
        for keyword in profile["keywords"]:
            keyword_hit = False
            lowered_keyword = keyword.lower()
            keyword_bonus = 2 if len(keyword) >= 4 else 0
            for field_name, text, weight in texts:
                if not text or lowered_keyword not in text.lower():
                    continue
                score += weight + keyword_bonus
                evidences.append(f"{TEXT_SOURCE_LABELS.get(field_name, field_name)}包含“{keyword}”")
                keyword_hit = True
                break
            if keyword_hit and len(evidences) >= 3:
                break

        if score < 6:
            continue

        confidence = min(0.95, 0.45 + score / 30.0)
        ranked.append(
            {
                "score": score,
                "assignment": clone_rule_assignment(
                    rule,
                    confidence=confidence,
                    evidence="；".join(evidences[:3]),
                ),
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


def compute_assignments(
    rules: List[Dict[str, Any]],
    records: Dict[int, Dict[str, Any]],
) -> Tuple[Dict[int, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    assignments: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for company_id, record in records.items():
        for rule in rules:
            if int(rule.get("is_enabled", 0)) != 1:
                continue
            if evaluate_logic(rule["rule_definition"]["logic"], record):
                assignments[company_id].append(rule)
    conflicts = find_conflicts(assignments)
    return assignments, conflicts


def build_apply_sql(
    assignments: Dict[int, List[Dict[str, Any]]],
    rules: List[Dict[str, Any]],
    *,
    company_ids: List[int] | None = None,
) -> str:
    tag_ids = managed_tag_ids(rules)
    delete_tag_ids = ", ".join(str(tag_id) for tag_id in tag_ids)
    company_id_sql = ", ".join(str(company_id) for company_id in sorted(set(company_ids or [])))

    values_sql: List[str] = []
    for company_id in sorted(assignments):
        for rule in assignments[company_id]:
            confidence = float(rule.get("assigned_confidence", 1.0))
            values_sql.append(f"({company_id}, {int(rule['company_tag_id'])}, 2, {confidence:.2f}, NULL)")

    delete_filters = ["source = 2"]
    if delete_tag_ids:
        delete_filters.append(f"company_tag_id IN ({delete_tag_ids})")
    if company_id_sql:
        delete_filters.append(f"company_id IN ({company_id_sql})")

    statements = [
        "START TRANSACTION;",
        f"DELETE FROM company_tag_map WHERE {' AND '.join(delete_filters)};",
    ]
    if values_sql:
        statements.append(
            "INSERT INTO company_tag_map (company_id, company_tag_id, source, confidence, user_id)\nVALUES\n  "
            + ",\n  ".join(values_sql)
            + "\nON DUPLICATE KEY UPDATE source = VALUES(source), confidence = VALUES(confidence), user_id = VALUES(user_id), create_time = CURRENT_TIMESTAMP;"
        )
    statements.append("COMMIT;")
    return "\n".join(statements) + "\n"


def filter_records(records: Dict[int, Dict[str, Any]], company_ids: List[int] | None) -> Dict[int, Dict[str, Any]]:
    if not company_ids:
        return records
    company_id_set = set(company_ids)
    return {
        company_id: record
        for company_id, record in records.items()
        if company_id in company_id_set
    }


def build_json_summary(
    rules: List[Dict[str, Any]],
    assignments: Dict[int, List[Dict[str, Any]]],
    conflicts: List[Dict[str, Any]],
    records: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    catalog = load_tag_catalog()
    subdimensions_by_id = {
        int(row["company_tag_subdimension_id"]): row for row in catalog["subdimensions"]
    }
    dimensions_by_id = {
        int(row["company_tag_dimension_id"]): row for row in catalog["dimensions"]
    }

    results: List[Dict[str, Any]] = []
    for company_id in sorted(records):
        company_rules = assignments.get(company_id, [])
        company_tags: List[Dict[str, Any]] = []
        for rule in company_rules:
            tag_row = catalog["tags_by_id"].get(int(rule["company_tag_id"]))
            if tag_row is None:
                continue
            subdimension = subdimensions_by_id.get(int(tag_row["company_tag_subdimension_id"]))
            dimension = (
                dimensions_by_id.get(int(subdimension["company_tag_dimension_id"]))
                if subdimension is not None
                else None
            )
            company_tags.append(
                {
                    "company_tag_id": int(rule["company_tag_id"]),
                    "company_tag_name": rule["company_tag_name"],
                    "company_tag_subdimension_name": (
                        str(subdimension["company_tag_subdimension_name"]) if subdimension else None
                    ),
                    "company_tag_dimension_name": (
                        str(dimension["company_tag_dimension_name"]) if dimension else None
                    ),
                    "rule_type": rule["company_tag_auto_rule_type"],
                    "confidence": rule.get("assigned_confidence"),
                    "evidence": rule.get("assigned_evidence"),
                }
            )

        results.append(
            {
                "company_id": company_id,
                "tag_count": len(company_tags),
                "tags": company_tags,
            }
        )

    return {
        "company_count": len(records),
        "rule_count": len(rules),
        "assignment_count": sum(len(rows) for rows in assignments.values()),
        "conflicted_company_count": len({item["company_id"] for item in conflicts}),
        "conflicts": conflicts,
        "results": results,
    }


def render_report(
    report_path: Path,
    rules: List[Dict[str, Any]],
    assignments: Dict[int, List[Dict[str, Any]]],
    conflicts: List[Dict[str, Any]],
    records: Dict[int, Dict[str, Any]],
) -> None:
    tag_counts: Dict[int, int] = defaultdict(int)
    for company_id, rows in assignments.items():
        for row in rows:
            tag_counts[int(row["company_tag_id"])] += 1

    rules_by_tag_id = {int(rule["company_tag_id"]): rule for rule in rules}
    direct_rules = [rule for rule in rules if rule["company_tag_auto_rule_type"] == "direct_match"]
    derived_rules = [rule for rule in rules if rule["company_tag_auto_rule_type"] == "derived_rule"]
    heuristic_rules = [rule for rule in rules if rule["company_tag_auto_rule_type"] == HEURISTIC_RULE_TYPE]
    assigned_company_count = sum(1 for rows in assignments.values() if rows)
    total_assignment_count = sum(len(rows) for rows in assignments.values())

    lines = [
        "# 企业标签自动打标执行报告",
        "",
        f"- 生成日期: {date.today().isoformat()}",
        f"- 规则文件: `{RULES_JSON_PATH}`",
        f"- 企业总数: {len(records)}",
        f"- 启用规则数: {len(rules)}",
        f"- `direct_match`: {len(direct_rules)}",
        f"- `derived_rule`: {len(derived_rules)}",
        f"- `{HEURISTIC_RULE_TYPE}`: {len(heuristic_rules)}",
        f"- 至少命中 1 个标签的企业数: {assigned_company_count}",
        f"- 总打标条数: {total_assignment_count}",
        f"- 互斥冲突数: {len(conflicts)}",
        "",
        "## 标签命中数",
        "",
        "| 标签ID | 子维度 | 标签 | 规则类型 | 企业数 |",
        "| --- | --- | --- | --- | --- |",
    ]

    for tag_id in sorted(rules_by_tag_id):
        rule = rules_by_tag_id[tag_id]
        lines.append(
            f"| {tag_id} | {rule['company_tag_subdimension_name']} | {rule['company_tag_name']} | "
            f"{rule['company_tag_auto_rule_type']} | {tag_counts.get(tag_id, 0)} |"
        )

    lines.extend(["", "## 互斥冲突", ""])
    if not conflicts:
        lines.append("无冲突。")
    else:
        lines.extend(
            [
                "| company_id | exclusive_group | tag_ids | tag_names |",
                "| --- | --- | --- | --- |",
            ]
        )
        for conflict in conflicts[:100]:
            lines.append(
                f"| {conflict['company_id']} | {conflict['exclusive_group']} | "
                f"{', '.join(str(tag_id) for tag_id in conflict['tag_ids'])} | "
                f"{' / '.join(conflict['tag_names'])} |"
            )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply first-wave company tag auto rules to company_tag_map.")
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env"), help="Path to .env file")
    parser.add_argument(
        "--report",
        default=str(TMP_ROOT / f"company-tag-auto-rule-apply-report-{date.today().isoformat()}.md"),
        help="Markdown report output path",
    )
    parser.add_argument("--apply", action="store_true", help="Write computed auto tags into company_tag_map")
    parser.add_argument("--company-ids", default="", help="Comma-separated company_id list to limit evaluation scope")
    parser.add_argument("--dimension-ids", default="", help="Comma-separated company_tag_dimension_id list to limit rule scope")
    parser.add_argument("--tag-ids", default="", help="Comma-separated company_tag_id list to limit rule scope")
    parser.add_argument("--json-output", action="store_true", help="Print a JSON summary instead of plain logs")
    args = parser.parse_args()

    env = parse_env(Path(args.env_file))
    company_ids = parse_int_csv(args.company_ids)
    dimension_ids = parse_int_csv(args.dimension_ids)
    tag_ids = parse_int_csv(args.tag_ids)

    catalog = load_tag_catalog()
    base_rules = filter_rules(load_rules(), dimension_ids=dimension_ids, company_tag_ids=tag_ids)
    heuristic_rules = build_heuristic_rules(catalog, dimension_ids)
    if tag_ids:
        allowed_tag_ids = set(tag_ids)
        heuristic_rules = [
            rule for rule in heuristic_rules if int(rule["company_tag_id"]) in allowed_tag_ids
        ]
    rules = base_rules + heuristic_rules
    records = filter_records(fetch_base_records(env), company_ids)
    enrich_records(records, env)
    static_assignments, conflicts = compute_assignments(base_rules, records)
    heuristic_assignments = compute_heuristic_assignments(heuristic_rules, records)
    assignments: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for company_id in sorted(records):
        if static_assignments.get(company_id):
            assignments[company_id].extend(static_assignments[company_id])
        if heuristic_assignments.get(company_id):
            assignments[company_id].extend(heuristic_assignments[company_id])
    summary = build_json_summary(rules, assignments, conflicts, records)

    report_path = Path(args.report)
    render_report(report_path, rules, assignments, conflicts, records)
    if args.json_output:
        if conflicts:
            raise RuntimeError(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"[ok] generated report {report_path}")
        print(f"[ok] companies={len(records)}")
        print(f"[ok] rules={len(rules)}")
        print(f"[ok] assignments={sum(len(rows) for rows in assignments.values())}")
        print(f"[ok] conflicted_companies={len({item['company_id'] for item in conflicts})}")

    if conflicts:
        raise RuntimeError("检测到互斥组冲突，已停止写入 company_tag_map，请先修正规则")

    if not args.apply:
        if args.json_output:
            print(json.dumps(summary, ensure_ascii=False))
        return 0

    run_mysql_sql(build_apply_sql(assignments, rules, company_ids=company_ids), env)
    if args.json_output:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print("[ok] applied auto tags into company_tag_map")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise
