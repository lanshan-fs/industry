from django.urls import path

from . import views


urlpatterns = [
    path("health", views.health),
    path("register", views.register),
    path("login", views.login),
    path("send-code", views.send_code),
    path("reset-password", views.reset_password),
]
