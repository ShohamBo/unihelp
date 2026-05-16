from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/admin/", include("programs.urls")),
    path("api/programs/", include("programs.api_urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/institutions/", include("institutions.urls")),
    path("api/leads/", include("leads.urls")),
    path("social/", include("social_django.urls", namespace="social")),
]
