from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.views import HealthCheckView

# --- ADD THIS IMPORT ---
from platforms.views import (
    FacebookLoginView, InstagramLoginView,
    FacebookOAuthCallbackView, InstagramOAuthCallbackView,
    TwitterOAuthStartView, TwitterOAuthCallbackView,
)
# -----------------------

urlpatterns = [
    path("admin/", admin.site.urls),


    path("oauth/facebook/login/",  FacebookLoginView.as_view(),  name="facebook-login"),
    path("oauth/instagram/login/", InstagramLoginView.as_view(), name="instagram-login"),
    path("oauth/twitter/login/",   TwitterOAuthStartView.as_view(), name="twitter-login"),

    path("oauth/facebook/callback/",  FacebookOAuthCallbackView.as_view(),  name="facebook-callback"),
    path("oauth/instagram/callback/", InstagramOAuthCallbackView.as_view(), name="instagram-callback"),
    path("oauth/twitter/callback/",   TwitterOAuthCallbackView.as_view(),   name="twitter-callback"),
    # ---------------------------

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