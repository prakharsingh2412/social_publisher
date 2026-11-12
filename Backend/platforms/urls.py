from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlatformCredentialViewSet, PostViewSet, MediaUploadView

router = DefaultRouter()
router.register("platforms", PlatformCredentialViewSet, basename="platform")
router.register("posts", PostViewSet, basename="post")

urlpatterns = [
    path("", include(router.urls)),
    path('upload-media/', MediaUploadView.as_view(), name='upload-media'),
]