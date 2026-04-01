from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("auth_api.urls")),
    path("api/dashboard/", include("dashboard_api.urls")),
    path("api/system/", include("system_api.urls")),
    path("api/tags/", include("tag_api.urls")),
    path("api/weights/", include("weights_api.urls")),
    path("api/scoring/", include("scoring_api.urls")),
    path("api/", include("industry_api.urls")),
]
