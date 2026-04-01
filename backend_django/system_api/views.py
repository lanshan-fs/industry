from __future__ import annotations

from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from auth_api.views import _admin_user, _json_error, _normalize_text
from scoring_api.views import _resolve_company_id
from industry_api.views import _company_tags_map, _rows, _scalar


def _format_amount(value: Decimal | None) -> str:
    if value is None:
        return "-"
    amount = f"{Decimal(str(value)):.2f}".rstrip("0").rstrip(".")
    return f"{amount}万元"


def _format_datetime(value) -> str:
    return value.isoformat(sep=" ") if value else ""


def _list_stats(keyword: str) -> dict:
    params: list = []
    where = "WHERE 1 = 1"
    if keyword:
        where += " AND (company_name LIKE %s OR credit_code LIKE %s)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    total = int(_scalar(f"SELECT COUNT(*) FROM company_basic {where}", params) or 0)
    high_tech = int(
        _scalar(
            f"SELECT COUNT(*) FROM company_basic {where} AND COALESCE(is_high_tech_enterprise, 0) = 1",
            params,
        )
        or 0
    )
    scored = int(
        _scalar(
            f"""
            SELECT COUNT(*)
            FROM company_basic c
            JOIN scoring_scoreresult s ON s.enterprise_id = c.company_id
            {where}
            """,
            params,
        )
        or 0
    )
    recent_updated = int(
        _scalar(
            f"""
            SELECT COUNT(*)
            FROM company_basic
            {where} AND updated_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """,
            params,
        )
        or 0
    )
    return {
        "total": total,
        "highTech": high_tech,
        "scored": scored,
        "recentUpdated": recent_updated,
    }


@require_GET
def company_list(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    keyword = _normalize_text(request.GET.get("keyword"))
    page = max(int(_normalize_text(request.GET.get("page")) or 1), 1)
    page_size = max(int(_normalize_text(request.GET.get("pageSize")) or 15), 1)
    offset = (page - 1) * page_size

    params: list = []
    where = "WHERE 1 = 1"
    if keyword:
        where += " AND (company_name LIKE %s OR credit_code LIKE %s)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    total = int(_scalar(f"SELECT COUNT(*) FROM company_basic {where}", params) or 0)
    rows = _rows(
        f"""
        SELECT
          company_id,
          credit_code,
          company_name,
          legal_representative,
          register_capital,
          establish_date,
          updated_at,
          qualification_label,
          company_status,
          is_high_tech_enterprise
        FROM company_basic
        {where}
        ORDER BY updated_at DESC, company_id DESC
        LIMIT %s OFFSET %s
        """,
        [*params, page_size, offset],
    )

    company_ids = [int(row["company_id"]) for row in rows]
    tag_map = _company_tags_map(company_ids, limit=6)
    score_map = {
        int(row["enterprise_id"]): float(row["total_score"] or 0)
        for row in _rows(
            """
            SELECT enterprise_id, total_score
            FROM scoring_scoreresult
            WHERE enterprise_id IN ({})
            """.format(", ".join(["%s"] * len(company_ids))),
            company_ids,
        )
    } if company_ids else {}

    data = [
        {
            "key": _normalize_text(row["credit_code"]) or str(row["company_id"]),
            "companyId": int(row["company_id"]),
            "creditCode": _normalize_text(row["credit_code"]),
            "name": _normalize_text(row["company_name"]),
            "legalPerson": _normalize_text(row["legal_representative"]) or "-",
            "registeredCapital": float(row["register_capital"] or 0),
            "establishmentDate": row["establish_date"].isoformat() if row["establish_date"] else "",
            "updateTime": _format_datetime(row["updated_at"]),
            "qualificationLabel": _normalize_text(row["qualification_label"]),
            "companyStatus": _normalize_text(row["company_status"]) or "-",
            "variants": " | ".join(tag_map.get(int(row["company_id"]), [])),
            "tags": tag_map.get(int(row["company_id"]), []),
            "score": round(score_map.get(int(row["company_id"]), 0.0), 2),
            "isHighTech": str(row["is_high_tech_enterprise"] or 0) in {"1", "True", "true"},
        }
        for row in rows
    ]

    return JsonResponse(
        {
            "success": True,
            "data": data,
            "total": total,
            "stats": _list_stats(keyword),
        }
    )


@require_GET
def company_detail(request, identifier: str):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    company_id = _resolve_company_id(identifier, identifier)
    if not company_id:
        return _json_error("未找到对应企业", status=404)

    row = _rows(
        """
        SELECT
          company_id,
          credit_code,
          company_name,
          legal_representative,
          register_capital,
          paid_capital,
          establish_date,
          updated_at,
          qualification_label,
          company_status,
          company_type,
          org_type,
          company_scale,
          taxpayer_credit_rating,
          financing_round,
          register_address,
          register_address_detail,
          register_xian,
          subdistrict,
          contact_phone,
          email_business,
          insured_count,
          business_scope,
          is_high_tech_enterprise,
          is_tech_sme,
          is_srdi_sme,
          is_gazelle_company
        FROM company_basic
        WHERE company_id = %s
        LIMIT 1
        """,
        [company_id],
    )
    if not row:
        return _json_error("未找到对应企业", status=404)
    company = row[0]

    tags = _company_tags_map([company_id], limit=12).get(company_id, [])
    score_row = _rows(
        """
        SELECT total_score, basic_score, tech_score, professional_score
        FROM scoring_scoreresult
        WHERE enterprise_id = %s
        LIMIT 1
        """,
        [company_id],
    )
    score = score_row[0] if score_row else {}

    detail = {
        "companyId": company_id,
        "name": _normalize_text(company["company_name"]),
        "creditCode": _normalize_text(company["credit_code"]),
        "legalPerson": _normalize_text(company["legal_representative"]) or "-",
        "registeredCapital": _format_amount(company["register_capital"]),
        "paidCapital": _format_amount(company["paid_capital"]),
        "establishmentDate": company["establish_date"].isoformat() if company["establish_date"] else "-",
        "updateTime": _format_datetime(company["updated_at"]) or "-",
        "qualificationLabel": _normalize_text(company["qualification_label"]) or "-",
        "companyStatus": _normalize_text(company["company_status"]) or "-",
        "companyType": _normalize_text(company["company_type"]) or "-",
        "orgType": _normalize_text(company["org_type"]) or "-",
        "companyScale": _normalize_text(company["company_scale"]) or "-",
        "taxRating": _normalize_text(company["taxpayer_credit_rating"]) or "-",
        "financingRound": _normalize_text(company["financing_round"]) or "未融资",
        "address": _normalize_text(company["register_address_detail"]) or _normalize_text(company["register_address"]) or "-",
        "district": _normalize_text(company["register_xian"]) or "-",
        "street": _normalize_text(company["subdistrict"]) or "-",
        "phone": _normalize_text(company["contact_phone"]) or "-",
        "email": _normalize_text(company["email_business"]) or "-",
        "insuredNum": int(company["insured_count"] or 0),
        "businessScope": _normalize_text(company["business_scope"]) or "-",
        "tags": tags,
        "flags": {
            "highTech": str(company["is_high_tech_enterprise"] or 0) in {"1", "True", "true"},
            "techSme": str(company["is_tech_sme"] or 0) in {"1", "True", "true"},
            "srdi": str(company["is_srdi_sme"] or 0) in {"1", "True", "true"},
            "gazelle": str(company["is_gazelle_company"] or 0) in {"1", "True", "true"},
        },
        "score": {
            "total": round(float(score.get("total_score") or 0), 2),
            "basic": round(float(score.get("basic_score") or 0), 2),
            "tech": round(float(score.get("tech_score") or 0), 2),
            "professional": round(float(score.get("professional_score") or 0), 2),
        },
        "recordCounts": {
            "patents": int(_scalar("SELECT COUNT(*) FROM company_patent WHERE company_id = %s", [company_id]) or 0),
            "softwareCopyrights": int(_scalar("SELECT COUNT(*) FROM company_software_copyright WHERE company_id = %s", [company_id]) or 0),
            "qualifications": int(_scalar("SELECT COUNT(*) FROM company_qualification WHERE company_id = %s", [company_id]) or 0),
            "customers": int(_scalar("SELECT COUNT(*) FROM company_customer WHERE company_id = %s", [company_id]) or 0),
            "suppliers": int(_scalar("SELECT COUNT(*) FROM company_supplier WHERE company_id = %s", [company_id]) or 0),
            "risks": int(_scalar("SELECT COUNT(*) FROM company_risk WHERE company_id = %s", [company_id]) or 0),
        },
    }

    return JsonResponse({"success": True, "data": detail})
