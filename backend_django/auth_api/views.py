from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import smtplib
import string
from datetime import timedelta
from email.message import EmailMessage

import bcrypt
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import InviteCode, OperationLog, PlatformUser, Role, UserDomain, UserRoleAssignment


FIXED_INVITE_CODE = "CY2026"
RESERVED_ADMIN_USERNAME = "admin"
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
DOMAIN_NAME_TO_KEY = {config["domain_name"]: key for key, config in DOMAIN_CONFIG.items()}
ROLE_DEFINITIONS = [
    {"name": "ADMIN", "label": "系统管理员"},
    {"name": "senior_user", "label": "高级用户"},
    {"name": "ordinary_user", "label": "普通用户"},
]
ROLE_LABEL_MAP = {item["name"]: item["label"] for item in ROLE_DEFINITIONS}


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


def _normalize_domain_key(domain_value: str) -> str:
    normalized = _normalize_text(domain_value)
    if normalized in DOMAIN_CONFIG:
        return normalized
    return DOMAIN_NAME_TO_KEY.get(normalized, "")


def _get_domain_config(domain_value: str):
    domain_key = _normalize_domain_key(domain_value)
    return DOMAIN_CONFIG.get(domain_key)


def _resolve_domain(domain_value: str) -> tuple[UserDomain | None, dict | None, str | None]:
    domain_key = _normalize_domain_key(domain_value)
    config = DOMAIN_CONFIG.get(domain_key)
    if not config:
        return None, None, None
    domain, _ = UserDomain.objects.get_or_create(
        domain_name=config["domain_name"],
        defaults={"domain_description": f"{config['domain_name']}用户领域"},
    )
    return domain, config, domain_key


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


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


def _decode_jwt(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token")

    signing_input = ".".join(parts[:2])
    expected_signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    actual_signature = _base64url_decode(parts[2])
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("invalid signature")

    payload = json.loads(_base64url_decode(parts[1]).decode("utf-8"))
    if int(payload.get("exp", 0)) < int(timezone.now().timestamp()):
        raise ValueError("token expired")
    return payload


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


def _verify_password_hash(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    if password_hash.startswith(("$2a$", "$2b$", "$2y$")):
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    return check_password(password, password_hash)


def _ordered_roles() -> list[Role]:
    existing = {role.role_name: role for role in Role.objects.filter(role_name__in=[item["name"] for item in ROLE_DEFINITIONS])}
    missing = [item for item in ROLE_DEFINITIONS if item["name"] not in existing]
    if missing:
        for item in missing:
            Role.objects.create(role_name=item["name"], role_description=item["label"])
        existing = {role.role_name: role for role in Role.objects.filter(role_name__in=[item["name"] for item in ROLE_DEFINITIONS])}
    return [existing[item["name"]] for item in ROLE_DEFINITIONS if item["name"] in existing]


def _is_reserved_admin_username(username: str) -> bool:
    return _normalize_text(username).lower() == RESERVED_ADMIN_USERNAME


def _canonical_role_name(role_name: str) -> str:
    normalized = _normalize_text(role_name)
    if normalized == "ADMIN":
        return "ADMIN"
    if normalized in {"senior_user", "ordinary_user"}:
        return normalized
    return "ordinary_user"


def _role_name_from_user(user: PlatformUser) -> str:
    if _is_reserved_admin_username(user.user_name):
        return "ADMIN"
    assignment = next(iter(getattr(user, "role_assignments", []).all()), None) if hasattr(user, "role_assignments") else None
    if assignment and assignment.role and assignment.role.role_name:
        return assignment.role.role_name
    if _normalize_text(user.user_role):
        return _canonical_role_name(user.user_role)
    if user.is_superuser:
        return "ADMIN"
    return "ordinary_user"


def _ensure_reserved_admin_privileges(user: PlatformUser):
    if not _is_reserved_admin_username(user.user_name):
        return

    roles = {role.role_name: role for role in _ordered_roles()}
    admin_role = roles.get("ADMIN")
    now = timezone.now()

    update_fields: list[str] = []
    if user.user_role != "ADMIN":
        user.user_role = "ADMIN"
        update_fields.append("user_role")
    if not user.is_superuser:
        user.is_superuser = True
        update_fields.append("is_superuser")
    user.updated_at = now
    update_fields.append("updated_at")
    user.save(update_fields=update_fields)

    if not admin_role:
        return

    assignment = UserRoleAssignment.objects.filter(user=user).first()
    if assignment:
        assignment_updates: list[str] = []
        if assignment.role_id != admin_role.role_id:
            assignment.role = admin_role
            assignment_updates.append("role")
        if assignment.assigned_at is None:
            assignment.assigned_at = now
            assignment_updates.append("assigned_at")
        if assignment_updates:
            assignment.save(update_fields=assignment_updates)
        UserRoleAssignment.objects.filter(user=user).exclude(association_id=assignment.association_id).delete()
    else:
        UserRoleAssignment.objects.create(user=user, role=admin_role, assigned_at=now)


def _build_auth_user(user: PlatformUser) -> dict:
    domain_key = None
    if user.domain_id and user.domain:
        domain_key = DOMAIN_NAME_TO_KEY.get(user.domain.domain_name)

    role_name = _role_name_from_user(user)
    return {
        "id": user.user_id,
        "username": user.user_name,
        "role": role_name,
        "isAdmin": role_name == "ADMIN" or user.is_superuser,
        "realName": user.user_real_name or user.user_name,
        "domain": domain_key,
        "organization": user.organization or user.org_name,
    }


def _sync_user_role_fields(user: PlatformUser, role_name: str):
    canonical = _canonical_role_name(role_name)
    user.user_role = canonical
    user.is_superuser = canonical == "ADMIN"
    user.updated_at = timezone.now()
    user.save(update_fields=["user_role", "is_superuser", "updated_at"])


def _write_operation_log(user: PlatformUser, action: str):
    OperationLog.objects.create(user=user, action=action)


def _authenticated_user(request) -> PlatformUser | None:
    auth_header = _normalize_text(request.headers.get("Authorization"))
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        payload = _decode_jwt(token)
    except Exception:
        return None

    user = (
        PlatformUser.objects.select_related("domain")
        .prefetch_related("role_assignments__role")
        .filter(user_id=payload.get("id"))
        .first()
    )
    if not user or user.user_status == 0:
        return None
    _ensure_reserved_admin_privileges(user)
    return user


def _admin_user(request) -> PlatformUser | None:
    user = _authenticated_user(request)
    if not user:
        return None
    return user if _role_name_from_user(user) == "ADMIN" or user.is_superuser else None


def _role_payload(role: Role) -> dict:
    return {
        "id": role.role_id,
        "name": role.role_name,
        "label": ROLE_LABEL_MAP.get(role.role_name, role.role_description or role.role_name),
    }


def _user_list_item(user: PlatformUser) -> dict:
    role_name = _role_name_from_user(user)
    roles = {role.role_name: role for role in _ordered_roles()}
    role = roles.get(role_name)
    return {
        "user_id": user.user_id,
        "user_name": user.user_name,
        "role_id": role.role_id if role else None,
        "role_name": role_name,
        "is_active": 0 if user.user_status == 0 else 1,
    }


def _validate_unique_user_fields(
    *,
    username: str,
    email: str,
    phone: str,
    exclude_user_id: int | None = None,
) -> str | None:
    username_qs = PlatformUser.objects.filter(user_name=username)
    email_qs = PlatformUser.objects.filter(email=email) if email else PlatformUser.objects.none()
    phone_qs = PlatformUser.objects.filter(phone=phone) if phone else PlatformUser.objects.none()

    if exclude_user_id is not None:
        username_qs = username_qs.exclude(user_id=exclude_user_id)
        email_qs = email_qs.exclude(user_id=exclude_user_id)
        phone_qs = phone_qs.exclude(user_id=exclude_user_id)

    if username and username_qs.exists():
        return "用户名已存在"
    if email and email_qs.exists():
        return "邮箱已存在"
    if phone and phone_qs.exists():
        return "手机号已存在"
    return None


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

    domain, domain_config, _domain_key = _resolve_domain(payload.get("domain"))
    if not domain or not domain_config:
        return _json_error("请选择有效的所属领域")
    if not username or not password or not email or not phone or not company:
        return _json_error("请完整填写注册信息")

    duplicated_message = _validate_unique_user_fields(username=username, email=email, phone=phone)
    if duplicated_message:
        return _json_error(duplicated_message)

    roles = {role.role_name: role for role in _ordered_roles()}
    default_role = roles.get("ordinary_user")
    if not default_role:
        return _json_error("系统角色未初始化", status=500)

    now = timezone.now()
    password_hash = make_password(password)
    with transaction.atomic():
        invite = None
        if invite_code != FIXED_INVITE_CODE:
            invite = InviteCode.objects.select_for_update().filter(code=invite_code).first()
            if not invite or invite.is_used:
                return _json_error("邀请码无效")

        user = PlatformUser.objects.create(
            user_name=username,
            password_hash=password_hash,
            email=email,
            phone=phone,
            organization=company,
            position=job or None,
            user_nickname=username,
            user_type=domain_config["user_type"],
            is_superuser=False,
            user_role="ordinary_user",
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
        UserRoleAssignment.objects.create(user=user, role=default_role)
        if invite:
            invite.is_used = True
            invite.save(update_fields=["is_used"])
        _write_operation_log(user, "注册账号")

    return JsonResponse({"success": True, "message": "注册成功"})


@csrf_exempt
@require_POST
def login(request):
    payload = _json_body(request)
    username = _normalize_text(payload.get("username"))
    password = _normalize_text(payload.get("password"))

    if not username or not password:
        return _json_error("请输入用户名和密码")

    user = (
        PlatformUser.objects.select_related("domain")
        .prefetch_related("role_assignments__role")
        .filter(user_name=username)
        .first()
    )
    if not user:
        return _json_error("用户不存在")
    _ensure_reserved_admin_privileges(user)
    if user.user_status == 0:
        return _json_error("账号已被禁用", status=403)

    domain_config = _get_domain_config(payload.get("domain"))
    if domain_config and user.domain and user.domain.domain_name != domain_config["domain_name"]:
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
    _write_operation_log(user, "登录")
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
    _write_operation_log(user, "重置密码")
    return JsonResponse({"success": True, "message": "密码重置成功"})


@require_GET
def check_username(request):
    username = _normalize_text(request.GET.get("username"))
    exists = PlatformUser.objects.filter(user_name=username).exists() if username else False
    return JsonResponse({"exists": exists})


@require_GET
def user_roles(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)
    return JsonResponse({"success": True, "data": [_role_payload(role) for role in _ordered_roles()]})


@require_GET
def user_list(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    users = (
        PlatformUser.objects.prefetch_related("role_assignments__role")
        .order_by("-updated_at", "-user_id")
        .all()
    )
    return JsonResponse({"success": True, "data": [_user_list_item(user) for user in users]})


@csrf_exempt
@require_POST
def update_user_role(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    payload = _json_body(request)
    user_id = payload.get("user_id")
    role_id = payload.get("role_id")
    if not user_id or not role_id:
        return _json_error("参数不完整")

    target_user = PlatformUser.objects.filter(user_id=user_id).first()
    target_role = Role.objects.filter(role_id=role_id).first()
    if not target_user or not target_role:
        return _json_error("目标用户或角色不存在", status=404)

    with transaction.atomic():
        assignment = UserRoleAssignment.objects.filter(user=target_user).first()
        if assignment:
            assignment.role = target_role
            assignment.save(update_fields=["role"])
            UserRoleAssignment.objects.filter(user=target_user).exclude(association_id=assignment.association_id).delete()
        else:
            UserRoleAssignment.objects.create(user=target_user, role=target_role)
        _sync_user_role_fields(target_user, target_role.role_name)
        _write_operation_log(admin, f"修改用户角色:{target_user.user_name}->{target_role.role_name}")

    return JsonResponse({"success": True, "message": "角色权限更新成功"})


@csrf_exempt
@require_POST
def toggle_user_status(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    payload = _json_body(request)
    user_id = payload.get("user_id")
    target_status = int(payload.get("target_status", 0))
    if not user_id:
        return _json_error("缺少用户 ID")
    if int(user_id) == admin.user_id:
        return _json_error("不能操作当前登录账号")
    if target_status not in (0, 1):
        return _json_error("目标状态无效")

    target_user = PlatformUser.objects.filter(user_id=user_id).first()
    if not target_user:
        return _json_error("目标用户不存在", status=404)

    target_user.user_status = target_status
    target_user.updated_at = timezone.now()
    target_user.save(update_fields=["user_status", "updated_at"])
    action = "恢复账号" if target_status == 1 else "禁用账号"
    _write_operation_log(admin, f"{action}:{target_user.user_name}")
    return JsonResponse({"success": True, "message": f"{target_user.user_name}{'已恢复' if target_status == 1 else '已禁用'}"})


@require_GET
def invite_code_list(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    codes = InviteCode.objects.filter(is_used=False).order_by("-created_at", "-code")
    data = [
        {
            "code": code.code,
            "created_at": code.created_at.strftime("%Y-%m-%d %H:%M:%S") if code.created_at else None,
        }
        for code in codes
    ]
    return JsonResponse({"success": True, "data": data})


@csrf_exempt
@require_POST
def generate_invite_codes(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    payload = _json_body(request)
    count = int(payload.get("count", 1))
    if count < 1 or count > 50:
        return _json_error("一次最多生成 50 个邀请码")

    alphabet = string.ascii_uppercase + string.digits
    created_codes: list[str] = []
    while len(created_codes) < count:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if InviteCode.objects.filter(code=code).exists() or code in created_codes:
            continue
        InviteCode.objects.create(code=code, is_used=False)
        created_codes.append(code)

    _write_operation_log(admin, f"生成邀请码:{count}个")
    return JsonResponse({"success": True, "message": f"成功生成 {count} 个邀请码", "data": {"codes": created_codes}})


@csrf_exempt
@require_POST
def admin_create_user(request):
    admin = _admin_user(request)
    if not admin:
        return _json_error("无权访问", status=403)

    payload = _json_body(request)
    username = _normalize_text(payload.get("username"))
    password = _normalize_text(payload.get("password"))
    email = _normalize_text(payload.get("email"))
    phone = _normalize_text(payload.get("phone"))
    company = _normalize_text(payload.get("company"))
    job = _normalize_text(payload.get("job"))
    role_name = _canonical_role_name(payload.get("role"))
    domain, domain_config, _domain_key = _resolve_domain(payload.get("domain"))

    if not username or not password or not domain or not domain_config:
        return _json_error("请完整填写用户名、密码和领域信息")
    duplicated_message = _validate_unique_user_fields(username=username, email=email, phone=phone)
    if duplicated_message:
        return _json_error(duplicated_message)

    roles = {role.role_name: role for role in _ordered_roles()}
    target_role = roles.get(role_name)
    if not target_role:
        return _json_error("目标角色不存在")

    now = timezone.now()
    with transaction.atomic():
        user = PlatformUser.objects.create(
            user_name=username,
            password_hash=make_password(password),
            email=email or None,
            phone=phone or None,
            organization=company or None,
            position=job or None,
            user_nickname=username,
            user_type=domain_config["user_type"],
            is_superuser=role_name == "ADMIN",
            user_role=role_name,
            date_joined=now,
            password_update_time=now,
            user_real_name=username,
            org_name=company or None,
            dept_name=job or None,
            user_status=1,
            domain=domain,
            registered_at=now,
            updated_at=now,
        )
        UserRoleAssignment.objects.create(user=user, role=target_role)
        _write_operation_log(admin, f"管理员录入用户:{user.user_name}")

    return JsonResponse({"success": True, "message": "用户录入成功"})


@require_GET
def user_profile(request):
    user = _authenticated_user(request)
    if not user:
        return _json_error("身份验证失败", status=401)

    role_name = _role_name_from_user(user)
    return JsonResponse(
        {
            "success": True,
            "data": {
                "user_id": user.user_id,
                "user_name": user.user_name,
                "email": user.email,
                "phone": user.phone,
                "organization": user.organization or user.org_name,
                "position": user.position or user.dept_name,
                "domain_name": user.domain.domain_name if user.domain else None,
                "role_name": ROLE_LABEL_MAP.get(role_name, role_name),
                "role": role_name,
                "is_superuser": bool(user.is_superuser or role_name == "ADMIN"),
                "registered_at": user.registered_at.strftime("%Y-%m-%d %H:%M:%S") if user.registered_at else None,
            },
        }
    )


@csrf_exempt
@require_POST
def update_profile(request):
    user = _authenticated_user(request)
    if not user:
        return _json_error("身份验证失败", status=401)

    payload = _json_body(request)
    username = _normalize_text(payload.get("user_name")) or user.user_name
    email = _normalize_text(payload.get("email"))
    phone = _normalize_text(payload.get("phone"))
    organization = _normalize_text(payload.get("organization"))
    position = _normalize_text(payload.get("position"))

    duplicated_message = _validate_unique_user_fields(
        username=username,
        email=email,
        phone=phone,
        exclude_user_id=user.user_id,
    )
    if duplicated_message:
        return _json_error(duplicated_message)

    user.user_name = username
    user.email = email or None
    user.phone = phone or None
    user.organization = organization or None
    user.org_name = organization or None
    user.position = position or None
    user.dept_name = position or None
    user.updated_at = timezone.now()
    user.save(update_fields=["user_name", "email", "phone", "organization", "org_name", "position", "dept_name", "updated_at"])
    _write_operation_log(user, "更新个人资料")
    return JsonResponse({"success": True, "message": "资料更新成功"})


@csrf_exempt
@require_POST
def profile_security(request):
    user = _authenticated_user(request)
    if not user:
        return _json_error("身份验证失败", status=401)

    payload = _json_body(request)
    action = _normalize_text(payload.get("action"))
    if action == "change_password":
        old_password = _normalize_text(payload.get("old_password"))
        new_password = _normalize_text(payload.get("new_password"))
        if not old_password or not new_password:
            return _json_error("请完整填写密码信息")
        if not _verify_password_hash(old_password, user.password_hash):
            return _json_error("原密码错误")
        now = timezone.now()
        user.password_hash = make_password(new_password)
        user.password_update_time = now
        user.updated_at = now
        user.save(update_fields=["password_hash", "password_update_time", "updated_at"])
        _write_operation_log(user, "修改密码")
        return JsonResponse({"success": True, "message": "密码修改成功"})

    if action == "update_binding":
        email = _normalize_text(payload.get("email"))
        phone = _normalize_text(payload.get("phone"))
        duplicated_message = _validate_unique_user_fields(
            username=user.user_name,
            email=email,
            phone=phone,
            exclude_user_id=user.user_id,
        )
        if duplicated_message:
            return _json_error(duplicated_message)
        user.email = email or None
        user.phone = phone or None
        user.updated_at = timezone.now()
        user.save(update_fields=["email", "phone", "updated_at"])
        _write_operation_log(user, "更新绑定信息")
        return JsonResponse({"success": True, "message": "绑定信息更新成功"})

    return _json_error("无效操作")


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_profile(request):
    user = _authenticated_user(request)
    if not user:
        return _json_error("身份验证失败", status=401)

    user.user_status = 0
    user.updated_at = timezone.now()
    user.save(update_fields=["user_status", "updated_at"])
    _write_operation_log(user, "注销账号")
    return JsonResponse({"success": True, "message": "账号注销成功"})
