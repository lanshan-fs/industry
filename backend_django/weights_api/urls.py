from django.urls import path

from . import views


urlpatterns = [
    path("all/", views.all_weights),
    path("update/", views.update_weights),
    path("run/", views.run_scoring),
    path("status/", views.scoring_status),
]
