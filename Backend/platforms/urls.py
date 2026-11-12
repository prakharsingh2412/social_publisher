from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlatformCredentialViewSet, PostViewSet

router = DefaultRouter()
router.register("platforms", PlatformCredentialViewSet, basename="platform")
router.register("posts", PostViewSet, basename="post")

urlpatterns = [
    path("", include(router.urls)),
]