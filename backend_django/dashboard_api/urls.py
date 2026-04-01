from django.urls import path

from . import views


urlpatterns = [
    path("overview", views.overview),
    path("notices", views.notice_list),
    path("admin/notices", views.admin_notice_list),
    path("admin/notices/save", views.admin_notice_save),
    path("admin/notices/publish", views.admin_notice_publish),
    path("admin/notices/delete", views.admin_notice_delete),
]
