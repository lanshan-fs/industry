#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Set, Tuple

from _import_utils import parse_env, query_rows, run_mysql_sql


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = PROJECT_ROOT / "SQL"
TMP_ROOT = SQL_ROOT / "tmp"
RULES_JSON_PATH = SQL_ROOT / "data" / "category_industry_company_rules.json"
CHAIN_JSON_PATH = SQL_ROOT / "data" / "chain_industry_seed.json"

TEXT_COLUMNS = ["company_name", "industry_belong", "business_scope", "qualification_label"]
STAGE_NUMBERS = {"upstream": 1, "midstream": 2, "downstream": 3}
FIELD_WEIGHTS = {
    "industry_belong": 8,
    "company_name": 6,
    "qualification_label": 4,
    "business_scope": 2,
}
MIN_PRIMARY_SCORE = 8
MIN_SECONDARY_SCORE = 7
SECONDARY_SCORE_GAP = 4
MAX_SECONDARY_TAGS = 2
GENERIC_KEYWORDS = {
    "医疗",
    "健康",
    "医院",
    "门诊部",
    "技术服务",
    "技术开发",
    "技术咨询",
    "技术交流",
    "技术转让",
    "技术推广",
    "销售",
    "零售",
    "批发",
    "软件开发",
    "中药",
    "西药",
}
DIRECT_INDUSTRY_MAP = {
    "门诊部（所）": "0403",
    "专科医院": "0403",
    "综合医院": "0403",
    "中医医院": "0403",
    "卫生": "0403",
    "其他未列明卫生服务": "0403",
    "西药零售": "0402",
    "中药零售": "0402",
    "药品零售": "0402",
    "医疗用品及器材零售": "0402",
    "医疗器械零售": "0402",
    "护理机构服务": "0404",
    "老年人、残疾人养护服务": "0404",
    "医疗用品及器材批发": "0401",
    "医疗器械批发": "0401",
    "药品批发": "0401",
    "医药批发": "0401",
    "西药批发": "0401",
    "中药批发": "0401",
    "体外诊断试剂制造": "0301",
    "医疗器械设备制造": "0311",
    "制药专用设备制造": "0311",
}
DIRECT_INDUSTRY_CONTAINS_MAP = {
    "医疗用品及器材批发": "0401",
    "医疗用品及器材零售": "0402",
    "医疗器械批发": "0401",
    "医疗器械零售": "0402",
    "医疗设备及器械制造": "0311",
    "卫生材料及医药用品制造": "0310",
    "第三方医学检验": "0406",
    "检验检测服务": "0406",
    "中医诊所": "0404",
    "口腔诊所": "0404",
    "医疗美容": "0404",
    "医美": "0404",
}
SOFT_INDUSTRY_HINTS = {
    "0602": [
        "医学研究和试验发展",
        "研究和试验发展",
        "工程和技术研究和试验发展",
        "自然科学研究和试验发展",
        "生物技术推广服务",
    ],
}
CATEGORY_EXTRA_ALIASES = {
    "0101": ["智慧医院", "智慧诊疗", "医疗信息系统", "医院信息系统", "his系统", "lis系统", "pacs"],
    "0102": ["互联网健康", "健康平台", "患者管理平台", "慢病管理平台"],
    "0103": ["数字疗法", "数字治疗", "慢病管理", "远程康复", "睡眠管理"],
    "0201": ["脑机接口", "医疗机器人", "智能诊断", "ai辅助诊断"],
    "0301": ["体外诊断", "ivd", "poct", "诊断试剂", "分子诊断", "医学检验"],
    "0302": ["影像设备", "医学影像", "超声设备", "ct", "mri", "核磁", "内窥镜"],
    "0303": ["治疗设备", "放疗设备", "手术机器人", "能量治疗"],
    "0304": ["呼吸机", "监护仪", "麻醉机", "ecmo", "生命支持"],
    "0305": ["康复设备", "康复机器人", "康复辅具", "理疗设备"],
    "0306": ["辅助诊断软件", "诊断辅助软件", "医疗辅助软件"],
    "0307": ["家用医疗", "血糖仪", "血压计", "制氧机", "助听器"],
    "0308": ["高值耗材", "介入器械", "支架", "球囊", "导管"],
    "0309": ["植入器械", "植入材料", "心脏起搏器", "人工关节"],
    "0310": ["低值耗材", "敷料", "输液器", "注射器", "穿刺"],
    "0311": ["医疗器械制造", "医疗装备制造", "制药装备", "设备制造"],
    "0401": ["医药流通", "医药配送", "药品批发", "供应链配送", "医疗用品批发"],
    "0402": ["药店", "药房", "连锁药房", "西药零售", "器材零售"],
    "0403": ["综合医院", "医院管理", "门诊部", "卫生院", "社区卫生服务中心"],
    "0404": ["医美", "医疗美容", "口腔", "眼科", "体检", "中医诊所", "康复护理", "护理服务", "养生保健"],
    "0405": ["互联网医疗", "在线问诊", "在线诊疗", "远程问诊", "互联网医院"],
    "0406": ["检验中心", "病理中心", "影像中心", "第三方检验", "第三方医学检验"],
    "0407": ["健康险", "保险科技", "tpa", "保险支付"],
    "0501": ["化学制药", "化学药", "原料药", "化学制剂", "西药制剂"],
    "0502": ["生物制品", "生物药", "疫苗", "抗体药物", "细胞治疗", "基因治疗"],
    "0503": ["中药", "中成药", "中药饮片", "中医药"],
    "0601": ["ai药物研发平台", "ai药物发现", "药物发现平台", "分子设计平台"],
    "0602": ["cro", "ai cro", "合同研发", "临床前研究服务", "药物研发服务"],
    "0603": ["创新药研发", "自研管线", "候选药物", "管线研发"],
    "0604": ["药物研发软件", "药研工具平台", "分子模拟软件", "药物筛选软件"],
    "0605": ["肿瘤药物研发", "罕见病药物研发", "神经免疫疗法"],
}
CONSUMER_SERVICE_NAME_HINTS = [
    "医疗美容",
    "医美",
    "口腔",
    "眼科",
    "体检",
    "中医诊所",
    "专科诊所",
]
PHARMA_RETAIL_NAME_HINTS = [
    "医药",
    "药业",
    "药物",
    "药品",
    "药学",
    "制药",
    "制剂",
    "原料药",
    "生物制品",
    "生物医药",
]
DIGITAL_NAME_HINTS = ["智慧医疗", "医疗数据", "数字医疗", "医疗信息", "his", "lis", "pacs", "云医", "医疗科技"]
HEALTH_NAME_HINTS = ["健康管理", "慢病", "健康科技", "健康服务"]
INTERNET_HOSPITAL_NAME_HINTS = ["互联网医院", "在线问诊", "在线诊疗", "远程问诊"]
SERVICE_NAME_HINTS = ["科技", "技术", "研究院", "研究所", "研究中心", "实验室", "服务"]
BIO_NAME_HINTS = ["生物", "疫苗", "抗体", "生物药", "基因", "细胞"]
DEVICE_NAME_HINTS = ["医疗器械", "设备", "仪器", "助听器", "辅具", "影像", "内窥镜", "康复"]
MEDICAL_TECH_NAME_HINTS = ["医疗科技", "医疗技术", "数智", "数科", "医疗数据", "智慧", "云医", "互联网医疗"]
MEDICAL_HEALTH_NAME_HINTS = ["医疗管理", "健康管理", "大健康", "健康产业", "健康小屋", "医疗管理咨询"]
FALLBACK_TECH_INDUSTRY_HINTS = [
    "其他科技推广服务业",
    "其他技术推广服务",
    "生物技术推广服务",
    "医学研究和试验发展",
    "研究和试验发展",
    "工程和技术研究和试验发展",
    "自然科学研究和试验发展",
    "科技推广和应用服务业",
    "科技中介服务",
    "专业技术服务业",
]
FALLBACK_DIGITAL_INDUSTRY_HINTS = [
    "其他未列明信息技术服务业",
    "基础软件开发",
    "应用软件开发",
    "其他软件开发",
    "软件和信息技术服务业",
    "信息技术咨询服务",
    "信息系统集成服务",
    "互联网和相关服务",
    "互联网其他信息服务",
    "其他互联网平台",
    "其他数字内容服务",
    "物联网技术服务",
]
CATEGORY_CLUSTERS = {
    "0101": "digital",
    "0102": "digital",
    "0103": "digital",
    "0201": "digital",
    "0301": "device",
    "0302": "device",
    "0303": "device",
    "0304": "device",
    "0305": "device",
    "0306": "device",
    "0307": "device",
    "0308": "device",
    "0309": "device",
    "0310": "device",
    "0311": "device",
    "0401": "channel",
    "0402": "channel",
    "0403": "service",
    "0404": "service",
    "0405": "service",
    "0406": "service",
    "0407": "service",
    "0501": "pharma",
    "0502": "pharma",
    "0503": "pharma",
    "0601": "rnd",
    "0602": "rnd",
    "0603": "rnd",
    "0604": "rnd",
    "0605": "rnd",
}
EXCLUSIVE_CODE_GROUPS = [
    {"0401", "0402"},
    {"0403", "0404", "0406"},
    {"0501", "0502", "0503"},
]
ALLOWED_MULTI_PAIRS = {
    ("0101", "0403"),
    ("0101", "0405"),
    ("0102", "0405"),
    ("0103", "0404"),
    ("0301", "0406"),
    ("0311", "0401"),
    ("0311", "0402"),
    ("0401", "0311"),
    ("0402", "0311"),
    ("0403", "0101"),
    ("0403", "0404"),
    ("0403", "0405"),
    ("0404", "0403"),
    ("0404", "0103"),
    ("0404", "0405"),
    ("0405", "0101"),
    ("0405", "0102"),
    ("0405", "0403"),
    ("0405", "0404"),
    ("0406", "0301"),
    ("0601", "0501"),
    ("0601", "0502"),
    ("0602", "0501"),
    ("0602", "0502"),
    ("0603", "0501"),
    ("0603", "0502"),
}
ALLOWED_MULTI_CLUSTER_PAIRS = {
    ("channel", "device"),
    ("device", "channel"),
    ("channel", "pharma"),
    ("pharma", "channel"),
    ("channel", "digital"),
    ("digital", "channel"),
}


def normalize_text(value: str) -> str:
    return re.sub(r"[\s\-/+()（）【】\[\]{}|,:：;；、，。.\"'·]+", "", (value or "").lower())


def load_rules() -> List[Dict[str, object]]:
    rules = json.loads(RULES_JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"{RULES_JSON_PATH} 缺少有效规则")
    for rule in rules:
        rule["include_any"] = [normalize_text(str(item)) for item in rule.get("include_any", []) if str(item).strip()]
        rule["exclude_any"] = [normalize_text(str(item)) for item in rule.get("exclude_any", []) if str(item).strip()]
    return rules


def load_stage_map() -> Dict[str, int]:
    seeds = json.loads(CHAIN_JSON_PATH.read_text(encoding="utf-8"))
    return {str(item["category_level_code"]): STAGE_NUMBERS[str(item["stage_key"])] for item in seeds}


def fetch_category_maps(env: Dict[str, str]) -> Tuple[Dict[str, int], Dict[str, str]]:
    rows = query_rows(
        "SELECT category_level_code, category_id, category_name FROM category_industry WHERE category_level = 1 AND field_belong = 1;",
        env,
    )
    code_to_id: Dict[str, int] = {}
    code_to_name: Dict[str, str] = {}
    for code, category_id, name in rows:
        code_to_id[str(code)] = int(category_id)
        code_to_name[str(code)] = str(name)
    return code_to_id, code_to_name


def fetch_company_rows(env: Dict[str, str]) -> List[Dict[str, object]]:
    rows = query_rows(
        """
        SELECT
          company_id,
          REPLACE(REPLACE(REPLACE(COALESCE(company_name, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
          REPLACE(REPLACE(REPLACE(COALESCE(industry_belong, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
          REPLACE(REPLACE(REPLACE(COALESCE(business_scope, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' '),
          REPLACE(REPLACE(REPLACE(COALESCE(qualification_label, ''), CHAR(9), ' '), CHAR(10), ' '), CHAR(13), ' ')
        FROM company_basic
        ORDER BY company_id;
        """,
        env,
    )
    companies: List[Dict[str, object]] = []
    for company_id, company_name, industry_belong, business_scope, qualification_label in rows:
        companies.append(
            {
                "company_id": int(company_id),
                "company_name": company_name,
                "industry_belong": industry_belong,
                "business_scope": business_scope,
                "qualification_label": qualification_label,
            }
        )
    return companies


def normalized_company_fields(company: Dict[str, object]) -> Dict[str, str]:
    return {column: normalize_text(str(company.get(column, ""))) for column in TEXT_COLUMNS}


def company_text(company: Dict[str, object]) -> str:
    fields = normalized_company_fields(company)
    return " ".join(fields[column] for column in TEXT_COLUMNS if fields[column])


def is_generic_keyword(keyword: str) -> bool:
    text = normalize_text(keyword)
    return text in {normalize_text(item) for item in GENERIC_KEYWORDS} or len(text) <= 2


def build_rule_profiles(
    rules: List[Dict[str, object]],
    code_to_name: Dict[str, str],
) -> Dict[str, Dict[str, object]]:
    profiles: Dict[str, Dict[str, object]] = {}
    for rule in rules:
        code = str(rule["category_level_code"])
        category_name = code_to_name.get(code, code)
        include_keywords = [normalize_text(str(item)) for item in rule.get("include_any", []) if str(item).strip()]
        exclude_keywords = [normalize_text(str(item)) for item in rule.get("exclude_any", []) if str(item).strip()]
        alias_keywords = [normalize_text(category_name)]
        alias_keywords.extend(normalize_text(item) for item in CATEGORY_EXTRA_ALIASES.get(code, []))
        strong_keywords = [keyword for keyword in include_keywords if not is_generic_keyword(keyword)]
        weak_keywords = [keyword for keyword in include_keywords if is_generic_keyword(keyword)]
        profiles[code] = {
            "code": code,
            "category_name": category_name,
            "include_keywords": include_keywords,
            "exclude_keywords": exclude_keywords,
            "alias_keywords": [keyword for keyword in dict.fromkeys(alias_keywords) if keyword],
            "strong_keywords": strong_keywords,
            "weak_keywords": weak_keywords,
        }
    return profiles


def direct_industry_code(fields: Dict[str, str]) -> str | None:
    industry_text = fields.get("industry_belong", "")
    for raw_text, code in DIRECT_INDUSTRY_MAP.items():
        if normalize_text(raw_text) == industry_text:
            return code
    for raw_text, code in DIRECT_INDUSTRY_CONTAINS_MAP.items():
        if normalize_text(raw_text) in industry_text:
            return code
    return None


def soft_industry_hint_score(fields: Dict[str, str], code: str) -> int:
    industry_text = fields.get("industry_belong", "")
    if not industry_text:
        return 0
    for raw_text in SOFT_INDUSTRY_HINTS.get(code, []):
        normalized_hint = normalize_text(raw_text)
        if industry_text == normalized_hint:
            return 6
        if normalized_hint in industry_text:
            return 4
    return 0


def score_keyword_in_field(keyword: str, field_text: str, field_name: str) -> int:
    if not keyword or not field_text:
        return 0
    base = FIELD_WEIGHTS[field_name]
    if field_text == keyword:
        return base + 8
    if keyword in field_text:
        bonus = 4 if field_name == "industry_belong" else 2 if field_name == "company_name" else 1
        return base + bonus
    return 0


def score_category(fields: Dict[str, str], profile: Dict[str, object]) -> Tuple[int, List[str]]:
    for keyword in profile["exclude_keywords"]:
        if any(keyword in fields[field_name] for field_name in TEXT_COLUMNS if fields[field_name]):
            return 0, []

    direct_code = direct_industry_code(fields)
    score = 0
    evidences: List[str] = []
    strong_hit_count = 0
    alias_hit = False
    soft_hint_hit = False

    if direct_code == profile["code"]:
        score += 18
        alias_hit = True
        evidences.append("所属行业命中高置信行业归属")

    soft_hint_score = soft_industry_hint_score(fields, profile["code"])
    if soft_hint_score > 0:
        score += soft_hint_score
        soft_hint_hit = True
        evidences.append("所属行业命中弱行业归属提示")

    for alias in profile["alias_keywords"]:
        alias_score = score_keyword_in_field(alias, fields["industry_belong"], "industry_belong")
        if alias_score > 0:
            score += alias_score
            alias_hit = True
            evidences.append(f"所属行业命中别名“{alias}”")
            break

    if not alias_hit:
        for alias in profile["alias_keywords"]:
            alias_score = score_keyword_in_field(alias, fields["company_name"], "company_name")
            if alias_score > 0 and not is_generic_keyword(alias):
                score += alias_score
                alias_hit = True
                evidences.append(f"企业名称命中别名“{alias}”")
                break

    for keyword in profile["strong_keywords"]:
        for field_name in ("industry_belong", "company_name", "qualification_label", "business_scope"):
            hit_score = score_keyword_in_field(keyword, fields[field_name], field_name)
            if hit_score <= 0:
                continue
            if field_name == "business_scope" and is_generic_keyword(keyword):
                continue
            score += hit_score
            strong_hit_count += 1
            evidences.append(f"{field_name}命中“{keyword}”")
            break

    for keyword in profile["weak_keywords"]:
        for field_name in ("industry_belong", "company_name", "qualification_label"):
            hit_score = score_keyword_in_field(keyword, fields[field_name], field_name)
            if hit_score <= 0:
                continue
            score += max(1, hit_score - 4)
            evidences.append(f"{field_name}弱命中“{keyword}”")
            break

    if strong_hit_count == 0 and direct_code != profile["code"] and not alias_hit and not soft_hint_hit:
        return 0, []

    if not evidences:
        return 0, []

    return score, evidences[:3]


def score_legacy_rule(fields: Dict[str, str], rule: Dict[str, object]) -> Tuple[int, List[str]]:
    score = 0
    evidences: List[str] = []
    hit_fields = 0
    for field_name in ("industry_belong", "company_name", "qualification_label", "business_scope"):
        best_keyword = ""
        best_score = 0
        field_text = fields[field_name]
        if not field_text:
            continue
        for keyword in rule.get("include_any", []):
            if not keyword or keyword not in field_text:
                continue
            base_score = FIELD_WEIGHTS[field_name]
            if is_generic_keyword(keyword):
                base_score = max(1, base_score - 3)
            if base_score > best_score:
                best_score = base_score
                best_keyword = keyword
        if best_score <= 0:
            continue
        hit_fields += 1
        score += best_score
        evidences.append(f"{field_name}命中旧规则词“{best_keyword}”")
    if hit_fields >= 2:
        score += 2
    return score, evidences[:3]


def is_direct_match(fields: Dict[str, str], code: str) -> bool:
    return direct_industry_code(fields) == code


def cluster_of(code: str) -> str:
    return CATEGORY_CLUSTERS.get(code, "")


def are_exclusive_codes(code_a: str, code_b: str) -> bool:
    if code_a == code_b:
        return True
    for group in EXCLUSIVE_CODE_GROUPS:
        if code_a in group and code_b in group:
            return True
    return False


def can_coexist(primary_code: str, candidate_code: str, primary_score: int, candidate_score: int) -> bool:
    if (primary_code, candidate_code) in ALLOWED_MULTI_PAIRS:
        return True
    if are_exclusive_codes(primary_code, candidate_code):
        return False
    primary_cluster = cluster_of(primary_code)
    candidate_cluster = cluster_of(candidate_code)
    if "0311" in {primary_code, candidate_code} and primary_cluster == "device" and candidate_cluster == "device":
        return True
    if (primary_cluster, candidate_cluster) in ALLOWED_MULTI_CLUSTER_PAIRS:
        return True
    if (
        primary_cluster
        and primary_cluster == candidate_cluster
        and primary_score >= 10
        and candidate_score >= 10
        and candidate_score >= primary_score - 2
    ):
        return True
    if candidate_score >= primary_score and candidate_score >= 12:
        return True
    return False


def has_identity_evidence(evidences: List[str]) -> bool:
    for evidence in evidences:
        if evidence.startswith("所属行业命中"):
            return True
        if evidence.startswith("industry_belong命中旧规则词"):
            return True
        if evidence.startswith("industry_belong弱命中"):
            return True
        if evidence.startswith("企业名称命中别名"):
            return True
        if evidence.startswith("company_name命中"):
            return True
        if evidence.startswith("qualification_label命中"):
            return True
    return False


def company_name_has_any(fields: Dict[str, str], raw_keywords: List[str]) -> bool:
    company_name = fields.get("company_name", "")
    return any(normalize_text(keyword) in company_name for keyword in raw_keywords)


def allow_pair_by_business_boundary(
    primary_code: str,
    candidate_code: str,
    fields: Dict[str, str],
    candidate_evidences: List[str],
) -> bool:
    if {primary_code, candidate_code} == {"0403", "0404"}:
        return company_name_has_any(fields, CONSUMER_SERVICE_NAME_HINTS)
    if primary_code == "0402" and candidate_code in {"0501", "0502"}:
        return company_name_has_any(fields, PHARMA_RETAIL_NAME_HINTS) or any(
            evidence.startswith("company_name命中") or evidence.startswith("企业名称命中别名")
            for evidence in candidate_evidences
        )
    return True


def build_ranked_matches(
    fields: Dict[str, str],
    normalized_text: str,
    rule_profiles: Dict[str, Dict[str, object]],
    rule_map: Dict[str, Dict[str, object]],
    code_to_id: Dict[str, int],
    min_score: int = 1,
) -> List[Tuple[int, str, List[str]]]:
    ranked_matches: List[Tuple[int, str, List[str]]] = []
    for code, profile in rule_profiles.items():
        if code not in code_to_id:
            continue
        score, evidences = score_category(fields, profile)
        legacy_rule = rule_map.get(code)
        if legacy_rule and matches_rule(normalized_text, legacy_rule):
            legacy_score, legacy_evidences = score_legacy_rule(fields, legacy_rule)
            if legacy_score > score:
                score = legacy_score
                evidences = legacy_evidences
            elif score > 0:
                score += 2
        if score >= min_score:
            ranked_matches.append((score, code, evidences))
    ranked_matches.sort(key=lambda item: (-item[0], item[1]))
    return ranked_matches


def score_to_confidence(score: int, fallback: bool = False, secondary: bool = False) -> float:
    if fallback:
        return 0.58 if score >= 6 else 0.52
    if secondary:
        return round(min(0.88, 0.45 + score / 25), 2)
    return round(min(0.95, 0.55 + score / 25), 2)


def choose_low_score_primary(
    ranked_matches: List[Tuple[int, str, List[str]]],
    fields: Dict[str, str],
) -> Tuple[str | None, float]:
    if not ranked_matches:
        return None, 0.0
    top_score, top_code, top_evidences = ranked_matches[0]
    name_code = fallback_code_from_name(fields)
    if top_code == "0602" and name_code and name_code != "0602":
        return name_code, 0.57
    if top_code in {"0101", "0102"} and name_code and name_code not in {"0101", "0102", "0602"}:
        return name_code, 0.57
    if top_score >= 6 and (has_identity_evidence(top_evidences) or is_direct_match(fields, top_code)):
        return top_code, score_to_confidence(top_score, fallback=True)
    if top_score >= 4 and company_name_has_any(fields, DEVICE_NAME_HINTS + DIGITAL_NAME_HINTS + BIO_NAME_HINTS + PHARMA_RETAIL_NAME_HINTS):
        return top_code, score_to_confidence(top_score, fallback=True)
    return None, 0.0


def fallback_code_from_name(fields: Dict[str, str]) -> str | None:
    if company_name_has_any(fields, INTERNET_HOSPITAL_NAME_HINTS):
        return "0405"
    if company_name_has_any(fields, CONSUMER_SERVICE_NAME_HINTS):
        return "0404"
    if company_name_has_any(fields, ["门诊", "医院", "诊所", "卫生院"]):
        return "0403"
    if company_name_has_any(fields, MEDICAL_TECH_NAME_HINTS):
        return "0101"
    if company_name_has_any(fields, MEDICAL_HEALTH_NAME_HINTS):
        return "0102"
    if company_name_has_any(fields, DIGITAL_NAME_HINTS):
        return "0101"
    if company_name_has_any(fields, HEALTH_NAME_HINTS):
        return "0102"
    if company_name_has_any(fields, ["中医药", "本草", "中药", "中成药", "中药饮片"]):
        return "0503"
    if company_name_has_any(fields, BIO_NAME_HINTS):
        return "0502"
    if company_name_has_any(fields, PHARMA_RETAIL_NAME_HINTS + ["药业", "药厂", "化学药"]):
        return "0501"
    if company_name_has_any(fields, ["影像", "超声", "ct", "mri", "内窥镜"]):
        return "0302"
    if company_name_has_any(fields, ["康复", "辅具", "助听器"]):
        return "0305"
    if company_name_has_any(fields, DEVICE_NAME_HINTS):
        return "0311"
    if company_name_has_any(fields, SERVICE_NAME_HINTS):
        return "0602"
    return None


def fallback_code_from_industry(fields: Dict[str, str]) -> str | None:
    industry_text = fields.get("industry_belong", "")
    if not industry_text:
        return None
    direct_code = direct_industry_code(fields)
    if direct_code:
        return direct_code
    name_code = fallback_code_from_name(fields)
    if any(normalize_text(item) in industry_text for item in FALLBACK_DIGITAL_INDUSTRY_HINTS):
        if company_name_has_any(fields, INTERNET_HOSPITAL_NAME_HINTS):
            return "0405"
        if company_name_has_any(fields, HEALTH_NAME_HINTS):
            return "0102"
        if name_code:
            return name_code
        return "0101"
    if any(normalize_text(item) in industry_text for item in FALLBACK_TECH_INDUSTRY_HINTS):
        if name_code:
            return name_code
        if company_name_has_any(fields, BIO_NAME_HINTS):
            return "0502"
        if company_name_has_any(fields, PHARMA_RETAIL_NAME_HINTS):
            return "0501"
        if company_name_has_any(fields, DEVICE_NAME_HINTS):
            return "0311"
        if company_name_has_any(fields, HEALTH_NAME_HINTS + MEDICAL_HEALTH_NAME_HINTS):
            return "0102"
        if company_name_has_any(fields, DIGITAL_NAME_HINTS + MEDICAL_TECH_NAME_HINTS):
            return "0101"
        if company_name_has_any(fields, SERVICE_NAME_HINTS):
            return "0602"
        return "0101"
    if "门诊" in industry_text or "医院" in industry_text or "卫生服务" in industry_text:
        return "0404" if company_name_has_any(fields, CONSUMER_SERVICE_NAME_HINTS) else "0403"
    if "零售" in industry_text:
        return "0402"
    if "批发" in industry_text:
        return "0401"
    return None


def select_full_coverage_primary(
    fields: Dict[str, str],
    ranked_all: List[Tuple[int, str, List[str]]],
) -> Tuple[str, float, str]:
    low_score_code, low_score_confidence = choose_low_score_primary(ranked_all, fields)
    if low_score_code:
        return low_score_code, low_score_confidence, "low_score_primary"
    industry_code = fallback_code_from_industry(fields)
    if industry_code:
        return industry_code, 0.56, "industry_fallback"
    name_code = fallback_code_from_name(fields)
    if name_code:
        return name_code, 0.54, "name_fallback"
    return "0602", 0.5, "default_fallback"


def select_category_codes(
    ranked_matches: List[Tuple[int, str, List[str]]],
    fields: Dict[str, str],
) -> List[str]:
    if not ranked_matches:
        return []
    primary_score, primary_code, _ = ranked_matches[0]
    if primary_score < MIN_PRIMARY_SCORE:
        return []

    selected_codes = [primary_code]
    for candidate_score, candidate_code, candidate_evidences in ranked_matches[1:]:
        if len(selected_codes) >= 1 + MAX_SECONDARY_TAGS:
            break
        if candidate_score < MIN_SECONDARY_SCORE:
            continue
        if candidate_code in selected_codes:
            continue
        candidate_has_identity = has_identity_evidence(candidate_evidences)
        gap_override = candidate_has_identity and (
            (primary_code, candidate_code) in ALLOWED_MULTI_PAIRS
            or (candidate_code, primary_code) in ALLOWED_MULTI_PAIRS
            or
            (cluster_of(primary_code), cluster_of(candidate_code)) in ALLOWED_MULTI_CLUSTER_PAIRS
            or "0311" in {primary_code, candidate_code}
            or "0405" in {primary_code, candidate_code}
        )
        if primary_score - candidate_score > SECONDARY_SCORE_GAP and not gap_override:
            continue
        direct_or_strong = (
            is_direct_match(fields, candidate_code)
            or candidate_score >= primary_score - 1
            or candidate_has_identity
        )
        if not direct_or_strong:
            continue
        if not allow_pair_by_business_boundary(primary_code, candidate_code, fields, candidate_evidences):
            continue
        if not can_coexist(primary_code, candidate_code, primary_score, candidate_score):
            continue
        if any(
            are_exclusive_codes(existing_code, candidate_code)
            and (existing_code, candidate_code) not in ALLOWED_MULTI_PAIRS
            and (candidate_code, existing_code) not in ALLOWED_MULTI_PAIRS
            for existing_code in selected_codes
        ):
            continue
        selected_codes.append(candidate_code)
    return selected_codes


def matches_rule(normalized_company_text: str, rule: Dict[str, object]) -> bool:
    include_any = rule.get("include_any", [])
    if not include_any:
        return False
    if not any(keyword in normalized_company_text for keyword in include_any):
        return False
    exclude_any = rule.get("exclude_any", [])
    return not any(keyword in normalized_company_text for keyword in exclude_any)


def apply_assignments(assignments: Dict[int, Set[int]], company_stage_map: Dict[int, int], env: Dict[str, str]) -> None:
    statements = [
        "START TRANSACTION;",
        "DELETE FROM category_industry_company_map;",
        "UPDATE company_basic SET industry_chain_link = NULL;",
    ]
    values: List[str] = []
    for company_id in sorted(assignments):
        for category_id in sorted(assignments[company_id]):
            values.append(f"({category_id}, {company_id})")
    if values:
        statements.append("INSERT INTO category_industry_company_map (category_id, company_id) VALUES\n" + ",\n".join(values) + ";")
    for company_id, stage in sorted(company_stage_map.items()):
        statements.append(f"UPDATE company_basic SET industry_chain_link = {stage} WHERE company_id = {company_id};")
    statements.append("COMMIT;")
    run_mysql_sql("\n".join(statements) + "\n", env)


def sql_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "''")


def fetch_formal_tag_catalog(env: Dict[str, str]) -> tuple[Dict[str, int], Dict[str, int]]:
    rows = query_rows(
        """
        SELECT company_tag_id, company_tag_name, company_tag_subdimension_id
        FROM company_tag_library
        WHERE company_tag_subdimension_id IN (63, 64)
        ORDER BY company_tag_id
        """,
        env,
    )
    chain_tag_ids: Dict[str, int] = {}
    category_tag_ids: Dict[str, int] = {}
    for company_tag_id, company_tag_name, subdimension_id in rows:
        tag_id = int(company_tag_id)
        tag_name = str(company_tag_name)
        if int(subdimension_id) == 63:
            chain_tag_ids[tag_name] = tag_id
            continue
        match = re.search(r"（(\d{4})）$", tag_name)
        if match:
            category_tag_ids[match.group(1)] = tag_id
    return chain_tag_ids, category_tag_ids


def sync_formal_industry_tags(
    assignments: Dict[int, Set[int]],
    assignment_confidences: Dict[tuple[int, int], float],
    category_id_to_code: Dict[int, str],
    code_to_name: Dict[str, str],
    env: Dict[str, str],
) -> None:
    chain_tag_ids, category_tag_ids = fetch_formal_tag_catalog(env)
    inserts: List[tuple[int, int, float]] = []
    insert_keys: Set[tuple[int, int]] = set()
    for company_id, category_ids in assignments.items():
        for category_id in category_ids:
            code = category_id_to_code.get(category_id)
            if not code:
                continue
            category_tag_id = category_tag_ids.get(code)
            if category_tag_id:
                key = (company_id, category_tag_id)
                if key not in insert_keys:
                    insert_keys.add(key)
                    inserts.append((company_id, category_tag_id, assignment_confidences.get((company_id, category_id), 0.6)))
            chain_tag_id = chain_tag_ids.get(code_to_name.get(code, ""))
            if chain_tag_id:
                key = (company_id, chain_tag_id)
                if key not in insert_keys:
                    insert_keys.add(key)
                    chain_confidence = max(0.45, round(assignment_confidences.get((company_id, category_id), 0.6) - 0.05, 2))
                    inserts.append((company_id, chain_tag_id, chain_confidence))

    statements = [
        "START TRANSACTION;",
        """
DELETE ctm
FROM company_tag_map ctm
JOIN company_tag_library l ON ctm.company_tag_id = l.company_tag_id
WHERE ctm.source = 2
  AND l.company_tag_subdimension_id IN (63, 64);
""".strip(),
    ]
    if inserts:
        chunk_size = 4000
        for index in range(0, len(inserts), chunk_size):
            chunk = inserts[index : index + chunk_size]
            values = ",\n".join(
                f"({company_id}, {tag_id}, 2, {confidence:.2f}, NULL)"
                for company_id, tag_id, confidence in chunk
            )
            statements.append(
                "INSERT INTO company_tag_map (company_id, company_tag_id, source, confidence, user_id) VALUES\n"
                + values
                + "\nON DUPLICATE KEY UPDATE source = VALUES(source), confidence = VALUES(confidence), user_id = VALUES(user_id), create_time = CURRENT_TIMESTAMP;"
            )
    statements.append("COMMIT;")
    run_mysql_sql("\n".join(statements) + "\n", env)


def build_report(
    total_companies: int,
    matched_company_count: int,
    assignments: Dict[int, Set[int]],
    company_stage_map: Dict[int, int],
    code_to_id: Dict[str, int],
    code_to_name: Dict[str, str],
) -> Path:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = TMP_ROOT / f"category-industry-company-map-report-{date.today().isoformat()}.md"

    category_company_counts: Counter[int] = Counter()
    for category_ids in assignments.values():
        for category_id in category_ids:
            category_company_counts[category_id] += 1
    multi_tag_companies = sum(1 for category_ids in assignments.values() if len(category_ids) > 1)
    total_mappings = sum(len(items) for items in assignments.values())

    stage_counts = Counter(company_stage_map.values())
    stage_name_map = {1: "上游", 2: "中游", 3: "下游"}
    lines = [
        "# 行业分类企业映射重建报告",
        "",
        f"- 日期: {date.today().isoformat()}",
        f"- 企业总数: {total_companies}",
        f"- 命中至少一个行业分类的企业数: {matched_company_count}",
        f"- 未命中企业数: {max(total_companies - matched_company_count, 0)}",
        f"- 生成映射总数: {total_mappings}",
        f"- 多标签企业数: {multi_tag_companies}",
        f"- 单企业平均标签数: {total_mappings / matched_company_count:.2f}" if matched_company_count else "- 单企业平均标签数: 0",
        "",
        "## 产业链环节回填",
        "",
        *(f"- {stage_name_map[stage]}: {stage_counts.get(stage, 0)}" for stage in (1, 2, 3)),
        "",
        "## 一级行业分类命中数",
        "",
    ]
    for code, name in sorted(code_to_name.items()):
        lines.append(f"- {code} {name}: {category_company_counts.get(code_to_id[code], 0)}")
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 当前为首页链路与正式行业标签链路共享的一级行业分类映射。",
            "- 本版已升级为字段加权 + 主标签 / 副标签判定，不再把所有命中分类全部写入。",
            "- 每家企业默认保留 1 个主标签，最多补充 2 个副标签。",
            "- 副标签需满足分差、证据强度与共存约束，不是简单放开多选。",
            "- 未命中企业会按行业归属和名称线索补齐到全量覆盖，并以较低置信度同步到正式标签。",
            "- 规则仍兼容 `SQL/data/category_industry_company_rules.json`，便于继续调词。",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild category_industry_company_map with keyword rules.")
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env"), help="Path to .env file")
    parser.add_argument("--apply", action="store_true", help="Apply rebuilt mappings to MySQL")
    args = parser.parse_args()

    env = parse_env(Path(args.env_file))
    rules = load_rules()
    stage_map = load_stage_map()
    code_to_id, code_to_name = fetch_category_maps(env)
    companies = fetch_company_rows(env)
    rule_profiles = build_rule_profiles(rules, code_to_name)
    rule_map = {str(rule["category_level_code"]): rule for rule in rules}
    category_id_to_code = {category_id: code for code, category_id in code_to_id.items()}

    assignments: Dict[int, Set[int]] = defaultdict(set)
    company_stage_map: Dict[int, int] = {}
    assignment_confidences: Dict[tuple[int, int], float] = {}

    for company in companies:
        fields = normalized_company_fields(company)
        company_id = int(company["company_id"])
        normalized_text = company_text(company)
        ranked_matches = build_ranked_matches(fields, normalized_text, rule_profiles, rule_map, code_to_id, min_score=MIN_PRIMARY_SCORE)
        ranked_all = ranked_matches if ranked_matches else build_ranked_matches(fields, normalized_text, rule_profiles, rule_map, code_to_id, min_score=1)
        selected_codes = select_category_codes(ranked_matches, fields)
        fallback_primary_code = None
        fallback_confidence = 0.0
        if not selected_codes:
            fallback_primary_code, fallback_confidence, _ = select_full_coverage_primary(fields, ranked_all)
            selected_codes = [fallback_primary_code]
        primary_code = selected_codes[0]
        for index, selected_code in enumerate(selected_codes):
            category_id = code_to_id[selected_code]
            assignments[company_id].add(category_id)
            if fallback_primary_code and selected_code == fallback_primary_code:
                assignment_confidences[(company_id, category_id)] = fallback_confidence
                continue
            selected_score = next((score for score, code, _ in ranked_all if code == selected_code), MIN_PRIMARY_SCORE)
            assignment_confidences[(company_id, category_id)] = score_to_confidence(selected_score, secondary=index > 0)
        company_stage_map[company_id] = stage_map[primary_code]

    if args.apply:
        apply_assignments(assignments, company_stage_map, env)
        sync_formal_industry_tags(assignments, assignment_confidences, category_id_to_code, code_to_name, env)

    report_path = build_report(
        total_companies=len(companies),
        matched_company_count=len(assignments),
        assignments=assignments,
        company_stage_map=company_stage_map,
        code_to_id=code_to_id,
        code_to_name=code_to_name,
    )

    print(f"[ok] matched companies: {len(assignments)} / {len(companies)}")
    print(f"[ok] generated category/company mappings: {sum(len(items) for items in assignments.values())}")
    print(f"[ok] multi-tag companies: {sum(1 for items in assignments.values() if len(items) > 1)}")
    print(f"[ok] report: {report_path}")
    if args.apply:
        print("[ok] applied category_industry_company_map rebuild")
        print("[ok] synced formal industry tags to company_tag_map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
