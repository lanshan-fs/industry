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


def _bool_text(value, yes: str = "是", no: str = "否") -> str:
    return yes if bool(value) else no


def _presence_text(flag, count: int | None = None, yes: str = "有", no: str = "无") -> str:
    return yes if bool(flag) or int(count or 0) > 0 else no


def _risk_record_text(flag, count: int | None = None) -> str:
    return "有记录" if bool(flag) or int(count or 0) > 0 else "无"


def _listing_status_text(value) -> str:
    if value in (None, "", 0, "0"):
        return "未披露"
    return "已上市/挂牌"


def _date_text(value) -> str:
    return value.isoformat() if value else "-"


def _risk_table_data(company_id: int) -> list[dict]:
    rows = _rows(
        """
        SELECT
          b.has_legal_document,
          b.has_dishonest_execution,
          b.has_business_abnormal,
          b.has_admin_penalty,
          b.has_env_penalty,
          b.has_equity_freeze,
          b.has_chattel_mortgage,
          b.has_bankruptcy_overlap,
          b.has_executed_person,
          b.has_consumption_restriction,
          COALESCE(c.legal_doc_case_count, 0) AS legal_doc_case_count,
          COALESCE(c.legal_doc_all_count, 0) AS legal_doc_all_count,
          COALESCE(c.dishonest_execution_count, 0) AS dishonest_execution_count,
          COALESCE(c.business_abnormal_count, 0) AS business_abnormal_count,
          COALESCE(c.admin_penalty_count, 0) AS admin_penalty_count,
          COALESCE(c.env_penalty_count, 0) AS env_penalty_count,
          COALESCE(c.equity_freeze_count, 0) AS equity_freeze_count,
          COALESCE(c.chattel_mortgage_count, 0) AS chattel_mortgage_count,
          COALESCE(c.bankruptcy_overlap_count, 0) AS bankruptcy_overlap_count,
          COALESCE(c.liquidation_info_count, 0) AS liquidation_info_count,
          COALESCE(c.executed_person_count, 0) AS executed_person_count
        FROM company_basic b
        LEFT JOIN company_basic_count c ON b.company_id = c.company_id
        WHERE b.company_id = %s
        LIMIT 1
        """,
        [company_id],
    )
    if not rows:
        return []
    row = rows[0]
    definitions = [
        ("司法案件", row["legal_doc_case_count"], None),
        ("法律文书", row["legal_doc_all_count"], row["has_legal_document"]),
        ("失信被执行", row["dishonest_execution_count"], row["has_dishonest_execution"]),
        ("被执行人", row["executed_person_count"], row["has_executed_person"]),
        ("限制高消费", 0, row["has_consumption_restriction"]),
        ("经营异常", row["business_abnormal_count"], row["has_business_abnormal"]),
        ("行政处罚", row["admin_penalty_count"], row["has_admin_penalty"]),
        ("环保处罚", row["env_penalty_count"], row["has_env_penalty"]),
        ("股权冻结", row["equity_freeze_count"], row["has_equity_freeze"]),
        ("动产抵押", row["chattel_mortgage_count"], row["has_chattel_mortgage"]),
        ("破产重整", row["bankruptcy_overlap_count"], row["has_bankruptcy_overlap"]),
        ("清算信息", row["liquidation_info_count"], row["liquidation_info_count"]),
    ]
    return [
        {
            "key": index + 1,
            "item": item,
            "hasRisk": _risk_record_text(flag, count),
            "count": int(count or 0),
        }
        for index, (item, count, flag) in enumerate(definitions)
    ]


def _qualification_table_data(company_id: int) -> list[dict]:
    rows = _rows(
        """
        SELECT
          b.has_work_copyright,
          b.has_software_copyright,
          b.is_high_tech_enterprise,
          b.is_srdi_sme,
          b.is_gazelle_company,
          b.is_tech_sme,
          b.is_egalet_company,
          b.is_srdi_little_giant,
          b.is_innovative_sme,
          b.has_patent,
          b.has_trademark,
          COALESCE(c.work_copyright_count, 0) AS work_copyright_count,
          COALESCE(c.software_copyright_count, 0) AS software_copyright_count,
          COALESCE(c.patent_count, 0) AS patent_count,
          COALESCE(c.trademark_count, 0) AS trademark_count
        FROM company_basic b
        LEFT JOIN company_basic_count c ON b.company_id = c.company_id
        WHERE b.company_id = %s
        LIMIT 1
        """,
        [company_id],
    )
    if not rows:
        return []
    row = rows[0]
    definitions = [
        ("是否有作品著作", _bool_text(bool(row["has_work_copyright"]) or int(row["work_copyright_count"] or 0) > 0), "-"),
        ("作品著作权数量", "-", int(row["work_copyright_count"] or 0)),
        ("是否有软件著作", _bool_text(bool(row["has_software_copyright"]) or int(row["software_copyright_count"] or 0) > 0), "-"),
        ("软件著作权数量", "-", int(row["software_copyright_count"] or 0)),
        ("是否是高新技术企业", _bool_text(row["is_high_tech_enterprise"]), "-"),
        ("是否是专精特新中小企业", _bool_text(row["is_srdi_sme"]), "-"),
        ("是否是瞪羚企业", _bool_text(row["is_gazelle_company"]), "-"),
        ("是否是科技型中小企业", _bool_text(row["is_tech_sme"]), "-"),
        ("是否是雏鹰企业", _bool_text(row["is_egalet_company"]), "-"),
        ("是否是专精特新小巨人", _bool_text(row["is_srdi_little_giant"]), "-"),
        ("是否是创新型中小企业", _bool_text(row["is_innovative_sme"]), "-"),
        ("是否有专利", _bool_text(bool(row["has_patent"]) or int(row["patent_count"] or 0) > 0), "-"),
        ("专利数量", "-", int(row["patent_count"] or 0)),
        ("是否有商标", _bool_text(bool(row["has_trademark"]) or int(row["trademark_count"] or 0) > 0), "-"),
        ("商标数量", "-", int(row["trademark_count"] or 0)),
    ]
    return [
        {
            "key": f"q{index + 1}",
            "item": item,
            "status": status,
            "count": count,
        }
        for index, (item, status, count) in enumerate(definitions)
    ]


def _ip_detail_payload(company_id: int) -> dict[str, list[dict]]:
    patent_rows = _rows(
        """
        SELECT
          company_patent_name,
          company_patent_number,
          application_date,
          auth_date,
          publication_date,
          tech_attribute_label
        FROM company_patent
        WHERE company_id = %s
        ORDER BY COALESCE(auth_date, publication_date, application_date) DESC, company_patent_id DESC
        LIMIT 100
        """,
        [company_id],
    )
    software_rows = _rows(
        """
        SELECT
          company_software_copyright_name,
          company_software_copyright_register_number,
          company_software_copyright_register_date,
          company_software_copyright_status,
          company_software_copyright_for_short
        FROM company_software_copyright
        WHERE company_id = %s
        ORDER BY COALESCE(company_software_copyright_register_date, '1900-01-01') DESC, company_software_copyright_id DESC
        LIMIT 100
        """,
        [company_id],
    )
    work_rows = _rows(
        """
        SELECT
          company_work_copyright_name,
          company_work_copyright_register_number,
          company_work_copyright_type,
          company_work_copyright_publish_date,
          company_work_copyright_register_date,
          company_work_copyright_status
        FROM company_work_copyright
        WHERE company_id = %s
        ORDER BY COALESCE(company_work_copyright_register_date, company_work_copyright_publish_date, '1900-01-01') DESC, company_work_copyright_id DESC
        LIMIT 100
        """,
        [company_id],
    )
    trademark_rows = _rows(
        """
        SELECT
          company_trademark_name,
          company_trademark_register_number,
          company_trademark_application_date
        FROM company_trademark
        WHERE company_id = %s
        ORDER BY COALESCE(company_trademark_application_date, '1900-01-01') DESC, company_trademark_id DESC
        LIMIT 100
        """,
        [company_id],
    )
    return {
        "专利数量": [
            {
                "key": f"patent-{index + 1}",
                "name": _normalize_text(row["company_patent_name"]) or "-",
                "number": _normalize_text(row["company_patent_number"]) or "-",
                "applicationDate": _date_text(row["application_date"]),
                "authDate": _date_text(row["auth_date"]),
                "publicationDate": _date_text(row["publication_date"]),
                "techAttribute": _normalize_text(row["tech_attribute_label"]) or "-",
            }
            for index, row in enumerate(patent_rows)
        ],
        "软件著作权数量": [
            {
                "key": f"software-{index + 1}",
                "name": _normalize_text(row["company_software_copyright_name"]) or "-",
                "number": _normalize_text(row["company_software_copyright_register_number"]) or "-",
                "registerDate": _date_text(row["company_software_copyright_register_date"]),
                "status": _normalize_text(row["company_software_copyright_status"]) or "-",
                "shortName": _normalize_text(row["company_software_copyright_for_short"]) or "-",
            }
            for index, row in enumerate(software_rows)
        ],
        "作品著作权数量": [
            {
                "key": f"work-{index + 1}",
                "name": _normalize_text(row["company_work_copyright_name"]) or "-",
                "number": _normalize_text(row["company_work_copyright_register_number"]) or "-",
                "type": _normalize_text(row["company_work_copyright_type"]) or "-",
                "publishDate": _date_text(row["company_work_copyright_publish_date"]),
                "registerDate": _date_text(row["company_work_copyright_register_date"]),
                "status": _normalize_text(row["company_work_copyright_status"]) or "-",
            }
            for index, row in enumerate(work_rows)
        ],
        "商标数量": [
            {
                "key": f"trademark-{index + 1}",
                "name": _normalize_text(row["company_trademark_name"]) or "-",
                "number": _normalize_text(row["company_trademark_register_number"]) or "-",
                "applicationDate": _date_text(row["company_trademark_application_date"]),
            }
            for index, row in enumerate(trademark_rows)
        ],
    }


def _migration_risk_from_recruitment(company_id: int) -> dict:
    row = _rows(
        """
        SELECT
          COUNT(*) AS recruit_count,
          SUM(CASE WHEN company_recruit_work_place LIKE %s THEN 1 ELSE 0 END) AS beijing_recruit_count
        FROM company_recruit
        WHERE company_id = %s
        """,
        ["%北京%", company_id],
    )[0]
    recruit_count = int(row["recruit_count"] or 0)
    beijing_recruit_count = int(row["beijing_recruit_count"] or 0)
    beijing_ratio = round(beijing_recruit_count / recruit_count * 100, 2) if recruit_count else 0.0

    if recruit_count == 0:
        return {
            "level": "高",
            "color": "#ff4d4f",
            "score": 88,
            "label": "未检出招聘吸附信号",
            "factors": [
                {"name": "招聘信息数量", "desc": "库内未检出招聘记录", "impact": "High"},
                {"name": "在京招聘占比", "desc": "无可计算样本", "impact": "High"},
                {"name": "判定口径", "desc": "有招聘记录时，以在京占比 >=60% 判低风险、30%-60% 判中风险、<30% 判高风险", "impact": "Low"},
            ],
            "recruitCount": 0,
            "beijingRecruitCount": 0,
            "beijingRatio": 0.0,
        }

    if beijing_ratio >= 60:
        level = "低"
        color = "#52c41a"
        score = 26
        label = "在京招聘吸附度较强"
    elif beijing_ratio >= 30:
        level = "中"
        color = "#fa8c16"
        score = 56
        label = "在京招聘吸附度一般"
    else:
        level = "高"
        color = "#ff4d4f"
        score = 82
        label = "在京招聘吸附度偏弱"

    impact = "Low" if level == "低" else "Medium" if level == "中" else "High"
    return {
        "level": level,
        "color": color,
        "score": score,
        "label": label,
        "factors": [
            {"name": "招聘信息数量", "desc": f"库内检出 {recruit_count} 条招聘记录", "impact": impact},
            {"name": "在京招聘数量", "desc": f"{beijing_recruit_count} 条岗位工作地位于北京", "impact": impact},
            {"name": "在京招聘占比", "desc": f"{beijing_ratio:.2f}%", "impact": impact},
            {"name": "判定口径", "desc": "有招聘记录时，以在京占比 >=60% 判低风险、30%-60% 判中风险、<30% 判高风险", "impact": "Low"},
        ],
        "recruitCount": recruit_count,
        "beijingRecruitCount": beijing_recruit_count,
        "beijingRatio": beijing_ratio,
    }


def _operation_table_data(company_id: int) -> list[dict]:
    rows = _rows(
        """
        SELECT
          b.employee_count,
          b.insured_count,
          b.listing_status,
          b.industry_belong,
          b.contact_info,
          b.same_phone_company_count,
          b.email_business,
          b.is_general_taxpayer,
          b.financing_round,
          b.has_bidding,
          b.has_recruitment,
          COALESCE(c.bidding_count, 0) AS bidding_count,
          COALESCE(c.recruit_count, 0) AS recruit_count,
          COALESCE(c.customer_count, 0) AS customer_count,
          COALESCE(c.ranking_count, 0) AS ranking_count
        FROM company_basic b
        LEFT JOIN company_basic_count c ON b.company_id = c.company_id
        WHERE b.company_id = %s
        LIMIT 1
        """,
        [company_id],
    )
    if not rows:
        return []
    row = rows[0]
    definitions = [
        ("员工人数", str(row["employee_count"] or "-"), "-"),
        ("社保人数", "-", int(row["insured_count"] or 0)),
        ("上市状态", _listing_status_text(row["listing_status"]), "-"),
        ("国标行业", _normalize_text(row["industry_belong"]) or "-", "-"),
        ("联系方式", _normalize_text(row["contact_info"]) or "-", "-"),
        ("同企业电话", str(row["same_phone_company_count"] or 0), "-"),
        ("邮箱（工商信息）", _normalize_text(row["email_business"]) or "-", "-"),
        ("是否为一般纳税人", _bool_text(row["is_general_taxpayer"]), "-"),
        ("融资轮次", _normalize_text(row["financing_round"]) or "-", "-"),
        ("有无招投标", _presence_text(row["has_bidding"], row["bidding_count"]), "-"),
        ("招投标数量", "-", int(row["bidding_count"] or 0)),
        ("有无招聘", _presence_text(row["has_recruitment"], row["recruit_count"]), "-"),
        ("招聘信息数量", "-", int(row["recruit_count"] or 0)),
        ("是否有客户信息", _presence_text(row["customer_count"], row["customer_count"]), "-"),
        ("客户数量", "-", int(row["customer_count"] or 0)),
        ("是否有上榜榜单", _presence_text(row["ranking_count"], row["ranking_count"]), "-"),
        ("上榜榜单数量", "-", int(row["ranking_count"] or 0)),
    ]
    return [
        {
            "key": f"o{index + 1}",
            "item": item,
            "status": status,
            "count": count,
        }
        for index, (item, status, count) in enumerate(definitions)
    ]


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
    compliance_risk = _risk_profile(company.risk_map)
    migration_risk = _migration_risk_from_recruitment(company.company_id)
    innovation_dimension = next((item for item in score["breakdown"]["professional"] if item["key"] == "innovation"), None)
    overall_radar = [
        {"item": "基础评分", "score": float(score["basic_score"])},
        {"item": "科技属性", "score": float(score["tech_score"])},
        {"item": "专业能力", "score": float(score["professional_score"])},
        {"item": "创新活力", "score": float(innovation_dimension["score"]) if innovation_dimension else 0},
        {"item": "合规风险", "score": max(0, 100 - int(compliance_risk["score"]))},
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

    risk_table_data = _risk_table_data(company.company_id)
    qual_table_data = _qualification_table_data(company.company_id)
    operate_table_data = _operation_table_data(company.company_id)
    ip_details = _ip_detail_payload(company.company_id)

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
        "riskTableData": risk_table_data,
        "qualTableData": qual_table_data,
        "ipDetails": ip_details,
        "operateTableData": operate_table_data,
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
