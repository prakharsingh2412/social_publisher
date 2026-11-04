from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from .models import PlatformCredential, Post, PostStatus
from .serializers import (
    PlatformCredentialPublicSerializer,
    PostSerializer,
    PostCreateSerializer,
    PublishNowSerializer,
)


# ============================================================
# PLATFORMS  — public listing
# ============================================================

class PlatformListView(generics.ListAPIView):
    """
    List platforms that currently have an active credential.
    Used by the frontend to render the platform picker.
    """
    serializer_class   = PlatformCredentialPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PlatformCredential.objects.filter(is_active=True)


# ============================================================
# POSTS  — full CRUD + publish-now
# ============================================================

class PostViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for posts.
    Users only see (and only affect) their own posts.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Per-user isolation
        return (
            Post.objects
            .filter(user=self.request.user)
            .prefetch_related("platform_results")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return PostCreateSerializer
        if self.action == "publish_now":
            return PublishNowSerializer
        return PostSerializer

    # -------- custom create: write with one serializer, respond with another
    def create(self, request, *args, **kwargs):
        write = PostCreateSerializer(data=request.data, context={"request": request})
        write.is_valid(raise_exception=True)
        post = write.save()
        return Response(
            PostSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    # -------- only drafts can be edited
    def update(self, request, *args, **kwargs):
        post = self.get_object()
        if post.status != PostStatus.DRAFT:
            return Response(
                {"detail": f"Cannot edit a post with status '{post.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    # -------- cannot delete published / partially-published posts
    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        if post.status in (PostStatus.PUBLISHED, PostStatus.PARTIAL):
            return Response(
                {"detail": "Cannot delete a published post."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    # -------- POST /api/posts/{id}/publish-now/
    @extend_schema(
        request=PublishNowSerializer,
        responses=PostSerializer,
        summary="Publish a post immediately",
    )
    @action(detail=True, methods=["post"], url_path="publish-now")
    def publish_now(self, request, pk=None):
        post = self.get_object()

        if post.status in (PostStatus.PUBLISHING, PostStatus.PUBLISHED):
            return Response(
                {"detail": f"Post is already '{post.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        post.scheduled_at = timezone.now()
        post.status       = PostStatus.QUEUED
        post.save(update_fields=["scheduled_at", "status"])

        # (Celery enqueue is added in Block B)
        return Response(PostSerializer(post, context={"request": request}).data)