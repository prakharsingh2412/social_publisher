import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Post, PostPlatformResult, PlatformCredential, PostStatus
from .publishers import (
    get_publisher, Payload, PublishResult,
    TransientError, PermanentError,
)

log = logging.getLogger(__name__)

MAX_RETRIES     = 3
RETRY_BACKOFF   = 60     # seconds; doubles each attempt

def _build_payload(post: Post, platform: str) -> Payload:
    content = (post.content_overrides or {}).get(platform, post.content)
    return Payload(
        content=content,
        media_urls=list(post.media_urls or []),
        title=post.title,
    )

def _rollup(post: Post) -> None:
    statuses = list(post.platform_results.values_list("status", flat=True))
    if not statuses:
        return

    published = statuses.count("published")
    failed    = statuses.count("failed")
    
    if published == len(statuses):
        post.status = PostStatus.PUBLISHED
    elif failed == len(statuses):
        post.status = PostStatus.FAILED
    elif published > 0:
        post.status = PostStatus.PARTIAL
    else:
        post.status = PostStatus.FAILED
        
    post.save(update_fields=["status", "updated_at"])

@shared_task
def scan_due_posts():
    """Periodic (Beat, every 60 s) — enqueue queued posts + rescue stuck ones."""
    now = timezone.now()
    stuck_cutoff = now - timedelta(minutes=15)

    queued = list(
        Post.objects.filter(status=PostStatus.QUEUED, scheduled_at__lte=now)
        .values_list("id", flat=True)
    )
    stuck = list(
        Post.objects.filter(
            status=PostStatus.PUBLISHING, updated_at__lte=stuck_cutoff
        ).values_list("id", flat=True)
    )
    for post_id in queued + stuck:
        publish_post_task.delay(post_id)
    return {"queued": len(queued), "stuck": len(stuck)}

@shared_task(bind=True, max_retries=MAX_RETRIES)
def publish_post_task(self, post_id: int):
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return {"status": "gone"}

    pending = post.platform_results.filter(
        status__in=[PostStatus.QUEUED, PostStatus.PUBLISHING]
    ).select_related("credential")

    if not pending.exists():
        _rollup(post)
        return {"status": "nothing-to-do"}

    post.status = PostStatus.PUBLISHING
    post.save(update_fields=["status", "updated_at"])

    retry_needed = False

    for result in pending:
        publisher = get_publisher(result.platform)
        payload   = _build_payload(post, result.platform)

        errors = publisher.validate(payload)
        if errors:
            print(f"❌ VALIDATION ERROR on {result.platform}: {errors}") # ADDED PRINT
            result.status        = PostStatus.FAILED
            result.error_message = "; ".join(errors)
            result.save()
            continue

        result.status = PostStatus.PUBLISHING
        result.save(update_fields=["status"])

        try:
            out: PublishResult = publisher.publish(result.credential, payload)
            result.status           = PostStatus.PUBLISHED
            result.platform_post_id = out.platform_post_id
            result.published_at     = timezone.now()
            result.error_message    = ""
            result.save()
            
            # ADDED PRINT ON SUCCESS
            print(f"✅ SUCCESS: Published to {result.platform}! (ID: {out.platform_post_id})")

        except TransientError as exc:
            # ADDED PRINT FOR TRANSIENT ERROR
            print(f"⚠️ TRANSIENT ERROR on {result.platform}: {exc}")
            result.retry_count  += 1
            result.error_message = str(exc)
            result.status        = PostStatus.QUEUED
            result.save()
            retry_needed = True

        except PermanentError as exc:
            # ADDED PRINT FOR PERMANENT ERROR
            print(f"❌ PERMANENT ERROR on {result.platform}: {exc}")
            result.status        = PostStatus.FAILED
            result.error_message = str(exc)
            result.save()

        except Exception as exc:
            # ADDED PRINT FOR UNEXPECTED ERROR
            log.exception("Unexpected error in %s publisher", result.platform)
            print(f"💥 UNEXPECTED ERROR on {result.platform}: {exc}")
            result.status        = PostStatus.FAILED
            result.error_message = f"Unexpected: {exc!r}"
            result.save()

    if retry_needed and self.request.retries < MAX_RETRIES:
        countdown = RETRY_BACKOFF * (2 ** self.request.retries)
        raise self.retry(countdown=countdown)

    if retry_needed:   # retries exhausted → mark remaining as failed
        post.platform_results.filter(status=PostStatus.QUEUED).update(
            status=PostStatus.FAILED
        )

    _rollup(post)
    return {"status": post.status}

@shared_task
def refresh_expiring_credentials():
    """Refresh OAuth tokens 30 min before expiry (LinkedIn / FB / IG)."""
    threshold = timezone.now() + timedelta(minutes=30)
    creds = PlatformCredential.objects.filter(
        is_active=True,
        token_expires_at__isnull=False,
        token_expires_at__lte=threshold,
    )
    refreshed = 0
    for cred in creds:
        try:
            get_publisher(cred.platform).refresh(cred)
            cred.save()
            refreshed += 1
        except Exception as exc:
            print(f"❌ Failed to refresh credential for {cred.platform}: {exc}") # ADDED PRINT
            log.exception("Failed to refresh credential for %s", cred.platform)
    return {"refreshed": refreshed}