from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
import re
from time import perf_counter

from django.db import connection, transaction
from django.db import close_old_connections
from django.utils import timezone

from weights_api.models import (
    ScoreModelBasicWeight,
    ScoreModelProfessionalWeight,
    ScoreModelTechWeight,
    ScoreModelTotalWeight,
)

from .models import ScoreIndustryPath, ScoreLog, ScoreResult


TOTAL_DEFAULTS = [
    ("基础指标", Decimal("33.34")),
    ("科技指标", Decimal("33.33")),
    ("专业指标", Decimal("33.33")),
]
BASE_MAX = {
    "established_year": 5.0,
    "registered_capital": 6.0,
    "actual_paid_capital": 8.0,
    "company_type": 7.0,
    "enterprise_size_type": 5.0,
    "social_security_count": 6.0,
    "website": 2.0,
    "business_scope": 5.0,
    "tax_rating": 3.0,
    "tax_type": 3.0,
    "funding_round": 10.0,
    "patent_type": 15.0,
    "software_copyright": 15.0,
    "technology_enterprise": 10.0,
    "tech_patent_type": 10.0,
    "patent_tech_attribute": 20.0,
    "tech_software_copyright": 10.0,
    "software_copyright_tech_attribute": 20.0,
    "tech_technology_enterprise": 15.0,
    "industry_university_research": 15.0,
    "national_provincial_award": 10.0,
    "national_tech_honor": 20.0,
    "provincial_tech_honor": 15.0,
    "medical_ai_model_filing": 10.0,
    "high_quality_dataset": 10.0,
    "industry_market_size": 10.0,
    "industry_heat": 10.0,
    "industry_profit_margin": 10.0,
    "qualification": 20.0,
    "certificates": 20.0,
    "innovation": 10.0,
    "partnership_score": 10.0,
    "ranking": 10.0,
}
GROUP_FIELD_KEYS = {
    "basic": [
        "established_year",
        "registered_capital",
        "actual_paid_capital",
        "company_type",
        "enterprise_size_type",
        "social_security_count",
        "website",
        "business_scope",
        "tax_rating",
        "tax_type",
        "funding_round",
        "patent_type",
        "software_copyright",
        "technology_enterprise",
    ],
    "tech": [
        "tech_patent_type",
        "patent_tech_attribute",
        "tech_software_copyright",
        "software_copyright_tech_attribute",
        "tech_technology_enterprise",
        "industry_university_research",
        "national_provincial_award",
        "national_tech_honor",
        "provincial_tech_honor",
        "medical_ai_model_filing",
        "high_quality_dataset",
    ],
    "pro": [
        "industry_market_size",
        "industry_heat",
        "industry_profit_margin",
        "qualification",
        "certificates",
        "innovation",
        "partnership_score",
        "ranking",
    ],
}
TECH_KEYWORDS = [
    "AI",
    "算法",
    "5G",
    "物联网",
    "传感器",
    "区块链",
    "机器人",
    "3D打印",
    "人工智能",
    "人机交互",
    "基因",
    "生物",
    "诊断",
    "体外诊断",
    "IVD",
    "可穿戴",
    "医学影像",
    "数字疗法",
    "智慧医疗",
    "互联网医疗",
]
MEDICAL_DEVICE_SCOPE_RULES = [
    (["第三类", "Ⅲ类", "III类", "3类"], ["生产"], 5.0, "经营范围：命中第三类生产"),
    (["第二类", "Ⅱ类", "II类", "2类"], ["生产"], 4.0, "经营范围：命中第二类生产"),
    (["第三类", "Ⅲ类", "III类", "3类"], ["销售", "经营"], 3.0, "经营范围：命中第三类销售/经营"),
    (["第二类", "Ⅱ类", "II类", "2类"], ["销售", "经营"], 2.0, "经营范围：命中第二类销售/经营"),
    (["第一类", "Ⅰ类", "I类", "1类"], ["销售", "经营"], 1.0, "经营范围：命中第一类销售/经营"),
]
NATIONAL_TECH_HONOR_KEYWORDS = [
    "国家级技术创新示范企业",
    "国家级企业技术中心",
    "国家火炬计划项目",
    "创新型领军企业",
    "隐形冠军",
    "独角兽企业",
    "未来独角兽企业",
    "潜在独角兽企业",
    "种子独角兽企业",
]
PROVINCIAL_TECH_HONOR_KEYWORDS = [
    "瞪羚企业",
    "省级技术创新示范企业",
    "省级企业技术中心",
    "技术先进型服务企业",
    "科技小巨人企业",
    "专精特新小巨人",
    "创新型试点企业",
    "雏鹰企业",
]
MEDICAL_AI_MODEL_FILING_KEYWORDS = [
    "算法备案",
    "深度合成",
    "医疗大模型",
]
HIGH_QUALITY_DATASET_KEYWORDS = [
    "高质量数据集",
    "医疗数据集",
]
INDUSTRY_UNIVERSITY_RESEARCH_KEYWORDS = [
    "互联网医院100强",
    "医院综合排行榜100强",
    "ABC中国大学排名",
    "中国医药类大学排名",
]
INNOVATION_QUALIFICATION_RULES = [
    (["国家创新医疗器械", "国家级创新医疗器械"], 10.0, "命中国家创新医疗器械"),
    (["北京市创新医疗器械", "北京创新医疗器械"], 7.0, "命中北京市创新医疗器械"),
    (["药物纳入优先审评品种名单", "纳入优先审评品种名单"], 10.0, "命中纳入优先审评品种名单"),
    (["药物拟纳入优先审评品种名单", "拟纳入优先审评"], 7.0, "命中拟纳入优先审评"),
    (["突破性治疗"], 7.0, "命中突破性治疗"),
    (["主文档"], 5.0, "命中医疗器械主文档登记信息"),
]
QUALIFICATION_NOISE_KEYWORDS = [
    "小微企业",
    "曾用名",
    "无特殊",
    "无明确",
    "无",
    "正常经营",
    "司法案件",
    "经营异常",
    "被执行人",
    "失信被执行",
    "事业单位",
]
CERTIFICATE_LIKE_KEYWORDS = [
    "许可",
    "备案",
    "注册",
    "认证",
    "证书",
    "GMP",
    "ISO",
    "受理",
    "在审",
    "临床",
    "原料",
    "辅料",
    "包材",
    "原辅包",
]
INDUSTRY_MARKET_RULES = [
    (["医药流通", "医药零售", "医药商业 / 流通", "医疗零售"], 10, "医药流通/零售"),
    (["CXO", "高值耗材", "高值医用耗材", "化学制药"], 8, "CXO/高值耗材/化学制药"),
    (
        ["创新药", "生物技术", "医疗器械（设备）", "影像设备", "治疗设备", "生命信息支持设备", "康复设备", "民营医院"],
        7,
        "创新药/生物技术/医疗器械设备/民营医院",
    ),
    (
        ["数字医疗", "医疗信息化", "智慧医疗", "互联网医疗", "互联网+健康", "数字疗法", "中药", "疫苗", "第三方医学检验", "第三方中心"],
        6,
        "数字医疗/中药/疫苗/第三方中心",
    ),
    (["化学原料药", "血制品"], 5, "化学原料药/血制品"),
    (["医疗AI", "AI 药物研", "前沿技术", "前沿技术融合"], 4, "医疗AI/前沿技术"),
]
INDUSTRY_HEAT_RULES = [
    (["创新药", "生物技术", "医疗AI", "AI 药物研"], 9, "创新药/生物技术/医疗AI"),
    (["数字医疗", "医疗信息化", "智慧医疗", "互联网医疗", "互联网+健康", "数字疗法"], 8, "数字医疗/医疗信息化"),
    (["高值耗材", "高值医用耗材"], 7, "高值耗材"),
    (["CXO", "医疗器械（设备）", "影像设备", "治疗设备"], 6, "CXO/医疗器械设备"),
    (["中药", "疫苗", "民营医院"], 5, "中药/疫苗/民营医院"),
    (
        ["化学原料药", "血制品", "第三方医学检验", "第三方中心", "医药流通", "医药零售", "医药商业 / 流通", "医疗零售"],
        4,
        "化学原料药/血制品/第三方中心/流通零售",
    ),
]
INDUSTRY_PROFIT_RULES = [
    (["血制品"], 9, "血制品"),
    (["高值耗材", "高值医用耗材", "疫苗", "中药"], 8, "高值耗材/疫苗/中药"),
    (["CXO", "医疗器械（设备）", "影像设备", "治疗设备"], 7, "CXO/医疗器械设备"),
    (["民营医院"], 6, "民营医院"),
    (["创新药", "生物技术", "化学原料药", "第三方医学检验", "第三方中心"], 5, "创新药/生物技术/化学原料药/第三方中心"),
    (["数字医疗", "医疗信息化", "智慧医疗", "互联网医疗", "互联网+健康", "数字疗法"], 4, "数字医疗/医疗信息化"),
    (["医疗AI", "AI 药物研", "医药流通", "医药零售", "医药商业 / 流通", "医疗零售"], 3, "医疗AI/流通零售"),
]
BASIC_DEFAULT_VALUES = {
    "established_year": Decimal("5.0"),
    "registered_capital": Decimal("6.0"),
    "actual_paid_capital": Decimal("8.0"),
    "company_type": Decimal("7.0"),
    "enterprise_size_type": Decimal("5.0"),
    "social_security_count": Decimal("6.0"),
    "website": Decimal("2.0"),
    "business_scope": Decimal("5.0"),
    "tax_rating": Decimal("3.0"),
    "tax_type": Decimal("3.0"),
    "funding_round": Decimal("10.0"),
    "patent_type": Decimal("15.0"),
    "software_copyright": Decimal("15.0"),
    "technology_enterprise": Decimal("10.0"),
}
TECH_DEFAULT_VALUES = {
    "tech_patent_type": Decimal("10.0"),
    "patent_tech_attribute": Decimal("20.0"),
    "tech_software_copyright": Decimal("10.0"),
    "software_copyright_tech_attribute": Decimal("20.0"),
    "tech_technology_enterprise": Decimal("15.0"),
    "industry_university_research": Decimal("15.0"),
    "national_provincial_award": Decimal("10.0"),
    "national_tech_honor": Decimal("20.0"),
    "provincial_tech_honor": Decimal("15.0"),
    "medical_ai_model_filing": Decimal("10.0"),
    "high_quality_dataset": Decimal("10.0"),
}
PRO_DEFAULT_VALUES = {
    "industry_market_size": Decimal("10.0"),
    "industry_heat": Decimal("10.0"),
    "industry_profit_margin": Decimal("10.0"),
    "qualification": Decimal("20.0"),
    "certificates": Decimal("20.0"),
    "innovation": Decimal("10.0"),
    "partnership_score": Decimal("10.0"),
    "ranking": Decimal("10.0"),
}


@dataclass
class PatentRecord:
    patent_number: str = ""
    patent_name: str = ""
    tech_attribute_label: str = ""
    patent_types: list[str] = field(default_factory=list)


@dataclass
class CompanySnapshot:
    company_id: int
    company_name: str
    credit_code: str
    legal_representative: str
    establish_date: date | None
    approved_date: date | None
    register_capital: Decimal | None
    paid_capital: Decimal | None
    company_type: str
    company_status: str
    company_scale: str
    employee_count: int | None
    insured_count: int | None
    website: str
    business_scope: str
    register_address: str
    register_address_detail: str
    taxpayer_credit_rating: str
    taxpayer_qualifications: str
    is_general_taxpayer: bool
    financing_round: str
    qualification_label: str
    stock_code: str
    listing_status: int | None
    is_high_tech_enterprise: bool
    is_srdi_sme: bool
    is_srdi_little_giant: bool
    is_innovative_sme: bool
    is_tech_sme: bool
    is_gazelle_company: bool
    is_egalet_company: bool
    has_dishonest_execution: bool
    has_business_abnormal: bool
    has_consumption_restriction: bool
    consumption_restriction_count: int
    patents: list[PatentRecord] = field(default_factory=list)
    software_names: list[str] = field(default_factory=list)
    qualification_texts: list[str] = field(default_factory=list)
    ai_model_filings: list[str] = field(default_factory=list)
    high_quality_datasets: list[str] = field(default_factory=list)
    innovation_texts: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    suppliers: list[str] = field(default_factory=list)
    rankings: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    risk_map: dict[str, int] = field(default_factory=dict)


def _set_status(callback, status: str, message: str):
    if callback:
        callback(status, message)


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", "").strip()


def _contains_any(text: str, keywords: list[str]) -> bool:
    normalized = _normalize_text(text).upper()
    return any(keyword.upper() in normalized for keyword in keywords)


def _split_text_tokens(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[\n,，;；、]+", _normalize_text(value)) if item.strip()]


def _fetch_rows(query: str, params: list | tuple | None = None) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


_TABLE_EXISTS_CACHE: dict[str, bool] = {}


def _table_exists(table_name: str) -> bool:
    if table_name not in _TABLE_EXISTS_CACHE:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = %s
                """,
                [table_name],
            )
            _TABLE_EXISTS_CACHE[table_name] = bool(cursor.fetchone()[0])
    return _TABLE_EXISTS_CACHE[table_name]


def _ensure_weight_rows():
    if ScoreModelTotalWeight.objects.count() == 0:
        for name, weight in TOTAL_DEFAULTS:
            ScoreModelTotalWeight.objects.create(model_name=name, model_weight=weight)
    basic_row = ScoreModelBasicWeight.objects.order_by("model_id").first()
    if not basic_row:
        ScoreModelBasicWeight.objects.create(model_name="基础指标模型", **BASIC_DEFAULT_VALUES)
    elif all(float(getattr(basic_row, field) or 0) == 0 for field in BASIC_DEFAULT_VALUES):
        for field, value in BASIC_DEFAULT_VALUES.items():
            setattr(basic_row, field, value)
        basic_row.save(update_fields=list(BASIC_DEFAULT_VALUES.keys()))

    tech_row = ScoreModelTechWeight.objects.order_by("model_id").first()
    if not tech_row:
        ScoreModelTechWeight.objects.create(model_name="科技指标模型", **TECH_DEFAULT_VALUES)
    elif all(float(getattr(tech_row, field) or 0) == 0 for field in TECH_DEFAULT_VALUES):
        for field, value in TECH_DEFAULT_VALUES.items():
            setattr(tech_row, field, value)
        tech_row.save(update_fields=list(TECH_DEFAULT_VALUES.keys()))
    else:
        missing_fields = [
            field
            for field, value in TECH_DEFAULT_VALUES.items()
            if float(getattr(tech_row, field) or 0) == 0 and value > 0
        ]
        if missing_fields:
            for field in missing_fields:
                setattr(tech_row, field, TECH_DEFAULT_VALUES[field])
            tech_row.save(update_fields=missing_fields)

    pro_row = ScoreModelProfessionalWeight.objects.order_by("model_id").first()
    if not pro_row:
        ScoreModelProfessionalWeight.objects.create(model_name="专业指标模型", **PRO_DEFAULT_VALUES)
    elif all(float(getattr(pro_row, field) or 0) == 0 for field in PRO_DEFAULT_VALUES):
        for field, value in PRO_DEFAULT_VALUES.items():
            setattr(pro_row, field, value)
        pro_row.save(update_fields=list(PRO_DEFAULT_VALUES.keys()))


def _resolve_total_weight(total_map: dict[str, float], aliases: list[str], default: float) -> float:
    for alias in aliases:
        if alias in total_map:
            return float(total_map[alias])
    return default


def _coerce_bool(value) -> bool:
    return str(value or 0) in {"1", "True", "true"}


def _safe_decimal(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _years_since(establish_date: date | None) -> int | None:
    if not establish_date:
        return None
    today = date.today()
    years = today.year - establish_date.year
    if (today.month, today.day) < (establish_date.month, establish_date.day):
        years -= 1
    return max(years, 0)


def _in_clause(ids: list[int]) -> tuple[str, list[int]]:
    placeholders = ", ".join(["%s"] * len(ids))
    return f"({placeholders})", ids


def _load_weights() -> dict:
    _ensure_weight_rows()
    return {
        "basic": ScoreModelBasicWeight.objects.order_by("model_id").first(),
        "tech": ScoreModelTechWeight.objects.order_by("model_id").first(),
        "pro": ScoreModelProfessionalWeight.objects.order_by("model_id").first(),
        "total": {row.model_name: float(row.model_weight) for row in ScoreModelTotalWeight.objects.all()},
    }


def _load_company_data(company_ids: list[int] | None = None) -> dict[int, CompanySnapshot]:
    where_clause = ""
    params: list[int] = []
    if company_ids:
        in_clause, params = _in_clause(company_ids)
        where_clause = f"WHERE company_id IN {in_clause}"
    company_rows = _fetch_rows(
        f"""
        SELECT
          company_id,
          company_name,
          credit_code,
          legal_representative,
          establish_date,
          approved_date,
          register_capital,
          paid_capital,
          company_type,
          company_status,
          company_scale,
          employee_count,
          insured_count,
          website,
          business_scope,
          register_address,
          register_address_detail,
          taxpayer_credit_rating,
          taxpayer_qualifications,
          is_general_taxpayer,
          financing_round,
          qualification_label,
          stock_code,
          listing_status,
          is_high_tech_enterprise,
          is_srdi_sme,
          is_srdi_little_giant,
          is_innovative_sme,
          is_tech_sme,
          is_gazelle_company,
          is_egalet_company,
          has_dishonest_execution,
          has_business_abnormal,
          has_consumption_restriction,
          consumption_restriction_count
        FROM company_basic
        {where_clause}
        ORDER BY company_id
        """,
        params,
    )
    companies: dict[int, CompanySnapshot] = {}
    for row in company_rows:
        companies[row["company_id"]] = CompanySnapshot(
            company_id=row["company_id"],
            company_name=_normalize_text(row["company_name"]),
            credit_code=_normalize_text(row["credit_code"]),
            legal_representative=_normalize_text(row["legal_representative"]),
            establish_date=row["establish_date"],
            approved_date=row["approved_date"],
            register_capital=row["register_capital"],
            paid_capital=row["paid_capital"],
            company_type=_normalize_text(row["company_type"]),
            company_status=_normalize_text(row["company_status"]),
            company_scale=_normalize_text(row["company_scale"]),
            employee_count=row["employee_count"],
            insured_count=row["insured_count"],
            website=_normalize_text(row["website"]),
            business_scope=_normalize_text(row["business_scope"]),
            register_address=_normalize_text(row["register_address"]),
            register_address_detail=_normalize_text(row["register_address_detail"]),
            taxpayer_credit_rating=_normalize_text(row["taxpayer_credit_rating"]).upper(),
            taxpayer_qualifications=_normalize_text(row["taxpayer_qualifications"]),
            is_general_taxpayer=_coerce_bool(row["is_general_taxpayer"]),
            financing_round=_normalize_text(row["financing_round"]),
            qualification_label=_normalize_text(row["qualification_label"]),
            stock_code=_normalize_text(row["stock_code"]),
            listing_status=row["listing_status"],
            is_high_tech_enterprise=_coerce_bool(row["is_high_tech_enterprise"]),
            is_srdi_sme=_coerce_bool(row["is_srdi_sme"]),
            is_srdi_little_giant=_coerce_bool(row["is_srdi_little_giant"]),
            is_innovative_sme=_coerce_bool(row["is_innovative_sme"]),
            is_tech_sme=_coerce_bool(row["is_tech_sme"]),
            is_gazelle_company=_coerce_bool(row["is_gazelle_company"]),
            is_egalet_company=_coerce_bool(row["is_egalet_company"]),
            has_dishonest_execution=_coerce_bool(row["has_dishonest_execution"]),
            has_business_abnormal=_coerce_bool(row["has_business_abnormal"]),
            has_consumption_restriction=_coerce_bool(row["has_consumption_restriction"]),
            consumption_restriction_count=int(row["consumption_restriction_count"] or 0),
        )

    if not companies:
        return {}

    filter_ids = list(companies.keys())
    in_clause, in_params = _in_clause(filter_ids)

    patent_rows = _fetch_rows(
        f"""
        SELECT
          p.company_id,
          p.company_patent_number,
          p.company_patent_name,
          COALESCE(p.tech_attribute_label, '') AS tech_attribute_label,
          GROUP_CONCAT(DISTINCT t.company_patent_type_name ORDER BY t.company_patent_type_name SEPARATOR '|') AS patent_types
        FROM company_patent p
        LEFT JOIN company_patent_patent_type_map m ON m.company_patent_id = p.company_patent_id
        LEFT JOIN company_patent_type t ON t.company_patent_type_id = m.company_patent_type_id
        WHERE p.company_id IN {in_clause}
        GROUP BY p.company_patent_id, p.company_id, p.company_patent_number, p.company_patent_name, p.tech_attribute_label
        """,
        in_params,
    )
    for row in patent_rows:
        company = companies.get(row["company_id"])
        if not company:
            continue
        patent_types = [item for item in _normalize_text(row["patent_types"]).split("|") if item]
        company.patents.append(
            PatentRecord(
                patent_number=_normalize_text(row["company_patent_number"]),
                patent_name=_normalize_text(row["company_patent_name"]),
                tech_attribute_label=_normalize_text(row["tech_attribute_label"]),
                patent_types=patent_types,
            )
        )

    software_rows = _fetch_rows(
        f"""
        SELECT company_id, company_software_copyright_name, company_software_copyright_for_short
        FROM company_software_copyright
        WHERE company_id IN {in_clause}
        """,
        in_params,
    )
    for row in software_rows:
        company = companies.get(row["company_id"])
        if not company:
            continue
        texts = [
            _normalize_text(row["company_software_copyright_name"]),
            _normalize_text(row["company_software_copyright_for_short"]),
        ]
        company.software_names.extend([text for text in texts if text])

    qualification_rows = _fetch_rows(
        f"""
        SELECT company_id, qualification_name, qualification_type
        FROM company_qualification
        WHERE company_id IN {in_clause}
        """,
        in_params,
    )
    for row in qualification_rows:
        company = companies.get(row["company_id"])
        if not company:
            continue
        text = " ".join(
            [
                _normalize_text(row["qualification_name"]),
                _normalize_text(row["qualification_type"]),
            ]
        ).strip()
        if not text:
            continue
        upper_text = text.upper()
        if any(keyword.upper() in upper_text for keyword in QUALIFICATION_NOISE_KEYWORDS) and not any(
            keyword.upper() in upper_text for keyword in CERTIFICATE_LIKE_KEYWORDS
        ):
            continue
        company.qualification_texts.append(text)

    if _table_exists("company_ai_model_filing"):
        for row in _fetch_rows(
            f"""
            SELECT company_id, model_name, filing_no, filing_type, territory
            FROM company_ai_model_filing
            WHERE company_id IN {in_clause}
            """,
            in_params,
        ):
            company = companies.get(row["company_id"])
            if not company:
                continue
            text = " ".join(
                item
                for item in [
                    "算法备案 医疗大模型",
                    _normalize_text(row["model_name"]),
                    _normalize_text(row["filing_no"]),
                    _normalize_text(row["filing_type"]),
                    _normalize_text(row["territory"]),
                ]
                if item
            ).strip()
            if text:
                company.ai_model_filings.append(text)

    if _table_exists("company_high_quality_dataset"):
        for row in _fetch_rows(
            f"""
            SELECT company_id, dataset_name, applicant_unit_raw, recommender_unit
            FROM company_high_quality_dataset
            WHERE company_id IN {in_clause}
            """,
            in_params,
        ):
            company = companies.get(row["company_id"])
            if not company:
                continue
            text = " ".join(
                item
                for item in [
                    "高质量数据集",
                    _normalize_text(row["dataset_name"]),
                    _normalize_text(row["applicant_unit_raw"]),
                    _normalize_text(row["recommender_unit"]),
                ]
                if item
            ).strip()
            if text:
                company.high_quality_datasets.append(text)

    if _table_exists("company_innovation_notice"):
        notice_aliases = {
            "innovative_medical_device_beijing": "北京市创新医疗器械",
            "innovative_medical_device_national": "国家创新医疗器械",
            "priority_review_candidate": "药物拟纳入优先审评品种名单",
            "breakthrough_therapy": "突破性治疗",
            "master_file": "主文档登记信息",
        }
        for row in _fetch_rows(
            f"""
            SELECT company_id, notice_type, notice_title, notice_category, product_name, reg_no, acceptance_no, owner_name
            FROM company_innovation_notice
            WHERE company_id IN {in_clause}
            """,
            in_params,
        ):
            company = companies.get(row["company_id"])
            if not company:
                continue
            notice_type = _normalize_text(row["notice_type"])
            text = " ".join(
                item
                for item in [
                    notice_aliases.get(notice_type, notice_type),
                    _normalize_text(row["notice_title"]),
                    _normalize_text(row["notice_category"]),
                    _normalize_text(row["product_name"]),
                    _normalize_text(row["reg_no"]),
                    _normalize_text(row["acceptance_no"]),
                    _normalize_text(row["owner_name"]),
                ]
                if item
            ).strip()
            if text:
                company.innovation_texts.append(text)

    for row in _fetch_rows(
        f"SELECT company_id, company_customer_name FROM company_customer WHERE company_customer_name IS NOT NULL AND company_id IN {in_clause}",
        in_params,
    ):
        company = companies.get(row["company_id"])
        if company:
            company.customers.append(_normalize_text(row["company_customer_name"]))

    for row in _fetch_rows(
        f"SELECT company_id, company_supplier_name FROM company_supplier WHERE company_supplier_name IS NOT NULL AND company_id IN {in_clause}",
        in_params,
    ):
        company = companies.get(row["company_id"])
        if company:
            company.suppliers.append(_normalize_text(row["company_supplier_name"]))

    for row in _fetch_rows(
        f"SELECT company_id, company_ranking_name FROM company_ranking WHERE company_ranking_name IS NOT NULL AND company_id IN {in_clause}",
        in_params,
    ):
        company = companies.get(row["company_id"])
        if company:
            company.rankings.append(_normalize_text(row["company_ranking_name"]))

    for row in _fetch_rows(
        f"SELECT company_id, company_risk_category_name, company_risk_category_count FROM company_risk WHERE company_id IN {in_clause}",
        in_params,
    ):
        company = companies.get(row["company_id"])
        if company:
            company.risk_map[_normalize_text(row["company_risk_category_name"])] = int(row["company_risk_category_count"] or 0)

    category_rows = _fetch_rows(
        """
        SELECT category_id, category_name, category_level_code, category_level_code_parent
        FROM category_industry
        """
    )
    category_by_id = {row["category_id"]: row for row in category_rows}
    category_by_code = {row["category_level_code"]: row for row in category_rows}
    path_cache: dict[int, str] = {}

    def build_path(category_id: int) -> str:
        if category_id in path_cache:
            return path_cache[category_id]
        row = category_by_id[category_id]
        parts = [row["category_name"]]
        parent_code = row["category_level_code_parent"]
        while parent_code and parent_code in category_by_code:
            parent = category_by_code[parent_code]
            parts.append(parent["category_name"])
            parent_code = parent["category_level_code_parent"]
        path = "/".join(reversed(parts))
        path_cache[category_id] = path
        return path

    for row in _fetch_rows(
        f"SELECT company_id, category_id FROM category_industry_company_map WHERE company_id IN {in_clause}",
        in_params,
    ):
        company = companies.get(row["company_id"])
        if company and row["category_id"] in category_by_id:
            company.industries.append(build_path(row["category_id"]))

    for company in companies.values():
        company.industries = sorted(set([path for path in company.industries if path]), key=lambda item: (item.count("/"), item))
        company.customers = [name for name in company.customers if name]
        company.suppliers = [name for name in company.suppliers if name]
        company.rankings = [name for name in company.rankings if name]

    return companies


def get_company_scoring_snapshot(company_id: int) -> dict | None:
    weights = _load_weights()
    companies = _load_company_data([company_id])
    company = companies.get(company_id)
    if not company:
        return None
    scorer = CompanyScorer(company, weights)
    result = scorer.calculate_all()
    return {"company": company, "score": result}


class CompanyScorer:
    def __init__(self, company: CompanySnapshot, weights: dict):
        self.company = company
        self.weights = weights
        self.logs: list[dict] = []
        self.breakdown = {"basic": [], "tech": [], "professional": []}

    def _scale(self, level: str, field_key: str, raw_score: float) -> float:
        config = self.weights[level]
        target_weight = float(getattr(config, field_key, BASE_MAX[field_key])) if config else BASE_MAX[field_key]
        return raw_score * (target_weight / BASE_MAX[field_key])

    def _weight_value(self, level: str, field_key: str) -> float:
        config = self.weights[level]
        if field_key not in BASE_MAX:
            return 0.0
        return float(getattr(config, field_key, BASE_MAX[field_key])) if config else BASE_MAX[field_key]

    def _group_target_total(self, level: str) -> float:
        field_keys = GROUP_FIELD_KEYS[level]
        total = sum(self._weight_value(level, field_key) for field_key in field_keys)
        return total or sum(BASE_MAX[field_key] for field_key in field_keys)

    def _add_log(self, score_type: str, score_value: float, description: str):
        self.logs.append(
            {
                "score_type": score_type,
                "score_value": round(float(score_value), 2),
                "description": description,
            }
        )

    def _record_dimension(
        self,
        *,
        group: str,
        field_key: str,
        name: str,
        raw_score: float,
        scaled_score: float,
        description: str,
    ):
        self.breakdown[group].append(
            {
                "key": field_key,
                "name": name,
                "weight": round(self._weight_value("pro" if group == "professional" else group, field_key), 2)
                if field_key in BASE_MAX
                else 0,
                "rawScore": round(float(raw_score), 2),
                "score": round(float(scaled_score), 2),
                "description": description,
            }
        )

    def _primary_industry(self) -> str:
        if not self.company.industries:
            return ""
        return sorted(self.company.industries, key=lambda item: (item.count("/"), item), reverse=True)[0]

    def _all_qualification_texts(self) -> list[str]:
        values = list(self.company.qualification_texts)
        values.extend(_split_text_tokens(self.company.qualification_label))
        result = []
        seen = set()
        for value in values:
            normalized = _normalize_text(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    def _honor_text_pool(self) -> list[str]:
        values = (
            self._all_qualification_texts()
            + self.company.ai_model_filings
            + self.company.high_quality_datasets
            + self.company.innovation_texts
            + self.company.rankings
        )
        result = []
        seen = set()
        for value in values:
            normalized = _normalize_text(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    def _score_from_rules(self, score_type: str, label: str, industry: str, rules: list[tuple[list[str], int, str]], default_score: int, plus_one: bool = False) -> float:
        if not industry:
            self._add_log(score_type, default_score, f"{label}：无行业分类数据，{default_score}分")
            return float(default_score)
        for keywords, score, reason in rules:
            if any(keyword in industry for keyword in keywords):
                actual = score + 1 if plus_one else score
                self._add_log(score_type, actual, f"{label}：{industry} -> {reason}，{actual}分")
                return float(actual)
        self._add_log(score_type, default_score, f"{label}：{industry} -> 其他，{default_score}分")
        return float(default_score)

    def calculate_all(self) -> dict:
        basic_score = self.calculate_basic_score()
        tech_score = self.calculate_tech_score()
        professional_score = self.calculate_professional_score()

        total_weights = self.weights["total"]
        basic_ratio = _resolve_total_weight(total_weights, ["基础指标", "基础评分模型", "基础指标模型", "企业基础标准评分模型"], 33.34) / 100.0
        tech_ratio = _resolve_total_weight(total_weights, ["科技指标", "科技属性评分模型", "科技指标模型", "科技属性标准评分模型"], 33.33) / 100.0
        professional_ratio = _resolve_total_weight(total_weights, ["专业指标", "专业能力评分模型", "专业指标模型", "专业能力标准评分模型"], 33.33) / 100.0
        total_score = (basic_score * basic_ratio) + (tech_score * tech_ratio) + (professional_score * professional_ratio)

        return {
            "enterprise_id": self.company.company_id,
            "company_name": self.company.company_name,
            "basic_score": round(max(basic_score, 0), 2),
            "tech_score": round(max(tech_score, 0), 2),
            "professional_score": round(max(professional_score, 0), 2),
            "total_score": round(max(total_score, 0), 2),
            "logs": self.logs,
            "breakdown": self.breakdown,
            "industry_paths": self.company.industries,
        }

    def calculate_basic_score(self) -> float:
        scaled_score = 0.0
        raw_score = 0.0
        items = [
            ("established_year", "成立年限", self.calculate_established_year),
            ("registered_capital", "注册资本", self.calculate_registered_capital),
            ("actual_paid_capital", "实缴资本", self.calculate_actual_paid_capital),
            ("company_type", "公司类型", self.calculate_company_type),
            ("enterprise_size_type", "企业规模", self.calculate_enterprise_size_type),
            ("social_security_count", "社保人数", self.calculate_social_security_count),
            ("website", "网址", self.calculate_website),
            ("business_scope", "经营范围", self.calculate_business_scope),
            ("tax_rating", "纳税人等级", self.calculate_tax_rating),
            ("tax_type", "纳税人类型", self.calculate_tax_type),
            ("funding_round", "投融资轮次", self.calculate_funding_round),
            ("patent_type", "专利类型", self.calculate_patent_type),
            ("software_copyright", "软件著作权", self.calculate_software_copyright),
            ("technology_enterprise", "科技型企业", self.calculate_technology_enterprise),
        ]
        for field_key, label, func in items:
            start_index = len(self.logs)
            raw = func()
            description = "；".join(log["description"] for log in self.logs[start_index:]) or f"{label}：{raw}分"
            raw_score += raw
            scaled_value = self._scale("basic", field_key, raw)
            scaled_score += scaled_value
            self._record_dimension(
                group="basic",
                field_key=field_key,
                name=label,
                raw_score=raw,
                scaled_score=scaled_value,
                description=description,
            )
        risk_start = len(self.logs)
        risk_penalty = self.calculate_risk_penalties()
        scaled_score += risk_penalty
        risk_description = "；".join(log["description"] for log in self.logs[risk_start:]) or "风险扣分：0分"
        self._record_dimension(
            group="basic",
            field_key="risk_penalties",
            name="风险扣分",
            raw_score=risk_penalty,
            scaled_score=risk_penalty,
            description=risk_description,
        )
        group_total = self._group_target_total("basic")
        final_score = max(round((scaled_score / group_total) * 100, 2), 0) if group_total else 0
        self._add_log("basic", final_score, f"基础模块：原始分 {round(raw_score, 2)}，加权分 {round(scaled_score, 2)} / {round(group_total, 2)}，归一后 {final_score} 分")
        return final_score

    def calculate_website(self) -> float:
        score = 2.0 if self.company.website else 0.0
        self._add_log("basic", score, f"网址：{'存在官网地址' if self.company.website else '未提供官网'}，{score}分")
        return score

    def calculate_established_year(self) -> float:
        years = _years_since(self.company.establish_date)
        if years is None:
            score = 1.0
            self._add_log("basic", score, "成立年限：缺失，1分")
            return score
        if years >= 10:
            score = 5.0
        elif years >= 5:
            score = 4.0
        elif years >= 1:
            score = 3.0
        else:
            score = 1.0
        self._add_log("basic", score, f"成立年限：{years}年，{score}分")
        return score

    def calculate_registered_capital(self) -> float:
        capital = float(_safe_decimal(self.company.register_capital))
        if capital > 1000:
            score = 6.0
        elif capital >= 500:
            score = 5.0
        elif capital >= 200:
            score = 4.0
        elif capital >= 100:
            score = 3.0
        elif capital >= 0:
            score = 2.0
        else:
            score = 0.0
        self._add_log("basic", score, f"注册资本：{capital}万元，{score}分")
        return score

    def calculate_actual_paid_capital(self) -> float:
        capital = float(_safe_decimal(self.company.paid_capital))
        if capital > 500:
            score = 8.0
        elif capital >= 100:
            score = 6.0
        elif capital > 0:
            score = 3.0
        else:
            score = 1.0
        self._add_log("basic", score, f"实缴资本：{capital}万元，{score}分")
        return score

    def calculate_company_type(self) -> float:
        company_type = _normalize_text(self.company.company_type)
        if self.company.listing_status == 1 or self.company.stock_code or _contains_any(company_type, ["上市", "央企"]):
            score = 7.0
        elif _contains_any(company_type, ["自然人投资或控股", "股份合作制"]):
            score = 3.0
        elif _contains_any(company_type, ["个人独资", "自然人独资", "合伙"]):
            score = 2.0
        elif _contains_any(company_type, ["国有", "股份有限公司"]):
            score = 5.0
        elif _contains_any(company_type, ["有限责任公司", "外商投资", "台港澳", "外国法人"]):
            score = 4.0
        elif "个体工商户" in company_type:
            score = 2.0
        else:
            score = 1.0
        self._add_log("basic", score, f"公司类型：{company_type or '未提供'}，{score}分")
        return score

    def calculate_enterprise_size_type(self) -> float:
        size_text = _normalize_text(self.company.company_scale)
        if "大" in size_text:
            score = 5.0
        elif "中" in size_text:
            score = 4.0
        elif "小" in size_text:
            score = 3.0
        elif "微" in size_text:
            score = 2.0
        else:
            score = 1.0
        self._add_log("basic", score, f"企业规模：{size_text or '未提供'}，{score}分")
        return score

    def calculate_social_security_count(self) -> float:
        count = int(self.company.insured_count or 0)
        if count >= 500:
            score = 6.0
        elif count >= 100:
            score = 5.0
        elif count >= 50:
            score = 4.0
        elif count >= 30:
            score = 3.0
        elif count > 0:
            score = 2.0
        else:
            score = 0.0
        self._add_log("basic", score, f"社保人数：{count}人，{score}分")
        return score

    def calculate_business_scope(self) -> float:
        scope = _normalize_text(self.company.business_scope)
        if not scope:
            self._add_log("basic", 0.0, "经营范围：缺失，0分")
            return 0.0
        for class_keywords, action_keywords, score, description in MEDICAL_DEVICE_SCOPE_RULES:
            if any(keyword in scope for keyword in class_keywords) and any(keyword in scope for keyword in action_keywords):
                self._add_log("basic", score, f"{description}，{score}分")
                return score
        self._add_log("basic", 0.0, "经营范围：未命中医疗器械分档关键词，0分")
        return 0.0

    def calculate_tax_rating(self) -> float:
        rating = self.company.taxpayer_credit_rating
        score = 3.0 if rating == "A" else 1.0
        self._add_log("basic", score, f"纳税人等级：{rating or '未提供'}，{score}分")
        return score

    def calculate_tax_type(self) -> float:
        score = 3.0 if self.company.is_general_taxpayer else 1.0
        self._add_log("basic", score, f"纳税人类型：{'一般纳税人' if self.company.is_general_taxpayer else (self.company.taxpayer_qualifications or '未提供')}，{score}分")
        return score

    def calculate_funding_round(self) -> float:
        round_text = self.company.financing_round.upper()
        if not round_text:
            score = 1.0
        elif _contains_any(round_text, ["IPO", "上市"]):
            score = 10.0
        elif _contains_any(round_text, ["PRE-IPO"]):
            score = 10.0
        elif _contains_any(round_text, ["D轮", "E轮", "D ", "E "]):
            score = 8.0
        elif _contains_any(round_text, ["C轮", "战略投资", "战略融资"]):
            score = 6.0
        elif _contains_any(round_text, ["B轮", "股权融资"]):
            score = 5.0
        elif _contains_any(round_text, ["天使", "ANGEL", "A轮", "PREA", "PRE-A", "A "]):
            score = 4.0
        else:
            score = 1.0
        self._add_log("basic", score, f"投融资轮次：{self.company.financing_round or '未提供'}，{score}分")
        return score

    def calculate_patent_type(self) -> float:
        score = 0.0
        pct_count = 0
        invention_auth = 0
        invention_public = 0
        substantial_exam = 0
        utility = 0
        design = 0
        for patent in self.company.patents:
            patent_types = patent.patent_types
            patent_number = patent.patent_number.upper()
            if "PCT" in patent_number or patent_number.startswith("WO"):
                score += 4.0
                pct_count += 1
            elif "发明授权" in patent_types:
                score += 2.0
                invention_auth += 1
            elif "发明公开" in patent_types:
                score += 1.0
                invention_public += 1
            elif any("实质审查" in patent_type for patent_type in patent_types):
                score += 0.5
                substantial_exam += 1
            elif "实用新型" in patent_types:
                score += 0.5
                utility += 1
            elif "外观设计" in patent_types:
                score += 0.5
                design += 1
        score = min(score, 15.0)
        self._add_log(
            "basic",
            score,
            f"专利类型：PCT{pct_count}、发明授权{invention_auth}、发明公开{invention_public}、实质审查{substantial_exam}、实用新型{utility}、外观设计{design}，{score}分",
        )
        return score

    def calculate_software_copyright(self) -> float:
        count = len(self.company.software_names)
        score = min(float(count), 15.0)
        self._add_log("basic", score, f"软件著作权：{count}项，{score}分")
        return score

    def calculate_technology_enterprise(self) -> float:
        score = 1.0
        descriptions: list[str] = ["无"]
        if self.company.is_srdi_little_giant or self.company.is_srdi_sme:
            score += 8.0
            descriptions = ["专精特新"]
        if self.company.is_innovative_sme:
            score += 6.0
            descriptions.append("创新型企业")
        if self.company.is_high_tech_enterprise:
            score += 4.0
            descriptions.append("高新企业")
        score = min(score, 10.0)
        label = "、".join(descriptions)
        self._add_log("basic", score, f"科技型企业：{label}，{score}分")
        return score

    def calculate_risk_penalties(self) -> float:
        total_penalty = 0.0
        dishonest = self.company.has_dishonest_execution or any("失信" in name and count > 0 for name, count in self.company.risk_map.items())
        restricted = self.company.has_consumption_restriction or self.company.consumption_restriction_count > 0 or any("限制高消费" in name and count > 0 for name, count in self.company.risk_map.items())
        abnormal = self.company.has_business_abnormal or any("经营异常" in name and count > 0 for name, count in self.company.risk_map.items())
        if dishonest:
            total_penalty -= 50.0
            self._add_log("basic", -50.0, "风险项：存在失信被执行记录，扣50分")
        if restricted:
            total_penalty -= 50.0
            self._add_log("basic", -50.0, "风险项：存在限制高消费记录，扣50分")
        if abnormal:
            total_penalty -= 10.0
            self._add_log("basic", -10.0, "风险项：存在经营异常记录，扣10分")
        if "集群注册" in (self.company.register_address or "") or "集群注册" in (self.company.register_address_detail or ""):
            total_penalty -= 2.0
            self._add_log("basic", -2.0, "风险项：注册地址命中集群注册，扣2分")
        return total_penalty

    def calculate_tech_score(self) -> float:
        items = [
            ("tech_patent_type", "专利类型", self.calculate_tech_patent_type),
            ("patent_tech_attribute", "专利科技属性", self.calculate_patent_tech_attribute),
            ("tech_software_copyright", "软件著作权", self.calculate_tech_software_copyright),
            ("software_copyright_tech_attribute", "软著科技属性", self.calculate_software_copyright_tech_attribute),
            ("tech_technology_enterprise", "科技型企业", self.calculate_tech_technology_enterprise),
            ("industry_university_research", "产学研合作", self.calculate_industry_university_research),
            ("national_provincial_award", "国家/省级奖励", self.calculate_national_provincial_award),
            ("national_tech_honor", "科技荣誉（国家级）", self.calculate_national_tech_honor),
            ("provincial_tech_honor", "科技荣誉（省级）", self.calculate_provincial_tech_honor),
            ("medical_ai_model_filing", "算法备案的医疗大模型", self.calculate_medical_ai_model_filing),
            ("high_quality_dataset", "高质量数据集", self.calculate_high_quality_dataset),
        ]
        raw_score = 0.0
        scaled_score = 0.0
        for field_key, label, func in items:
            start_index = len(self.logs)
            raw = func()
            description = "；".join(log["description"] for log in self.logs[start_index:]) or f"{label}：{raw}分"
            raw_score += raw
            scaled_value = self._scale("tech", field_key, raw)
            scaled_score += scaled_value
            self._record_dimension(
                group="tech",
                field_key=field_key,
                name=label,
                raw_score=raw,
                scaled_score=scaled_value,
                description=description,
            )
        group_total = self._group_target_total("tech")
        final_score = max(round((scaled_score / group_total) * 100, 2), 0) if group_total else 0
        self._add_log("tech", final_score, f"科技模块：原始分 {round(raw_score, 2)}，加权分 {round(scaled_score, 2)} / {round(group_total, 2)}，归一后 {final_score} 分")
        return final_score

    def calculate_tech_patent_type(self) -> float:
        pct_count = 0
        invention_count = 0
        other_count = 0
        for patent in self.company.patents:
            patent_types = patent.patent_types
            patent_number = patent.patent_number.upper()
            if "PCT" in patent_number or patent_number.startswith("WO"):
                pct_count += 1
            if "发明授权" in patent_types or "发明公开" in patent_types:
                invention_count += 1
            elif any(keyword in patent_type for patent_type in patent_types for keyword in ["实质审查", "实用新型", "外观设计"]):
                other_count += 1

        if pct_count >= 5 or invention_count >= 20:
            score = 10.0
        elif 3 <= pct_count <= 5 or 10 <= invention_count < 20:
            score = 8.0
        elif 1 <= pct_count < 3 or 5 <= invention_count < 10:
            score = 6.0
        elif 1 <= invention_count < 5:
            score = 3.0
        elif other_count > 0:
            score = min(other_count * 0.5, 2.0)
        else:
            score = 0.0
        self._add_log("tech", score, f"专利类型（科技）：PCT {pct_count} 项、发明专利 {invention_count} 项、其他专利 {other_count} 项，{score}分")
        return score

    def calculate_patent_tech_attribute(self) -> float:
        score = 0.0
        hits = 0
        for patent in self.company.patents:
            text = " ".join([patent.patent_name, patent.tech_attribute_label])
            if _contains_any(text, TECH_KEYWORDS):
                hits += 1
                score += 1.0
        score = min(score, 20.0)
        self._add_log("tech", score, f"专利科技属性：命中 {hits} 项，{score}分")
        return score

    def calculate_tech_software_copyright(self) -> float:
        count = len(self.company.software_names)
        if count >= 20:
            score = 10.0
        elif count >= 10:
            score = 8.0
        elif count >= 5:
            score = 6.0
        elif count >= 3:
            score = 2.0
        elif count >= 1:
            score = 1.0
        else:
            score = 0.0
        self._add_log("tech", score, f"软件著作权（科技）：{count}项，{score}分")
        return score

    def calculate_software_copyright_tech_attribute(self) -> float:
        hits = 0
        for text in self.company.software_names:
            if _contains_any(text, TECH_KEYWORDS):
                hits += 1
        score = min(float(hits), 20.0)
        self._add_log("tech", score, f"软著科技属性：命中 {hits} 项，{score}分")
        return score

    def calculate_tech_technology_enterprise(self) -> float:
        score = 0.0
        descriptions: list[str] = []
        if self.company.is_srdi_little_giant or self.company.is_srdi_sme:
            score += 8.0
            descriptions.append("专精特新")
        if self.company.is_innovative_sme:
            score += 6.0
            descriptions.append("创新型企业")
        if self.company.is_high_tech_enterprise:
            score += 4.0
            descriptions.append("高新企业")
        score = min(score, 15.0)
        self._add_log("tech", score, f"科技型企业（科技）：{'、'.join(descriptions) if descriptions else '无'}，{score}分")
        return score

    def calculate_industry_university_research(self) -> float:
        text_pool = self._honor_text_pool()
        match_count = sum(1 for keyword in INDUSTRY_UNIVERSITY_RESEARCH_KEYWORDS if any(keyword in text for text in text_pool))
        score = min(match_count * 3.0, 15.0)
        self._add_log("tech", score, f"产学研合作：命中 {match_count} 类名单关键词，{score}分")
        return score

    def calculate_national_provincial_award(self) -> float:
        text_pool = self._honor_text_pool()
        if any("国家科学技术进步奖" in text and "特等奖" in text for text in text_pool):
            score = 10.0
        elif any("国家科学技术进步奖" in text and "一等奖" in text for text in text_pool):
            score = 8.0
        elif any("国家科学技术进步奖" in text and "二等奖" in text for text in text_pool):
            score = 7.0
        elif any("国家科学技术进步奖" in text and "三等奖" in text for text in text_pool):
            score = 6.0
        else:
            score = 0.0
        self._add_log("tech", score, f"国家/省级奖励：{'命中科技进步奖等级' if score else '未命中'}，{score}分")
        return score

    def calculate_national_tech_honor(self) -> float:
        text_pool = self._honor_text_pool()
        matched = next((keyword for keyword in NATIONAL_TECH_HONOR_KEYWORDS if any(keyword in text for text in text_pool)), "")
        score = 20.0 if matched else 0.0
        self._add_log("tech", score, f"科技荣誉（国家级）：{matched or '未命中'}，{score}分")
        return score

    def calculate_provincial_tech_honor(self) -> float:
        text_pool = self._honor_text_pool()
        matched = next((keyword for keyword in PROVINCIAL_TECH_HONOR_KEYWORDS if any(keyword in text for text in text_pool)), "")
        score = 15.0 if matched else 0.0
        self._add_log("tech", score, f"科技荣誉（省级）：{matched or '未命中'}，{score}分")
        return score

    def calculate_medical_ai_model_filing(self) -> float:
        matched = self.company.ai_model_filings[0] if self.company.ai_model_filings else ""
        text_pool = self._honor_text_pool() if not matched else []
        if not matched:
            matched = next((text for text in text_pool if _contains_any(text, MEDICAL_AI_MODEL_FILING_KEYWORDS)), "")
        score = 10.0 if matched else 0.0
        self._add_log("tech", score, f"算法备案的医疗大模型：{'命中' if matched else '未命中'}，{score}分")
        return score

    def calculate_high_quality_dataset(self) -> float:
        matched = self.company.high_quality_datasets[0] if self.company.high_quality_datasets else ""
        text_pool = self._honor_text_pool() if not matched else []
        if not matched:
            matched = next((text for text in text_pool if _contains_any(text, HIGH_QUALITY_DATASET_KEYWORDS)), "")
        score = 10.0 if matched else 0.0
        self._add_log("tech", score, f"高质量数据集：{'命中' if matched else '未命中'}，{score}分")
        return score

    def calculate_professional_score(self) -> float:
        items = [
            ("industry_market_size", "行业市场规模", self.calculate_industry_market_size),
            ("industry_heat", "行业热度", self.calculate_industry_heat),
            ("industry_profit_margin", "行业利润率", self.calculate_industry_profit_margin),
            ("qualification", "资质", self.calculate_qualification),
            ("certificates", "证书", self.calculate_certificates),
            ("innovation", "创新性", self.calculate_innovation),
            ("partnership_score", "合作上下游", self.calculate_partnership_score),
            ("ranking", "专业榜单入选", self.calculate_ranking_score),
        ]
        raw_score = 0.0
        scaled_score = 0.0
        for field_key, label, func in items:
            start_index = len(self.logs)
            raw = func()
            description = "；".join(log["description"] for log in self.logs[start_index:]) or f"{label}：{raw}分"
            raw_score += raw
            scaled_value = self._scale("pro", field_key, raw)
            scaled_score += scaled_value
            self._record_dimension(
                group="professional",
                field_key=field_key,
                name=label,
                raw_score=raw,
                scaled_score=scaled_value,
                description=description,
            )
        group_total = self._group_target_total("pro")
        final_score = max(round((scaled_score / group_total) * 100, 2), 0) if group_total else 0
        self._add_log("professional", final_score, f"专业模块：原始分 {round(raw_score, 2)}，加权分 {round(scaled_score, 2)} / {round(group_total, 2)}，归一后 {final_score} 分")
        return final_score

    def calculate_industry_market_size(self) -> float:
        return self._score_from_rules("professional", "行业市场规模", self._primary_industry(), INDUSTRY_MARKET_RULES, 3)

    def calculate_industry_heat(self) -> float:
        return self._score_from_rules("professional", "行业热度", self._primary_industry(), INDUSTRY_HEAT_RULES, 3)

    def calculate_industry_profit_margin(self) -> float:
        return self._score_from_rules("professional", "行业利润率", self._primary_industry(), INDUSTRY_PROFIT_RULES, 2)

    def calculate_qualification(self) -> float:
        score = 0.0
        for text in self.company.qualification_texts:
            upper_text = text.upper()
            is_certificate = (
                ("药品" in upper_text and "注册" in upper_text)
                or ("器械" in upper_text and "注册" in upper_text)
                or ("临床" in upper_text)
                or any(keyword in upper_text for keyword in ["受理", "在审", "原料", "辅料", "包材", "原辅包"])
                or ("器械" in upper_text and "产品" in upper_text and "备案" in upper_text)
            )
            if is_certificate:
                continue
            if "药品" in upper_text and "生产" in upper_text and "许可" in upper_text:
                score += 5.0
            elif "器械" in upper_text and "生产" in upper_text and "许可" in upper_text:
                score += 5.0
            elif "GMP" in upper_text:
                score += 5.0
            elif "深度合成" in upper_text and "算法" in upper_text:
                score += 5.0
            elif "实验动物" in upper_text or "病原微生物" in upper_text or "互联网药品信息" in upper_text or "网络信息服务备案" in upper_text:
                score += 3.0
            elif "辐射安全" in upper_text or "核辐射" in upper_text or ("器械" in upper_text and "经营" in upper_text) or ("电信" in upper_text and "许可" in upper_text) or "监控化学品" in upper_text or "中药提取物" in upper_text:
                score += 2.0
            elif ("器械" in upper_text and "生产" in upper_text and "备案" in upper_text) or "出口证书" in upper_text or "质量管理" in upper_text or "ISO9001" in upper_text or "环境管理" in upper_text or "ISO14001" in upper_text or "职业健康" in upper_text or "ISO45001" in upper_text:
                score += 1.0
            else:
                score += 0.5
        score = min(score, 20.0)
        self._add_log("professional", score, f"资质：有效资质文本 {len(self.company.qualification_texts)} 条，{score}分")
        return score

    def calculate_certificates(self) -> float:
        score = 0.0
        for text in self.company.qualification_texts:
            upper_text = text.upper()
            if ("药品" in upper_text and "注册" in upper_text) or ("器械" in upper_text and "注册" in upper_text):
                score += 10.0
                continue
            if "临床" in upper_text:
                score += 5.0
                continue
            if any(keyword in upper_text for keyword in ["受理", "在审", "原料", "辅料", "包材", "原辅包"]):
                score += 3.0
                continue
            if "器械" in upper_text and "产品" in upper_text and "备案" in upper_text:
                score += 1.0
                continue
        score = min(score, 20.0)
        self._add_log("professional", score, f"证书：有效证书文本 {len(self.company.qualification_texts)} 条，{score}分")
        return score

    def calculate_innovation(self) -> float:
        text_pool = self.company.innovation_texts or self._honor_text_pool()
        score = 0.0
        description = "未命中"
        for keywords, value, reason in INNOVATION_QUALIFICATION_RULES:
            if any(_contains_any(text, keywords) for text in text_pool):
                score = value
                description = reason
                break
        self._add_log("professional", score, f"创新性：{description}，{score}分")
        return score

    def calculate_partnership_score(self) -> float:
        raw_score = (len(self.company.customers) * 0.5) + (len(self.company.suppliers) * 0.5)
        score = min(raw_score, 10.0)
        self._add_log("professional", score, f"上下游合作：客户 {len(self.company.customers)} 个，供应商 {len(self.company.suppliers)} 个，{score}分")
        return score

    def calculate_ranking_score(self) -> float:
        raw_score = float(len(self.company.rankings))
        score = min(raw_score, 10.0)
        self._add_log("professional", score, f"专业榜单入选：{len(self.company.rankings)} 项，{score}分")
        return score


def _expand_industry_paths(paths: list[str]) -> set[str]:
    expanded: set[str] = set()
    for path in paths:
        parts = [part for part in path.split("/") if part]
        for index in range(1, len(parts) + 1):
            expanded.add("/".join(parts[:index]))
    return expanded


def run_full_scoring(status_callback=None) -> dict:
    close_old_connections()
    started_at = perf_counter()
    _set_status(status_callback, "running", "正在准备权重与企业数据")
    _ensure_weight_rows()
    weights = {
        "basic": ScoreModelBasicWeight.objects.order_by("model_id").first(),
        "tech": ScoreModelTechWeight.objects.order_by("model_id").first(),
        "pro": ScoreModelProfessionalWeight.objects.order_by("model_id").first(),
        "total": {row.model_name: float(row.model_weight) for row in ScoreModelTotalWeight.objects.all()},
    }

    _set_status(status_callback, "running", "正在加载企业源数据")
    companies = _load_company_data()
    result_rows: list[ScoreResult] = []
    log_rows: list[ScoreLog] = []
    industry_stats: dict[str, dict] = defaultdict(lambda: {"sum": 0.0, "company_ids": set()})
    now = timezone.now()

    _set_status(status_callback, "running", f"正在计算 {len(companies)} 家企业评分")
    for company in companies.values():
        scorer = CompanyScorer(company, weights)
        result = scorer.calculate_all()
        result_rows.append(
            ScoreResult(
                enterprise_id=result["enterprise_id"],
                company_name=result["company_name"],
                total_score=result["total_score"],
                basic_score=result["basic_score"],
                tech_score=result["tech_score"],
                professional_score=result["professional_score"],
                created_at=now,
                updated_at=now,
            )
        )
        for log in result["logs"]:
            log_rows.append(
                ScoreLog(
                    enterprise_id=result["enterprise_id"],
                    enterprise_name=result["company_name"],
                    score_type=log["score_type"],
                    score_value=log["score_value"],
                    description=log["description"],
                    created_at=now,
                )
            )
        for path in _expand_industry_paths(result["industry_paths"]):
            industry_stats[path]["sum"] += float(result["total_score"])
            industry_stats[path]["company_ids"].add(result["enterprise_id"])

    _set_status(status_callback, "running", "正在回写评分结果与行业聚合")
    industry_rows = []
    for path, stats in industry_stats.items():
        company_count = len(stats["company_ids"])
        avg_score = round(stats["sum"] / company_count, 2) if company_count else 0
        industry_rows.append(
            ScoreIndustryPath(
                industry_path=path,
                path_level=path.count("/") + 1,
                avg_score=avg_score,
                company_count=company_count,
            )
        )

    with transaction.atomic():
        ScoreLog.objects.all().delete()
        ScoreResult.objects.all().delete()
        ScoreIndustryPath.objects.all().delete()
        ScoreResult.objects.bulk_create(result_rows, batch_size=500)
        ScoreLog.objects.bulk_create(log_rows, batch_size=1000)
        ScoreIndustryPath.objects.bulk_create(sorted(industry_rows, key=lambda row: (row.path_level or 0, row.industry_path)), batch_size=500)

    duration = round(perf_counter() - started_at, 2)
    close_old_connections()
    return {
        "company_count": len(result_rows),
        "log_count": len(log_rows),
        "industry_count": len(industry_rows),
        "duration_seconds": duration,
    }
