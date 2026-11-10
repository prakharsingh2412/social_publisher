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
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema

from .models import PlatformCredential, Post, PostStatus, Platform
from .serializers import (
    PlatformCredentialPublicSerializer,
    PostSerializer,
    PostCreateSerializer,
    PublishNowSerializer,
)

from .oauth_utils import (
    OAuthError,
    consume_state,
    exchange_code_for_user_token,
    exchange_for_long_lived_token,
    issue_state,
    list_pages,
    oauth_respond,
)

User = get_user_model()

# ============================================================
# PLATFORMS  — public listing
# ============================================================

class PlatformListView(generics.ListAPIView):
    serializer_class   = PlatformCredentialPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PlatformCredential.objects.filter(
            user=self.request.user,     
            is_active=True,
        )


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
    permission_classes = [IsAuthenticated]   # was AllowAny — JWT required

    def get(self, request):
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip("=")
        )
        state = issue_state(
            request.user.id, platform="twitter", code_verifier=code_verifier
        )

        params = {
            "response_type": "code",
            "client_id": settings.TWITTER_CLIENT_ID,
            "redirect_uri": settings.TWITTER_REDIRECT_URI,
            "scope": "tweet.read tweet.write users.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return Response(
            {"auth_url": f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"}
        )


class TwitterOAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if request.GET.get("error"):
            return oauth_respond(
                "twitter", False,
                request.GET.get("error_description", request.GET["error"]),
            )

        code = request.GET.get("code")
        state = request.GET.get("state")

        data = consume_state(state)
        if not data or data.get("platform") != "twitter":
            return oauth_respond("twitter", False, "Invalid or expired state.")

        code_verifier = data.get("code_verifier")
        user = User.objects.filter(pk=data["user_id"]).first()
        if user is None or not code_verifier:
            return oauth_respond("twitter", False, "Session expired. Try again.")

        auth_str = f"{settings.TWITTER_CLIENT_ID}:{settings.TWITTER_CLIENT_SECRET}"
        headers = {
            "Authorization": "Basic " + base64.b64encode(auth_str.encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = requests.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.TWITTER_CLIENT_ID,
                "redirect_uri": settings.TWITTER_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            headers=headers,
            timeout=20,
        )
        if resp.status_code != 200:
            return oauth_respond("twitter", False, f"Token exchange failed: {resp.text[:200]}")

        tokens = resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in")

        me = requests.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        username = (
            me.json().get("data", {}).get("username", "unknown")
            if me.status_code == 200 else "unknown"
        )

        credential, _ = PlatformCredential.objects.update_or_create(
            user=user,                      # ← the critical fix
            platform=Platform.TWITTER,
            defaults={
                "label": f"@{username}",
                "encrypted_token": access_token,
                "encrypted_secret": refresh_token,   # store refresh token here
                "extra_config": {"username": username},
                "is_active": True,
                "token_expires_at": (
                    timezone.now() + timedelta(seconds=expires_in)
                    if expires_in else None
                ),
            },
        )
        return oauth_respond("twitter", True, f"Connected @{username}.", label=credential.label)

# ============================================================
# STEP 1 (updated) — login URL generation
# ============================================================

class MetaOAuthLoginView(APIView):
    permission_classes = [IsAuthenticated]
    platform_name = None
    scopes: list[str] = []
    redirect_uri_setting = None

    def get(self, request):
        state = issue_state(request.user.id, platform=self.platform_name)

        params = {
            "client_id": settings.FACEBOOK_APP_ID,
            "redirect_uri": getattr(settings, self.redirect_uri_setting),
            "state": state,
            "response_type": "code",
            "scope": ",".join(self.scopes),
        }
        auth_url = "https://www.facebook.com/v19.0/dialog/oauth?" + urlencode(params)
        return Response({"auth_url": auth_url})


class FacebookLoginView(MetaOAuthLoginView):
    platform_name = "facebook"
    redirect_uri_setting = "FACEBOOK_REDIRECT_URI"
    scopes = [
        "public_profile",
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "business_management",
    ]


class InstagramLoginView(MetaOAuthLoginView):
    platform_name = "instagram"
    redirect_uri_setting = "INSTAGRAM_REDIRECT_URI"
    scopes = [
        "public_profile",
        "pages_show_list",
        "pages_read_engagement",
        "instagram_basic",
        "instagram_content_publish",
        "business_management",
    ]


# ============================================================
# STEP 2 — Meta callbacks
# ============================================================

class MetaOAuthCallbackView(APIView):
    """
    Shared handshake:
      code → short-lived user token → long-lived user token → /me/accounts
    Subclasses pick the right Page and decide what to persist.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    platform: str = None
    redirect_uri_setting: str = None

    def get(self, request):
        # User clicked "Cancel" on the Facebook dialog
        if request.GET.get("error"):
            return oauth_respond(
                self.platform, False,
                request.GET.get("error_description", request.GET["error"]),
            )

        code = request.GET.get("code")
        state = request.GET.get("state")
        if not code or not state:
            return oauth_respond(self.platform, False, "Missing code or state.")

        data = consume_state(state)
        if not data:
            return oauth_respond(
                self.platform, False,
                "Invalid or expired state. Please start the connection again.",
            )

        user = User.objects.filter(pk=data["user_id"]).first()
        if user is None:
            return oauth_respond(self.platform, False, "User no longer exists.")

        try:
            short_token = exchange_code_for_user_token(
                code, getattr(settings, self.redirect_uri_setting)
            )
            long_token, _expires_in = exchange_for_long_lived_token(short_token)
            pages = list_pages(long_token)
        except OAuthError as e:
            return oauth_respond(self.platform, False, str(e))

        page = self.select_page(pages)
        if page is None:
            return oauth_respond(self.platform, False, self.no_page_message())

        try:
            credential = self.save_credential(user, page)
        except Exception as e:  # IntegrityError, encryption misconfig, etc.
            return oauth_respond(self.platform, False, f"Could not save credential: {e}")

        return oauth_respond(
            self.platform, True,
            f"Connected {credential.label}.",
            label=credential.label,
        )

    # ── subclass hooks ────────────────────────────────────────────────────────
    def select_page(self, pages: list[dict]) -> dict | None:
        raise NotImplementedError

    def no_page_message(self) -> str:
        return "No eligible Facebook Page found."

    def save_credential(self, user, page: dict) -> PlatformCredential:
        raise NotImplementedError


class FacebookOAuthCallbackView(MetaOAuthCallbackView):
    platform = "facebook"
    redirect_uri_setting = "FACEBOOK_REDIRECT_URI"

    def select_page(self, pages):
        return pages[0] if pages else None

    def no_page_message(self):
        return (
            "No Facebook Page found on this account. Meta's API blocks posting "
            "to personal profiles — create a Page first, then reconnect."
        )

    def save_credential(self, user, page):
        # Page tokens minted from a long-lived user token do not expire,
        # so token_expires_at stays None.
        credential, _created = PlatformCredential.objects.update_or_create(
            user=user,
            platform=Platform.FACEBOOK,
            defaults={
                "label": f"Facebook Page: {page['name']}",
                "encrypted_token": page["access_token"],
                "encrypted_secret": None,
                "extra_config": {
                    "page_id": page["id"],
                    "page_name": page["name"],
                },
                "is_active": True,
                "token_expires_at": None,
            },
        )
        return credential


class InstagramOAuthCallbackView(MetaOAuthCallbackView):
    platform = "instagram"
    redirect_uri_setting = "INSTAGRAM_REDIRECT_URI"

    def select_page(self, pages):
        # Instagram publishing requires a Page that owns an IG Business account
        for p in pages:
            if p.get("instagram_business_account"):
                return p
        return None

    def no_page_message(self):
        return (
            "No Instagram Business account linked to a Facebook Page. "
            "Convert the IG account to Business/Creator, link it to a Page, then reconnect."
        )

    def save_credential(self, user, page):
        ig = page["instagram_business_account"]
        credential, _created = PlatformCredential.objects.update_or_create(
            user=user,
            platform=Platform.INSTAGRAM,
            defaults={
                "label": f"Instagram: @{ig.get('username', ig['id'])}",
                # Page token is what the IG Graph endpoints expect
                "encrypted_token": page["access_token"],
                "encrypted_secret": None,
                "extra_config": {
                    "page_id": page["id"],
                    "ig_user_id": ig["id"],
                    "ig_username": ig.get("username"),
                },
                "is_active": True,
                "token_expires_at": None,
            },
        )
        return credential