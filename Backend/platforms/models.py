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


# -------------------- Admin-managed credentials --------------------
class PlatformCredential(models.Model):
    """
    Global (app-owned) credentials for each platform.
    Managed via Django admin — users never see or touch these.
    """
    platform         = models.CharField(max_length=20, choices=Platform.choices)
    label            = models.CharField(max_length=100)  # e.g. "Main Twitter"
    encrypted_token  = EncryptedTextField()               # API key / bot token / webhook URL
    encrypted_secret = EncryptedTextField(null=True, blank=True)  # API secret if needed
    extra_config     = models.JSONField(default=dict, blank=True)  # e.g. {"subreddit": "python"}
    is_active        = models.BooleanField(default=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("platform", "label")
        ordering = ["platform", "label"]

    def __str__(self):
        return f"{self.get_platform_display()} — {self.label}"


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
    user         = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="posts"
    )
    content      = models.TextField()
    media_urls   = models.JSONField(default=list, blank=True)
    scheduled_at = models.DateTimeField(db_index=True)
    status       = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.QUEUED,
        db_index=True,
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

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
    published_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("post", "platform")
        ordering = ["platform"]

    def __str__(self):
        return f"Post #{self.post_id} → {self.platform} ({self.status})"