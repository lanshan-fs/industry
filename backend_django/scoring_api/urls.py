from django.urls import path

from . import views


urlpatterns = [
    path("industry-tree/", views.industry_tree),
    path("enterprise-profile/", views.enterprise_profile),
    path("enterprise-score/", views.enterprise_score),
]
