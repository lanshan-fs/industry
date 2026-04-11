from __future__ import annotations

from collections import defaultdict

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from auth_api.views import _json_body, _json_error, _normalize_text


TAG_DIMENSION_META_BY_NAME = {
    "基本信息": {"key": "basic", "color": "#1890ff"},
    "经营状况": {"key": "business", "color": "#fa8c16"},
    "知识产权": {"key": "tech", "color": "#722ed1"},
    "风险信息": {"key": "risk", "color": "#f5222d"},
    "街道地区": {"key": "region", "color": "#13c2c2"},
    "行业标签": {"key": "industry", "color": "#fa8c16"},
    "应用场景": {"key": "scene", "color": "#52c41a"},
}
TAG_BUCKET_KEYS = ["basic", "business", "tech", "risk", "region", "industry", "scene"]
INDUSTRY_CHAIN_SUBDIMENSION_NAME = "产业链"
INDUSTRY_CATEGORY_SUBDIMENSION_NAME = "行业分类"


def _rows(query: str, params: list | tuple | None = None) -> list[dict]:
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _scalar(query: str, params: list | tuple | None = None):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        row = cursor.fetchone()
    return row[0] if row else None


def _execute(query: str, params: list | tuple | None = None):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(query, params or [])


def _positive_int(value, fallback: int) -> int:
    text = _normalize_text(value)
    return int(text) if text.isdigit() and int(text) > 0 else fallback


def _credit_code(value) -> str:
    return _normalize_text(value)


def _tag_dimension_meta(dimension_name: str) -> dict:
    return TAG_DIMENSION_META_BY_NAME.get(_normalize_text(dimension_name), {"key": "other", "color": "#8c8c8c"})


def _fetch_company_tags(credit_codes: list[str]) -> list[dict]:
    if not credit_codes:
        return []
    placeholders = ", ".join(["%s"] * len(credit_codes))
    return _rows(
        f"""
        SELECT
          ctm.credit_code AS companyId,
          ctm.create_time AS taggedAt,
          l.company_tag_id AS companyTagId,
          l.company_tag_name AS tagName,
          sd.company_tag_subdimension_id AS subdimensionId,
          sd.company_tag_subdimension_name AS subdimensionName,
          d.company_tag_dimension_id AS dimensionId,
          d.company_tag_dimension_name AS dimensionName
        FROM company_tag_map ctm
        JOIN company_tag_library l
          ON ctm.company_tag_id = l.company_tag_id
        JOIN company_tag_subdimension sd
          ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
        JOIN company_tag_dimension d
          ON sd.company_tag_dimension_id = d.company_tag_dimension_id
        WHERE ctm.credit_code IN ({placeholders})
        ORDER BY ctm.credit_code, d.sort_order, sd.sort_order, l.sort_order, l.company_tag_name
        """,
        credit_codes,
    )


def _empty_tag_buckets() -> dict:
    return {key: [] for key in TAG_BUCKET_KEYS}


def _build_company_tag_view(company_rows: list[dict], tag_rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in tag_rows:
        grouped[_credit_code(row["companyId"])].append(row)

    result = []
    for row in company_rows:
        credit_code = _credit_code(row["companyId"])
        dimensions = _empty_tag_buckets()
        related_tags = grouped.get(credit_code, [])
        tag_details = []
        for tag_row in related_tags:
            meta = _tag_dimension_meta(tag_row["dimensionName"])
            if meta["key"] in dimensions:
                dimensions[meta["key"]].append(_normalize_text(tag_row["tagName"]))
            tag_details.append(
                {
                    "id": int(tag_row["companyTagId"]),
                    "name": _normalize_text(tag_row["tagName"]),
                    "dimensionId": int(tag_row["dimensionId"]),
                    "dimensionName": _normalize_text(tag_row["dimensionName"]),
                    "subdimensionId": int(tag_row["subdimensionId"]),
                    "subdimensionName": _normalize_text(tag_row["subdimensionName"]),
                    "taggedAt": tag_row["taggedAt"].isoformat(sep=" ") if tag_row.get("taggedAt") else "",
                }
            )

        result.append(
            {
                "key": credit_code,
                "companyId": credit_code,
                "name": _normalize_text(row["companyName"]),
                "code": _normalize_text(row["creditCode"]) or credit_code,
                "updateTime": row["updateTime"].isoformat(sep=" ") if row.get("updateTime") else "",
                "dimensions": dimensions,
                "tagCount": len(tag_details),
                "tags": tag_details,
            }
        )
    return result


@require_GET
def tag_companies(request):
    page = _positive_int(request.GET.get("page"), 1)
    page_size = _positive_int(request.GET.get("pageSize"), 10)
    keyword = _normalize_text(request.GET.get("keyword"))
    offset = (page - 1) * page_size

    where = "WHERE 1=1"
    params: list = []
    if keyword:
        where += " AND (company_name LIKE %s OR credit_code LIKE %s)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    total = int(_scalar(f"SELECT COUNT(*) FROM company_basic {where}", params) or 0)
    rows = _rows(
        f"""
        SELECT
          credit_code AS companyId,
          company_name AS companyName,
          credit_code AS creditCode,
          updated_at AS updateTime
        FROM company_basic
        {where}
        ORDER BY updated_at DESC, credit_code DESC
        LIMIT %s OFFSET %s
        """,
        [*params, page_size, offset],
    )
    tag_rows = _fetch_company_tags([_credit_code(row["companyId"]) for row in rows])
    return JsonResponse({"success": True, "data": {"list": _build_company_tag_view(rows, tag_rows), "total": total}})


@csrf_exempt
@require_POST
def tag_add(request):
    payload = _json_body(request)
    credit_code = _credit_code(payload.get("companyId") or payload.get("creditCode"))
    tag_id = _positive_int(payload.get("tagId"), 0)
    tag_name = _normalize_text(payload.get("tagName"))
    if not credit_code or (not tag_id and not tag_name):
        return _json_error("缺少企业或标签参数")

    resolved_tag_id = tag_id
    if not resolved_tag_id and tag_name:
        resolved_tag_id = int(_scalar("SELECT company_tag_id FROM company_tag_library WHERE company_tag_name = %s LIMIT 1", [tag_name]) or 0)
    if not resolved_tag_id:
        return _json_error("标签不存在")

    _execute(
        """
        INSERT INTO company_tag_map (credit_code, company_tag_id, source, confidence, user_id)
        VALUES (%s, %s, 1, 1.00, NULL)
        ON DUPLICATE KEY UPDATE source = VALUES(source), confidence = VALUES(confidence), create_time = CURRENT_TIMESTAMP
        """,
        [credit_code, resolved_tag_id],
    )
    return JsonResponse({"success": True})


@csrf_exempt
@require_POST
def tag_delete(request):
    payload = _json_body(request)
    credit_code = _credit_code(payload.get("companyId") or payload.get("creditCode"))
    tag_id = _positive_int(payload.get("tagId"), 0)
    tag_name = _normalize_text(payload.get("tagName"))
    if not credit_code or (not tag_id and not tag_name):
        return _json_error("缺少企业或标签参数")

    resolved_tag_id = tag_id
    if not resolved_tag_id and tag_name:
        resolved_tag_id = int(_scalar("SELECT company_tag_id FROM company_tag_library WHERE company_tag_name = %s LIMIT 1", [tag_name]) or 0)
    if resolved_tag_id:
        _execute("DELETE FROM company_tag_map WHERE credit_code = %s AND company_tag_id = %s", [credit_code, resolved_tag_id])
    return JsonResponse({"success": True})


@require_GET
def tag_library_options(_request):
    rows = _rows(
        """
        SELECT
          d.company_tag_dimension_id AS dimensionId,
          d.company_tag_dimension_name AS dimensionName,
          sd.company_tag_subdimension_id AS subdimensionId,
          sd.company_tag_subdimension_name AS subdimensionName,
          l.company_tag_id AS tagId,
          l.company_tag_name AS tagName
        FROM company_tag_library l
        JOIN company_tag_subdimension sd
          ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
        JOIN company_tag_dimension d
          ON sd.company_tag_dimension_id = d.company_tag_dimension_id
        ORDER BY d.sort_order, sd.sort_order, l.sort_order, l.company_tag_name
        """
    )

    grouped: dict[str, list[dict]] = {}
    dimensions: dict[int, dict] = {}
    for row in rows:
        meta = _tag_dimension_meta(row["dimensionName"])
        grouped.setdefault(meta["key"], []).append(
            {
                "id": int(row["tagId"]),
                "name": _normalize_text(row["tagName"]),
                "dimensionId": int(row["dimensionId"]),
                "dimensionName": _normalize_text(row["dimensionName"]),
                "subdimensionId": int(row["subdimensionId"]),
                "subdimensionName": _normalize_text(row["subdimensionName"]),
            }
        )
        dimensions.setdefault(
            int(row["dimensionId"]),
            {
                "id": int(row["dimensionId"]),
                "key": meta["key"],
                "name": _normalize_text(row["dimensionName"]),
                "color": meta["color"],
                "tags": [],
            },
        )
        dimensions[int(row["dimensionId"])]["tags"].append(
            {
                "id": int(row["tagId"]),
                "name": _normalize_text(row["tagName"]),
                "subdimensionId": int(row["subdimensionId"]),
                "subdimensionName": _normalize_text(row["subdimensionName"]),
            }
        )
    for key in TAG_BUCKET_KEYS:
        grouped.setdefault(key, [])
    return JsonResponse({"success": True, "data": {"grouped": grouped, "dimensions": list(dimensions.values())}})


@require_GET
def dimension_stats(_request):
    total_companies = int(_scalar("SELECT COUNT(*) FROM company_basic") or 0)
    covered_enterprises = int(
        _scalar(
            """
            SELECT COUNT(DISTINCT b.credit_code)
            FROM company_tag_map m
            JOIN company_basic b ON m.credit_code = b.credit_code
            """
        )
        or 0
    )
    rows = _rows(
        """
        SELECT
          d.company_tag_dimension_id AS id,
          d.company_tag_dimension_name AS name,
          COUNT(DISTINCT l.company_tag_id) AS tagCount,
          COUNT(DISTINCT b.credit_code) AS usedCount
        FROM company_tag_dimension d
        LEFT JOIN company_tag_subdimension sd
          ON d.company_tag_dimension_id = sd.company_tag_dimension_id
        LEFT JOIN company_tag_library l
          ON sd.company_tag_subdimension_id = l.company_tag_subdimension_id
        LEFT JOIN company_tag_map m
          ON l.company_tag_id = m.company_tag_id
        LEFT JOIN company_basic b
          ON m.credit_code = b.credit_code
        GROUP BY d.company_tag_dimension_id, d.company_tag_dimension_name, d.sort_order
        ORDER BY d.sort_order, d.company_tag_dimension_id
        """
    )
    dimensions = []
    for row in rows:
        meta = _tag_dimension_meta(row["name"])
        used_count = int(row["usedCount"] or 0)
        dimensions.append(
            {
                "id": int(row["id"]),
                "name": _normalize_text(row["name"]),
                "tagCount": int(row["tagCount"] or 0),
                "usedCount": used_count,
                "key": meta["key"],
                "color": meta["color"],
                "coverage": round(used_count / total_companies * 100) if total_companies else 0,
            }
        )
    return JsonResponse(
        {
            "success": True,
            "data": {
                "dimensions": dimensions,
                "overview": {
                    "totalTags": sum(int(item["tagCount"]) for item in dimensions),
                    "coveredEnterprises": covered_enterprises,
                    "totalCompanies": total_companies,
                },
            },
        }
    )


@require_GET
def dimension_detail(_request, dimension_id: str):
    dimension_pk = _positive_int(dimension_id, 0)
    if not dimension_pk:
        return _json_error("无效的维度 ID")

    subdimension_id = _positive_int(_request.GET.get("subdimensionId"), 0)
    tag_id = _positive_int(_request.GET.get("tagId"), 0)
    company_page = _positive_int(_request.GET.get("companyPage"), 1)
    company_page_size = _positive_int(_request.GET.get("companyPageSize"), 10)
    company_offset = (company_page - 1) * company_page_size
    keyword = _normalize_text(_request.GET.get("keyword"))

    dimension_rows = _rows(
        """
        SELECT
          d.company_tag_dimension_id AS id,
          d.company_tag_dimension_name AS name,
          d.company_tag_dimension_des AS description,
          COUNT(DISTINCT l.company_tag_id) AS tagCount,
          COUNT(DISTINCT b.credit_code) AS usedCount
        FROM company_tag_dimension d
        LEFT JOIN company_tag_subdimension sd
          ON d.company_tag_dimension_id = sd.company_tag_dimension_id
        LEFT JOIN company_tag_library l
          ON sd.company_tag_subdimension_id = l.company_tag_subdimension_id
        LEFT JOIN company_tag_map m
          ON l.company_tag_id = m.company_tag_id
        LEFT JOIN company_basic b
          ON m.credit_code = b.credit_code
        WHERE d.company_tag_dimension_id = %s
        GROUP BY d.company_tag_dimension_id, d.company_tag_dimension_name, d.company_tag_dimension_des
        """,
        [dimension_pk],
    )
    if not dimension_rows:
        return _json_error("未找到标签维度", status=404)
    dimension = dimension_rows[0]

    total_companies = int(_scalar("SELECT COUNT(*) FROM company_basic") or 0)
    subdimension_rows = _rows(
        """
        SELECT
          sd.company_tag_subdimension_id AS id,
          sd.company_tag_subdimension_name AS name,
          COUNT(DISTINCT l.company_tag_id) AS tagCount,
          COUNT(DISTINCT b.credit_code) AS usedCount
        FROM company_tag_subdimension sd
        LEFT JOIN company_tag_library l
          ON sd.company_tag_subdimension_id = l.company_tag_subdimension_id
        LEFT JOIN company_tag_map m
          ON l.company_tag_id = m.company_tag_id
        LEFT JOIN company_basic b
          ON m.credit_code = b.credit_code
        WHERE sd.company_tag_dimension_id = %s
        GROUP BY sd.company_tag_subdimension_id, sd.company_tag_subdimension_name, sd.sort_order
        ORDER BY sd.sort_order, sd.company_tag_subdimension_id
        """,
        [dimension_pk],
    )
    tag_rows = _rows(
        """
        SELECT
          l.company_tag_id AS id,
          l.company_tag_name AS name,
          sd.company_tag_subdimension_id AS subdimensionId,
          sd.company_tag_subdimension_name AS subdimensionName,
          COUNT(DISTINCT b.credit_code) AS usedCount
        FROM company_tag_library l
        JOIN company_tag_subdimension sd
          ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
        LEFT JOIN company_tag_map m
          ON l.company_tag_id = m.company_tag_id
        LEFT JOIN company_basic b
          ON m.credit_code = b.credit_code
        WHERE sd.company_tag_dimension_id = %s
        GROUP BY l.company_tag_id, l.company_tag_name, sd.company_tag_subdimension_id, sd.company_tag_subdimension_name, sd.sort_order, l.sort_order
        ORDER BY sd.sort_order, l.sort_order, l.company_tag_name
        """,
        [dimension_pk],
    )

    company_conditions = ["sd.company_tag_dimension_id = %s"]
    company_params: list = [dimension_pk]
    if subdimension_id:
        company_conditions.append("sd.company_tag_subdimension_id = %s")
        company_params.append(subdimension_id)
    if tag_id:
        company_conditions.append("l.company_tag_id = %s")
        company_params.append(tag_id)
    if keyword:
        company_conditions.append("(b.company_name LIKE %s OR b.credit_code LIKE %s)")
        company_params.extend([f"%{keyword}%", f"%{keyword}%"])

    company_total = int(
        _scalar(
            f"""
            SELECT COUNT(DISTINCT b.credit_code)
            FROM company_basic b
            JOIN company_tag_map m ON b.credit_code = m.credit_code
            JOIN company_tag_library l ON m.company_tag_id = l.company_tag_id
            JOIN company_tag_subdimension sd ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
            WHERE {' AND '.join(company_conditions)}
            """,
            company_params,
        )
        or 0
    )
    company_rows = _rows(
        f"""
        SELECT
          b.credit_code AS companyId,
          b.company_name AS companyName,
          b.credit_code AS creditCode,
          MAX(m.create_time) AS lastMatchedUsed
        FROM company_basic b
        JOIN company_tag_map m ON b.credit_code = m.credit_code
        JOIN company_tag_library l ON m.company_tag_id = l.company_tag_id
        JOIN company_tag_subdimension sd ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
        WHERE {' AND '.join(company_conditions)}
        GROUP BY b.credit_code, b.company_name, b.credit_code
        ORDER BY lastMatchedUsed DESC, b.credit_code DESC
        LIMIT %s OFFSET %s
        """,
        [*company_params, company_page_size, company_offset],
    )
    matched_company_ids = [_credit_code(row["companyId"]) for row in company_rows]
    company_list = []
    if matched_company_ids:
        placeholders = ", ".join(["%s"] * len(matched_company_ids))
        tag_conditions = ["sd.company_tag_dimension_id = %s", f"b.credit_code IN ({placeholders})"]
        tag_params: list = [dimension_pk, *matched_company_ids]
        if subdimension_id:
            tag_conditions.append("sd.company_tag_subdimension_id = %s")
            tag_params.append(subdimension_id)
        company_tag_rows = _rows(
            f"""
            SELECT
              b.credit_code AS companyId,
              COUNT(DISTINCT m.company_tag_id) AS tagCount,
              GROUP_CONCAT(DISTINCT l.company_tag_name ORDER BY l.company_tag_name SEPARATOR '||') AS tagNames,
              MAX(m.create_time) AS lastUsed
            FROM company_basic b
            JOIN company_tag_map m ON b.credit_code = m.credit_code
            JOIN company_tag_library l ON m.company_tag_id = l.company_tag_id
            JOIN company_tag_subdimension sd ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
            WHERE {' AND '.join(tag_conditions)}
            GROUP BY b.credit_code
            """,
            tag_params,
        )
        company_tag_map = {_credit_code(row["companyId"]): row for row in company_tag_rows}
        company_list = [
            {
                "id": _credit_code(row["companyId"]),
                "name": _normalize_text(row["companyName"]),
                "code": _normalize_text(row["creditCode"]) or _credit_code(row["companyId"]),
                "tagCount": int(company_tag_map.get(_credit_code(row["companyId"]), {}).get("tagCount") or 0),
                "tags": company_tag_map.get(_credit_code(row["companyId"]), {}).get("tagNames", "").split("||")
                if company_tag_map.get(_credit_code(row["companyId"]), {}).get("tagNames")
                else [],
                "lastUsed": (
                    company_tag_map.get(_credit_code(row["companyId"]), {}).get("lastUsed") or row.get("lastMatchedUsed")
                ).isoformat(sep=" ")
                if (company_tag_map.get(_credit_code(row["companyId"]), {}).get("lastUsed") or row.get("lastMatchedUsed"))
                else "",
            }
            for row in company_rows
        ]

    meta = _tag_dimension_meta(dimension["name"])
    normalized_dimension = {
        "id": int(dimension["id"]),
        "name": _normalize_text(dimension["name"]),
        "key": meta["key"],
        "color": meta["color"],
        "description": _normalize_text(dimension["description"]) or f"{_normalize_text(dimension['name'])}标签管理",
        "tagCount": int(dimension["tagCount"] or 0),
        "usedCount": int(dimension["usedCount"] or 0),
        "coverage": round(int(dimension["usedCount"] or 0) / total_companies * 100) if total_companies else 0,
        "totalCompanies": total_companies,
    }
    top_tags = sorted(
        [
            {
                "id": int(row["id"]),
                "name": _normalize_text(row["name"]),
                "subdimensionId": int(row["subdimensionId"]),
                "subdimensionName": _normalize_text(row["subdimensionName"]),
                "usedCount": int(row["usedCount"] or 0),
            }
            for row in tag_rows
        ],
        key=lambda item: (-item["usedCount"], item["name"]),
    )[:8]
    normalized_subdimensions = [
        {"id": int(row["id"]), "name": _normalize_text(row["name"]), "tagCount": int(row["tagCount"] or 0), "usedCount": int(row["usedCount"] or 0)}
        for row in subdimension_rows
    ]
    top_subdimension = sorted(normalized_subdimensions, key=lambda item: (-item["usedCount"], -item["tagCount"]))[:1]
    industry_highlights = (
        {
            "chain": next((row for row in normalized_subdimensions if row["name"] == INDUSTRY_CHAIN_SUBDIMENSION_NAME), None),
            "category": next((row for row in normalized_subdimensions if row["name"] == INDUSTRY_CATEGORY_SUBDIMENSION_NAME), None),
        }
        if meta["key"] == "industry"
        else None
    )
    normalized_tags = [
        {
            "id": int(row["id"]),
            "name": _normalize_text(row["name"]),
            "subdimensionId": int(row["subdimensionId"]),
            "subdimensionName": _normalize_text(row["subdimensionName"]),
            "usedCount": int(row["usedCount"] or 0),
        }
        for row in tag_rows
    ]

    return JsonResponse(
        {
            "success": True,
            "data": {
                "dimension": normalized_dimension,
                "subdimensions": normalized_subdimensions,
                "tags": normalized_tags,
                "highlights": {
                    "topSubdimension": top_subdimension[0] if top_subdimension else None,
                    "topTags": top_tags,
                    "industry": industry_highlights,
                },
                "filters": {"subdimensionId": subdimension_id, "tagId": tag_id, "keyword": keyword},
                "companies": {
                    "list": company_list,
                    "total": company_total,
                    "page": company_page,
                    "pageSize": company_page_size,
                },
            },
        }
    )
