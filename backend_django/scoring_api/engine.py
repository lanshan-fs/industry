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
    "基因技术",
    "生物",
    "生物技术",
    "诊断",
    "体外诊断",
    "IVD",
    "可穿戴",
    "医学影像",
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
TECH_WEIGHT_MODEL_FIELDS = {field.name for field in ScoreModelTechWeight._meta.local_fields}


@dataclass
class PatentRecord:
    patent_number: str = ""
    patent_name: str = ""
    tech_attribute_label: str = ""
    patent_types: list[str] = field(default_factory=list)


@dataclass
class CompanySnapshot:
    credit_code: str
    company_name: str
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


def _contains_all(text: str, keywords: list[str]) -> bool:
    normalized = _normalize_text(text).upper()
    return all(keyword.upper() in normalized for keyword in keywords)


def _parse_amount_to_wan(value) -> float | None:
    if value is None or value == "":
        return None
    match = re.search(r"(\d+\.?\d*)", str(value))
    if not match:
        return None
    return float(match.group(1))


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
        ScoreModelTechWeight.objects.create(
            model_name="科技指标模型",
            **{field: value for field, value in TECH_DEFAULT_VALUES.items() if field in TECH_WEIGHT_MODEL_FIELDS},
        )
    elif all(float(getattr(tech_row, field, 0) or 0) == 0 for field in TECH_DEFAULT_VALUES):
        supported_fields = [field for field in TECH_DEFAULT_VALUES if field in TECH_WEIGHT_MODEL_FIELDS]
        for field in supported_fields:
            value = TECH_DEFAULT_VALUES[field]
            setattr(tech_row, field, value)
        tech_row.save(update_fields=supported_fields)
    else:
        missing_fields = [
            field
            for field, value in TECH_DEFAULT_VALUES.items()
            if field in TECH_WEIGHT_MODEL_FIELDS and float(getattr(tech_row, field, 0) or 0) == 0 and value > 0
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


def _in_clause(ids: list[str]) -> tuple[str, list[str]]:
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


def _load_company_data(credit_codes: list[str] | None = None) -> dict[str, CompanySnapshot]:
    where_clause = ""
    params: list[str] = []
    if credit_codes:
        in_clause, params = _in_clause(credit_codes)
        where_clause = f"WHERE credit_code IN {in_clause}"
    company_rows = _fetch_rows(
        f"""
        SELECT
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
        ORDER BY credit_code
        """,
        params,
    )
    companies: dict[str, CompanySnapshot] = {}
    for row in company_rows:
        credit_code = _normalize_text(row["credit_code"])
        companies[credit_code] = CompanySnapshot(
            credit_code=credit_code,
            company_name=_normalize_text(row["company_name"]),
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
          p.credit_code,
          p.company_patent_number,
          p.company_patent_name,
          COALESCE(p.tech_attribute_label, '') AS tech_attribute_label,
          GROUP_CONCAT(DISTINCT t.company_patent_type_name ORDER BY t.company_patent_type_name SEPARATOR '|') AS patent_types
        FROM company_patent p
        LEFT JOIN company_patent_patent_type_map m ON m.company_patent_id = p.company_patent_id
        LEFT JOIN company_patent_type t ON t.company_patent_type_id = m.company_patent_type_id
        WHERE p.credit_code IN {in_clause}
        GROUP BY p.company_patent_id, p.credit_code, p.company_patent_number, p.company_patent_name, p.tech_attribute_label
        """,
        in_params,
    )
    for row in patent_rows:
        company = companies.get(_normalize_text(row["credit_code"]))
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
        SELECT credit_code, company_software_copyright_name, company_software_copyright_for_short
        FROM company_software_copyright
        WHERE credit_code IN {in_clause}
        """,
        in_params,
    )
    for row in software_rows:
        company = companies.get(_normalize_text(row["credit_code"]))
        if not company:
            continue
        texts = [
            _normalize_text(row["company_software_copyright_name"]),
            _normalize_text(row["company_software_copyright_for_short"]),
        ]
        company.software_names.extend([text for text in texts if text])

    qualification_rows = _fetch_rows(
        f"""
        SELECT credit_code, qualification_name, qualification_type
        FROM company_qualification
        WHERE credit_code IN {in_clause}
        """,
        in_params,
    )
    for row in qualification_rows:
        company = companies.get(_normalize_text(row["credit_code"]))
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
            SELECT credit_code, model_name, filing_no, filing_type, territory
            FROM company_ai_model_filing
            WHERE credit_code IN {in_clause}
            """,
            in_params,
        ):
            company = companies.get(_normalize_text(row["credit_code"]))
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
            SELECT credit_code, dataset_name, applicant_unit_raw, recommender_unit
            FROM company_high_quality_dataset
            WHERE credit_code IN {in_clause}
            """,
            in_params,
        ):
            company = companies.get(_normalize_text(row["credit_code"]))
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
            SELECT credit_code, notice_type, notice_title, notice_category, product_name, reg_no, acceptance_no, owner_name
            FROM company_innovation_notice
            WHERE credit_code IN {in_clause}
            """,
            in_params,
        ):
            company = companies.get(_normalize_text(row["credit_code"]))
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
        f"SELECT credit_code, company_customer_name FROM company_customer WHERE company_customer_name IS NOT NULL AND credit_code IN {in_clause}",
        in_params,
    ):
        company = companies.get(_normalize_text(row["credit_code"]))
        if company:
            company.customers.append(_normalize_text(row["company_customer_name"]))

    for row in _fetch_rows(
        f"SELECT credit_code, company_supplier_name FROM company_supplier WHERE company_supplier_name IS NOT NULL AND credit_code IN {in_clause}",
        in_params,
    ):
        company = companies.get(_normalize_text(row["credit_code"]))
        if company:
            company.suppliers.append(_normalize_text(row["company_supplier_name"]))

    for row in _fetch_rows(
        f"SELECT credit_code, company_ranking_name FROM company_ranking WHERE company_ranking_name IS NOT NULL AND credit_code IN {in_clause}",
        in_params,
    ):
        company = companies.get(_normalize_text(row["credit_code"]))
        if company:
            company.rankings.append(_normalize_text(row["company_ranking_name"]))

    for row in _fetch_rows(
        f"SELECT credit_code, company_risk_category_name, company_risk_category_count FROM company_risk WHERE credit_code IN {in_clause}",
        in_params,
    ):
        company = companies.get(_normalize_text(row["credit_code"]))
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
        f"SELECT credit_code, category_id FROM category_industry_company_map WHERE credit_code IN {in_clause}",
        in_params,
    ):
        company = companies.get(_normalize_text(row["credit_code"]))
        if company and row["category_id"] in category_by_id:
            company.industries.append(build_path(row["category_id"]))

    for company in companies.values():
        company.industries = sorted(set([path for path in company.industries if path]), key=lambda item: (item.count("/"), item))
        company.customers = [name for name in company.customers if name]
        company.suppliers = [name for name in company.suppliers if name]
        company.rankings = [name for name in company.rankings if name]

    return companies


def get_company_scoring_snapshot(credit_code: str) -> dict | None:
    weights = _load_weights()
    companies = _load_company_data([credit_code])
    company = companies.get(credit_code)
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
        self.breakdown = {"basic": [], "tech": [], "professional": [], "bonus": []}

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

    def _fym_industry_categories(self) -> list[str]:
        categories: list[str] = []
        for industry in self.company.industries:
            normalized = _normalize_text(industry)
            if not normalized:
                continue
            if any(keyword in normalized for keyword in ["医药商业 / 流通", "医疗零售"]):
                categories.append("医药流通/零售")
            if any(keyword in normalized for keyword in ["高值医用耗材", "植入器械/材料"]):
                categories.append("医疗器械（高值耗材）")
            if any(
                keyword in normalized
                for keyword in ["影像设备", "治疗设备", "生命信息支持设备", "康复设备", "辅助设备", "家用医疗设备", "装备制造"]
            ):
                categories.append("医疗器械（设备）")
            if any(keyword in normalized for keyword in ["智慧医疗", "互联网+健康", "数字疗法", "互联网医疗"]):
                categories.append("数字医疗/医疗信息化")
            if any(keyword in normalized for keyword in ["前沿技术融合", "AI 药物研发平台", "AI CRO / 技术服务商", "AI 自研管线企业", "AI 软件 / 工具平台"]):
                categories.append("医疗AI")
            if "中药" in normalized:
                categories.append("中药")
            if "化学制药" in normalized:
                categories.append("创新药/生物技术")
            if "生物制品" in normalized:
                categories.append("创新药/生物技术")
            if any(keyword in normalized for keyword in ["严肃医疗", "消费医疗"]):
                categories.append("医疗服务（民营医院）")
            if "第三方中心" in normalized:
                categories.append("医疗服务（第三方医学检验）")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in categories or ["其他"]:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    def _qualification_label(self, text: str) -> str:
        upper_text = _normalize_text(text).upper()
        if not upper_text:
            return "其他"
        rules = [
            (["药品", "生产", "许可"], "药品生产许可证"),
            (["器械", "生产", "许可"], "医疗器械生产许可证"),
            (["GMP"], "GMP认证"),
            (["深度合成", "算法"], "深度合成服务算法备案"),
            (["实验动物"], "实验动物许可"),
            (["病原微生物"], "病原微生物实验室备案"),
            (["互联网药品信息服务"], "互联网药品信息服务资格证书"),
            (["药品医疗器械网络信息服务"], "药品医疗器械网络信息服务备案"),
            (["网络信息服务", "备案"], "药品医疗器械网络信息服务备案"),
            (["辐射安全"], "辐射安全许可证"),
            (["核辐射"], "核辐射利用安全许可证"),
            (["器械", "经营", "许可"], "医疗器械经营许可证"),
            (["电信", "许可"], "电信许可"),
            (["监控化学品"], "第二类监控化学品使用许可证"),
            (["中药提取物"], "中药提取物备案公示"),
            (["器械", "生产", "备案"], "医疗器械生产备案凭证"),
            (["出口证书"], "出口证书"),
            (["质量管理"], "质量管理体系认证"),
            (["ISO9001"], "质量管理体系认证"),
            (["环境管理"], "环境管理体系认证"),
            (["ISO14001"], "环境管理体系认证"),
            (["职业健康"], "职业健康安全管理体系认证"),
            (["ISO45001"], "职业健康安全管理体系认证"),
        ]
        for keywords, label in rules:
            if _contains_all(upper_text, keywords):
                return label
        return "其他"

    def _certificate_label(self, text: str) -> str:
        upper_text = _normalize_text(text).upper()
        if not upper_text:
            return "其他"
        if "药品" in upper_text and "注册" in upper_text:
            return "药品注册证"
        if "器械" in upper_text and "注册" in upper_text:
            return "器械注册证"
        if "临床" in upper_text:
            return "临床批件"
        if "受理公示" in upper_text:
            return "受理公示"
        if "在审公示" in upper_text:
            return "在审公示"
        if "受理" in upper_text and "品种" in upper_text:
            return "受理品种"
        if "在审" in upper_text and "品种" in upper_text:
            return "在审品种"
        if "原辅包" in upper_text and "登记" in upper_text:
            return "原辅包登记"
        if "原料" in upper_text:
            return "原料"
        if "辅料" in upper_text:
            return "辅料"
        if "包材" in upper_text:
            return "包材"
        if "医疗器械产品备案" in upper_text or ("器械" in upper_text and "产品" in upper_text and "备案" in upper_text):
            return "医疗器械产品备案"
        return "其他"

    def calculate_all(self) -> dict:
        basic_score = self.calculate_basic_score()
        tech_score = self.calculate_tech_score()
        professional_score = self.calculate_professional_score()
        bonus_score = self.calculate_bonus_score()
        total_score = basic_score + tech_score + professional_score + bonus_score

        return {
            "enterprise_credit_code": self.company.credit_code,
            "company_name": self.company.company_name,
            "basic_score": round(max(basic_score, 0), 2),
            "tech_score": round(max(tech_score, 0), 2),
            "professional_score": round(max(professional_score, 0), 2),
            "bonus_score": round(max(bonus_score, 0), 2),
            "total_score": round(max(total_score, 0), 2),
            "logs": self.logs,
            "breakdown": self.breakdown,
            "industry_paths": self.company.industries,
        }

    def calculate_basic_score(self) -> float:
        score = 0.0
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
            scaled_value = self._scale("basic", field_key, raw)
            score += scaled_value
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
        score += risk_penalty
        risk_description = "；".join(log["description"] for log in self.logs[risk_start:]) or "风险扣分：0分"
        self._record_dimension(
            group="basic",
            field_key="risk_penalties",
            name="风险扣分",
            raw_score=risk_penalty,
            scaled_score=risk_penalty,
            description=risk_description,
        )
        final_score = max(round(score, 2), 0)
        self._add_log("basic", final_score, f"基础模块计算完毕：累加分 {final_score}")
        return final_score

    def calculate_website(self) -> float:
        if self.company.website:
            self._add_log("basic", 2.0, "网址：有网址，2分")
            return 2.0
        self._add_log("basic", 0.0, "网址：无网址，0分")
        return 0.0

    def calculate_established_year(self) -> float:
        years = _years_since(self.company.establish_date)
        if years is None:
            score = 1.0
            self._add_log("basic", score, "成立年限：未提供，基础分1分")
            return score
        if years <= 1:
            score = 1.0
        elif years <= 5:
            score = 3.0
        elif years <= 10:
            score = 4.0
        else:
            score = 5.0
        self._add_log("basic", score, f"成立年限：{years}年，{score}分")
        return score

    def calculate_registered_capital(self) -> float:
        capital = _parse_amount_to_wan(self.company.register_capital)
        if capital is None:
            score = 2.0
            self._add_log("basic", score, "注册资本：未提供，基础分2分")
            return score
        if capital <= 100:
            score = 2.0
        elif capital <= 200:
            score = 3.0
        elif capital <= 500:
            score = 4.0
        elif capital <= 1000:
            score = 5.0
        else:
            score = 6.0
        self._add_log("basic", score, f"注册资本：{capital}万元，{score}分")
        return score

    def calculate_actual_paid_capital(self) -> float:
        capital = _parse_amount_to_wan(self.company.paid_capital)
        if capital is None:
            score = 1.0
            self._add_log("basic", score, "实缴资本：未提供，基础分1分")
            return score
        if capital == 0:
            score = 1.0
        elif capital <= 100:
            score = 3.0
        elif capital <= 500:
            score = 6.0
        else:
            score = 8.0
        self._add_log("basic", score, f"实缴资本：{capital}万元，{score}分")
        return score

    def calculate_company_type(self) -> float:
        company_type = _normalize_text(self.company.company_type)
        if not company_type:
            score = 1.0
        elif any(keyword in company_type for keyword in ["央企", "上市", "国有控股"]):
            score = 7.0
        elif any(keyword in company_type for keyword in ["国有", "股份有限"]):
            score = 5.0
        elif any(keyword in company_type for keyword in ["有限", "外商", "合资", "港澳台"]):
            score = 4.0
        elif any(keyword in company_type for keyword in ["自然人投资", "股份合作", "控股"]):
            score = 3.0
        elif any(keyword in company_type for keyword in ["个人独资", "自然人独资", "合伙", "个体工商户"]):
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
        if self.company.insured_count is None:
            self._add_log("basic", 0.0, "社保人数：未提供，0分")
            return 0.0
        count = int(self.company.insured_count or 0)
        if count <= 0:
            self._add_log("basic", 0.0, "社保人数：0人，0分")
            return 0.0
        if count >= 500:
            score = 6.0
        elif count >= 100:
            score = 5.0
        elif count >= 50:
            score = 4.0
        elif count >= 30:
            score = 3.0
        else:
            score = 2.0
        self._add_log("basic", score, f"社保人数：{count}人，{score}分")
        return score

    def calculate_business_scope(self) -> float:
        scope = _normalize_text(self.company.business_scope)
        if not scope:
            self._add_log("basic", 1.0, "经营范围：未提供，基础分1分")
            return 1.0

        score_rules = [
            (["第三类", "III类", "Ⅲ类", "三类"], ["生产", "制造", "加工"], 5.0, "3类生产"),
            (["第二类", "II类", "Ⅱ类", "二类"], ["生产", "制造", "加工"], 4.0, "二类生产"),
            (["第三类", "III类", "Ⅲ类", "三类"], ["销售", "经营"], 3.0, "3类销售/经营"),
            (["第二类", "II类", "Ⅱ类", "二类"], ["销售", "经营"], 2.0, "二类销售/经营"),
            (["第一类", "I类", "Ⅰ类", "一类"], ["销售", "经营"], 1.0, "一类销售/经营"),
        ]
        main_items = [item.strip() for item in scope.split("；") if item.strip()]
        all_items: list[str] = []
        for item in main_items:
            item_clean = re.sub(r"（[^）]*）", "", item)
            item_clean = re.sub(r"\([^)]*\)", "", item_clean)
            all_items.extend([sub.strip() for sub in item_clean.split("、") if sub.strip()])

        highest_score = 1.0
        highest_desc = "无有效类别，1分"
        for item in all_items:
            for keywords, biz_types, item_score, desc in score_rules:
                if any(keyword in item for keyword in keywords) and any(biz_type in item for biz_type in biz_types):
                    if item_score > highest_score:
                        highest_score = item_score
                        highest_desc = f"{item}（{desc}），{item_score}分"
                    break

        self._add_log("basic", highest_score, f"经营范围：{highest_desc}")
        return highest_score

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
        round_text = _normalize_text(self.company.financing_round)
        if not round_text or round_text == "无投融资信息":
            score = 1.0
        elif any(keyword in round_text for keyword in ["天使轮", "A轮", "a轮", "PreA", "Pre-A", "prea", "种子轮"]):
            score = 4.0
        elif any(keyword in round_text for keyword in ["B轮", "b轮", "股权融资", "并购融资", "战略融资", "融资"]):
            score = 5.0
        elif any(keyword in round_text for keyword in ["C轮", "c轮", "战略投资"]):
            score = 6.0
        elif any(keyword in round_text for keyword in ["D轮", "d轮", "E轮", "e轮"]):
            score = 8.0
        elif any(keyword in round_text for keyword in ["IPO", "ipo", "上市"]):
            score = 10.0
        else:
            score = 1.0
        self._add_log("basic", score, f"投融资轮次：{round_text or '未融资'}，{score}分")
        return score

    def calculate_patent_type(self) -> float:
        score = 0.0
        patent_count = 0
        for patent in self.company.patents:
            patent_count += 1
            patent_types = patent.patent_types
            patent_number = patent.patent_number.upper()
            patent_text = "|".join(patent_types)
            if "PCT" in patent_number or "PCT" in patent_text:
                score += 4.0
            elif "发明授权" in patent_types:
                score += 2.0
            elif "发明公开" in patent_types:
                score += 1.0
            elif (
                any("实质审查" in patent_type for patent_type in patent_types)
                or "实用新型" in patent_types
                or "外观设计" in patent_types
                or any("商标" in patent_type for patent_type in patent_types)
            ):
                score += 0.5
        score = min(score, 15.0)
        self._add_log("basic", score, f"专利类型：{patent_count}项专利，{score}分")
        return score

    def calculate_software_copyright(self) -> float:
        count = len(self.company.software_names)
        score = min(float(count), 15.0)
        self._add_log("basic", score, f"软件著作权：{count}项，{score}分")
        return score

    def calculate_technology_enterprise(self) -> float:
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
        final_score = min(score, 10.0) if score else 1.0
        if not descriptions:
            descriptions.append("无")
        self._add_log("basic", final_score, f"科技型企业：{'、'.join(descriptions) if descriptions else '无'}，{final_score}分")
        return final_score

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
        ]
        score = 0.0
        for field_key, label, func in items:
            start_index = len(self.logs)
            raw = func()
            description = "；".join(log["description"] for log in self.logs[start_index:]) or f"{label}：{raw}分"
            scaled_value = self._scale("tech", field_key, raw)
            score += scaled_value
            self._record_dimension(
                group="tech",
                field_key=field_key,
                name=label,
                raw_score=raw,
                scaled_score=scaled_value,
                description=description,
            )
        final_score = round(score, 2)
        self._add_log("tech", final_score, f"科技模块计算完毕：累加分 {final_score}")
        return final_score

    def calculate_bonus_score(self) -> float:
        score = 0.0
        details: list[tuple[str, float, str]] = []
        if self.company.ai_model_filings:
            score += 10.0
            details.append(("medical_ai_model_filing", 10.0, "附加分：有算法备案的医疗大模型，加10分"))
        if self.company.high_quality_datasets:
            score += 10.0
            details.append(("high_quality_dataset", 10.0, "附加分：有高质量数据集，加10分"))
        text_pool = self._honor_text_pool()
        if any(keyword in text for text in text_pool for keyword in NATIONAL_TECH_HONOR_KEYWORDS):
            score += 20.0
            details.append(("national_tech_honor", 20.0, "附加分：科技荣誉（国家级），加20分"))
        if any(keyword in text for text in text_pool for keyword in PROVINCIAL_TECH_HONOR_KEYWORDS):
            score += 15.0
            details.append(("provincial_tech_honor", 15.0, "附加分：科技荣誉（省级），加15分"))

        label_map = {
            "national_tech_honor": "科技荣誉（国家级）",
            "provincial_tech_honor": "科技荣誉（省级）",
            "medical_ai_model_filing": "算法备案的医疗大模型",
            "high_quality_dataset": "高质量数据集",
        }
        recorded_keys = set()
        for field_key, raw_score, description in details:
            recorded_keys.add(field_key)
            self._add_log("bonus", raw_score, description)
            self._record_dimension(
                group="bonus",
                field_key=field_key,
                name=label_map[field_key],
                raw_score=raw_score,
                scaled_score=raw_score,
                description=description,
            )
        for field_key, name in label_map.items():
            if field_key in recorded_keys:
                continue
            description = f"附加分：{name}未命中，0分"
            self._add_log("bonus", 0.0, description)
            self._record_dimension(
                group="bonus",
                field_key=field_key,
                name=name,
                raw_score=0.0,
                scaled_score=0.0,
                description=description,
            )
        final_score = round(score, 2)
        self._add_log("bonus", final_score, f"附加分计算完毕：累加分 {final_score}")
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
        self._add_log("tech", 15.0, "产学研合作，先赋予15分")
        return 15.0

    def calculate_national_provincial_award(self) -> float:
        self._add_log("tech", 10.0, "国家/省级奖励，先赋予10分")
        return 10.0

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
        score = 0.0
        for field_key, label, func in items:
            start_index = len(self.logs)
            raw = func()
            description = "；".join(log["description"] for log in self.logs[start_index:]) or f"{label}：{raw}分"
            scaled_value = self._scale("pro", field_key, raw)
            score += scaled_value
            self._record_dimension(
                group="professional",
                field_key=field_key,
                name=label,
                raw_score=raw,
                scaled_score=scaled_value,
                description=description,
            )
        final_score = max(score, 0)
        self._add_log("professional", final_score, f"专业能力模块计算完毕：累加分 {round(final_score, 2)}")
        return final_score

    def calculate_industry_market_size(self) -> float:
        categories = self._fym_industry_categories()
        scoring_rules = [
            (["医药流通/零售"], 10.0, "医药流通/零售"),
            (["CXO", "医疗器械（高值耗材）"], 8.0, "CXO、医疗器械（高值耗材）"),
            (["创新药/生物技术", "医疗器械（设备）", "医疗服务（民营医院）"], 7.0, "创新药/生物技术、医疗器械（设备）、医疗服务（民营医院）"),
            (["数字医疗/医疗信息化", "中药", "生物制品（疫苗）", "医疗服务（第三方医学检验）"], 6.0, "数字医疗/医疗信息化、中药、生物制品（疫苗）、医疗服务（第三方医学检验）"),
            (["化学原料药", "生物制品（血制品）"], 5.0, "化学原料药、生物制品（血制品）"),
            (["医疗AI"], 4.0, "医疗AI"),
            (["其他"], 3.0, "其他"),
        ]
        max_score = 3.0
        best_category = "其他"
        best_reason = "其他"
        matched_details: list[str] = []
        for category in categories:
            matched = False
            for rule_categories, item_score, reason in scoring_rules:
                if category in rule_categories:
                    matched = True
                    matched_details.append(f"{category} -> {item_score}分")
                    if item_score > max_score:
                        max_score = item_score
                        best_category = category
                        best_reason = reason
                    break
            if not matched:
                matched_details.append(f"{category} -> 未匹配规则")
        self._add_log("professional", max_score, f"行业市场规模：分类={categories} -> 匹配详情={matched_details} -> 最终：{best_category} -> {best_reason}，{max_score}分")
        return max_score

    def calculate_industry_heat(self) -> float:
        categories = self._fym_industry_categories()
        scoring_rules = [
            (["创新药/生物技术", "医疗AI"], 9.0, "创新药/生物技术、医疗AI"),
            (["数字医疗/医疗信息化"], 8.0, "数字医疗/医疗信息化"),
            (["医疗器械（高值耗材）"], 7.0, "医疗器械（高值耗材）"),
            (["CXO", "医疗器械（设备）"], 6.0, "CXO、医疗器械（设备）"),
            (["中药", "生物制品（疫苗）", "医疗服务（民营医院）"], 5.0, "中药、生物制品（疫苗）、医疗服务（民营医院）"),
            (["化学原料药", "生物制品（血制品）", "医疗服务（第三方医学检验）", "医药流通/零售"], 4.0, "化学原料药、生物制品（血制品）、医疗服务（第三方医学检验）、医药流通/零售"),
            (["其他"], 3.0, "其他"),
        ]
        max_score = 3.0
        best_category = "其他"
        best_reason = "其他"
        matched_details: list[str] = []
        for category in categories:
            matched = False
            for rule_categories, item_score, reason in scoring_rules:
                if category in rule_categories:
                    matched = True
                    adjusted_score = item_score + 1.0
                    matched_details.append(f"{category} -> {adjusted_score}分")
                    if adjusted_score > max_score:
                        max_score = adjusted_score
                        best_category = category
                        best_reason = reason
                    break
            if not matched:
                matched_details.append(f"{category} -> 未匹配规则")
        self._add_log("professional", max_score, f"行业热度：分类={categories} -> 匹配详情={matched_details} -> 最终：{best_category} -> {best_reason}，{max_score}分")
        return max_score

    def calculate_industry_profit_margin(self) -> float:
        categories = self._fym_industry_categories()
        scoring_rules = [
            (["生物制品（血制品）"], 9.0, "生物制品（血制品）"),
            (["医疗器械（高值耗材）", "生物制品（疫苗）", "中药"], 8.0, "医疗器械（高值耗材）、生物制品（疫苗）、中药"),
            (["CXO", "医疗器械（设备）"], 7.0, "CXO、医疗器械（设备）"),
            (["医疗服务（民营医院）"], 6.0, "医疗服务（民营医院）"),
            (["创新药/生物技术", "化学原料药", "医疗服务（第三方医学检验）"], 5.0, "创新药/生物技术、化学原料药、医疗服务（第三方医学检验）"),
            (["数字医疗/医疗信息化"], 4.0, "数字医疗/医疗信息化"),
            (["医疗AI", "医药流通/零售"], 3.0, "医疗AI、医药流通/零售"),
            (["其他"], 2.0, "其他"),
        ]
        max_score = 2.0
        best_category = "其他"
        best_reason = "其他"
        matched_details: list[str] = []
        for category in categories:
            matched = False
            for rule_categories, item_score, reason in scoring_rules:
                if category in rule_categories:
                    matched = True
                    adjusted_score = item_score + 1.0
                    matched_details.append(f"{category} -> {adjusted_score}分")
                    if adjusted_score > max_score:
                        max_score = adjusted_score
                        best_category = category
                        best_reason = reason
                    break
            if not matched:
                matched_details.append(f"{category} -> 未匹配规则")
        self._add_log("professional", max_score, f"行业利润率：分类={categories} -> 匹配详情={matched_details} -> 最终：{best_category} -> {best_reason}，{max_score}分")
        return max_score

    def calculate_qualification(self) -> float:
        score = 0.0
        label_scores = {
            "药品生产许可证": 5.0,
            "医疗器械生产许可证": 5.0,
            "GMP认证": 5.0,
            "深度合成服务算法备案": 5.0,
            "实验动物许可": 3.0,
            "病原微生物实验室备案": 3.0,
            "互联网药品信息服务资格证书": 3.0,
            "药品医疗器械网络信息服务备案": 3.0,
            "辐射安全许可证": 2.0,
            "核辐射利用安全许可证": 2.0,
            "医疗器械经营许可证": 2.0,
            "电信许可": 2.0,
            "第二类监控化学品使用许可证": 2.0,
            "中药提取物备案公示": 2.0,
            "医疗器械生产备案凭证": 1.0,
            "出口证书": 1.0,
            "质量管理体系认证": 1.0,
            "环境管理体系认证": 1.0,
            "职业健康安全管理体系认证": 1.0,
            "其他": 0.5,
        }
        for text in self._all_qualification_texts():
            score += label_scores.get(self._qualification_label(text), 0.5)
        score = min(score, 20.0)
        self._add_log("professional", score, f"资质得分：{score}")
        return score

    def calculate_certificates(self) -> float:
        score = 0.0
        label_scores = {
            "药品注册证": 10.0,
            "器械注册证": 10.0,
            "临床批件": 5.0,
            "受理品种": 3.0,
            "在审品种": 3.0,
            "在审公示": 3.0,
            "受理公示": 3.0,
            "原料": 3.0,
            "辅料": 3.0,
            "包材": 3.0,
            "原辅包登记": 3.0,
            "医疗器械产品备案": 1.0,
            "其他": 0.0,
        }
        for text in self._all_qualification_texts():
            score += label_scores.get(self._certificate_label(text), 0.0)
        score = min(score, 20.0)
        self._add_log("professional", score, f"证书得分：{score}")
        return score

    def calculate_innovation(self) -> float:
        score = 0.0
        text_pool = self.company.innovation_texts or self._honor_text_pool()
        if any(_contains_any(text, ["国家创新医疗器械", "国家级创新医疗器械"]) for text in text_pool):
            score += 10.0
        if any(_contains_any(text, ["北京市创新医疗器械", "北京创新医疗器械"]) for text in text_pool):
            score += 7.0
        if any(_contains_any(text, ["药物纳入优先审评品种名单", "药物拟纳入优先审评品种名单", "拟纳入优先审评"]) for text in text_pool):
            score += 7.0
        if any("主文档" in text for text in text_pool):
            score += 5.0
        score = min(score, 10.0)
        self._add_log("professional", score, f"创新性得分：{score}")
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
    industry_stats: dict[str, dict] = defaultdict(lambda: {"sum": 0.0, "credit_codes": set()})
    now = timezone.now()

    _set_status(status_callback, "running", f"正在计算 {len(companies)} 家企业评分")
    for company in companies.values():
        scorer = CompanyScorer(company, weights)
        result = scorer.calculate_all()
        result_rows.append(
            ScoreResult(
                enterprise_credit_code=result["enterprise_credit_code"],
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
                    enterprise_credit_code=result["enterprise_credit_code"],
                    enterprise_name=result["company_name"],
                    score_type=log["score_type"],
                    score_value=log["score_value"],
                    description=log["description"],
                    created_at=now,
                )
            )
        for path in _expand_industry_paths(result["industry_paths"]):
            industry_stats[path]["sum"] += float(result["total_score"])
            industry_stats[path]["credit_codes"].add(result["enterprise_credit_code"])

    _set_status(status_callback, "running", "正在回写评分结果与行业聚合")
    industry_rows = []
    for path, stats in industry_stats.items():
        company_count = len(stats["credit_codes"])
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
