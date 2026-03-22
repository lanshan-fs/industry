from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

import bcrypt
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import PlatformUser, UserDomain


FIXED_INVITE_CODE = "CY2026"
JWT_SECRET = os.getenv("JWT_SECRET", "chaoyang_industrial_secret_2026")
EMAIL_HOST = (os.getenv("EMAIL_HOST") or "smtp.163.com").replace("\r", "").strip()
EMAIL_PORT = int((os.getenv("EMAIL_PORT") or "465").replace("\r", "").strip())
EMAIL_USER = (os.getenv("EMAIL_USER") or "").replace("\r", "").strip()
EMAIL_PASS = (os.getenv("EMAIL_PASS") or "").replace("\r", "").strip()
EMAIL_TIMEOUT = 5
RESET_CODE_CACHE: dict[str, dict[str, str | int]] = {}
DOMAIN_CONFIG = {
    "digital_medical": {"domain_name": "数字医疗", "user_type": 1},
    "digital_wellness": {"domain_name": "数字康养", "user_type": 2},
}


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", "").strip()


def _json_body(request) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return {}


def _json_error(message: str, status: int = 400):
    return JsonResponse({"success": False, "message": message}, status=status)


def _get_domain_config(domain_key: str):
    return DOMAIN_CONFIG.get(_normalize_text(domain_key))


def _resolve_domain(domain_key: str) -> tuple[UserDomain | None, dict | None]:
    config = _get_domain_config(domain_key)
    if not config:
        return None, None
    domain, _ = UserDomain.objects.get_or_create(
        domain_name=config["domain_name"],
        defaults={"domain_description": f"{config['domain_name']}用户领域"},
    )
    return domain, config


def _build_auth_user(user: PlatformUser) -> dict:
    domain_key = None
    if user.domain_id:
        if user.domain and user.domain.domain_name == "数字医疗":
            domain_key = "digital_medical"
        elif user.domain and user.domain.domain_name == "数字康养":
            domain_key = "digital_wellness"

    return {
        "id": user.user_id,
        "username": user.user_name,
        "role": user.user_role or "user",
        "realName": user.user_real_name or user.user_name,
        "domain": domain_key,
        "organization": user.organization or user.org_name,
    }


def _verify_password_hash(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False

    if password_hash.startswith("$2a$") or password_hash.startswith("$2b$") or password_hash.startswith("$2y$"):
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    return check_password(password, password_hash)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _create_jwt(payload: dict, expires_in_hours: int = 24) -> str:
    now = int(timezone.now().timestamp())
    claims = {
        **payload,
        "iat": now,
        "exp": now + expires_in_hours * 3600,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _base64url(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
            _base64url(json.dumps(claims, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
        ]
    )
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_base64url(signature)}"


def _client_ip(request) -> str | None:
    forwarded = _normalize_text(request.META.get("HTTP_X_FORWARDED_FOR"))
    if forwarded:
        return forwarded.split(",")[0].strip()
    remote = _normalize_text(request.META.get("REMOTE_ADDR"))
    return remote or None


def _send_reset_email(target_email: str, code: str) -> tuple[bool, str]:
    if not EMAIL_USER or not EMAIL_PASS:
        return False, f"(模拟) 验证码：{code}"

    message = EmailMessage()
    message["From"] = f"朝阳产业链平台 <{EMAIL_USER}>"
    message["To"] = target_email
    message["Subject"] = "【安全验证】找回您的登录密码"
    message.set_content(
        f"您好，您正在申请重置密码。\n\n您的验证码是：{code}\n验证码 5 分钟内有效。\n",
        subtype="plain",
        charset="utf-8",
    )

    try:
        if EMAIL_PORT == 465:
            with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, timeout=EMAIL_TIMEOUT) as server:
                server.login(EMAIL_USER, EMAIL_PASS)
                server.send_message(message)
        else:
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=EMAIL_TIMEOUT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.send_message(message)
        return True, "验证码已发送至您的邮箱"
    except Exception as error:
        print(f"send_mail failed, fallback to mock code: {error}")
        return False, f"(模拟) 验证码：{code}"


@require_GET
def health(_request):
    return JsonResponse({"success": True, "service": "django-auth"})


@csrf_exempt
@require_POST
def register(request):
    payload = _json_body(request)
    username = _normalize_text(payload.get("username"))
    password = _normalize_text(payload.get("password"))
    email = _normalize_text(payload.get("email"))
    phone = _normalize_text(payload.get("phone"))
    company = _normalize_text(payload.get("company"))
    job = _normalize_text(payload.get("job"))
    invite_code = _normalize_text(payload.get("inviteCode"))

    domain, domain_config = _resolve_domain(payload.get("domain"))
    if not domain or not domain_config:
        return _json_error("请选择有效的所属领域")
    if not username or not password or not email or not phone or not company:
        return _json_error("请完整填写注册信息")
    if invite_code != FIXED_INVITE_CODE:
        return _json_error("邀请码无效")

    if PlatformUser.objects.filter(user_name=username).exists():
        return _json_error("用户名、邮箱或手机号已存在")
    if email and PlatformUser.objects.filter(email=email).exists():
        return _json_error("用户名、邮箱或手机号已存在")
    if phone and PlatformUser.objects.filter(phone=phone).exists():
        return _json_error("用户名、邮箱或手机号已存在")

    now = timezone.now()
    password_hash = make_password(password)
    with transaction.atomic():
        PlatformUser.objects.create(
            user_name=username,
            password_hash=password_hash,
            email=email,
            phone=phone,
            organization=company,
            position=job or None,
            user_nickname=username,
            user_type=domain_config["user_type"],
            is_superuser=False,
            user_role="user",
            date_joined=now,
            password_update_time=now,
            user_real_name=username,
            org_name=company,
            dept_name=job or None,
            user_status=1,
            domain=domain,
            registered_at=now,
            updated_at=now,
        )

    return JsonResponse({"success": True, "message": "注册成功"})


@csrf_exempt
@require_POST
def login(request):
    payload = _json_body(request)
    username = _normalize_text(payload.get("username"))
    password = _normalize_text(payload.get("password"))

    if not username or not password:
        return _json_error("请输入用户名和密码")

    user = PlatformUser.objects.select_related("domain").filter(user_name=username).first()
    if not user:
        return _json_error("用户不存在")
    if user.user_status == 0:
        return _json_error("账号已被禁用", status=403)

    domain_config = _get_domain_config(payload.get("domain"))
    if domain_config:
        if user.domain and user.domain.domain_name != domain_config["domain_name"]:
            return _json_error("所属领域与账号不匹配")

    if not _verify_password_hash(password, user.password_hash):
        return _json_error("密码错误")

    now = timezone.now()
    user.last_login_at = now
    user.last_login_time = now
    user.last_login_ip = _client_ip(request)
    user.updated_at = now
    if user.user_status == 2:
        user.user_status = 1
    user.save(update_fields=["last_login_at", "last_login_time", "last_login_ip", "updated_at", "user_status"])

    auth_user = _build_auth_user(user)
    token = _create_jwt(
        {
            "id": auth_user["id"],
            "username": auth_user["username"],
            "role": auth_user["role"],
        }
    )
    return JsonResponse({"success": True, "data": {"token": token, "user": auth_user}})


@csrf_exempt
@require_POST
def send_code(request):
    payload = _json_body(request)
    username = _normalize_text(payload.get("username"))
    email = _normalize_text(payload.get("email"))

    if not username or not email:
        return _json_error("请输入用户名和绑定邮箱")

    user = PlatformUser.objects.filter(user_name=username, email=email).first()
    if not user:
        return _json_error("用户名与绑定的邮箱不匹配")

    code = f"{secrets.randbelow(900000) + 100000:06d}"
    RESET_CODE_CACHE[username] = {
        "code": code,
        "email": email,
        "expire_at": int((timezone.now() + timedelta(minutes=5)).timestamp()),
    }
    _, message = _send_reset_email(email, code)
    return JsonResponse({"success": True, "message": message})


@csrf_exempt
@require_POST
def reset_password(request):
    payload = _json_body(request)
    username = _normalize_text(payload.get("username"))
    code = _normalize_text(payload.get("code"))
    new_password = _normalize_text(payload.get("newPassword"))

    if not username or not code or not new_password:
        return _json_error("请完整填写重置信息")

    cached = RESET_CODE_CACHE.get(username)
    if not cached:
        return _json_error("验证码无效或已过期")
    if cached.get("code") != code or int(cached.get("expire_at", 0)) < int(timezone.now().timestamp()):
        return _json_error("验证码无效或已过期")

    user = PlatformUser.objects.filter(user_name=username).first()
    if not user:
        return _json_error("用户不存在")

    now = timezone.now()
    user.password_hash = make_password(new_password)
    user.password_update_time = now
    user.updated_at = now
    user.save(update_fields=["password_hash", "password_update_time", "updated_at"])
    RESET_CODE_CACHE.pop(username, None)
    return JsonResponse({"success": True, "message": "密码重置成功"})
