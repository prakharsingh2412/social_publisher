from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlatformListView, PostViewSet

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")

urlpatterns = [
    path("platforms/", PlatformListView.as_view(), name="platform-list"),
    path("", include(router.urls)),
]