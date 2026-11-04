from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),

    # System
    path("api/v1/health/", HealthCheckView.as_view(), name="health"),

    # Auth — mount at /api/v1/auth/
    path("api/v1/auth/", include("accounts.urls")),

    # Platforms + Posts — mount at /api/v1/ (internal paths disambiguate)
    path("api/v1/", include("platforms.urls")),

    # Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)