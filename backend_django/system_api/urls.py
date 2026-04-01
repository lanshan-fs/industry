from django.urls import path

from . import views


urlpatterns = [
    path("companies", views.company_list),
    path("companies/<str:identifier>", views.company_detail),
]
