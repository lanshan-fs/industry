from django.urls import path

from . import views


urlpatterns = [
    path("health", views.health),
    path("register", views.register),
    path("login", views.login),
    path("send-code", views.send_code),
    path("reset-password", views.reset_password),
    path("check-username", views.check_username),
    path("users/roles", views.user_roles),
    path("users/list", views.user_list),
    path("users/update-role", views.update_user_role),
    path("users/delete", views.toggle_user_status),
    path("invite-codes/list", views.invite_code_list),
    path("invite-codes/generate", views.generate_invite_codes),
    path("users/admin-create", views.admin_create_user),
    path("users/profile", views.user_profile),
    path("users/profile/update", views.update_profile),
    path("users/profile/security", views.profile_security),
    path("users/profile/delete", views.delete_profile),
]
