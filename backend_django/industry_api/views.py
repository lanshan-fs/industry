from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import median

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from industry_api.ecology_rules import ecology_keywords
from scoring_api.engine import get_company_scoring_snapshot
from scoring_api.views import _company_tags, _normalize_text, _risk_profile


STAGE_ROOTS = [
    {"key": "stage_上游", "title": "上游"},
    {"key": "stage_中游", "title": "中游"},
    {"key": "stage_下游", "title": "下游"},
]
SEED_STAGE_TO_ROOT_KEY = {
    "upstream": "stage_上游",
    "midstream": "stage_中游",
    "downstream": "stage_下游",
}
ROOT_KEY_TO_STAGE_TEXT = {
    "stage_上游": "上游",
    "stage_中游": "中游",
    "stage_下游": "下游",
}
ROOT_KEY_TO_STAGE_DESC = {
    "stage_上游": "上游 - 研发与技术",
    "stage_中游": "中游 - 产品与制造",
    "stage_下游": "下游 - 应用与服务",
}
ROOT_CATEGORY_STAGE_KEY = {
    "前沿技术": "upstream",
    "AI 药物研": "upstream",
    "医疗器械": "midstream",
    "药品": "midstream",
    "数字医疗": "downstream",
    "医疗服务": "downstream",
}
STAGE_KEY_TO_TITLE = {
    "upstream": "上游 - 研发与技术",
    "midstream": "中游 - 产品与制造",
    "downstream": "下游 - 应用与服务",
}
SUBDIMENSION_KEY_MAPPING = {
    "成立年限": "EST_AGE",
    "注册资本": "REG_CAPITAL",
    "实缴资本": "PAID_CAPITAL",
    "经营状态": "BIZ_STATUS",
    "企业类型": "ENT_TYPE",
    "组织类型": "ORG_TYPE",
    "企业规模": "ENT_SCALE",
    "分支机构数量": "BRANCH_STATUS",
    "地址信息": "ADDR_INFO",
    "员工人数": "STAFF_RANGE",
    "社保人数": "INSURED_RANGE",
    "上市状态": "LISTING_STATUS",
    "联系方式": "CONTACT_TYPE",
    "工商信息邮箱": "EMAIL_STATUS",
    "小微企业": "SMALL_MICRO",
    "变更信息": "CHANGE_INFO",
    "一般纳税人": "TAX_PAYER",
    "投融资轮次": "FINANCING",
    "融资信息": "FINANCING",
    "招投标": "BIDDING",
    "招聘信息": "RECRUITMENT",
    "税务评级": "TAX_RATING",
    "开户行": "BANK_TYPE",
    "专利类型": "PATENT_TYPE",
    "企业科技属性": "TECH_ATTR",
    "资质证书": "CERT_TYPE",
    "商标信息": "IP_STATUS_TRADEMARK",
    "专利信息": "IP_STATUS_PATENT",
    "作品著作权": "IP_STATUS_COPYRIGHT",
    "软件著作权": "IP_STATUS_SOFTWARE",
    "高新技术企业": "IP_STATUS_HIGH_TECH",
    "微信公众号": "IP_STATUS_WECHAT",
    "标准制定": "IP_STATUS_STANDARD",
    "网址信息": "IP_STATUS_WEB",
    "备案网站检测": "IP_STATUS_ICP",
    "商业特许经营": "IP_STATUS_FRANCHISE",
    "失信被执行": "RISK_DISHONEST",
    "动产抵押": "RISK_MORTGAGE",
    "经营异常": "RISK_ABNORMAL",
    "法律文书": "RISK_LEGAL_DOC",
    "行政处罚": "RISK_PENALTY",
    "破产重叠": "RISK_BANKRUPTCY",
    "清算信息": "RISK_LIQUIDATION",
    "环保处罚": "RISK_ENV_PENALTY",
    "股权冻结": "RISK_EQUITY_FREEZE",
    "被执行人": "RISK_EXECUTOR",
    "限制高消费": "RISK_LIMIT_CONSUMPTION",
}


def _rows(query: str, params: list | tuple | None = None) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _scalar(query: str, params: list | tuple | None = None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        row = cursor.fetchone()
    return row[0] if row else None


def _load_chain_seed() -> list[dict]:
    rows = _rows(
        """
        SELECT
          ci.chain_id,
          ci.chain_name,
          c.category_level_code,
          root.category_name AS root_name
        FROM chain_industry ci
        JOIN chain_industry_category_industry_map cic
          ON cic.chain_id = ci.chain_id
        JOIN category_industry c
          ON c.category_id = cic.category_id
        LEFT JOIN category_industry root
          ON root.category_level_code = LEFT(c.category_level_code, 2)
        ORDER BY ci.chain_id
        """
    )
    seed_rows = []
    for row in rows:
        root_name = _normalize_text(row["root_name"])
        stage_key = ROOT_CATEGORY_STAGE_KEY.get(root_name)
        if not stage_key:
            continue
        seed_rows.append(
            {
                "chain_name": _normalize_text(row["chain_name"]),
                "category_level_code": _normalize_text(row["category_level_code"]),
                "stage_key": stage_key,
                "stage_title": STAGE_KEY_TO_TITLE[stage_key],
                "sort_order": int(row["chain_id"] or 0),
            }
        )
    return seed_rows


def _option_rows(values: list[str]) -> list[dict]:
    seen = set()
    result = []
    for value in values:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append({"label": normalized, "value": normalized})
    return result


def _in_clause(values: list) -> tuple[str, list]:
    placeholders = ", ".join(["%s"] * len(values))
    return f"({placeholders})", values


def _clean_values(values) -> list[str]:
    if values is None:
        source = []
    elif isinstance(values, str):
        source = [values]
    else:
        source = list(values)
    result = []
    seen = set()
    for value in source:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _request_values(request, key: str) -> list[str]:
    raw_values = []
    for raw in request.GET.getlist(key):
        text = str(raw or "")
        if "," in text:
            raw_values.extend(text.split(","))
        else:
            raw_values.append(text)
    return _clean_values(raw_values)


def _load_categories() -> tuple[list[dict], dict[int, dict], dict[str, dict]]:
    rows = _rows(
        """
        SELECT
          category_id,
          category_name,
          category_level,
          category_level_code,
          category_level_code_parent
        FROM category_industry
        ORDER BY category_level_code
        """
    )
    by_id = {int(row["category_id"]): row for row in rows}
    by_code = {str(row["category_level_code"]): row for row in rows}
    return rows, by_id, by_code


def _build_category_paths(rows: list[dict], by_code: dict[str, dict]) -> dict[int, str]:
    path_map: dict[int, str] = {}

    def build_path(row: dict) -> str:
        category_id = int(row["category_id"])
        if category_id in path_map:
            return path_map[category_id]
        parts = [_normalize_text(row["category_name"])]
        parent_code = _normalize_text(row["category_level_code_parent"])
        while parent_code and parent_code in by_code:
            parent = by_code[parent_code]
            parts.append(_normalize_text(parent["category_name"]))
            parent_code = _normalize_text(parent["category_level_code_parent"])
        path_map[category_id] = "/".join(reversed([part for part in parts if part]))
        return path_map[category_id]

    for row in rows:
        build_path(row)
    return path_map


def _score_industry_count_map() -> dict[str, int]:
    rows = _rows("SELECT industry_path, company_count FROM score_industry_path")
    return {_normalize_text(row["industry_path"]): int(row["company_count"] or 0) for row in rows}


def _industry_tree_payload() -> list[dict]:
    seed_rows = _load_chain_seed()
    category_rows, _, by_code = _load_categories()
    path_map = _build_category_paths(category_rows, by_code)
    count_map = _score_industry_count_map()

    node_map: dict[int, dict] = {}
    child_ids: set[int] = set()
    for row in category_rows:
        if int(row["category_level"]) == 0:
            continue
        category_id = int(row["category_id"])
        node_map[category_id] = {
            "key": category_id,
            "title": _normalize_text(row["category_name"]),
            "count": count_map.get(path_map.get(category_id, ""), 0),
            "children": [],
        }

    for row in category_rows:
        category_level = int(row["category_level"])
        if category_level <= 1:
            continue
        category_id = int(row["category_id"])
        parent_code = _normalize_text(row["category_level_code_parent"])
        parent = by_code.get(parent_code)
        if not parent:
            continue
        parent_id = int(parent["category_id"])
        parent_node = node_map.get(parent_id)
        current_node = node_map.get(category_id)
        if parent_node and current_node:
            parent_node["children"].append(current_node)
            child_ids.add(category_id)

    stage_tree = {
        root["key"]: {"key": root["key"], "title": root["title"], "children": [], "isStage": True}
        for root in STAGE_ROOTS
    }
    attached_level1_ids: set[int] = set()
    for seed in sorted(seed_rows, key=lambda item: int(item["sort_order"])):
        category = by_code.get(str(seed["category_level_code"]))
        if not category:
            continue
        category_id = int(category["category_id"])
        node = node_map.get(category_id)
        stage_key = SEED_STAGE_TO_ROOT_KEY.get(str(seed["stage_key"]))
        if node and stage_key and category_id not in attached_level1_ids:
            stage_tree[stage_key]["children"].append(node)
            attached_level1_ids.add(category_id)

    return [stage_tree[root["key"]] for root in STAGE_ROOTS]


def _tree_select_payload(nodes: list[dict]) -> list[dict]:
    result = []
    for node in nodes:
        children = _tree_select_payload(node.get("children", []))
        result.append(
            {
                **node,
                "value": node["key"],
                "children": children,
            }
        )
    return result


def _company_ids_for_category_ids(category_ids: list[int]) -> list[int]:
    if not category_ids:
        return []
    in_clause, params = _in_clause(category_ids)
    rows = _rows(
        f"""
        SELECT DISTINCT company_id
        FROM category_industry_company_map
        WHERE category_id IN {in_clause}
        ORDER BY company_id
        """,
        params,
    )
    return [int(row["company_id"]) for row in rows]


def _resolve_category_ids(
    *,
    tag_id: str | None = None,
    stage_key: str | None = None,
    industry_name: str | None = None,
    category_values: list[str] | None = None,
) -> dict:
    category_rows, by_id, _ = _load_categories()
    seed_rows = _load_chain_seed()

    selected_rows: list[dict] = []
    stage_display = ""
    if category_values:
        stage_keys = []
        for value in _clean_values(category_values):
            if value.startswith("stage_"):
                stage_keys.append(value)
            elif value.isdigit():
                selected = by_id.get(int(value))
                if selected:
                    selected_rows.append(selected)
        if stage_keys:
            stage_key = stage_keys[0]
    elif tag_id and str(tag_id).isdigit():
        selected = by_id.get(int(tag_id))
        if selected:
            selected_rows = [selected]

    if stage_key and not industry_name:
        target_stage = None
        if stage_key == "stage_上游":
            target_stage = "upstream"
        elif stage_key == "stage_中游":
            target_stage = "midstream"
        elif stage_key == "stage_下游":
            target_stage = "downstream"
        if target_stage:
            target_codes = {str(seed["category_level_code"]) for seed in seed_rows if str(seed["stage_key"]) == target_stage}
            selected_rows.extend([row for row in category_rows if str(row["category_level_code"]) in target_codes])
            stage_display = ROOT_KEY_TO_STAGE_DESC.get(stage_key, ROOT_KEY_TO_STAGE_TEXT.get(stage_key, ""))
    elif industry_name and not selected_rows:
        normalized_name = _normalize_text(industry_name)
        exact_rows = [row for row in category_rows if _normalize_text(row["category_name"]) == normalized_name]
        if exact_rows:
            exact_rows.sort(key=lambda row: (int(row["category_level"]), len(str(row["category_level_code"])), str(row["category_level_code"])))
            selected_rows = [exact_rows[0]]

    selected_rows = list({int(row["category_id"]): row for row in selected_rows}.values())

    if not selected_rows:
        return {"selected": None, "category_ids": [], "company_ids": [], "stage": stage_display}

    selected_codes = [str(row["category_level_code"]) for row in selected_rows]
    selected_names = [_normalize_text(row["category_name"]) for row in selected_rows]
    descendant_ids = [
        int(row["category_id"])
        for row in category_rows
        if any(str(row["category_level_code"]).startswith(code) for code in selected_codes)
    ]

    if not stage_display:
        seed_by_code = {str(seed["category_level_code"]): seed for seed in seed_rows}
        first_code = selected_codes[0]
        seed = seed_by_code.get(first_code[:4])
        if seed:
            stage_key = SEED_STAGE_TO_ROOT_KEY.get(str(seed["stage_key"]))
            stage_display = ROOT_KEY_TO_STAGE_DESC.get(stage_key, str(seed.get("stage_title") or ""))

    return {
        "selected": selected_names[0] if len(selected_names) == 1 else " / ".join(selected_names),
        "category_ids": descendant_ids,
        "selected_category_ids": [int(row["category_id"]) for row in selected_rows],
        "selected_codes": selected_codes,
        "company_ids": _company_ids_for_category_ids(descendant_ids),
        "stage": stage_display,
    }


def _company_tags_map(company_ids: list[int], limit: int = 8) -> dict[int, list[str]]:
    if not company_ids:
        return {}
    in_clause, params = _in_clause(company_ids)
    rows = _rows(
        f"""
        SELECT
          m.company_id,
          l.company_tag_name,
          COALESCE(m.confidence, 0) AS confidence,
          m.company_tag_map_id
        FROM company_tag_map m
        JOIN company_tag_library l ON l.company_tag_id = m.company_tag_id
        WHERE m.company_id IN {in_clause}
        ORDER BY m.company_id, confidence DESC, m.company_tag_map_id DESC
        """,
        params,
    )
    result: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        company_id = int(row["company_id"])
        tag_name = _normalize_text(row["company_tag_name"])
        if not tag_name or tag_name in result[company_id]:
            continue
        if len(result[company_id]) >= limit:
            continue
        result[company_id].append(tag_name)
    return result


def _company_risk_map(company_ids: list[int]) -> dict[int, dict[str, int]]:
    if not company_ids:
        return {}
    in_clause, params = _in_clause(company_ids)
    rows = _rows(
        f"""
        SELECT company_id, company_risk_category_name, company_risk_category_count
        FROM company_risk
        WHERE company_id IN {in_clause}
        """,
        params,
    )
    result: dict[int, dict[str, int]] = defaultdict(dict)
    for row in rows:
        result[int(row["company_id"])][_normalize_text(row["company_risk_category_name"])] = int(row["company_risk_category_count"] or 0)
    return result


def _format_amount(value: Decimal | None) -> str:
    if value is None:
        return "-"
    text = f"{Decimal(str(value)):.2f}".rstrip("0").rstrip(".")
    return f"{text}万元"


def _format_capital_number(value: Decimal | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def _format_ratio(value: float) -> str:
    return f"{value:.2f}%"


def _subdimension_tags(subdimension_name: str) -> list[str]:
    rows = _rows(
        """
        SELECT l.company_tag_name
        FROM company_tag_library l
        JOIN company_tag_subdimension s ON s.company_tag_subdimension_id = l.company_tag_subdimension_id
        WHERE s.company_tag_subdimension_name = %s
        ORDER BY l.sort_order, l.company_tag_id
        """,
        [subdimension_name],
    )
    return [_normalize_text(row["company_tag_name"]) for row in rows]


def _legacy_dictionary_payload() -> dict[str, list[dict]]:
    rows = _rows(
        """
        SELECT
          s.company_tag_subdimension_name,
          l.company_tag_name
        FROM company_tag_library l
        JOIN company_tag_subdimension s ON s.company_tag_subdimension_id = l.company_tag_subdimension_id
        ORDER BY s.sort_order, l.sort_order, l.company_tag_id
        """
    )
    raw_dictionary: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        source_key = SUBDIMENSION_KEY_MAPPING.get(_normalize_text(row["company_tag_subdimension_name"]))
        tag_name = _normalize_text(row["company_tag_name"])
        if not source_key or not tag_name:
            continue
        raw_dictionary[source_key].append(tag_name)

    direct_value_sources = {
        "ENT_TYPE": _distinct_company_values("company_type"),
        "ORG_TYPE": _distinct_company_values("org_type"),
        "ENT_SCALE": _distinct_company_values("company_scale"),
        "BIZ_STATUS": _distinct_company_values("company_status"),
        "FINANCING": _distinct_company_values("financing_round"),
        "TAX_RATING": _distinct_company_values("taxpayer_credit_rating"),
    }
    for key, values in direct_value_sources.items():
        raw_dictionary[key].extend(values)

    return {key: _option_rows(values) for key, values in raw_dictionary.items()}


def _distinct_company_values(column: str) -> list[str]:
    rows = _rows(
        f"""
        SELECT DISTINCT {column} AS value
        FROM company_basic
        WHERE {column} IS NOT NULL AND {column} <> ''
        ORDER BY {column}
        """
    )
    return [_normalize_text(row["value"]) for row in rows]


def _apply_exact_match(where_clauses: list[str], query_params: list, column: str, values: list[str]):
    values = _clean_values(values)
    if not values:
        return
    in_clause, params = _in_clause(values)
    where_clauses.append(f"c.{column} IN {in_clause}")
    query_params.extend(params)


def _apply_tag_exists(where_clauses: list[str], query_params: list, subdimension_name: str, values: list[str], alias: str):
    values = _clean_values(values)
    if not values:
        return
    in_clause, params = _in_clause(values)
    where_clauses.append(
        f"""
        EXISTS (
          SELECT 1
          FROM company_tag_map {alias}m
          JOIN company_tag_library {alias}l ON {alias}l.company_tag_id = {alias}m.company_tag_id
          JOIN company_tag_subdimension {alias}s ON {alias}s.company_tag_subdimension_id = {alias}l.company_tag_subdimension_id
          WHERE {alias}m.company_id = c.company_id
            AND {alias}s.company_tag_subdimension_name = %s
            AND {alias}l.company_tag_name IN {in_clause}
        )
        """
    )
    query_params.append(subdimension_name)
    query_params.extend(params)


def _apply_patent_type(where_clauses: list[str], query_params: list, values: list[str]):
    values = _clean_values(values)
    if not values:
        return
    in_clause, params = _in_clause(values)
    where_clauses.append(
        f"""
        EXISTS (
          SELECT 1
          FROM company_patent p
          JOIN company_patent_patent_type_map pm ON pm.company_patent_id = p.company_patent_id
          JOIN company_patent_type pt ON pt.company_patent_type_id = pm.company_patent_type_id
          WHERE p.company_id = c.company_id
            AND pt.company_patent_type_name IN {in_clause}
        )
        """
    )
    query_params.extend(params)


def _apply_flag(where_clauses: list[str], column: str, values: list[str]):
    values = _clean_values(values)
    if values:
        where_clauses.append(f"COALESCE(c.{column}, 0) = 1")


def _apply_qualification_filter(where_clauses: list[str], query_params: list, values: list[str]):
    values = _clean_values(values)
    if not values:
        return

    label_conditions = {
        "上市企业": "(c.listing_status IS NOT NULL AND c.listing_status <> 0)",
        "外资企业": "(c.company_type LIKE '%外商%' OR c.company_type LIKE '%外国%' OR c.company_type LIKE '%台港澳%')",
        "独角兽": "(COALESCE(c.is_gazelle_company, 0) = 1 OR COALESCE(c.is_egalet_company, 0) = 1)",
        "专精特新": "(COALESCE(c.is_srdi_sme, 0) = 1 OR COALESCE(c.is_srdi_little_giant, 0) = 1)",
        "高新技术": "COALESCE(c.is_high_tech_enterprise, 0) = 1",
        "科技中小": "COALESCE(c.is_tech_sme, 0) = 1",
    }

    conditions = [label_conditions[value] for value in values if value in label_conditions]
    if conditions:
        where_clauses.append(f"({' OR '.join(conditions)})")


def _apply_ecology_filter(where_clauses: list[str], query_params: list, values: list[str]):
    values = _clean_values(values)
    if not values:
        return

    ecology_conditions = []
    for value in values:
        keywords = ecology_keywords(value)
        keyword_conditions = []
        for keyword in keywords:
            like_value = f"%{keyword}%"
            keyword_conditions.append(
                "(c.company_name LIKE %s OR c.company_type LIKE %s OR c.org_type LIKE %s OR c.business_scope LIKE %s OR c.register_address LIKE %s)"
            )
            query_params.extend([like_value, like_value, like_value, like_value, like_value])
        if keyword_conditions:
            ecology_conditions.append(f"({' OR '.join(keyword_conditions)})")

    if ecology_conditions:
        where_clauses.append(f"({' OR '.join(ecology_conditions)})")


def _industry_company_base_rows(params: dict) -> list[dict]:
    selected_company_ids = params.get("selected_company_ids") or []
    query_params: list = []
    where_clauses = ["1 = 1"]
    search_scope = _normalize_text(params.get("searchScope"))

    if selected_company_ids:
        in_clause, company_params = _in_clause(selected_company_ids)
        where_clauses.append(f"c.company_id IN {in_clause}")
        query_params.extend(company_params)

    keyword = _normalize_text(params.get("keyword"))
    if keyword:
        like_value = f"%{keyword}%"
        if search_scope == "person":
            where_clauses.append("c.legal_representative LIKE %s")
            query_params.append(like_value)
        elif search_scope == "qualification":
            where_clauses.append(
                """
                (
                  c.qualification_label LIKE %s
                  OR EXISTS (
                    SELECT 1
                    FROM company_qualification q
                    WHERE q.company_id = c.company_id
                      AND (q.qualification_name LIKE %s OR q.qualification_type LIKE %s)
                  )
                )
                """
            )
            query_params.extend([like_value, like_value, like_value])
        elif search_scope == "risk":
            where_clauses.append(
                """
                EXISTS (
                  SELECT 1
                  FROM company_risk r
                  WHERE r.company_id = c.company_id
                    AND r.company_risk_category_name LIKE %s
                )
                """
            )
            query_params.append(like_value)
        else:
            where_clauses.append(
                "(c.company_name LIKE %s OR c.credit_code LIKE %s OR CAST(c.company_id AS CHAR) LIKE %s)"
            )
            query_params.extend([like_value, like_value, like_value])

    _apply_exact_match(where_clauses, query_params, "company_type", params.get("entType"))
    _apply_exact_match(where_clauses, query_params, "org_type", params.get("orgType"))
    _apply_exact_match(where_clauses, query_params, "company_scale", params.get("scale"))
    _apply_exact_match(where_clauses, query_params, "company_status", params.get("bizStatus"))
    _apply_exact_match(where_clauses, query_params, "financing_round", params.get("financing"))
    _apply_exact_match(where_clauses, query_params, "subdistrict", params.get("street"))
    _apply_exact_match(where_clauses, query_params, "register_xian", params.get("district"))
    _apply_exact_match(where_clauses, query_params, "taxpayer_credit_rating", params.get("taxRating"))

    _apply_tag_exists(where_clauses, query_params, "企业科技属性", params.get("techAttr"), "t")
    _apply_tag_exists(where_clauses, query_params, "应用场景", params.get("scenario"), "s")
    _apply_patent_type(where_clauses, query_params, params.get("patentType"))
    _apply_qualification_filter(where_clauses, query_params, params.get("qualification"))
    _apply_ecology_filter(
        where_clauses,
        query_params,
        params.get("ecology") or ([keyword] if search_scope == "ecology" and keyword else []),
    )

    _apply_flag(where_clauses, "is_high_tech_enterprise", params.get("highTechStatus"))
    _apply_flag(where_clauses, "has_business_abnormal", params.get("riskAbnormal"))
    _apply_flag(where_clauses, "has_dishonest_execution", params.get("riskDishonest"))
    _apply_flag(where_clauses, "has_chattel_mortgage", params.get("riskMortgage"))
    _apply_flag(where_clauses, "has_legal_document", params.get("riskLegal"))
    _apply_flag(where_clauses, "has_admin_penalty", params.get("riskPenalty"))
    _apply_flag(where_clauses, "has_bankruptcy_overlap", params.get("riskBankruptcy"))
    _apply_flag(where_clauses, "has_liquidation_info", params.get("riskLiquidation"))
    _apply_flag(where_clauses, "has_env_penalty", params.get("riskEnv"))
    _apply_flag(where_clauses, "has_equity_freeze", params.get("riskEquity"))
    _apply_flag(where_clauses, "has_executed_person", params.get("riskExecutor"))
    _apply_flag(where_clauses, "has_consumption_restriction", params.get("riskLimit"))

    tech_field_values = _clean_values(params.get("techField"))
    if tech_field_values:
        tech_conditions = []
        for value in tech_field_values:
            like_value = f"%{value}%"
            tech_conditions.append(
                """
                (
                  c.business_scope LIKE %s
                  OR EXISTS (
                    SELECT 1
                    FROM company_patent p
                    WHERE p.company_id = c.company_id
                      AND (p.company_patent_name LIKE %s OR p.tech_attribute_label LIKE %s)
                  )
                  OR EXISTS (
                    SELECT 1
                    FROM company_software_copyright s
                    WHERE s.company_id = c.company_id
                      AND (
                        s.company_software_copyright_name LIKE %s
                        OR s.company_software_copyright_for_short LIKE %s
                      )
                  )
                )
                """
            )
            query_params.extend([like_value, like_value, like_value, like_value, like_value])
        where_clauses.append(f"({' OR '.join(tech_conditions)})")

    sort_key = _normalize_text(params.get("sort"))
    if sort_key == "capital_desc":
        order_by = "COALESCE(c.register_capital, 0) DESC, COALESCE(sr.total_score, 0) DESC, c.company_id ASC"
    elif sort_key == "date_desc":
        order_by = "COALESCE(c.establish_date, '1900-01-01') DESC, COALESCE(sr.total_score, 0) DESC, c.company_id ASC"
    elif sort_key == "score_desc":
        order_by = "COALESCE(sr.total_score, 0) DESC, c.company_id ASC"
    else:
        order_by = "COALESCE(sr.total_score, 0) DESC, COALESCE(c.register_capital, 0) DESC, c.company_id ASC"

    return _rows(
        f"""
        SELECT
          c.company_id,
          c.company_name,
          c.register_capital,
          c.legal_representative,
          c.establish_date,
          c.company_scale,
          c.register_xian,
          c.subdistrict,
          c.contact_phone,
          c.email_business,
          c.financing_round,
          c.register_address,
          c.register_address_detail,
          c.is_high_tech_enterprise,
          COALESCE(sr.total_score, 0) AS total_score
        FROM company_basic c
        LEFT JOIN scoring_scoreresult sr ON sr.enterprise_id = c.company_id
        WHERE {" AND ".join(where_clauses)}
        ORDER BY {order_by}
        LIMIT 100
        """,
        query_params,
    )


def _score_level(total_score: float) -> str:
    if total_score >= 45:
        return "AAA"
    if total_score >= 35:
        return "AA"
    if total_score >= 25:
        return "A"
    if total_score >= 15:
        return "BBB"
    return "BB"


def _aggregate_risk_sections(company_ids: list[int]) -> dict:
    if not company_ids:
        return {"high": [], "medium": [], "low": []}
    in_clause, params = _in_clause(company_ids)
    rows = _rows(
        f"""
        SELECT company_risk_category_name, SUM(company_risk_category_count) AS total_count
        FROM company_risk
        WHERE company_id IN {in_clause}
        GROUP BY company_risk_category_name
        ORDER BY total_count DESC, company_risk_category_name
        """,
        params,
    )
    sections = {"high": [], "medium": [], "low": []}
    for row in rows:
        item = {"name": _normalize_text(row["company_risk_category_name"]), "count": int(row["total_count"] or 0)}
        count = item["count"]
        if count >= 50:
            sections["high"].append(item)
        elif count >= 10:
            sections["medium"].append(item)
        elif count > 0:
            sections["low"].append(item)
    return sections


def _overall_score_averages() -> dict[str, float]:
    row = _rows(
        """
        SELECT
          COALESCE(AVG(basic_score), 0) AS avg_basic_score,
          COALESCE(AVG(tech_score), 0) AS avg_tech_score,
          COALESCE(AVG(professional_score), 0) AS avg_professional_score
        FROM scoring_scoreresult
        """
    )[0]
    return {
        "basic": round(float(row["avg_basic_score"] or 0), 2),
        "tech": round(float(row["avg_tech_score"] or 0), 2),
        "professional": round(float(row["avg_professional_score"] or 0), 2),
    }


def _selection_candidate_rows(selection: dict) -> list[dict]:
    selected_ids = {int(category_id) for category_id in selection.get("selected_category_ids") or []}
    if not selected_ids:
        return []

    category_rows, by_id, _ = _load_categories()
    selected_rows = [by_id[category_id] for category_id in selected_ids if category_id in by_id]
    if len(selected_rows) == 1:
        parent_code = str(selected_rows[0]["category_level_code"])
        children = [
            row
            for row in category_rows
            if str(row["category_level_code_parent"] or "") == parent_code
        ]
        if children:
            return children

    selected_rows.sort(
        key=lambda row: (
            int(row["category_level"]),
            len(str(row["category_level_code"])),
            str(row["category_level_code"]),
        )
    )
    return selected_rows


def _category_aggregate_scores(category_ids: list[int]) -> dict[str, float]:
    if not category_ids:
        return {"company_count": 0, "avg_total_score": 0.0, "avg_tech_score": 0.0, "avg_professional_score": 0.0}
    in_clause, params = _in_clause(category_ids)
    row = _rows(
        f"""
        SELECT
          COUNT(DISTINCT m.company_id) AS company_count,
          COALESCE(AVG(sr.total_score), 0) AS avg_total_score,
          COALESCE(AVG(sr.tech_score), 0) AS avg_tech_score,
          COALESCE(AVG(sr.professional_score), 0) AS avg_professional_score
        FROM category_industry_company_map m
        LEFT JOIN scoring_scoreresult sr ON sr.enterprise_id = m.company_id
        WHERE m.category_id IN {in_clause}
        """,
        params,
    )[0]
    return {
        "company_count": int(row["company_count"] or 0),
        "avg_total_score": round(float(row["avg_total_score"] or 0), 2),
        "avg_tech_score": round(float(row["avg_tech_score"] or 0), 2),
        "avg_professional_score": round(float(row["avg_professional_score"] or 0), 2),
    }


def _fallback_weak_dimensions(avg_basic: float, avg_tech: float, avg_professional: float) -> list[dict]:
    benchmark = _overall_score_averages()
    dimension_rows = [
        ("基础支撑能力", avg_basic, benchmark["basic"], "经营规模、资本实力与经营稳定性"),
        ("科技创新能力", avg_tech, benchmark["tech"], "专利、软著与科技属性资质"),
        ("专业场景能力", avg_professional, benchmark["professional"], "行业位置、资质证书与上下游协同"),
    ]
    items = []
    for name, score, baseline, scope in sorted(
        dimension_rows,
        key=lambda item: ((item[1] / item[2]) if item[2] else item[1], item[1]),
    ):
        if baseline <= 0:
            continue
        if score >= baseline * 0.9:
            continue
        level = "高危" if score < baseline * 0.75 else "预警"
        items.append(
            {
                "name": name,
                "level": level,
                "reason": f"{scope} 均分为 {score:.2f}，低于全库均值 {baseline:.2f}。",
                "type": "dimension",
            }
        )
    return items[:3]


def _industry_weak_links(
    selection: dict,
    total_companies: int,
    avg_total_score: float,
    avg_basic: float,
    avg_tech: float,
    avg_professional: float,
) -> list[dict]:
    candidate_rows = _selection_candidate_rows(selection)
    if len(candidate_rows) < 2 or total_companies <= 0:
        return _fallback_weak_dimensions(avg_basic, avg_tech, avg_professional)

    category_rows, _, _ = _load_categories()
    stats = []
    for row in candidate_rows:
        code = str(row["category_level_code"])
        descendant_ids = [
            int(candidate["category_id"])
            for candidate in category_rows
            if str(candidate["category_level_code"]).startswith(code)
        ]
        aggregate = _category_aggregate_scores(descendant_ids)
        stats.append(
            {
                "name": _normalize_text(row["category_name"]),
                "company_count": aggregate["company_count"],
                "avg_total_score": aggregate["avg_total_score"],
                "avg_tech_score": aggregate["avg_tech_score"],
                "avg_professional_score": aggregate["avg_professional_score"],
            }
        )

    counts = [item["company_count"] for item in stats]
    if len(counts) < 2:
        return _fallback_weak_dimensions(avg_basic, avg_tech, avg_professional)

    median_count = float(median(counts))
    items = []
    for item in stats:
        company_count = int(item["company_count"])
        share = company_count / total_companies if total_companies else 0.0
        coverage_gap = company_count == 0 or share < 0.05 or (
            median_count >= 5 and company_count < median_count * 0.35
        )
        total_gap = avg_total_score >= 1 and item["avg_total_score"] < avg_total_score * 0.8
        tech_gap = avg_tech >= 0.5 and item["avg_tech_score"] < avg_tech * 0.7
        professional_gap = avg_professional >= 1 and item["avg_professional_score"] < avg_professional * 0.8
        signal_count = sum([coverage_gap, total_gap, tech_gap, professional_gap])
        if company_count > 0 and signal_count == 0:
            continue

        level = "高危" if company_count == 0 or (coverage_gap and signal_count >= 2) else "预警"
        reasons = [f"库内企业 {company_count} 家，占当前行业 {share * 100:.1f}%"]
        if coverage_gap:
            reasons.append(f"同层级企业数中位数为 {median_count:.0f} 家")
        if total_gap:
            reasons.append(f"综合均分 {item['avg_total_score']:.2f}，低于行业均值 {avg_total_score:.2f}")
        if tech_gap:
            reasons.append(f"科技均分 {item['avg_tech_score']:.2f}，低于行业均值 {avg_tech:.2f}")
        elif professional_gap:
            reasons.append(
                f"专业均分 {item['avg_professional_score']:.2f}，低于行业均值 {avg_professional:.2f}"
            )
        items.append(
            {
                "name": item["name"],
                "level": level,
                "reason": "；".join(reasons) + "。",
                "type": "segment",
                "signalCount": signal_count,
                "companyCount": company_count,
            }
        )

    items.sort(
        key=lambda item: (
            0 if item["level"] == "高危" else 1,
            -int(item["signalCount"]),
            int(item["companyCount"]),
            item["name"],
        )
    )
    if items:
        return [
            {
                "name": item["name"],
                "level": item["level"],
                "reason": item["reason"],
                "type": item["type"],
            }
            for item in items[:3]
        ]
    return _fallback_weak_dimensions(avg_basic, avg_tech, avg_professional)


def _detail_rows(snapshot: dict, group: str) -> list[dict]:
    return [
        {
            "name": item["name"],
            "weight": round(float(item["weight"]), 2),
            "score": round(float(item["score"]), 2),
        }
        for item in snapshot["score"]["breakdown"][group]
    ]


def _build_model_company_rows(company_ids: list[int], score_field: str, group: str, limit: int = 8) -> list[dict]:
    if not company_ids:
        return []
    in_clause, params = _in_clause(company_ids)
    rows = _rows(
        f"""
        SELECT enterprise_id, company_name, {score_field} AS score
        FROM scoring_scoreresult
        WHERE enterprise_id IN {in_clause}
        ORDER BY {score_field} DESC, total_score DESC, enterprise_id ASC
        LIMIT {int(limit)}
        """,
        params,
    )

    result = []
    for row in rows:
        snapshot = get_company_scoring_snapshot(int(row["enterprise_id"]))
        if not snapshot:
            continue
        result.append(
            {
                "id": int(row["enterprise_id"]),
                "name": _normalize_text(row["company_name"]),
                "score": round(float(row["score"] or 0), 2),
                "details": _detail_rows(snapshot, group),
            }
        )
    return result


def _build_top_company_rows(company_ids: list[int], limit: int = 10) -> list[dict]:
    if not company_ids:
        return []
    in_clause, params = _in_clause(company_ids)
    rows = _rows(
        f"""
        SELECT
          c.company_id,
          c.company_name,
          c.register_capital,
          COALESCE(sr.total_score, 0) AS total_score
        FROM company_basic c
        LEFT JOIN scoring_scoreresult sr ON sr.enterprise_id = c.company_id
        WHERE c.company_id IN {in_clause}
        ORDER BY COALESCE(sr.total_score, 0) DESC, COALESCE(c.register_capital, 0) DESC, c.company_id ASC
        LIMIT {int(limit)}
        """,
        params,
    )
    tags_map = _company_tags_map([int(row["company_id"]) for row in rows], limit=4)
    result = []
    for row in rows:
        company_id = int(row["company_id"])
        tags = tags_map.get(company_id, [])
        if not tags:
            snapshot = get_company_scoring_snapshot(company_id)
            if snapshot:
                company = snapshot["company"]
                tags = _company_tags(company_id, company.industries, company.qualification_label)[:4]
        result.append(
            {
                "id": company_id,
                "name": _normalize_text(row["company_name"]),
                "capital": _format_capital_number(row["register_capital"]),
                "score": round(float(row["total_score"] or 0), 2),
                "tags": tags,
            }
        )
    return result


def _build_migration_risk_rows(company_ids: list[int], limit: int = 15) -> list[dict]:
    if not company_ids:
        return []
    in_clause, params = _in_clause(company_ids)
    row = _rows(
        f"""
        SELECT
          SUM(
            CASE
              WHEN COALESCE(cc.recruit_count, 0) = 0 AND COALESCE(cb.has_recruitment, 0) = 0
              THEN 1 ELSE 0
            END
          ) AS high_count,
          SUM(
            CASE
              WHEN COALESCE(cc.recruit_count, 0) BETWEEN 1 AND 4 AND COALESCE(cb.has_recruitment, 0) = 0
              THEN 1 ELSE 0
            END
          ) AS medium_count,
          SUM(
            CASE
              WHEN COALESCE(cc.recruit_count, 0) >= 5 OR COALESCE(cb.has_recruitment, 0) = 1
              THEN 1 ELSE 0
            END
          ) AS low_count
        FROM company_basic cb
        LEFT JOIN company_basic_count cc ON cc.company_id = cb.company_id
        WHERE cb.company_id IN {in_clause}
        """,
        params,
    )[0]
    total = len(company_ids)
    definitions = [
        ("高", int(row["high_count"] or 0), "库内未检出招聘记录"),
        ("中", int(row["medium_count"] or 0), "库内检出 1-4 条招聘记录"),
        ("低", int(row["low_count"] or 0), "库内检出 >=5 条招聘记录或招聘状态为“有”"),
    ]
    result = []
    for level, company_count, rule in definitions:
        result.append(
            {
                "riskLevel": level,
                "companyCount": company_count,
                "ratio": round(company_count / total * 100, 2) if total else 0.0,
                "rule": rule,
            }
        )
    return result


@require_GET
def meta_all(_request):
    industry_tree = _industry_tree_payload()
    response_data = {
        "dictionary": _legacy_dictionary_payload(),
        "industryTree": _tree_select_payload(industry_tree),
        "scenarios": _option_rows(_subdimension_tags("应用场景")),
        "regions": {
            "street": _option_rows(_subdimension_tags("街道") + _distinct_company_values("subdistrict")),
            "area": _option_rows(_subdimension_tags("地区") + _distinct_company_values("register_xian")),
        },
    }
    return JsonResponse({"success": True, "data": response_data})


@require_GET
def industry_tree(_request):
    return JsonResponse({"success": True, "data": _industry_tree_payload()})


@require_GET
def industry_companies(request):
    advanced_category_values = _request_values(request, "industryCategory")
    selection = _resolve_category_ids(
        tag_id=request.GET.get("tagId"),
        stage_key=request.GET.get("stageKey"),
        category_values=advanced_category_values,
    )
    rows = _industry_company_base_rows(
        {
            "selected_company_ids": selection["company_ids"],
            "keyword": request.GET.get("keyword"),
            "searchScope": request.GET.get("searchScope"),
            "entType": _request_values(request, "entType"),
            "orgType": _request_values(request, "orgType"),
            "scale": _request_values(request, "scale"),
            "bizStatus": _request_values(request, "bizStatus"),
            "financing": _request_values(request, "financing"),
            "street": _request_values(request, "street"),
            "qualification": _request_values(request, "qualification"),
            "ecology": _request_values(request, "ecology"),
            "district": _request_values(request, "district"),
            "taxRating": _request_values(request, "taxRating"),
            "techAttr": _request_values(request, "techAttr"),
            "techField": _request_values(request, "techField"),
            "scenario": _request_values(request, "scenario"),
            "patentType": _request_values(request, "patentType"),
            "highTechStatus": _request_values(request, "highTechStatus"),
            "riskAbnormal": _request_values(request, "riskAbnormal"),
            "riskDishonest": _request_values(request, "riskDishonest"),
            "riskMortgage": _request_values(request, "riskMortgage"),
            "riskLegal": _request_values(request, "riskLegal"),
            "riskPenalty": _request_values(request, "riskPenalty"),
            "riskBankruptcy": _request_values(request, "riskBankruptcy"),
            "riskLiquidation": _request_values(request, "riskLiquidation"),
            "riskEnv": _request_values(request, "riskEnv"),
            "riskEquity": _request_values(request, "riskEquity"),
            "riskExecutor": _request_values(request, "riskExecutor"),
            "riskLimit": _request_values(request, "riskLimit"),
            "sort": request.GET.get("sort"),
        }
    )

    company_ids = [int(row["company_id"]) for row in rows]
    tag_map = _company_tags_map(company_ids)
    risk_map = _company_risk_map(company_ids)
    data = []
    for row in rows:
        company_id = int(row["company_id"])
        risk_profile = _risk_profile(risk_map.get(company_id, {}))
        data.append(
            {
                "company_id": company_id,
                "company_name": _normalize_text(row["company_name"]),
                "registeredCapital": _format_amount(row["register_capital"]),
                "legalPerson": _normalize_text(row["legal_representative"]) or "-",
                "establishmentDate": row["establish_date"].isoformat() if row["establish_date"] else "-",
                "scale": _normalize_text(row["company_scale"]) or "-",
                "district": _normalize_text(row["register_xian"]) or "-",
                "street": _normalize_text(row["subdistrict"]) or "-",
                "phone": _normalize_text(row["contact_phone"]) or "-",
                "email": _normalize_text(row["email_business"]) or "-",
                "financing_round": _normalize_text(row["financing_round"]) or "未融资",
                "tags": tag_map.get(company_id, []),
                "key": company_id,
                "is_high_tech": str(row["is_high_tech_enterprise"] or 0) in {"1", "True", "true"},
                "risk_score": max(0, 100 - int(risk_profile["score"])),
                "total_score": round(float(row["total_score"] or 0), 2),
                "address": _normalize_text(row["register_address_detail"]) or _normalize_text(row["register_address"]) or "-",
            }
        )
    return JsonResponse({"success": True, "data": data})


@require_GET
def industry_profile(request):
    selection = _resolve_category_ids(industry_name=request.GET.get("industryName"))
    company_ids = selection["company_ids"]
    industry_name = selection["selected"] or _normalize_text(request.GET.get("industryName"))

    if not industry_name:
        return JsonResponse({"success": False, "message": "未找到匹配行业"}, status=404)

    if not company_ids:
        empty_data = {
            "basicInfo": {
                "industryName": industry_name,
                "growthRate": "0.00%",
                "department": "待补充",
                "policyCount": 0,
                "chainLink": selection["stage"] or "待补充",
                "description": f"行业画像基于当前本地库中归属到「{industry_name}」及其下级分类企业的评分、标签和风险数据实时汇总。",
                "totalCompanies": 0,
                "totalCapital": 0,
            },
            "totalScore": 0,
            "level": _score_level(0),
            "overallRadar": [
                {"item": "基础评分", "score": 0, "date": "当前"},
                {"item": "科技属性", "score": 0, "date": "当前"},
                {"item": "专业能力", "score": 0, "date": "当前"},
                {"item": "合规风险", "score": 100, "date": "当前"},
            ],
            "models": {
                "basic": {"score": 0, "companies": []},
                "tech": {"score": 0, "companies": []},
                "ability": {"score": 0, "companies": []},
            },
            "risks": {"high": [], "medium": [], "low": []},
            "weakLinks": [],
            "migrationRisks": [],
            "topCompanies": [],
        }
        return JsonResponse({"success": True, "data": empty_data})

    in_clause, params = _in_clause(company_ids)
    aggregate = _rows(
        f"""
        SELECT
          COUNT(DISTINCT c.company_id) AS total_companies,
          COALESCE(SUM(c.register_capital), 0) AS total_capital,
          COALESCE(AVG(sr.total_score), 0) AS avg_total_score,
          COALESCE(AVG(sr.basic_score), 0) AS avg_basic_score,
          COALESCE(AVG(sr.tech_score), 0) AS avg_tech_score,
          COALESCE(AVG(sr.professional_score), 0) AS avg_professional_score
        FROM company_basic c
        LEFT JOIN scoring_scoreresult sr ON sr.enterprise_id = c.company_id
        WHERE c.company_id IN {in_clause}
        """,
        params,
    )[0]

    total_companies = int(aggregate["total_companies"] or 0)
    avg_total_score = round(float(aggregate["avg_total_score"] or 0), 2)
    avg_basic_score = round(float(aggregate["avg_basic_score"] or 0), 2)
    avg_tech_score = round(float(aggregate["avg_tech_score"] or 0), 2)
    avg_professional_score = round(float(aggregate["avg_professional_score"] or 0), 2)
    risk_sections = _aggregate_risk_sections(company_ids)

    top_companies = _build_top_company_rows(company_ids, limit=10)
    migration_risks = _build_migration_risk_rows(company_ids, limit=15)
    model_basic_companies = _build_model_company_rows(company_ids, "basic_score", "basic", limit=8)
    model_tech_companies = _build_model_company_rows(company_ids, "tech_score", "tech", limit=8)
    model_professional_companies = _build_model_company_rows(company_ids, "professional_score", "professional", limit=8)

    total_capital_yi = round(float(aggregate["total_capital"] or 0) / 10000, 2)
    growth_ratio = 0.0
    if total_companies:
        high_tech_count = int(
            _scalar(
                f"SELECT COUNT(*) FROM company_basic WHERE company_id IN {in_clause} AND is_high_tech_enterprise = 1",
                params,
            )
            or 0
        )
        growth_ratio = round(high_tech_count / total_companies * 100, 2)

    industry_risk_score = 0
    if risk_sections["high"]:
        industry_risk_score = 85
    elif risk_sections["medium"]:
        industry_risk_score = 55
    elif risk_sections["low"]:
        industry_risk_score = 25

    overall_radar = [
        {"item": "基础评分", "score": avg_basic_score, "date": "当前"},
        {"item": "科技属性", "score": avg_tech_score, "date": "当前"},
        {"item": "专业能力", "score": avg_professional_score, "date": "当前"},
        {"item": "合规风险", "score": max(0, 100 - industry_risk_score), "date": "当前"},
    ]

    data = {
        "basicInfo": {
            "industryName": industry_name,
            "growthRate": _format_ratio(growth_ratio),
            "department": "待补充",
            "policyCount": 0,
            "chainLink": selection["stage"] or "待补充",
            "description": f"行业画像基于当前本地库中归属到「{industry_name}」及其下级分类企业的评分、标签和风险数据实时汇总。",
            "totalCompanies": total_companies,
            "totalCapital": total_capital_yi,
        },
        "totalScore": avg_total_score,
        "level": _score_level(avg_total_score),
        "overallRadar": overall_radar,
        "models": {
            "basic": {"score": avg_basic_score, "companies": model_basic_companies},
            "tech": {"score": avg_tech_score, "companies": model_tech_companies},
            "ability": {"score": avg_professional_score, "companies": model_professional_companies},
        },
        "risks": risk_sections,
        "weakLinks": _industry_weak_links(
            selection,
            total_companies,
            avg_total_score,
            avg_basic_score,
            avg_tech_score,
            avg_professional_score,
        ),
        "migrationRisks": migration_risks,
        "topCompanies": top_companies,
    }
    return JsonResponse({"success": True, "data": data})
