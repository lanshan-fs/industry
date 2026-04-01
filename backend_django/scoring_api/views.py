from __future__ import annotations

from decimal import Decimal

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .engine import get_company_scoring_snapshot
from .models import ScoreIndustryPath


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", "").strip()


def _format_amount(value: Decimal | None) -> str:
    if value is None:
        return "-"
    amount = f"{Decimal(str(value)):.2f}".rstrip("0").rstrip(".")
    return f"{amount}万元"


def _rows(query: str, params: list | tuple | None = None) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _resolve_company_id(identifier: str | None, company_keyword: str | None) -> int | None:
    with connection.cursor() as cursor:
        if identifier:
            normalized = _normalize_text(identifier)
            if normalized.isdigit():
                cursor.execute("SELECT company_id FROM company_basic WHERE company_id = %s LIMIT 1", [int(normalized)])
                row = cursor.fetchone()
                if row:
                    return int(row[0])
            cursor.execute(
                """
                SELECT company_id
                FROM company_basic
                WHERE credit_code = %s OR company_name = %s
                ORDER BY company_id
                LIMIT 1
                """,
                [normalized, normalized],
            )
            row = cursor.fetchone()
            if row:
                return int(row[0])

        if company_keyword:
            normalized = _normalize_text(company_keyword)
            cursor.execute("SELECT company_id FROM company_basic WHERE company_name = %s LIMIT 1", [normalized])
            row = cursor.fetchone()
            if row:
                return int(row[0])
            cursor.execute(
                """
                SELECT company_id
                FROM company_basic
                WHERE company_name LIKE %s
                ORDER BY company_id
                LIMIT 1
                """,
                [f"%{normalized}%"],
            )
            row = cursor.fetchone()
            if row:
                return int(row[0])
    return None


def _build_tree(rows: list[ScoreIndustryPath]) -> list[dict]:
    root: dict[str, dict] = {}

    for row in rows:
        parts = [part.strip() for part in str(row.industry_path).split("/") if part.strip()]
        if not parts:
            continue

        current = root
        for index, part in enumerate(parts):
            node = current.setdefault(
                part,
                {
                    "name": part,
                    "value": None,
                    "children": {},
                    "company_count": 0,
                    "path_level": index,
                },
            )
            if index == len(parts) - 1:
                node["value"] = float(row.avg_score or 0)
                node["company_count"] = int(row.company_count or 0)
            current = node["children"]

    def to_list(tree: dict[str, dict]) -> list[dict]:
        result = []
        for node in tree.values():
            children = to_list(node["children"])
            result.append(
                {
                    "name": node["name"],
                    "value": node["value"],
                    "children": children,
                    "company_count": node["company_count"],
                }
            )
        return result

    return to_list(root)


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


def _risk_profile(risk_map: dict[str, int]) -> dict:
    factor_rows = sorted(
        [{"name": name, "count": count} for name, count in risk_map.items() if count > 0],
        key=lambda item: item["count"],
        reverse=True,
    )
    total_count = sum(item["count"] for item in factor_rows)
    if total_count >= 10:
        level = "高"
        score = 85
        color = "#ff4d4f"
    elif total_count >= 3:
        level = "中"
        score = 55
        color = "#faad14"
    else:
        level = "低"
        score = 15 if total_count == 0 else 25
        color = "#52c41a"
    factors = []
    for item in factor_rows[:5]:
        count = item["count"]
        factors.append(
            {
                "name": item["name"],
                "desc": f"{count}条相关记录",
                "impact": "High" if count >= 5 else "Medium" if count >= 2 else "Low",
            }
        )
    return {"level": level, "score": score, "color": color, "factors": factors}


def _company_tags(company_id: int, fallback_industries: list[str], qualification_label: str) -> list[str]:
    rows = _rows(
        """
        SELECT l.company_tag_name
        FROM company_tag_map m
        JOIN company_tag_library l ON l.company_tag_id = m.company_tag_id
        WHERE m.company_id = %s
        ORDER BY COALESCE(m.confidence, 0) DESC, m.company_tag_map_id DESC
        LIMIT 12
        """,
        [company_id],
    )
    tags = [_normalize_text(row["company_tag_name"]) for row in rows if _normalize_text(row["company_tag_name"])]
    if not tags:
        tags = [path.split("/")[-1] for path in fallback_industries[:6]]
        if qualification_label:
            tags.append(qualification_label)
    return list(dict.fromkeys([tag for tag in tags if tag]))


def _company_rank(company_id: int, total_score: float) -> int | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT total_score FROM scoring_scoreresult WHERE enterprise_id = %s LIMIT 1", [company_id])
        row = cursor.fetchone()
        compare_score = float(row[0]) if row else float(total_score)
        cursor.execute("SELECT COUNT(*) + 1 FROM scoring_scoreresult WHERE total_score > %s", [compare_score])
        rank_row = cursor.fetchone()
    return int(rank_row[0]) if rank_row else None


def _profile_payload(snapshot: dict) -> dict:
    company = snapshot["company"]
    score = snapshot["score"]
    primary_industry_path = score["industry_paths"][-1] if score["industry_paths"] else ""
    primary_industry = primary_industry_path.split("/")[-1] if primary_industry_path else ""
    root_industry = primary_industry_path.split("/")[0] if primary_industry_path else ""

    shareholder_rows = _rows(
        """
        SELECT shareholder_name, holding_ratio, subscribed_amount
        FROM company_shareholder
        WHERE company_id = %s
        ORDER BY is_latest DESC, holding_ratio DESC, company_shareholder_id
        LIMIT 20
        """,
        [company.company_id],
    )
    branch_rows = _rows(
        """
        SELECT company_branch_name, company_branch_legal_representative, company_branch_establish_date
        FROM company_branch
        WHERE company_id = %s
        ORDER BY company_branch_establish_date DESC, company_branch_id DESC
        LIMIT 20
        """,
        [company.company_id],
    )
    change_rows = _rows(
        """
        SELECT change_date, change_item, before_change, after_change
        FROM company_change
        WHERE company_id = %s
        ORDER BY change_date DESC, company_change_id DESC
        LIMIT 20
        """,
        [company.company_id],
    )
    social_rows = _rows(
        """
        SELECT stat_year, employee_count
        FROM company_employee_count
        WHERE company_id = %s
        ORDER BY stat_year DESC
        LIMIT 5
        """,
        [company.company_id],
    )
    qualification_rows = _rows(
        """
        SELECT qualification_name, issued_at
        FROM company_qualification
        WHERE company_id = %s
        ORDER BY COALESCE(issued_at, '1900-01-01') DESC, company_qualification_id DESC
        LIMIT 10
        """,
        [company.company_id],
    )
    ranking_rows = _rows(
        """
        SELECT company_ranking_name, company_ranking_publish_year
        FROM company_ranking
        WHERE company_id = %s
        ORDER BY COALESCE(company_ranking_publish_year, 0) DESC, company_ranking_id DESC
        LIMIT 10
        """,
        [company.company_id],
    )

    tags = _company_tags(company.company_id, score["industry_paths"], company.qualification_label)
    migration_risk = _risk_profile(company.risk_map)
    innovation_dimension = next((item for item in score["breakdown"]["professional"] if item["key"] == "innovation"), None)
    overall_radar = [
        {"item": "基础评分", "score": float(score["basic_score"])},
        {"item": "科技属性", "score": float(score["tech_score"])},
        {"item": "专业能力", "score": float(score["professional_score"])},
        {"item": "创新活力", "score": float(innovation_dimension["score"]) if innovation_dimension else 0},
        {"item": "合规风险", "score": max(0, 100 - int(migration_risk["score"]))},
    ]

    honors = []
    for row in ranking_rows:
        honors.append(
            {
                "year": row["company_ranking_publish_year"] or "-",
                "name": _normalize_text(row["company_ranking_name"]),
            }
        )
    for row in qualification_rows:
        honors.append(
            {
                "year": row["issued_at"].year if row["issued_at"] else "-",
                "name": _normalize_text(row["qualification_name"]),
            }
        )

    return {
        "baseInfo": {
            "id": company.company_id,
            "name": company.company_name,
            "type": company.company_type or "-",
            "legalPerson": company.legal_representative or "-",
            "status": company.company_status or "-",
            "creditCode": company.credit_code or "-",
            "taxId": company.credit_code or "-",
            "regCapital": _format_amount(company.register_capital),
            "paidInCapital": _format_amount(company.paid_capital),
            "establishDate": company.establish_date.isoformat() if company.establish_date else "-",
            "approvedDate": company.approved_date.isoformat() if company.approved_date else "-",
            "industry": primary_industry or root_industry or "-",
            "scope": company.business_scope or "-",
            "website": company.website or "-",
            "address": company.register_address_detail or company.register_address or "-",
            "insuredCount": company.insured_count or 0,
            "registrationAuthority": "-",
        },
        "basicInfoData": {
            "shareholders": [
                {
                    "key": index + 1,
                    "name": _normalize_text(row["shareholder_name"]),
                    "ratio": f"{row['holding_ratio']}%" if row["holding_ratio"] is not None else "-",
                    "capital": _format_amount(row["subscribed_amount"]),
                }
                for index, row in enumerate(shareholder_rows)
            ],
            "keyPersonnel": [{"key": 1, "name": company.legal_representative or "-", "title": "法定代表人"}],
            "branches": [
                {
                    "key": index + 1,
                    "name": _normalize_text(row["company_branch_name"]),
                    "principal": _normalize_text(row["company_branch_legal_representative"]) or "-",
                    "date": row["company_branch_establish_date"].isoformat() if row["company_branch_establish_date"] else "-",
                }
                for index, row in enumerate(branch_rows)
            ],
            "changes": [
                {
                    "key": index + 1,
                    "date": row["change_date"].isoformat() if row["change_date"] else "-",
                    "item": _normalize_text(row["change_item"]) or "-",
                    "before": _normalize_text(row["before_change"]) or "-",
                    "after": _normalize_text(row["after_change"]) or "-",
                }
                for index, row in enumerate(change_rows)
            ],
            "reports": [],
            "social": [
                {
                    "key": index + 1,
                    "year": row["stat_year"],
                    "pension": row["employee_count"],
                    "unemployment": "-",
                    "medical": "-",
                    "injury": "-",
                    "maternity": "-",
                }
                for index, row in enumerate(social_rows)
            ]
            or [
                {
                    "key": 1,
                    "year": "最新",
                    "pension": company.insured_count or 0,
                    "unemployment": "-",
                    "medical": "-",
                    "injury": "-",
                    "maternity": "-",
                }
            ],
            "related": [],
        },
        "tags": tags,
        "metrics": {
            "totalScore": float(score["total_score"]),
            "rank": _company_rank(company.company_id, float(score["total_score"])),
        },
        "migrationRisk": migration_risk,
        "overallRadar": overall_radar,
        "models": {
            "basic": {"score": float(score["basic_score"]), "dimensions": score["breakdown"]["basic"]},
            "tech": {"score": float(score["tech_score"]), "dimensions": score["breakdown"]["tech"]},
            "ability": {"score": float(score["professional_score"]), "dimensions": score["breakdown"]["professional"]},
        },
        "honors": honors[:12],
    }


def _score_payload(snapshot: dict) -> dict:
    company = snapshot["company"]
    score = snapshot["score"]
    primary_industry_path = score["industry_paths"][-1] if score["industry_paths"] else ""
    risk_profile = _risk_profile(company.risk_map)

    dimension_details = {
        "基础评分": {
            "formula": "基础评分 = 各基础指标分项得分按权重缩放后汇总，再叠加风险扣分",
            "desc": "评估企业经营稳定性、规模基础与合规风险。",
            "tableData": [
                {
                    "key": item["key"],
                    "item": item["name"],
                    "value": item["description"],
                    "rawScore": item["score"],
                    "time": "-",
                }
                for item in score["breakdown"]["basic"]
            ],
        },
        "科技属性": {
            "formula": "科技属性 = 专利、软著、科技企业资质、产学研和奖励分项按权重缩放后汇总",
            "desc": "评估企业技术创新、研发积累与科技属性。",
            "tableData": [
                {
                    "key": item["key"],
                    "item": item["name"],
                    "value": item["description"],
                    "rawScore": item["score"],
                    "time": "-",
                }
                for item in score["breakdown"]["tech"]
            ],
        },
        "专业能力": {
            "formula": "专业能力 = 行业位置、资质证书、创新性、上下游合作与榜单表现按权重缩放后汇总",
            "desc": "评估企业在垂直场景里的专业化能力与行业位置。",
            "tableData": [
                {
                    "key": item["key"],
                    "item": item["name"],
                    "value": item["description"],
                    "rawScore": item["score"],
                    "time": "-",
                }
                for item in score["breakdown"]["professional"]
            ],
        },
        "风险画像": {
            "formula": "风险画像 = 已结构化风险记录按类型聚合后映射为风险等级",
            "desc": "展示当前企业已纳入评分引擎的风险因子。",
            "tableData": [
                {
                    "key": factor["name"],
                    "item": factor["name"],
                    "value": factor["desc"],
                    "rawScore": factor["impact"],
                    "time": "-",
                }
                for factor in risk_profile["factors"]
            ],
        },
    }

    radar_data = [
        {"item": "基础评分", "score": float(score["basic_score"])},
        {"item": "科技属性", "score": float(score["tech_score"])},
        {"item": "专业能力", "score": float(score["professional_score"])},
        {
            "item": "风险画像",
            "score": max(0, 100 - int(risk_profile["score"])),
        },
    ]

    return {
        "enterprise": {
            "id": company.company_id,
            "name": company.company_name,
            "creditCode": company.credit_code or "-",
            "industry": primary_industry_path.split("/")[-1] if primary_industry_path else "-",
            "chainPosition": primary_industry_path or "-",
            "regCapital": _format_amount(company.register_capital),
            "estDate": company.establish_date.isoformat() if company.establish_date else "-",
        },
        "overview": {
            "totalScore": float(score["total_score"]),
            "level": _score_level(float(score["total_score"])),
            "rank": _company_rank(company.company_id, float(score["total_score"])),
        },
        "radarData": radar_data,
        "dimensionDetails": dimension_details,
    }


@require_GET
def industry_tree(_request):
    rows = list(ScoreIndustryPath.objects.order_by("industry_path"))
    return JsonResponse(_build_tree(rows), safe=False)


@require_GET
def enterprise_profile(request):
    company_id = _resolve_company_id(request.GET.get("id"), request.GET.get("company"))
    if not company_id:
        return JsonResponse({"success": False, "message": "未找到匹配企业"}, status=404)
    snapshot = get_company_scoring_snapshot(company_id)
    if not snapshot:
        return JsonResponse({"success": False, "message": "未找到评分数据"}, status=404)
    return JsonResponse({"success": True, "data": _profile_payload(snapshot)})


@require_GET
def enterprise_score(request):
    company_id = _resolve_company_id(request.GET.get("id"), request.GET.get("keyword") or request.GET.get("company"))
    if not company_id:
        return JsonResponse({"success": False, "message": "未找到匹配企业"}, status=404)
    snapshot = get_company_scoring_snapshot(company_id)
    if not snapshot:
        return JsonResponse({"success": False, "message": "未找到评分数据"}, status=404)
    return JsonResponse({"success": True, "data": _score_payload(snapshot)})
