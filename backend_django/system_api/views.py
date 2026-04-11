from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from auth_api.views import _admin_user, _json_body, _json_error, _normalize_text
from industry_api.views import _rows, _scalar
from scoring_api.views import _resolve_company_id


SYSTEM_COMPANY_TEMPLATE_HEADERS = [
    "company_name",
    "credit_code",
    "legal_representative",
    "establish_date",
    "industry_belong",
    "register_capital",
    "paid_capital",
    "financing_round",
    "company_type",
    "organization_type",
    "investment_type",
    "company_scale",
    "contact_phone",
    "email_business",
    "register_address",
    "shareholders",
    "qualification_label",
    "register_number",
    "org_code",
    "business_scope",
]

MANAGED_TABLE_EXCLUDED_NAMES = {
    "company_basic_count",
}

MANAGED_TABLE_EXCLUDED_PREFIXES = (
    "company_tag_",
)

CHINESE_TOKEN_MAP = {
    "company": "企业",
    "basic": "基础",
    "address": "地址",
    "ai": "算法",
    "applicant": "申报",
    "bidding": "招投标",
    "branch": "分支机构",
    "change": "变更",
    "consumption": "消费",
    "restriction": "限制",
    "contact": "联系方式",
    "info": "信息",
    "phone": "电话",
    "customer": "客户",
    "employee": "员工",
    "count": "数量",
    "dataset": "数据集",
    "disease": "病种",
    "financing": "融资",
    "file": "文件",
    "filing": "备案",
    "flag": "标记",
    "former": "曾用",
    "high": "高",
    "name": "名称",
    "innovation": "创新",
    "listing": "上市",
    "model": "模型",
    "notice": "公示",
    "patent": "专利",
    "period": "时期",
    "qualification": "资质",
    "quality": "质量",
    "ranking": "榜单",
    "rare": "罕见",
    "recommended": "推荐",
    "recommender": "推荐",
    "recruit": "招聘",
    "risk": "风险",
    "shareholder": "股东",
    "software": "软件",
    "sheet": "工作表",
    "source": "来源",
    "copyright": "著作权",
    "subdistrict": "街道",
    "supplier": "供应商",
    "territory": "属地",
    "trademark": "商标",
    "website": "网站",
    "work": "作品",
    "credit": "信用",
    "code": "代码",
    "legal": "法定",
    "representative": "代表人",
    "establish": "成立",
    "date": "日期",
    "industry": "行业",
    "belong": "归属",
    "register": "注册",
    "capital": "资本",
    "paid": "实缴",
    "round": "轮次",
    "type": "类型",
    "organization": "组织",
    "investment": "投资",
    "scale": "规模",
    "acceptance": "受理",
    "email": "邮箱",
    "shareholders": "股东",
    "number": "编号",
    "owner": "所有者",
    "product": "产品",
    "public": "公示",
    "scope": "范围",
    "status": "状态",
    "taxpayer": "纳税",
    "rating": "评级",
    "approved": "核准",
    "term": "期限",
    "sheng": "省",
    "shi": "市",
    "xian": "区县",
    "detail": "详情",
    "insured": "社保",
    "total": "综合",
    "score": "评分",
    "professional": "专业",
    "tech": "科技",
    "org": "机构",
    "business": "经营",
    "create": "创建",
    "created": "创建",
    "update": "更新",
    "updated": "更新",
    "latest": "最新",
}

COMPANY_DELETE_TABLES = [
    ("category_industry_company_map", "company_id"),
    ("company_address", "company_id"),
    ("company_ai_model_filing", "company_id"),
    ("company_bidding", "company_id"),
    ("company_branch", "company_id"),
    ("company_change", "company_id"),
    ("company_consumption_restriction", "company_id"),
    ("company_contact_info", "company_id"),
    ("company_contact_phone", "company_id"),
    ("company_employee_count", "company_id"),
    ("company_financing", "company_id"),
    ("company_former_name", "company_id"),
    ("company_high_quality_dataset", "company_id"),
    ("company_innovation_notice", "company_id"),
    ("company_listing_status", "company_id"),
    ("company_patent", "company_id"),
    ("company_qualification", "company_id"),
    ("company_ranking", "company_id"),
    ("company_recommended_phone", "company_id"),
    ("company_recruit", "company_id"),
    ("company_risk", "company_id"),
    ("company_shareholder", "company_id"),
    ("company_software_copyright", "company_id"),
    ("company_subdistrict", "company_id"),
    ("company_tag_batch_item", "company_id"),
    ("company_tag_llm_candidate", "company_id"),
    ("company_tag_map", "company_id"),
    ("company_trademark", "company_id"),
    ("company_website", "company_id"),
    ("company_work_copyright", "company_id"),
    ("scoring_scorelog", "enterprise_id"),
    ("scoring_scoreresult", "enterprise_id"),
    ("company_basic_count", "company_id"),
]


def _execute(query: str, params: list | tuple | None = None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])


def _database_name() -> str:
    return connection.settings_dict["NAME"]


def _is_managed_table(table_name: str) -> bool:
    if table_name in MANAGED_TABLE_EXCLUDED_NAMES:
        return False
    if any(table_name.startswith(prefix) for prefix in MANAGED_TABLE_EXCLUDED_PREFIXES):
        return False
    return table_name.startswith("company_")


def _fallback_chinese_label(name: str, suffix: str = "") -> str:
    parts = [CHINESE_TOKEN_MAP.get(part) for part in name.split("_")]
    merged = "".join([part for part in parts if part])
    if not merged:
        return suffix or "字段"
    if suffix and not merged.endswith(suffix):
        return f"{merged}{suffix}"
    return merged


def _unique_column_labels(columns: list[dict]) -> list[dict]:
    seen: dict[str, int] = {}
    for column in columns:
        label = column["label"]
        count = seen.get(label, 0) + 1
        seen[label] = count
        column["import_label"] = label if count == 1 else f"{label}（{count}）"
    return columns


BUSINESS_IDENTIFIER_COLUMN_NAMES = {
    "credit_code",
    "register_number",
    "org_code",
    "license_number",
    "tax_number",
    "taxpayer_number",
    "unified_social_credit_code",
}


def _is_internal_identifier_column(column_name: str, *, is_primary_key: bool) -> bool:
    normalized = _normalize_text(column_name).lower()
    return is_primary_key or normalized == "id" or normalized.endswith("_id")


def _is_business_identifier_column(column_name: str, *, is_unique_key: bool, is_internal_identifier: bool) -> bool:
    normalized = _normalize_text(column_name).lower()
    if normalized in BUSINESS_IDENTIFIER_COLUMN_NAMES:
        return True
    return is_unique_key and not is_internal_identifier


def _candidate_relation_table_name(column_name: str, table_names: set[str]) -> str | None:
    normalized = _normalize_text(column_name).lower()
    if normalized in {"company_id", "customer_company_id", "supplier_company_id"} or normalized.endswith("_company_id"):
        return "company_basic" if "company_basic" in table_names else None
    if normalized.endswith("_id"):
        candidate = normalized[:-3]
        if candidate in table_names:
            return candidate
    return None


def _pick_relation_label_column(target_table: dict) -> dict | None:
    columns = target_table["columns"]
    by_name = {column["name"]: column for column in columns}
    preferred_names = [
        "company_name",
        f"{target_table['table_name']}_name",
        "name",
        "title",
        f"{target_table['table_name']}_title",
    ]
    for candidate in preferred_names:
        if candidate in by_name:
            return by_name[candidate]
    for column in columns:
        normalized = column["name"].lower()
        if normalized.endswith("_name") or normalized.endswith("_title"):
            return column
    return None


def _pick_relation_subtitle_column(target_table: dict) -> dict | None:
    columns = target_table["columns"]
    by_name = {column["name"]: column for column in columns}
    preferred_names = [
        "credit_code",
        f"{target_table['table_name']}_number",
        "company_patent_number",
        "register_number",
        "org_code",
        "code",
    ]
    for candidate in preferred_names:
        if candidate in by_name:
            return by_name[candidate]
    return None


def _relation_display_label(column: dict, label_column: dict | None) -> str:
    label = column["label"]
    transformed = (
        label.replace("唯一标识", "名称")
        .replace(" ID", "名称")
        .replace("ID", "名称")
        .replace("编号", "名称")
    )
    if transformed != label:
        return transformed
    if label_column:
        return label_column["label"]
    return f"{label}名称"


def _attach_relation_metadata(table_map: dict[str, dict]):
    table_names = set(table_map.keys())
    for table in table_map.values():
        existing_column_names = {column["name"] for column in table["columns"]}
        frontend_columns: list[dict] = []
        for column in table["columns"]:
            relation = None
            if column["system_identifier"]:
                target_table_name = _candidate_relation_table_name(column["name"], table_names)
                target_table = table_map.get(target_table_name) if target_table_name else None
                if target_table:
                    label_column = _pick_relation_label_column(target_table)
                    if label_column:
                        subtitle_column = _pick_relation_subtitle_column(target_table)
                        relation = {
                            "target_table": target_table_name,
                            "value_field": target_table["primary_key"],
                            "label_field": label_column["name"],
                            "subtitle_field": subtitle_column["name"] if subtitle_column else None,
                            "display_column": f"__display__{column['name']}",
                            "display_label": _relation_display_label(column, label_column),
                        }
                        if target_table_name == table["table_name"] and label_column["name"] in existing_column_names:
                            relation = None
            column["relation"] = relation
            frontend_columns.append(column)
            if relation:
                frontend_columns.append(
                    {
                        "name": relation["display_column"],
                        "label": relation["display_label"],
                        "comment": relation["display_label"],
                        "data_type": "varchar",
                        "column_type": "varchar(255)",
                        "nullable": True,
                        "primary_key": False,
                        "auto_increment": False,
                        "unique_key": False,
                        "system_identifier": False,
                        "business_identifier": False,
                        "creatable": False,
                        "editable": False,
                        "searchable": False,
                        "listable": True,
                        "detail_visible": True,
                        "required": False,
                        "form_type": "text",
                        "import_label": relation["display_label"],
                        "relation_display": True,
                        "source_name": column["name"],
                    }
                )
        table["columns"] = frontend_columns


def _managed_table_map() -> dict[str, dict]:
    table_rows = _rows(
        """
        SELECT TABLE_NAME, TABLE_COMMENT
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """,
        [_database_name()],
    )
    managed_tables = [row for row in table_rows if _is_managed_table(row["TABLE_NAME"])]
    table_names = [row["TABLE_NAME"] for row in managed_tables]
    if not table_names:
        return {}

    placeholders = ", ".join(["%s"] * len(table_names))
    column_rows = _rows(
        f"""
        SELECT
          TABLE_NAME,
          COLUMN_NAME,
          COLUMN_COMMENT,
          DATA_TYPE,
          COLUMN_TYPE,
          IS_NULLABLE,
          COLUMN_KEY,
          EXTRA,
          ORDINAL_POSITION,
          COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({placeholders})
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """,
        [_database_name(), *table_names],
    )
    statistic_rows = _rows(
        f"""
        SELECT
          TABLE_NAME,
          COLUMN_NAME,
          INDEX_NAME,
          NON_UNIQUE
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({placeholders})
        """,
        [_database_name(), *table_names],
    )

    table_map: dict[str, dict] = {}
    unique_columns_by_table: dict[str, set[str]] = {}
    for row in managed_tables:
        table_name = row["TABLE_NAME"]
        comment = _normalize_text(row["TABLE_COMMENT"])
        table_map[table_name] = {
            "table_name": table_name,
            "label": comment or _fallback_chinese_label(table_name, "表"),
            "comment": comment or _fallback_chinese_label(table_name, "表"),
            "primary_key": "",
            "columns": [],
        }
        unique_columns_by_table[table_name] = set()

    for row in statistic_rows:
        if int(row.get("NON_UNIQUE") or 0) != 0:
            continue
        table_name = row["TABLE_NAME"]
        unique_columns_by_table.setdefault(table_name, set()).add(row["COLUMN_NAME"])

    for row in column_rows:
        table_name = row["TABLE_NAME"]
        comment = _normalize_text(row["COLUMN_COMMENT"])
        column_name = row["COLUMN_NAME"]
        data_type = _normalize_text(row["DATA_TYPE"]).lower()
        column_type = _normalize_text(row["COLUMN_TYPE"]).lower()
        extra = _normalize_text(row["EXTRA"]).lower()
        is_primary_key = _normalize_text(row["COLUMN_KEY"]).upper() == "PRI"
        is_auto = "auto_increment" in extra
        is_audit_field = column_name in {"created_at", "updated_at", "create_time", "update_time"}
        is_unique_key = is_primary_key or column_name in unique_columns_by_table.get(table_name, set())
        is_internal_identifier = _is_internal_identifier_column(column_name, is_primary_key=is_primary_key)
        is_business_identifier = _is_business_identifier_column(
            column_name,
            is_unique_key=is_unique_key,
            is_internal_identifier=is_internal_identifier,
        )
        form_type = "text"
        if data_type in {"text", "longtext", "mediumtext", "json"}:
          form_type = "textarea"
        elif data_type == "date":
          form_type = "date"
        elif data_type in {"datetime", "timestamp"}:
          form_type = "datetime"
        elif data_type in {"tinyint"} and column_type.startswith("tinyint(1)"):
          form_type = "boolean"
        elif data_type in {"int", "bigint", "smallint", "mediumint", "tinyint"}:
          form_type = "integer"
        elif data_type in {"decimal", "float", "double"}:
          form_type = "decimal"

        column_meta = {
            "name": column_name,
            "label": comment or _fallback_chinese_label(column_name),
            "comment": comment or _fallback_chinese_label(column_name),
            "data_type": data_type,
            "column_type": column_type,
            "nullable": _normalize_text(row["IS_NULLABLE"]).upper() == "YES",
            "primary_key": is_primary_key,
            "auto_increment": is_auto,
            "unique_key": is_unique_key,
            "system_identifier": is_internal_identifier,
            "business_identifier": is_business_identifier,
            "creatable": not is_auto and not is_audit_field and not is_primary_key,
            "editable": not is_auto and not is_audit_field and not is_primary_key and not is_internal_identifier and not is_business_identifier,
            "searchable": data_type in {"char", "varchar", "text", "longtext", "mediumtext"},
            "listable": not is_internal_identifier and not is_business_identifier and not (data_type in {"longtext", "mediumtext"} and column_name not in {"business_scope"}),
            "detail_visible": not is_internal_identifier and not is_business_identifier,
            "required": not (_normalize_text(row["IS_NULLABLE"]).upper() == "YES") and row["COLUMN_DEFAULT"] is None and not is_auto,
            "form_type": form_type,
        }
        table_map[table_name]["columns"].append(column_meta)
        if is_primary_key:
            table_map[table_name]["primary_key"] = column_name

    for table_name, meta in table_map.items():
        meta["columns"] = _unique_column_labels(meta["columns"])
        if not meta["primary_key"] and meta["columns"]:
            meta["primary_key"] = meta["columns"][0]["name"]
    _attach_relation_metadata(table_map)
    for table_name, meta in table_map.items():
        meta["creatable_columns"] = [column for column in meta["columns"] if column["creatable"]]
        meta["editable_columns"] = [column for column in meta["columns"] if column["editable"]]
        meta["searchable_columns"] = [column for column in meta["columns"] if column["searchable"]]
        meta["list_columns"] = [column for column in meta["columns"] if column["listable"]]

    return table_map


def _managed_table_or_error(table_name: str) -> tuple[dict | None, JsonResponse | None]:
    table = _managed_table_map().get(table_name)
    if not table:
        return None, _json_error("未找到可管理的数据表", status=404)
    return table, None


def _serialize_cell(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat(sep=" ")
        except TypeError:
            return value.isoformat()
    return value


def _parse_bool_like(text: str) -> int:
    normalized = _normalize_text(text)
    if normalized in {"1", "是", "true", "True", "TRUE", "y", "Y"}:
        return 1
    if normalized in {"0", "否", "false", "False", "FALSE", "n", "N"}:
        return 0
    raise ValueError("布尔字段请输入“是/否”或“1/0”")


def _coerce_value_by_column(column: dict, value):
    if value is None:
        return None
    text = _normalize_text(value)
    if text == "":
        return None

    data_type = column["data_type"]
    column_type = column["column_type"]
    if data_type == "date":
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError as error:
            raise ValueError(f"{column['label']}格式应为 YYYY-MM-DD") from error
    if data_type in {"datetime", "timestamp"}:
        normalized = text.replace("T", " ")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError as error:
            raise ValueError(f"{column['label']}格式应为 YYYY-MM-DD HH:MM:SS") from error
    if data_type in {"int", "bigint", "smallint", "mediumint"}:
        try:
            return int(text)
        except ValueError as error:
            raise ValueError(f"{column['label']}应为整数") from error
    if data_type == "tinyint":
        if column_type.startswith("tinyint(1)"):
            return _parse_bool_like(text)
        try:
            return int(text)
        except ValueError as error:
            raise ValueError(f"{column['label']}应为整数") from error
    if data_type in {"decimal", "float", "double"}:
        try:
            return Decimal(text)
        except InvalidOperation as error:
            raise ValueError(f"{column['label']}应为数字") from error
    return text


def _validated_row_payload(table: dict, payload: dict, *, mode: str = "update", include_primary_key: bool = False) -> dict:
    values = {}
    creatable_mode = mode in {"create", "import"}
    for column in table["columns"]:
        allowed = column["creatable"] if creatable_mode else column["editable"]
        if not include_primary_key and not allowed:
            continue
        if include_primary_key and column["primary_key"]:
            values[column["name"]] = _coerce_value_by_column(column, payload.get(column["name"]))
            continue
        if not allowed:
            continue
        coerced = _coerce_value_by_column(column, payload.get(column["name"]))
        if column["required"] and coerced is None:
            raise ValueError(f"{column['label']}不能为空")
        values[column["name"]] = coerced
    return values


def _pick_order_column(table: dict) -> str:
    column_names = {column["name"] for column in table["columns"]}
    for candidate in ["updated_at", "update_time", "created_at", "create_time", table["primary_key"]]:
        if candidate in column_names:
            return candidate
    return table["primary_key"]


def _enrich_relation_display_values(table: dict, rows: list[dict]):
    if not rows:
        return rows

    relation_columns = [column for column in table["columns"] if column.get("relation")]
    for column in relation_columns:
        relation = column["relation"]
        ids = []
        for row in rows:
            value = row.get(column["name"])
            if value not in (None, ""):
                ids.append(value)
        unique_ids = list(dict.fromkeys(ids))
        if not unique_ids:
            continue

        placeholders = ", ".join(["%s"] * len(unique_ids))
        select_fields = [
            f"`{relation['value_field']}` AS relation_value",
            f"`{relation['label_field']}` AS relation_label",
        ]
        if relation.get("subtitle_field"):
            select_fields.append(f"`{relation['subtitle_field']}` AS relation_subtitle")

        target_rows = _rows(
            f"""
            SELECT {", ".join(select_fields)}
            FROM `{relation['target_table']}`
            WHERE `{relation['value_field']}` IN ({placeholders})
            """,
            unique_ids,
        )

        relation_map = {}
        for target_row in target_rows:
            label = _normalize_text(target_row.get("relation_label"))
            subtitle = _normalize_text(target_row.get("relation_subtitle"))
            if subtitle:
                label = f"{label}（{subtitle}）" if label else subtitle
            relation_map[str(target_row["relation_value"])] = label or "未命名记录"

        for row in rows:
            raw_value = row.get(column["name"])
            if raw_value in (None, ""):
                row[relation["display_column"]] = ""
                continue
            row[relation["display_column"]] = relation_map.get(str(raw_value), "未匹配关联记录")

    return rows


def _positive_int(value, fallback: int) -> int:
    text = _normalize_text(value)
    return int(text) if text.isdigit() and int(text) > 0 else fallback


def _format_date_output(value) -> str:
    return value.isoformat() if value else ""


def _parse_date_input(value):
    text = _normalize_text(value)
    if not text:
        return None
    normalized = text[:10]
    try:
        return datetime.strptime(normalized, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("成立日期格式应为 YYYY-MM-DD") from error


def _parse_decimal_input(value):
    text = _normalize_text(value)
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError("资本字段格式不正确") from error


def _coerce_system_company_row(row: dict) -> dict:
    return {
        "company_name": _normalize_text(row.get("company_name")),
        "credit_code": _normalize_text(row.get("credit_code")).upper(),
        "legal_representative": _normalize_text(row.get("legal_representative")) or None,
        "establish_date": _parse_date_input(row.get("establish_date")),
        "industry_belong": _normalize_text(row.get("industry_belong")) or None,
        "register_capital": _parse_decimal_input(row.get("register_capital")),
        "paid_capital": _parse_decimal_input(row.get("paid_capital")),
        "financing_round": _normalize_text(row.get("financing_round")) or None,
        "company_type": _normalize_text(row.get("company_type")) or None,
        "organization_type": _normalize_text(row.get("organization_type")) or None,
        "investment_type": _normalize_text(row.get("investment_type")) or None,
        "company_scale": _normalize_text(row.get("company_scale")) or None,
        "contact_phone": _normalize_text(row.get("contact_phone")) or None,
        "email_business": _normalize_text(row.get("email_business")) or None,
        "register_address": _normalize_text(row.get("register_address")) or None,
        "shareholders": _normalize_text(row.get("shareholders")) or None,
        "qualification_label": _normalize_text(row.get("qualification_label")) or None,
        "register_number": _normalize_text(row.get("register_number")) or None,
        "org_code": _normalize_text(row.get("org_code")) or None,
        "business_scope": _normalize_text(row.get("business_scope")) or None,
    }


def _ensure_company_basic_count(company_id: int):
    _execute(
        """
        INSERT INTO company_basic_count (company_id)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE company_id = VALUES(company_id)
        """,
        [company_id],
    )


def _delete_companies_cascade(company_ids: list[int]):
    if not company_ids:
        return

    placeholders = ", ".join(["%s"] * len(company_ids))

    _execute(
        f"""
        DELETE ptm
        FROM company_patent_patent_type_map ptm
        JOIN company_patent cp ON cp.company_patent_id = ptm.company_patent_id
        WHERE cp.company_id IN ({placeholders})
        """,
        company_ids,
    )

    _execute(
        f"""
        DELETE pcm
        FROM company_patent_company_map pcm
        LEFT JOIN company_patent cp ON cp.company_patent_id = pcm.company_patent_id
        WHERE pcm.company_id IN ({placeholders}) OR cp.company_id IN ({placeholders})
        """,
        [*company_ids, *company_ids],
    )

    _execute(
        f"""
        DELETE FROM company_customer
        WHERE company_id IN ({placeholders}) OR customer_company_id IN ({placeholders})
        """,
        [*company_ids, *company_ids],
    )

    _execute(
        f"""
        DELETE FROM company_supplier
        WHERE company_id IN ({placeholders}) OR supplier_company_id IN ({placeholders})
        """,
        [*company_ids, *company_ids],
    )

    for table_name, column_name in COMPANY_DELETE_TABLES:
        _execute(
            f"DELETE FROM {table_name} WHERE {column_name} IN ({placeholders})",
            company_ids,
        )

    _execute(
        f"DELETE FROM company_basic WHERE company_id IN ({placeholders})",
        company_ids,
    )


def _list_stats(keyword: str) -> dict:
    params: list = []
    where = "WHERE 1 = 1"
    if keyword:
        where += " AND (cb.company_name LIKE %s OR cb.credit_code LIKE %s)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    rows = _rows(
        f"""
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN COALESCE(cb.is_high_tech_enterprise, 0) = 1 THEN 1 ELSE 0 END) AS highTech,
          SUM(CASE WHEN ss.enterprise_id IS NOT NULL THEN 1 ELSE 0 END) AS scored,
          SUM(CASE WHEN cb.updated_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) AS recentUpdated
        FROM company_basic cb
        LEFT JOIN scoring_scoreresult ss ON ss.enterprise_id = cb.company_id
        {where}
        """,
        params,
    )
    stats = rows[0] if rows else {}
    return {
        "total": int(stats.get("total") or 0),
        "highTech": int(stats.get("highTech") or 0),
        "scored": int(stats.get("scored") or 0),
        "recentUpdated": int(stats.get("recentUpdated") or 0),
    }


def _map_company_list_row(row: dict) -> dict:
    return {
        "company_id": int(row["company_id"]),
        "company_name": _normalize_text(row["company_name"]),
        "credit_code": _normalize_text(row["credit_code"]),
        "establish_date": _format_date_output(row.get("establish_date")),
        "register_capital": row.get("register_capital") or "",
        "paid_capital": row.get("paid_capital") or "",
        "company_type": _normalize_text(row.get("company_type")),
        "organization_type": _normalize_text(row.get("org_type")),
        "investment_type": _normalize_text(row.get("investment_type")),
        "company_scale": _normalize_text(row.get("company_scale")),
        "branch_count": int(row.get("branch_count") or 0),
        "branch_name": _normalize_text(row.get("branch_name")),
        "register_address": _normalize_text(row.get("register_address")),
        "financing_round": _normalize_text(row.get("financing_round")),
        "company_qualification": _normalize_text(row.get("qualification_label")),
        "legal_representative": _normalize_text(row.get("legal_representative")),
        "register_number": _normalize_text(row.get("register_number")),
        "org_code": _normalize_text(row.get("org_code")),
        "industry_belong": _normalize_text(row.get("industry_belong")),
        "business_scope": _normalize_text(row.get("business_scope")),
        "email_business": _normalize_text(row.get("email_business")),
        "shareholders": _normalize_text(row.get("latest_shareholder_name")),
        "contact_phone": _normalize_text(row.get("contact_phone")),
        "updated_at": row["updated_at"].isoformat(sep=" ") if row.get("updated_at") else "",
        "total_score": float(row.get("total_score") or 0) if row.get("total_score") is not None else None,
        "is_high_tech_enterprise": int(row.get("is_high_tech_enterprise") or 0),
        "is_tech_sme": int(row.get("is_tech_sme") or 0),
        "is_srdi_sme": int(row.get("is_srdi_sme") or 0),
        "is_gazelle_company": int(row.get("is_gazelle_company") or 0),
    }


def _fetch_company_detail_by_id(company_id: int) -> dict | None:
    rows = _rows(
        """
        SELECT
          cb.*,
          cbc.branch_count,
          ss.total_score,
          ss.basic_score,
          ss.tech_score,
          ss.professional_score
        FROM company_basic cb
        LEFT JOIN company_basic_count cbc ON cbc.company_id = cb.company_id
        LEFT JOIN scoring_scoreresult ss ON ss.enterprise_id = cb.company_id
        WHERE cb.company_id = %s
        LIMIT 1
        """,
        [company_id],
    )
    return rows[0] if rows else None


def _map_company_detail_row(row: dict) -> dict:
    return {
        **_map_company_list_row(row),
        "approved_date": _format_date_output(row.get("approved_date")),
        "business_term": _normalize_text(row.get("business_term")),
        "company_status": _normalize_text(row.get("company_status")),
        "website": _normalize_text(row.get("website")),
        "contact_info": _normalize_text(row.get("contact_info")),
        "recommended_phone": _normalize_text(row.get("recommended_phone")),
        "register_sheng": _normalize_text(row.get("register_sheng")),
        "register_shi": _normalize_text(row.get("register_shi")),
        "register_xian": _normalize_text(row.get("register_xian")),
        "subdistrict": _normalize_text(row.get("subdistrict")),
        "register_address_detail": _normalize_text(row.get("register_address_detail")),
        "employee_count": int(row.get("employee_count") or 0),
        "insured_count": int(row.get("insured_count") or 0),
        "taxpayer_credit_rating": _normalize_text(row.get("taxpayer_credit_rating")),
        "basic_score": float(row.get("basic_score") or 0) if row.get("basic_score") is not None else None,
        "tech_score": float(row.get("tech_score") or 0) if row.get("tech_score") is not None else None,
        "professional_score": float(row.get("professional_score") or 0) if row.get("professional_score") is not None else None,
    }


@require_GET
def company_list(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    keyword = _normalize_text(request.GET.get("keyword"))
    page = _positive_int(request.GET.get("page"), 1)
    page_size = _positive_int(request.GET.get("pageSize"), 15)
    offset = (page - 1) * page_size

    params: list = []
    where = "WHERE 1 = 1"
    if keyword:
        where += " AND (cb.company_name LIKE %s OR cb.credit_code LIKE %s)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    stats = _list_stats(keyword)
    rows = _rows(
        f"""
        SELECT
          cb.company_id,
          cb.company_name,
          cb.credit_code,
          cb.establish_date,
          cb.register_capital,
          cb.paid_capital,
          cb.company_type,
          cb.org_type,
          cb.investment_type,
          cb.company_scale,
          cb.branch_name,
          cb.register_address,
          cb.financing_round,
          cb.qualification_label,
          cb.legal_representative,
          cb.register_number,
          cb.org_code,
          cb.industry_belong,
          cb.business_scope,
          cb.email_business,
          cb.latest_shareholder_name,
          cb.contact_phone,
          cb.updated_at,
          cb.is_high_tech_enterprise,
          cb.is_tech_sme,
          cb.is_srdi_sme,
          cb.is_gazelle_company,
          cbc.branch_count,
          ss.total_score
        FROM company_basic cb
        LEFT JOIN company_basic_count cbc ON cbc.company_id = cb.company_id
        LEFT JOIN scoring_scoreresult ss ON ss.enterprise_id = cb.company_id
        {where}
        ORDER BY cb.updated_at DESC, cb.company_id DESC
        LIMIT %s OFFSET %s
        """,
        [*params, page_size, offset],
    )

    return JsonResponse(
        {
            "success": True,
            "data": [_map_company_list_row(row) for row in rows],
            "total": stats["total"],
            "stats": stats,
        }
    )


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def company_detail(request, identifier: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    company_id = _resolve_company_id(identifier, identifier)
    if not company_id:
        return _json_error("未找到对应企业", status=404)

    if request.method == "GET":
        company = _fetch_company_detail_by_id(company_id)
        if not company:
            return _json_error("未找到对应企业", status=404)
        return JsonResponse({"success": True, "data": _map_company_detail_row(company)})

    if request.method == "DELETE":
        with transaction.atomic():
            _delete_companies_cascade([company_id])
        return JsonResponse({"success": True, "message": "企业数据已删除"})

    payload = _json_body(request)
    try:
        company = _coerce_system_company_row(payload)
    except ValueError as error:
        return _json_error(str(error))

    if not company["company_name"] or not company["credit_code"]:
        return _json_error("企业名称和统一社会信用代码不能为空")

    existing = _scalar("SELECT company_id FROM company_basic WHERE company_id = %s LIMIT 1", [company_id])
    if not existing:
        return _json_error("未找到企业", status=404)

    duplicate = _scalar(
        "SELECT company_id FROM company_basic WHERE credit_code = %s AND company_id <> %s LIMIT 1",
        [company["credit_code"], company_id],
    )
    if duplicate:
        return _json_error("统一社会信用代码已存在", status=409)

    with transaction.atomic():
        _execute(
            """
            UPDATE company_basic
            SET
              company_name = %s,
              credit_code = %s,
              legal_representative = %s,
              establish_date = %s,
              industry_belong = %s,
              register_capital = %s,
              paid_capital = %s,
              financing_round = %s,
              company_type = %s,
              org_type = %s,
              investment_type = %s,
              company_scale = %s,
              contact_phone = %s,
              email_business = %s,
              register_address = %s,
              latest_shareholder_name = %s,
              qualification_label = %s,
              register_number = %s,
              org_code = %s,
              business_scope = %s
            WHERE company_id = %s
            """,
            [
                company["company_name"],
                company["credit_code"],
                company["legal_representative"],
                company["establish_date"],
                company["industry_belong"],
                company["register_capital"],
                company["paid_capital"],
                company["financing_round"],
                company["company_type"],
                company["organization_type"],
                company["investment_type"],
                company["company_scale"],
                company["contact_phone"],
                company["email_business"],
                company["register_address"],
                company["shareholders"],
                company["qualification_label"],
                company["register_number"],
                company["org_code"],
                company["business_scope"],
                company_id,
            ],
        )
        _ensure_company_basic_count(company_id)

    detail = _fetch_company_detail_by_id(company_id)
    return JsonResponse({"success": True, "data": _map_company_detail_row(detail)})


@csrf_exempt
@require_http_methods(["POST"])
def company_create(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    payload = _json_body(request)
    try:
        company = _coerce_system_company_row(payload)
    except ValueError as error:
        return _json_error(str(error))

    if not company["company_name"] or not company["credit_code"]:
        return _json_error("企业名称和统一社会信用代码不能为空")

    duplicate = _scalar(
        "SELECT company_id FROM company_basic WHERE credit_code = %s LIMIT 1",
        [company["credit_code"]],
    )
    if duplicate:
        return _json_error("统一社会信用代码已存在", status=409)

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO company_basic (
                  company_name,
                  credit_code,
                  legal_representative,
                  establish_date,
                  industry_belong,
                  register_capital,
                  paid_capital,
                  financing_round,
                  company_type,
                  org_type,
                  investment_type,
                  company_scale,
                  contact_phone,
                  email_business,
                  register_address,
                  latest_shareholder_name,
                  qualification_label,
                  register_number,
                  org_code,
                  business_scope
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    company["company_name"],
                    company["credit_code"],
                    company["legal_representative"],
                    company["establish_date"],
                    company["industry_belong"],
                    company["register_capital"],
                    company["paid_capital"],
                    company["financing_round"],
                    company["company_type"],
                    company["organization_type"],
                    company["investment_type"],
                    company["company_scale"],
                    company["contact_phone"],
                    company["email_business"],
                    company["register_address"],
                    company["shareholders"],
                    company["qualification_label"],
                    company["register_number"],
                    company["org_code"],
                    company["business_scope"],
                ],
            )
            company_id = int(cursor.lastrowid)
        _ensure_company_basic_count(company_id)

    detail = _fetch_company_detail_by_id(company_id)
    return JsonResponse({"success": True, "data": _map_company_detail_row(detail)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def company_batch_delete(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    payload = _json_body(request)
    ids = [
        _positive_int(value, 0)
        for value in (payload.get("ids") or [])
        if _positive_int(value, 0)
    ]
    if not ids:
        return _json_error("请选择要删除的企业")

    with transaction.atomic():
        _delete_companies_cascade(ids)

    return JsonResponse({"success": True, "message": f"已删除 {len(ids)} 家企业"})


@require_GET
def company_template_download(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(SYSTEM_COMPANY_TEMPLATE_HEADERS)
    writer.writerow(
        [
            "示例企业",
            "91110000123456789A",
            "张三",
            "2024-01-01",
            "生物制药",
            "1000",
            "500",
            "A轮",
            "有限责任公司",
            "企业法人",
            "民营",
            "100-499人",
            "010-12345678",
            "demo@example.com",
            "北京市朝阳区示例路1号",
            "示例股东",
            "高新技术企业",
            "110000000000001",
            "123456789",
            "技术开发；技术咨询；技术服务",
        ]
    )

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="enterprise-data-template.csv"'
    response.write("")
    response.content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    return response


@csrf_exempt
@require_http_methods(["POST"])
def company_import(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    payload = _json_body(request)
    csv_text = _normalize_text(payload.get("csvText"))
    if not csv_text:
        return _json_error("请先提供 CSV 内容")

    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    if len(rows) < 2:
        return _json_error("CSV 至少需要表头和一行数据")

    headers = [_normalize_text(header).lower() for header in rows[0]]
    missing_headers = [header for header in SYSTEM_COMPANY_TEMPLATE_HEADERS if header not in headers]
    if missing_headers:
        return _json_error(f"CSV 缺少字段：{'、'.join(missing_headers)}")

    payload_rows = []
    for cells in rows[1:]:
        raw = {}
        for index, header in enumerate(headers):
            raw[header] = _normalize_text(cells[index] if index < len(cells) else "")
        if _normalize_text(raw.get("company_name")) or _normalize_text(raw.get("credit_code")):
            try:
                payload_rows.append(_coerce_system_company_row(raw))
            except ValueError as error:
                return _json_error(str(error))

    if not payload_rows:
        return _json_error("未识别到有效企业数据")

    inserted_count = 0
    updated_count = 0

    with transaction.atomic():
        for company in payload_rows:
            if not company["company_name"] or not company["credit_code"]:
                return _json_error("存在缺少企业名称或统一社会信用代码的行")

            existing_id = _scalar(
                "SELECT company_id FROM company_basic WHERE credit_code = %s LIMIT 1",
                [company["credit_code"]],
            )

            if existing_id:
                _execute(
                    """
                    UPDATE company_basic
                    SET
                      company_name = %s,
                      legal_representative = %s,
                      establish_date = %s,
                      industry_belong = %s,
                      register_capital = %s,
                      paid_capital = %s,
                      financing_round = %s,
                      company_type = %s,
                      org_type = %s,
                      investment_type = %s,
                      company_scale = %s,
                      contact_phone = %s,
                      email_business = %s,
                      register_address = %s,
                      latest_shareholder_name = %s,
                      qualification_label = %s,
                      register_number = %s,
                      org_code = %s,
                      business_scope = %s
                    WHERE company_id = %s
                    """,
                    [
                        company["company_name"],
                        company["legal_representative"],
                        company["establish_date"],
                        company["industry_belong"],
                        company["register_capital"],
                        company["paid_capital"],
                        company["financing_round"],
                        company["company_type"],
                        company["organization_type"],
                        company["investment_type"],
                        company["company_scale"],
                        company["contact_phone"],
                        company["email_business"],
                        company["register_address"],
                        company["shareholders"],
                        company["qualification_label"],
                        company["register_number"],
                        company["org_code"],
                        company["business_scope"],
                        int(existing_id),
                    ],
                )
                _ensure_company_basic_count(int(existing_id))
                updated_count += 1
            else:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO company_basic (
                          company_name,
                          credit_code,
                          legal_representative,
                          establish_date,
                          industry_belong,
                          register_capital,
                          paid_capital,
                          financing_round,
                          company_type,
                          org_type,
                          investment_type,
                          company_scale,
                          contact_phone,
                          email_business,
                          register_address,
                          latest_shareholder_name,
                          qualification_label,
                          register_number,
                          org_code,
                          business_scope
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            company["company_name"],
                            company["credit_code"],
                            company["legal_representative"],
                            company["establish_date"],
                            company["industry_belong"],
                            company["register_capital"],
                            company["paid_capital"],
                            company["financing_round"],
                            company["company_type"],
                            company["organization_type"],
                            company["investment_type"],
                            company["company_scale"],
                            company["contact_phone"],
                            company["email_business"],
                            company["register_address"],
                            company["shareholders"],
                            company["qualification_label"],
                            company["register_number"],
                            company["org_code"],
                            company["business_scope"],
                        ],
                    )
                    company_id = int(cursor.lastrowid)
                _ensure_company_basic_count(company_id)
                inserted_count += 1

    return JsonResponse(
        {
            "success": True,
            "message": f"导入完成：新增 {inserted_count} 家，更新 {updated_count} 家",
            "data": {
                "insertedCount": inserted_count,
                "updatedCount": updated_count,
                "totalCount": len(payload_rows),
            },
        }
    )


@require_GET
def managed_table_list(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    tables = list(_managed_table_map().values())
    data = [
        {
            "tableName": table["table_name"],
            "label": table["label"],
            "comment": table["comment"],
            "primaryKey": table["primary_key"],
            "columnCount": len(table["columns"]),
        }
        for table in tables
    ]
    return JsonResponse({"success": True, "data": data})


@require_GET
def managed_table_schema(request, table_name: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    table, error = _managed_table_or_error(table_name)
    if error:
        return error

    return JsonResponse(
        {
            "success": True,
            "data": {
                "tableName": table["table_name"],
                "label": table["label"],
                "comment": table["comment"],
                "primaryKey": table["primary_key"],
                "columns": [
                    {
                        "name": column["name"],
                        "label": column["label"],
                        "comment": column["comment"],
                        "dataType": column["data_type"],
                        "columnType": column["column_type"],
                        "nullable": column["nullable"],
                        "primaryKey": column["primary_key"],
                        "autoIncrement": column["auto_increment"],
                        "uniqueKey": column["unique_key"],
                        "systemIdentifier": column["system_identifier"],
                        "businessIdentifier": column["business_identifier"],
                        "creatable": column["creatable"],
                        "editable": column["editable"],
                        "searchable": column["searchable"],
                        "listable": column["listable"],
                        "detailVisible": column["detail_visible"],
                        "relationDisplay": bool(column.get("relation_display")),
                        "relation": {
                            "targetTable": column["relation"]["target_table"],
                            "valueField": column["relation"]["value_field"],
                            "labelField": column["relation"]["label_field"],
                            "subtitleField": column["relation"].get("subtitle_field"),
                            "displayColumn": column["relation"]["display_column"],
                            "displayLabel": column["relation"]["display_label"],
                        } if column.get("relation") else None,
                        "required": column["required"],
                        "formType": column["form_type"],
                        "importLabel": column["import_label"],
                    }
                    for column in table["columns"]
                ],
            },
        }
    )


@require_GET
def managed_table_rows(request, table_name: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    table, error = _managed_table_or_error(table_name)
    if error:
        return error

    keyword = _normalize_text(request.GET.get("keyword"))
    page = _positive_int(request.GET.get("page"), 1)
    page_size = _positive_int(request.GET.get("pageSize"), 15)
    offset = (page - 1) * page_size

    where_parts = ["1 = 1"]
    params: list = []
    if keyword and table["searchable_columns"]:
        like_parts = []
        for column in table["searchable_columns"][:8]:
            like_parts.append(f"`{column['name']}` LIKE %s")
            params.append(f"%{keyword}%")
        where_parts.append(f"({' OR '.join(like_parts)})")

    where_clause = " AND ".join(where_parts)
    total = int(
        _scalar(
            f"SELECT COUNT(*) FROM `{table['table_name']}` WHERE {where_clause}",
            params,
        )
        or 0
    )

    order_column = _pick_order_column(table)
    rows = _rows(
        f"""
        SELECT *
        FROM `{table['table_name']}`
        WHERE {where_clause}
        ORDER BY `{order_column}` DESC
        LIMIT %s OFFSET %s
        """,
        [*params, page_size, offset],
    )

    data = []
    for row in rows:
        data.append({key: _serialize_cell(value) for key, value in row.items()})
    data = _enrich_relation_display_values(table, data)

    return JsonResponse(
        {
            "success": True,
            "data": {
                "table": {
                    "tableName": table["table_name"],
                    "label": table["label"],
                    "comment": table["comment"],
                    "primaryKey": table["primary_key"],
                },
                "columns": [
                    {
                        "name": column["name"],
                        "label": column["label"],
                        "comment": column["comment"],
                        "listable": column["listable"],
                        "detailVisible": column["detail_visible"],
                        "relationDisplay": bool(column.get("relation_display")),
                        "formType": column["form_type"],
                        "primaryKey": column["primary_key"],
                    }
                    for column in table["columns"]
                ],
                "rows": data,
                "total": total,
            },
        }
    )


@require_GET
def managed_table_relation_options(request, table_name: str, column_name: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    table, error = _managed_table_or_error(table_name)
    if error:
        return error

    column = next((item for item in table["columns"] if item["name"] == column_name), None)
    relation = column.get("relation") if column else None
    if not relation:
        return _json_error("当前字段不支持名称关联选择", status=404)

    keyword = _normalize_text(request.GET.get("keyword"))
    limit = min(_positive_int(request.GET.get("limit"), 20), 50)
    params: list = []
    where_parts = ["1 = 1"]
    if keyword:
        search_parts = [f"`{relation['label_field']}` LIKE %s"]
        params.append(f"%{keyword}%")
        if relation.get("subtitle_field"):
            search_parts.append(f"`{relation['subtitle_field']}` LIKE %s")
            params.append(f"%{keyword}%")
        where_parts.append(f"({' OR '.join(search_parts)})")

    target_table = _managed_table_map().get(relation["target_table"])
    order_column = _pick_order_column(target_table) if target_table else relation["label_field"]
    select_fields = [
        f"`{relation['value_field']}` AS relation_value",
        f"`{relation['label_field']}` AS relation_label",
    ]
    if relation.get("subtitle_field"):
        select_fields.append(f"`{relation['subtitle_field']}` AS relation_subtitle")

    rows = _rows(
        f"""
        SELECT {", ".join(select_fields)}
        FROM `{relation['target_table']}`
        WHERE {' AND '.join(where_parts)}
        ORDER BY `{order_column}` DESC
        LIMIT %s
        """,
        [*params, limit],
    )

    options = []
    for row in rows:
        label = _normalize_text(row.get("relation_label")) or "未命名记录"
        subtitle = _normalize_text(row.get("relation_subtitle"))
        options.append(
            {
                "value": _serialize_cell(row["relation_value"]),
                "label": label,
                "description": subtitle or None,
            }
        )

    return JsonResponse({"success": True, "data": options})


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def managed_table_row_detail(request, table_name: str, row_id: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    table, error = _managed_table_or_error(table_name)
    if error:
        return error

    pk_column = next((column for column in table["columns"] if column["name"] == table["primary_key"]), None)
    if not pk_column:
        return _json_error("当前数据表缺少主键，无法管理", status=400)

    try:
        pk_value = _coerce_value_by_column(pk_column, row_id)
    except ValueError as error:
        return _json_error(str(error))

    if request.method == "GET":
        rows = _rows(
            f"SELECT * FROM `{table['table_name']}` WHERE `{table['primary_key']}` = %s LIMIT 1",
            [pk_value],
        )
        if not rows:
            return _json_error("未找到对应记录", status=404)
        record = {key: _serialize_cell(value) for key, value in rows[0].items()}
        _enrich_relation_display_values(table, [record])
        return JsonResponse({"success": True, "data": record})

    if request.method == "DELETE":
        _execute(
            f"DELETE FROM `{table['table_name']}` WHERE `{table['primary_key']}` = %s",
            [pk_value],
        )
        return JsonResponse({"success": True, "message": "记录已删除"})

    payload = _json_body(request)
    try:
        values = _validated_row_payload(table, payload, mode="update")
    except ValueError as error:
        return _json_error(str(error))

    if not values:
        return _json_error("当前数据表没有可编辑字段")

    assignments = ", ".join([f"`{column_name}` = %s" for column_name in values])
    _execute(
        f"""
        UPDATE `{table['table_name']}`
        SET {assignments}
        WHERE `{table['primary_key']}` = %s
        """,
        [*values.values(), pk_value],
    )
    rows = _rows(
        f"SELECT * FROM `{table['table_name']}` WHERE `{table['primary_key']}` = %s LIMIT 1",
        [pk_value],
    )
    record = {key: _serialize_cell(value) for key, value in rows[0].items()}
    _enrich_relation_display_values(table, [record])
    return JsonResponse({"success": True, "data": record})


@csrf_exempt
@require_http_methods(["POST"])
def managed_table_row_create(request, table_name: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    table, error = _managed_table_or_error(table_name)
    if error:
        return error

    payload = _json_body(request)
    try:
        values = _validated_row_payload(table, payload, mode="create")
    except ValueError as error:
        return _json_error(str(error))

    if not values:
        return _json_error("当前数据表没有可新增字段")

    columns_sql = ", ".join([f"`{column_name}`" for column_name in values])
    placeholders = ", ".join(["%s"] * len(values))
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO `{table['table_name']}` ({columns_sql}) VALUES ({placeholders})",
                list(values.values()),
            )
            inserted_id = cursor.lastrowid

        if table["table_name"] == "company_basic" and inserted_id:
            _ensure_company_basic_count(int(inserted_id))

    pk_column = next((column for column in table["columns"] if column["name"] == table["primary_key"]), None)
    if inserted_id and pk_column and pk_column["auto_increment"]:
        pk_value = inserted_id
    else:
        pk_value = values.get(table["primary_key"])

    rows = _rows(
        f"SELECT * FROM `{table['table_name']}` WHERE `{table['primary_key']}` = %s LIMIT 1",
        [pk_value],
    )
    record = {key: _serialize_cell(value) for key, value in rows[0].items()}
    _enrich_relation_display_values(table, [record])
    return JsonResponse({"success": True, "data": record}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def managed_table_batch_delete(request, table_name: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    table, error = _managed_table_or_error(table_name)
    if error:
        return error

    pk_column = next((column for column in table["columns"] if column["name"] == table["primary_key"]), None)
    if not pk_column:
        return _json_error("当前数据表缺少主键，无法删除", status=400)

    payload = _json_body(request)
    raw_ids = payload.get("ids") or []
    ids = []
    try:
        for raw_id in raw_ids:
            ids.append(_coerce_value_by_column(pk_column, raw_id))
    except ValueError as error:
        return _json_error(str(error))
    ids = [value for value in ids if value is not None]
    if not ids:
        return _json_error("请选择要删除的记录")

    placeholders = ", ".join(["%s"] * len(ids))
    with transaction.atomic():
        _execute(
            f"DELETE FROM `{table['table_name']}` WHERE `{table['primary_key']}` IN ({placeholders})",
            ids,
        )
    return JsonResponse({"success": True, "message": f"已删除 {len(ids)} 条记录"})


@require_GET
def managed_table_template(request, table_name: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    table, error = _managed_table_or_error(table_name)
    if error:
        return error

    importable_columns = [column for column in table["columns"] if column["creatable"]]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([column["import_label"] for column in importable_columns])
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{table_name}-template.csv"'
    response.content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    return response


@csrf_exempt
@require_http_methods(["POST"])
def managed_table_import(request, table_name: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    table, error = _managed_table_or_error(table_name)
    if error:
        return error

    payload = _json_body(request)
    csv_text = _normalize_text(payload.get("csvText"))
    if not csv_text:
        return _json_error("请先提供 CSV 内容")

    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    if len(rows) < 2:
        return _json_error("CSV 至少需要表头和一行数据")

    importable_columns = [column for column in table["columns"] if column["creatable"]]
    label_map = {column["import_label"]: column for column in importable_columns}
    headers = [_normalize_text(header) for header in rows[0]]
    missing_headers = [column["import_label"] for column in importable_columns if column["required"] and column["import_label"] not in headers]
    if missing_headers:
        return _json_error(f"CSV 缺少必填字段：{'、'.join(missing_headers)}")

    inserted_count = 0
    with transaction.atomic():
        for cells in rows[1:]:
            raw = {}
            for index, header in enumerate(headers):
                column = label_map.get(header)
                if not column:
                    continue
                raw[column["name"]] = _normalize_text(cells[index] if index < len(cells) else "")
            if not any(_normalize_text(value) for value in raw.values()):
                continue
            try:
                values = _validated_row_payload(table, raw, mode="import")
            except ValueError as error:
                return _json_error(str(error))
            if not values:
                continue
            columns_sql = ", ".join([f"`{column_name}`" for column_name in values])
            placeholders = ", ".join(["%s"] * len(values))
            with connection.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO `{table['table_name']}` ({columns_sql}) VALUES ({placeholders})",
                    list(values.values()),
                )
                inserted_id = cursor.lastrowid
            if table["table_name"] == "company_basic" and inserted_id:
                _ensure_company_basic_count(int(inserted_id))
            inserted_count += 1

    return JsonResponse(
        {
            "success": True,
            "message": f"导入完成：新增 {inserted_count} 条记录",
            "data": {"insertedCount": inserted_count},
        }
    )
