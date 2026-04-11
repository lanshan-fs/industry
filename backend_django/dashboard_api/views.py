from __future__ import annotations

from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from auth_api.views import _admin_user, _json_body, _json_error, _normalize_text
from industry_api.ecology_rules import ECOLOGY_RULES, ecology_keywords


STAGE_ORDER = ["upstream", "midstream", "downstream"]
STAGE_COLORS = {
    "upstream": "#1890ff",
    "midstream": "#52c41a",
    "downstream": "#fa8c16",
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
    "upstream": "上游 · 研发与技术",
    "midstream": "中游 · 产品与制造",
    "downstream": "下游 · 应用与服务",
}
NOTICE_SEED = [
    {
        "title": "关于2026年第一季度高新技术企业申报的预通知",
        "notice_type": "通知",
        "publish_date": "2026-01-29",
        "sort_order": 100,
        "content": "平台现已同步本地企业资质数据，可用于提前梳理高新技术企业申报对象。建议相关企业优先核查知识产权、研发投入和人员结构信息，以便后续正式申报时直接复用。",
    },
    {
        "title": "朝阳区新增3家国家级专精特新“小巨人”企业名单公示",
        "notice_type": "动态",
        "publish_date": "2026-01-28",
        "sort_order": 90,
        "content": "本批次公示企业已纳入本地企业画像与评分体系，可在产业分类、企业画像和评分详情页中查看对应企业的资质标签、风险状态与行业位置。",
    },
    {
        "title": "产业链平台将于本周日凌晨 02:00 进行系统维护升级",
        "notice_type": "系统",
        "publish_date": "2026-01-27",
        "sort_order": 80,
        "content": "维护窗口预计持续30分钟，期间首页总览、行业画像与高级搜索功能可能出现短时不可用。评分结果与企业数据不会受影响。",
    },
    {
        "title": "2025年度全区数字经济产业发展报告已发布",
        "notice_type": "报告",
        "publish_date": "2026-01-25",
        "sort_order": 70,
        "content": "报告聚焦数字医疗、严肃医疗与医疗零售等重点方向，结合企业分布、评分结果和重点风险，给出当前产业链结构和未来补链建议。",
    },
    {
        "title": "关于举办“数据要素×”产业沙龙的邀请函",
        "notice_type": "活动",
        "publish_date": "2026-01-24",
        "sort_order": 60,
        "content": "活动将围绕产业数据治理、企业画像构建与场景落地展开，平台用户可结合高级搜索结果和企业评分报告准备交流材料。",
    },
]
_NOTICE_TABLE_READY = False


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


def _query_one(sql: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def _scalar(sql: str, params: list | tuple | None = None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
    return row[0] if row else None


def _rows(sql: str, params: list | tuple | None = None) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _execute(sql: str, params: list | tuple | None = None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])


def _ensure_notice_table():
    global _NOTICE_TABLE_READY
    if _NOTICE_TABLE_READY:
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_notice (
              notice_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
              title VARCHAR(255) NOT NULL,
              notice_type VARCHAR(32) NOT NULL DEFAULT '通知',
              content TEXT NOT NULL,
              publish_date DATE NULL,
              sort_order INT NOT NULL DEFAULT 0,
              is_published TINYINT(1) NOT NULL DEFAULT 1,
              is_deleted TINYINT(1) NOT NULL DEFAULT 0,
              created_by BIGINT NULL,
              updated_by BIGINT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              KEY idx_platform_notice_publish (is_deleted, is_published, publish_date),
              KEY idx_platform_notice_sort (sort_order, updated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute("SELECT COUNT(*) FROM platform_notice WHERE is_deleted = 0")
        row = cursor.fetchone()
        has_data = int(row[0] or 0) > 0 if row else False
        if not has_data:
            for item in NOTICE_SEED:
                cursor.execute(
                    """
                    INSERT INTO platform_notice (
                      title,
                      notice_type,
                      content,
                      publish_date,
                      sort_order,
                      is_published,
                      is_deleted
                    ) VALUES (%s, %s, %s, %s, %s, 1, 0)
                    """,
                    [
                        item["title"],
                        item["notice_type"],
                        item["content"],
                        item["publish_date"],
                        item["sort_order"],
                    ],
                )
    _NOTICE_TABLE_READY = True


def _notice_payload(row: dict, include_meta: bool = False) -> dict:
    payload = {
        "id": int(row["notice_id"]),
        "title": _normalize_text(row["title"]),
        "type": _normalize_text(row["notice_type"]) or "通知",
        "date": row["publish_date"].isoformat() if row.get("publish_date") else "",
        "content": _normalize_text(row["content"]),
        "sortOrder": int(row["sort_order"] or 0),
        "isPublished": bool(row["is_published"]),
    }
    if include_meta:
        payload["createdAt"] = row["created_at"].isoformat(sep=" ") if row.get("created_at") else ""
        payload["updatedAt"] = row["updated_at"].isoformat(sep=" ") if row.get("updated_at") else ""
    return payload


def _notice_rows(*, published_only: bool, limit: int | None = None) -> list[dict]:
    _ensure_notice_table()
    where_clauses = ["is_deleted = 0"]
    if published_only:
        where_clauses.append("is_published = 1")
    limit_sql = f"LIMIT {int(limit)}" if limit else ""
    return _rows(
        f"""
        SELECT
          notice_id,
          title,
          notice_type,
          content,
          publish_date,
          sort_order,
          is_published,
          created_at,
          updated_at
        FROM platform_notice
        WHERE {' AND '.join(where_clauses)}
        ORDER BY sort_order DESC, COALESCE(publish_date, DATE(updated_at)) DESC, notice_id DESC
        {limit_sql}
        """
    )


def _query_chain_counts() -> dict[str, int]:
    rows = _rows(
        """
        SELECT
          ci.chain_name,
          COUNT(DISTINCT cicm.credit_code) AS company_count
        FROM chain_industry ci
        LEFT JOIN chain_industry_category_industry_map cic
          ON cic.chain_id = ci.chain_id
        LEFT JOIN category_industry root
          ON root.category_id = cic.category_id
        LEFT JOIN category_industry descendant
          ON descendant.category_level_code LIKE CONCAT(root.category_level_code, '%%')
        LEFT JOIN category_industry_company_map cicm
          ON cicm.category_id = descendant.category_id
        GROUP BY ci.chain_id, ci.chain_name
        ORDER BY ci.chain_id
        """
    )
    return {str(row["chain_name"]): int(row["company_count"] or 0) for row in rows}


def _qualification_stats() -> list[dict]:
    return [
        {"label": "上市企业", "value": _query_one("SELECT COUNT(*) FROM company_basic WHERE listing_status IS NOT NULL AND listing_status <> 0")},
        {
            "label": "外资企业",
            "value": _query_one(
                """
                SELECT COUNT(*)
                FROM company_basic
                WHERE company_type LIKE '%外商%'
                   OR company_type LIKE '%外国%'
                   OR company_type LIKE '%台港澳%'
                """
            ),
        },
        {"label": "独角兽", "value": _query_one("SELECT COUNT(*) FROM company_basic WHERE is_gazelle_company = 1 OR is_egalet_company = 1")},
        {"label": "专精特新", "value": _query_one("SELECT COUNT(*) FROM company_basic WHERE is_srdi_sme = 1 OR is_srdi_little_giant = 1")},
        {"label": "高新技术", "value": _query_one("SELECT COUNT(*) FROM company_basic WHERE is_high_tech_enterprise = 1")},
        {"label": "科技中小", "value": _query_one("SELECT COUNT(*) FROM company_basic WHERE is_tech_sme = 1")},
    ]


def _count_company_matches(keywords: list[str]) -> int:
    conditions = []
    params: list[str] = []
    for keyword in keywords:
        like_value = f"%{keyword}%"
        conditions.append(
            "(company_name LIKE %s OR company_type LIKE %s OR org_type LIKE %s OR business_scope LIKE %s OR register_address LIKE %s)"
        )
        params.extend([like_value, like_value, like_value, like_value, like_value])
    return int(_scalar(f"SELECT COUNT(*) FROM company_basic WHERE {' OR '.join(conditions)}", params) or 0)


def _ecology_stats() -> list[dict]:
    return [{"label": label, "value": _count_company_matches(ecology_keywords(label))} for label in ECOLOGY_RULES]


def _hotspot_streets() -> list[dict]:
    rows = _rows(
        """
        SELECT subdistrict AS name, COUNT(*) AS company_count
        FROM company_basic
        WHERE subdistrict IS NOT NULL AND subdistrict <> ''
        GROUP BY subdistrict
        ORDER BY company_count DESC, subdistrict
        LIMIT 10
        """
    )
    max_count = max([int(row["company_count"] or 0) for row in rows], default=1)
    return [
        {
            "name": str(row["name"]),
            "count": int(row["company_count"] or 0),
            "percent": round(int(row["company_count"] or 0) / max_count * 100),
        }
        for row in rows
    ]


def _hot_tags(count_map: dict[str, int]) -> list[dict]:
    top_items = sorted(count_map.items(), key=lambda item: (-item[1], item[0]))[:10]
    max_count = max([int(count or 0) for _, count in top_items], default=0)
    if max_count <= 0:
        max_count = 1
    return [{"name": name, "count": int(count), "percent": round(int(count) / max_count * 100)} for name, count in top_items]


def _company_tags(credit_codes: list[str], limit: int = 3) -> dict[str, list[str]]:
    if not credit_codes:
        return {}
    placeholders = ", ".join(["%s"] * len(credit_codes))
    rows = _rows(
        f"""
        SELECT
          m.credit_code,
          l.company_tag_name,
          COALESCE(m.confidence, 0) AS confidence,
          m.company_tag_map_id
        FROM company_tag_map m
        JOIN company_tag_library l ON l.company_tag_id = m.company_tag_id
        WHERE m.credit_code IN ({placeholders})
        ORDER BY m.credit_code, confidence DESC, m.company_tag_map_id DESC
        """,
        credit_codes,
    )
    result: dict[str, list[str]] = {}
    for row in rows:
        credit_code = _normalize_text(row["credit_code"])
        tag_name = _normalize_text(row["company_tag_name"])
        if not tag_name:
            continue
        result.setdefault(credit_code, [])
        if tag_name in result[credit_code] or len(result[credit_code]) >= limit:
            continue
        result[credit_code].append(tag_name)
    return result


def _recommended_enterprises() -> list[dict]:
    rows = _rows(
        """
        SELECT
          sr.enterprise_credit_code,
          sr.company_name,
          sr.total_score,
          cb.register_shi,
          cb.register_xian
        FROM scoring_scoreresult sr
        JOIN company_basic cb ON cb.credit_code = sr.enterprise_credit_code
        ORDER BY sr.total_score DESC, sr.enterprise_credit_code ASC
        LIMIT 5
        """
    )
    tag_map = _company_tags([_normalize_text(row["enterprise_credit_code"]) for row in rows], limit=3)
    return [
        {
            "id": _normalize_text(row["enterprise_credit_code"]),
            "name": _normalize_text(row["company_name"]),
            "matchScore": round(float(row["total_score"] or 0)),
            "location": "·".join([part for part in [_normalize_text(row["register_shi"]), _normalize_text(row["register_xian"])] if part]) or "北京市",
            "tags": tag_map.get(_normalize_text(row["enterprise_credit_code"]), []),
        }
        for row in rows
    ]


def _search_hints(count_map: dict[str, int], recommendations: list[dict]) -> dict:
    industries = [name for name, _count in sorted(count_map.items(), key=lambda item: (-item[1], item[0]))[:4]]
    enterprises = [item["name"] for item in recommendations[:4]]
    return {"industries": industries, "enterprises": enterprises}


@require_GET
def overview(_request):
    _ensure_notice_table()
    seed_rows = _load_chain_seed()
    count_map = _query_chain_counts()
    total_companies = _query_one("SELECT COUNT(*) FROM company_basic")
    avg_score = float(_scalar("SELECT COALESCE(ROUND(AVG(total_score), 2), 0) FROM scoring_scoreresult") or 0)
    active_link_count = sum(1 for count in count_map.values() if int(count) > 0)
    synergy_rate = round(active_link_count / max(len(seed_rows), 1) * 100, 1)
    qualification_stats = _qualification_stats()
    ecology_stats = _ecology_stats()
    hotspot_streets = _hotspot_streets()
    hot_tags = _hot_tags(count_map)
    recommendations = _recommended_enterprises()
    search_hints = _search_hints(count_map, recommendations)
    notices = [_notice_payload(row) for row in _notice_rows(published_only=True, limit=6)]

    stage_map: dict[str, dict] = {}
    for stage_key in STAGE_ORDER:
        stage_map[stage_key] = {
            "type": stage_key,
            "title": STAGE_KEY_TO_TITLE[stage_key],
            "color": STAGE_COLORS[stage_key],
            "subTags": [],
            "total": 0,
        }

    for row in sorted(seed_rows, key=lambda item: int(item["sort_order"])):
        count = count_map.get(str(row["chain_name"]), 0)
        stage = stage_map[str(row["stage_key"])]
        stage["subTags"].append({"name": row["chain_name"], "count": count, "isWeak": count == 0})
        stage["total"] += count

    return JsonResponse(
        {
            "success": True,
            "data": {
                "totalCompanies": total_companies,
                "metrics": {
                    "totalCompanies": total_companies,
                    "averageScore": avg_score,
                    "synergyRate": synergy_rate,
                },
                "chainData": [stage_map[key] for key in STAGE_ORDER],
                "qualificationStats": qualification_stats,
                "ecologyStats": ecology_stats,
                "hotspotStreets": hotspot_streets,
                "hotTags": hot_tags,
                "recommendedEnterprises": recommendations,
                "hotSearches": search_hints,
                "notices": notices,
            },
        }
    )


@require_GET
def notice_list(request):
    limit = int(_normalize_text(request.GET.get("limit")) or 20)
    rows = _notice_rows(published_only=True, limit=limit)
    return JsonResponse({"success": True, "data": [_notice_payload(row) for row in rows]})


@require_GET
def admin_notice_list(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)
    rows = _notice_rows(published_only=False, limit=None)
    return JsonResponse({"success": True, "data": [_notice_payload(row, include_meta=True) for row in rows]})


@csrf_exempt
@require_POST
def admin_notice_save(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    _ensure_notice_table()
    payload = _json_body(request)
    notice_id = _normalize_text(payload.get("id"))
    title = _normalize_text(payload.get("title"))
    notice_type = _normalize_text(payload.get("type")) or "通知"
    content = _normalize_text(payload.get("content"))
    publish_date = _normalize_text(payload.get("date")) or None
    sort_order = int(payload.get("sortOrder") or 0)
    is_published = 1 if bool(payload.get("isPublished")) else 0
    if is_published and not publish_date:
        publish_date = timezone.now().date().isoformat()

    if not title or not content:
        return _json_error("请完整填写公告标题和内容")

    if notice_id:
        _execute(
            """
            UPDATE platform_notice
            SET
              title = %s,
              notice_type = %s,
              content = %s,
              publish_date = %s,
              sort_order = %s,
              is_published = %s,
              updated_by = %s
            WHERE notice_id = %s AND is_deleted = 0
            """,
            [title, notice_type, content, publish_date, sort_order, is_published, admin.user_id, int(notice_id)],
        )
        message = "公告更新成功"
    else:
        _execute(
            """
            INSERT INTO platform_notice (
              title,
              notice_type,
              content,
              publish_date,
              sort_order,
              is_published,
              is_deleted,
              created_by,
              updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s)
            """,
            [title, notice_type, content, publish_date, sort_order, is_published, admin.user_id, admin.user_id],
        )
        message = "公告创建成功"

    return JsonResponse({"success": True, "message": message})


@csrf_exempt
@require_POST
def admin_notice_publish(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    _ensure_notice_table()
    payload = _json_body(request)
    notice_id = int(payload.get("id") or 0)
    is_published = 1 if bool(payload.get("isPublished")) else 0
    if not notice_id:
        return _json_error("公告参数无效")

    existing_publish_date = _scalar("SELECT publish_date FROM platform_notice WHERE notice_id = %s AND is_deleted = 0", [notice_id])
    publish_date = existing_publish_date.isoformat() if existing_publish_date else None
    if is_published and not publish_date:
        publish_date = timezone.now().date().isoformat()

    _execute(
        """
        UPDATE platform_notice
        SET is_published = %s, publish_date = %s, updated_by = %s
        WHERE notice_id = %s AND is_deleted = 0
        """,
        [is_published, publish_date, admin.user_id, notice_id],
    )
    return JsonResponse({"success": True, "message": "公告状态已更新"})


@csrf_exempt
@require_POST
def admin_notice_delete(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    _ensure_notice_table()
    payload = _json_body(request)
    notice_id = int(payload.get("id") or 0)
    if not notice_id:
        return _json_error("公告参数无效")

    _execute(
        """
        UPDATE platform_notice
        SET is_deleted = 1, updated_by = %s
        WHERE notice_id = %s AND is_deleted = 0
        """,
        [admin.user_id, notice_id],
    )
    return JsonResponse({"success": True, "message": "公告已删除"})
