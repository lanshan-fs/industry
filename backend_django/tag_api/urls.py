from django.urls import path

from . import views


urlpatterns = [
    path("companies", views.tag_companies),
    path("add", views.tag_add),
    path("delete", views.tag_delete),
    path("library/options", views.tag_library_options),
    path("dimensions/stats", views.dimension_stats),
    path("dimensions/<str:dimension_id>/detail", views.dimension_detail),
]
