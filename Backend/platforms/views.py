import base64
import hashlib
import secrets
import requests
from urllib.parse import urlencode
from datetime import timedelta

from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from .models import PlatformCredential, Post, PostStatus, Platform
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
    serializer_class   = PlatformCredentialPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PlatformCredential.objects.filter(is_active=True)


# ============================================================
# POSTS  — full CRUD + publish-now
# ============================================================

EDITABLE_STATUSES = (PostStatus.DRAFT, PostStatus.QUEUED)


class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
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

    def create(self, request, *args, **kwargs):
        write = PostCreateSerializer(data=request.data, context={"request": request})
        write.is_valid(raise_exception=True)
        post = write.save()
        return Response(
            PostSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        if post.status not in EDITABLE_STATUSES:
            return Response(
                {"detail": f"Cannot edit a post with status '{post.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        if post.status in (PostStatus.PUBLISHED, PostStatus.PARTIAL):
            return Response(
                {"detail": "Cannot delete a published post."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

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

        post.platform_results.filter(status=PostStatus.FAILED).update(
            status=PostStatus.QUEUED,
            retry_count=0,
            error_message="",
        )

        post.scheduled_at = timezone.now()
        post.status       = PostStatus.QUEUED
        post.save(update_fields=["scheduled_at", "status", "updated_at"])

        from .tasks import publish_post_task
        publish_post_task.delay(post.id)

        return Response(PostSerializer(post, context={"request": request}).data)

# ============================================================
# TWITTER OAUTH 2.0 PKCE FLOW
# ============================================================

class TwitterOAuthStartView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        code_verifier = secrets.token_urlsafe(50)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        state = secrets.token_urlsafe(16)

        request.session['twitter_code_verifier'] = code_verifier
        request.session['twitter_state'] = state

        params = {
            "response_type": "code",
            "client_id": settings.TWITTER_CLIENT_ID,
            "redirect_uri": settings.TWITTER_REDIRECT_URI,
            "scope": "tweet.read tweet.write users.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"
        
        return redirect(auth_url)


class TwitterOAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        state = request.GET.get("state")
        error = request.GET.get("error")

        if error:
            return JsonResponse({"error": f"Authorization denied: {error}"}, status=400)
        
        session_state = request.session.get('twitter_state')
        if not state or state != session_state:
            return JsonResponse({"error": "State mismatch. Possible CSRF attack."}, status=400)
        
        code_verifier = request.session.get('twitter_code_verifier')
        if not code_verifier:
            return JsonResponse({"error": "Session expired or missing code_verifier."}, status=400)

        token_url = "https://api.twitter.com/2/oauth2/token"
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": settings.TWITTER_CLIENT_ID,
            "redirect_uri": settings.TWITTER_REDIRECT_URI,
            "code_verifier": code_verifier,
        }
        
        auth_str = f"{settings.TWITTER_CLIENT_ID}:{settings.TWITTER_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(token_url, data=data, headers=headers)
        
        if response.status_code != 200:
            return JsonResponse({"error": "Token exchange failed", "details": response.text}, status=400)
            
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in") 

        user_res = requests.get(
            "https://api.twitter.com/2/users/me", 
            headers={"Authorization": f"Bearer {access_token}"}
        )
        username = user_res.json().get("data", {}).get("username", "Unknown Twitter User") if user_res.status_code == 200 else "Twitter User"

        credential, created = PlatformCredential.objects.update_or_create(
            platform=Platform.TWITTER,
            label=f"@{username}",
            defaults={
                "encrypted_token": access_token,
                "encrypted_secret": refresh_token,
                "is_active": True,
                "token_expires_at": timezone.now() + timedelta(seconds=expires_in) if expires_in else None,
            }
        )

        return JsonResponse({
            "status": "success", 
            "message": f"Successfully authenticated as @{username}. You can close this window."
        })