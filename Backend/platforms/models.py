from django.db import models
from django.contrib.auth.models import User
from fernet_fields import EncryptedTextField


# -------------------- Platform choices --------------------
class Platform(models.TextChoices):
    YOUTUBE   = "youtube",   "YouTube"
    FACEBOOK  = "facebook",  "Facebook"
    TWITTER   = "twitter",   "Twitter / X"
    DISCORD   = "discord",   "Discord"
    REDDIT    = "reddit",    "Reddit"
    INSTAGRAM = "instagram", "Instagram"
    LINKEDIN  = "linkedin",  "LinkedIn"


# -------------------- Per-user platform credentials --------------------
class PlatformCredential(models.Model):
    """OAuth credential, owned by a specific user (one per platform per user)."""
    user             = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="platform_credentials",
    )
    platform         = models.CharField(max_length=20, choices=Platform.choices)
    label            = models.CharField(max_length=100)
    encrypted_token  = EncryptedTextField()
    encrypted_secret = EncryptedTextField(null=True, blank=True)
    extra_config     = models.JSONField(default=dict, blank=True)
    is_active        = models.BooleanField(default=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "platform")
        ordering = ["platform", "label"]

    def __str__(self):
        return f"{self.user.username} — {self.get_platform_display()} — {self.label}"


# -------------------- Post statuses --------------------
class PostStatus(models.TextChoices):
    DRAFT      = "draft",      "Draft"
    QUEUED     = "queued",     "Queued"
    PUBLISHING = "publishing", "Publishing"
    PUBLISHED  = "published",  "Published"
    PARTIAL    = "partial",    "Partially Published"
    FAILED     = "failed",     "Failed"


# -------------------- Post --------------------
class Post(models.Model):
    user              = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="posts"
    )
    title             = models.CharField(max_length=300, blank=True, null=True)
    content           = models.TextField()
    content_overrides = models.JSONField(default=dict, blank=True)
    media_urls        = models.JSONField(default=list, blank=True)
    scheduled_at      = models.DateTimeField(null=True, blank=True, db_index=True)
    status            = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.QUEUED,
        db_index=True,
    )
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post #{self.pk} by {self.user.username} ({self.status})"


# -------------------- Per-platform result --------------------
class PostPlatformResult(models.Model):
    post             = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="platform_results"
    )
    platform         = models.CharField(max_length=20, choices=Platform.choices)
    credential       = models.ForeignKey(
        PlatformCredential,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    platform_post_id = models.CharField(max_length=255, null=True, blank=True)
    status           = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.QUEUED,
        db_index=True,
    )
    error_message    = models.TextField(null=True, blank=True)
    retry_count      = models.PositiveIntegerField(default=0)
    published_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("post", "platform")
        ordering = ["platform"]

    def __str__(self):
        return f"Post #{self.post_id} → {self.platform} ({self.status})"