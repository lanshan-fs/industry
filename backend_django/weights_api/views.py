from __future__ import annotations

import json
import threading
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from auth_api.views import _admin_user, _json_body, _json_error, _write_operation_log
from scoring_api.engine import run_full_scoring

from .models import (
    ScoreModelBasicWeight,
    ScoreModelProfessionalWeight,
    ScoreModelTechWeight,
    ScoreModelTotalWeight,
)


SCORING_STATUS = {"status": "idle", "message": ""}

TOTAL_DEFAULTS = [
    ("基础指标", Decimal("33.34")),
    ("科技指标", Decimal("33.33")),
    ("专业指标", Decimal("33.33")),
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
BASIC_FIELDS = [
    ("established_year", "成立年限"),
    ("registered_capital", "注册资本"),
    ("actual_paid_capital", "实缴资本"),
    ("company_type", "公司类型"),
    ("enterprise_size_type", "企业规模"),
    ("social_security_count", "社保人数"),
    ("website", "网址"),
    ("business_scope", "经营范围"),
    ("tax_rating", "纳税人等级"),
    ("tax_type", "纳税人类型"),
    ("funding_round", "投融资轮次"),
    ("patent_type", "专利类型"),
    ("software_copyright", "软件著作权"),
    ("technology_enterprise", "科技型企业"),
]
TECH_FIELDS = [
    ("tech_patent_type", "专利类型"),
    ("patent_tech_attribute", "专利科技属性"),
    ("tech_software_copyright", "软件著作权"),
    ("software_copyright_tech_attribute", "软著科技属性"),
    ("tech_technology_enterprise", "科技型企业"),
    ("industry_university_research", "产学研合作"),
    ("national_provincial_award", "国家/省级奖励"),
]
PROFESSIONAL_FIELDS = [
    ("industry_market_size", "行业市场规模"),
    ("industry_heat", "行业热度"),
    ("industry_profit_margin", "行业利润率"),
    ("qualification", "资质"),
    ("certificates", "证书"),
    ("innovation", "创新性"),
    ("partnership_score", "合作上下游"),
    ("ranking", "专业榜单入选"),
]


def _to_float(value) -> float:
    return float(value or 0)


def _set_scoring_status(status: str, message: str):
    SCORING_STATUS["status"] = status
    SCORING_STATUS["message"] = message


def _ensure_seed_rows():
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

    pro_row = ScoreModelProfessionalWeight.objects.order_by("model_id").first()
    if not pro_row:
        ScoreModelProfessionalWeight.objects.create(model_name="专业指标模型", **PRO_DEFAULT_VALUES)
    elif all(float(getattr(pro_row, field) or 0) == 0 for field in PRO_DEFAULT_VALUES):
        for field, value in PRO_DEFAULT_VALUES.items():
            setattr(pro_row, field, value)
        pro_row.save(update_fields=list(PRO_DEFAULT_VALUES.keys()))


def _weights_payload():
    _ensure_seed_rows()
    total_rows = ScoreModelTotalWeight.objects.order_by("model_id")
    basic_row = ScoreModelBasicWeight.objects.order_by("model_id").first()
    tech_row = ScoreModelTechWeight.objects.order_by("model_id").first()
    professional_row = ScoreModelProfessionalWeight.objects.order_by("model_id").first()

    return {
        "total": [
            {"key": str(row.model_id), "name": row.model_name, "weight": _to_float(row.model_weight)}
            for row in total_rows
        ],
        "basic": [
            {"key": field, "name": label, "weight": _to_float(getattr(basic_row, field))}
            for field, label in BASIC_FIELDS
        ],
        "tech": [
            {"key": field, "name": label, "weight": _to_float(getattr(tech_row, field))}
            for field, label in TECH_FIELDS
        ],
        "professional": [
            {"key": field, "name": label, "weight": _to_float(getattr(professional_row, field))}
            for field, label in PROFESSIONAL_FIELDS
        ],
    }


@require_GET
def all_weights(request):
    user = _admin_user(request)
    if not user:
        return _json_error("无权访问", status=403)
    return JsonResponse({"success": True, "data": _weights_payload()})


@csrf_exempt
@require_POST
def update_weights(request):
    user = _admin_user(request)
    if not user:
        return _json_error("无权访问", status=403)

    payload = _json_body(request)
    level = str(payload.get("level") or "").upper()
    items = payload.get("data") or []
    if level not in {"TOTAL", "BASIC", "TECH", "PROFESSIONAL"}:
        return _json_error("未知权重分组")
    if not isinstance(items, list):
        return _json_error("权重数据格式错误")

    _ensure_seed_rows()
    try:
        with transaction.atomic():
            if level == "TOTAL":
                for item in items:
                    model_id = int(item["key"])
                    ScoreModelTotalWeight.objects.filter(model_id=model_id).update(model_weight=Decimal(str(item["weight"])))
            else:
                model = {
                    "BASIC": ScoreModelBasicWeight.objects.order_by("model_id").first(),
                    "TECH": ScoreModelTechWeight.objects.order_by("model_id").first(),
                    "PROFESSIONAL": ScoreModelProfessionalWeight.objects.order_by("model_id").first(),
                }[level]
                update_fields = {}
                allowed_fields = {
                    "BASIC": {field for field, _label in BASIC_FIELDS},
                    "TECH": {field for field, _label in TECH_FIELDS},
                    "PROFESSIONAL": {field for field, _label in PROFESSIONAL_FIELDS},
                }[level]
                for item in items:
                    key = str(item.get("key") or "")
                    if key in allowed_fields:
                        update_fields[key] = Decimal(str(item.get("weight") or 0))
                for key, value in update_fields.items():
                    setattr(model, key, value)
                model.save(update_fields=list(update_fields.keys()))
    except Exception as error:
        return JsonResponse({"success": False, "message": str(error)}, status=500)

    _write_operation_log(user, f"更新评分权重:{level}")
    return JsonResponse({"success": True, "message": "保存成功"})


def _run_scoring_task():
    try:
        summary = run_full_scoring(status_callback=_set_scoring_status)
        _set_scoring_status(
            "completed",
            "评分完成："
            f"{summary['company_count']} 家企业、"
            f"{summary['industry_count']} 条行业路径、"
            f"{summary['log_count']} 条日志，"
            f"耗时 {summary['duration_seconds']} 秒",
        )
    except Exception as error:
        _set_scoring_status("failed", f"评分失败：{error}")


@csrf_exempt
@require_POST
def run_scoring(request):
    user = _admin_user(request)
    if not user:
        return _json_error("无权访问", status=403)

    if SCORING_STATUS.get("status") == "running":
        return _json_error("评分任务正在执行中", status=409)

    _set_scoring_status("running", "评分任务已启动，正在准备数据")
    threading.Thread(target=_run_scoring_task, daemon=True).start()
    _write_operation_log(user, "触发评分任务")
    return JsonResponse(
        {
            "success": True,
            "message": "评分任务已启动，正在基于当前本地数据库重算企业与行业评分。",
        }
    )


@require_GET
def scoring_status(request):
    user = _admin_user(request)
    if not user:
        return _json_error("无权访问", status=403)
    return JsonResponse({"success": True, **SCORING_STATUS})
