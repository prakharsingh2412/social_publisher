from rest_framework import serializers
from .models import (
    PlatformCredential, Platform,
    Post, PostPlatformResult, PostStatus,
)


# ============================================================
# PLATFORM SERIALIZERS  (public — never expose tokens)
# ============================================================

class PlatformCredentialPublicSerializer(serializers.ModelSerializer):
    """
    Safe-for-users representation of a credential.
    Deliberately OMITS encrypted_token, encrypted_secret, extra_config.
    Users see which platforms exist; they never see the secrets.
    """
    platform_display = serializers.CharField(
        source="get_platform_display", read_only=True
    )

    class Meta:
        model  = PlatformCredential
        fields = ("id", "platform", "platform_display", "label", "is_active")
        read_only_fields = fields


# ============================================================
# POST RESULT SERIALIZER  (read-only nested output)
# ============================================================

class PostPlatformResultSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PostPlatformResult
        fields = (
            "id", "platform", "status",
            "platform_post_id", "published_at", "error_message",
        )
        read_only_fields = fields


# ============================================================
# POST SERIALIZERS
# ============================================================

class PostSerializer(serializers.ModelSerializer):
    """
    READ serializer — used for list, detail, and create-response.
    Includes nested platform results + author username.
    """
    platform_results = PostPlatformResultSerializer(many=True, read_only=True)
    author           = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model  = Post
        fields = (
            "id", "author", "content", "media_urls",
            "scheduled_at", "status", "platform_results",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "author", "status", "platform_results",
            "created_at", "updated_at",
        )


class PostCreateSerializer(serializers.ModelSerializer):
    """
    WRITE serializer — used only for POST /api/posts/.
    Accepts `platforms: ["discord", "twitter"]` and creates
    one PostPlatformResult per requested platform.
    """
    platforms = serializers.ListField(
        child=serializers.ChoiceField(choices=Platform.choices),
        write_only=True,
        min_length=1,
    )

    class Meta:
        model  = Post
        fields = ("id", "content", "media_urls", "scheduled_at", "platforms")
        read_only_fields = ("id",)

    def validate_platforms(self, value):
        # De-duplicate while preserving order
        seen, unique = set(), []
        for p in value:
            if p not in seen:
                seen.add(p)
                unique.append(p)

        # Every requested platform must have an active credential
        active = set(
            PlatformCredential.objects
            .filter(is_active=True, platform__in=unique)
            .values_list("platform", flat=True)
        )
        missing = set(unique) - active
        if missing:
            raise serializers.ValidationError(
                f"No active credential configured for: {', '.join(sorted(missing))}"
            )
        return unique

    def create(self, validated_data):
        platforms = validated_data.pop("platforms")
        user      = self.context["request"].user

        post = Post.objects.create(user=user, **validated_data)

        # Attach the active credential for each requested platform
        creds = {
            c.platform: c
            for c in PlatformCredential.objects.filter(
                is_active=True, platform__in=platforms
            )
        }
        PostPlatformResult.objects.bulk_create([
            PostPlatformResult(
                post=post,
                platform=p,
                credential=creds.get(p),
                status=PostStatus.QUEUED,
            )
            for p in platforms
        ])
        return post


class PublishNowSerializer(serializers.Serializer):
    """Empty body — exists only so Swagger shows a request schema."""
    pass