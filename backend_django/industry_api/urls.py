from django.urls import path

from . import views


urlpatterns = [
    path("meta/all", views.meta_all),
    path("industry/tree", views.industry_tree),
    path("industry/companies", views.industry_companies),
    path("industry/profile", views.industry_profile),
]

