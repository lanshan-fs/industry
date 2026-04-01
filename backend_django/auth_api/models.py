from django.db import models
from django.utils import timezone


class UserDomain(models.Model):
    domain_id = models.BigAutoField(primary_key=True, db_column="domain_id")
    domain_name = models.CharField(max_length=50, unique=True, db_column="domain_name")
    domain_description = models.TextField(blank=True, null=True, db_column="domain_description")
    created_at = models.DateTimeField(blank=True, null=True, db_column="created_at")

    class Meta:
        managed = False
        db_table = "user_domains"


class PlatformUser(models.Model):
    user_id = models.BigAutoField(primary_key=True, db_column="user_id")
    user_name = models.CharField(max_length=100, unique=True, db_column="user_name")
    password_hash = models.CharField(max_length=255, db_column="password_hash")
    email = models.CharField(max_length=100, blank=True, null=True, db_column="email")
    phone = models.CharField(max_length=20, blank=True, null=True, db_column="phone")
    organization = models.CharField(max_length=100, blank=True, null=True, db_column="organization")
    position = models.CharField(max_length=100, blank=True, null=True, db_column="position")
    user_nickname = models.CharField(max_length=255, blank=True, null=True, db_column="user_nickname")
    user_avatar = models.CharField(max_length=255, blank=True, null=True, db_column="user_avatar")
    user_type = models.PositiveSmallIntegerField(blank=True, null=True, db_column="user_type")
    is_superuser = models.BooleanField(default=False, db_column="is_superuser")
    user_role = models.CharField(max_length=255, blank=True, null=True, db_column="user_role")
    date_joined = models.DateTimeField(default=timezone.now, db_column="date_joined")
    last_login_time = models.DateTimeField(blank=True, null=True, db_column="last_login_time")
    last_login_ip = models.CharField(max_length=255, blank=True, null=True, db_column="last_login_ip")
    password_update_time = models.DateTimeField(blank=True, null=True, db_column="password_update_time")
    user_real_name = models.CharField(max_length=255, blank=True, null=True, db_column="user_real_name")
    org_name = models.CharField(max_length=255, blank=True, null=True, db_column="org_name")
    org_id = models.CharField(max_length=255, blank=True, null=True, db_column="org_id")
    dept_name = models.CharField(max_length=255, blank=True, null=True, db_column="dept_name")
    dept_id = models.CharField(max_length=255, blank=True, null=True, db_column="dept_id")
    user_status = models.PositiveSmallIntegerField(default=2, db_column="user_status")
    domain = models.ForeignKey(
        UserDomain,
        blank=True,
        null=True,
        db_column="domain_id",
        on_delete=models.SET_NULL,
        related_name="users",
    )
    registered_at = models.DateTimeField(blank=True, null=True, db_column="registered_at")
    last_login_at = models.DateTimeField(blank=True, null=True, db_column="last_login_at")
    updated_at = models.DateTimeField(blank=True, null=True, db_column="updated_at")

    class Meta:
        managed = False
        db_table = "users"


class InviteCode(models.Model):
    code = models.CharField(max_length=50, primary_key=True, db_column="invite_code")
    is_used = models.BooleanField(default=False, db_column="is_used")
    created_at = models.DateTimeField(blank=True, null=True, db_column="created_at")

    class Meta:
        managed = False
        db_table = "user_dinvite_codes"


class Role(models.Model):
    role_id = models.BigAutoField(primary_key=True, db_column="role_id")
    role_name = models.CharField(max_length=30, unique=True, db_column="role_name")
    role_description = models.TextField(blank=True, null=True, db_column="role_description")

    class Meta:
        managed = False
        db_table = "user_roles"


class UserRoleAssignment(models.Model):
    association_id = models.BigAutoField(primary_key=True, db_column="association_id")
    user = models.ForeignKey(
        PlatformUser,
        db_column="user_id",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        db_column="role_id",
        on_delete=models.CASCADE,
        related_name="user_assignments",
    )
    assigned_at = models.DateTimeField(blank=True, null=True, db_column="assigned_at")

    class Meta:
        managed = False
        db_table = "user_and_roles"


class OperationLog(models.Model):
    log_id = models.BigAutoField(primary_key=True, db_column="log_id")
    user = models.ForeignKey(
        PlatformUser,
        db_column="user_id",
        on_delete=models.CASCADE,
        related_name="operation_logs",
    )
    operation_time = models.DateTimeField(blank=True, null=True, db_column="operation_time")
    action = models.CharField(max_length=50, db_column="action")

    class Meta:
        managed = False
        db_table = "user_operation_logs"
