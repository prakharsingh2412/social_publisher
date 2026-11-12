from django.utils import timezone
from rest_framework import serializers

from .models import (
    PlatformCredential, Platform,
    Post, PostPlatformResult, PostStatus,
)


# ============================================================
# PLATFORM SERIALIZERS  (public — never expose tokens)
# ============================================================

class PlatformCredentialPublicSerializer(serializers.ModelSerializer):
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
            "retry_count",
        )
        read_only_fields = fields


# ============================================================
# POST SERIALIZERS
# ============================================================

class PostSerializer(serializers.ModelSerializer):
    platform_results = PostPlatformResultSerializer(many=True, read_only=True)
    author           = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model  = Post
        fields = (
            "id", "author",
            "title", "content", "content_overrides",
            "media_urls", "scheduled_at", "status",
            "platform_results", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "author", "status", "platform_results",
            "created_at", "updated_at",
        )


class PostCreateSerializer(serializers.ModelSerializer):
    platforms = serializers.ListField(
        child=serializers.ChoiceField(choices=Platform.choices),
        write_only=True,
        min_length=1,
    )
    publish_now = serializers.BooleanField(write_only=True, default=False)
    
    # FIXED: Explicitly make scheduled_at optional
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model  = Post
        fields = (
            "id",
            "title", "content", "content_overrides",
            "media_urls", "scheduled_at",
            "platforms", "publish_now",
        )
        read_only_fields = ("id",)

    def validate_platforms(self, value):
        seen, unique = set(), []
        for p in value:
            if p not in seen:
                seen.add(p)
                unique.append(p)

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
        platforms   = validated_data.pop("platforms")
        publish_now = validated_data.pop("publish_now", False)
        user        = self.context["request"].user

        creds = {
            c.platform: c
            for c in PlatformCredential.objects.filter(
                is_active=True, platform__in=platforms
            )
        }


        scheduled_at = validated_data.get("scheduled_at")
        due = publish_now or (scheduled_at and scheduled_at <= timezone.now())
        
        validated_data["status"] = (
            PostStatus.QUEUED if due else PostStatus.DRAFT
        )

        post = Post.objects.create(user=user, **validated_data)

        PostPlatformResult.objects.bulk_create([
            PostPlatformResult(
                post=post,
                platform=p,
                credential=creds.get(p),
                status=PostStatus.QUEUED,
            )
            for p in platforms
        ])

        if due:
            from .tasks import publish_post_task
            publish_post_task.delay(post.id)

        return post


class PublishNowSerializer(serializers.Serializer):
    """Empty body — exists only so Swagger shows a request schema."""
    pass