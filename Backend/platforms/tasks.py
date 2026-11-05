import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Post, PostPlatformResult, PlatformCredential
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
    published = statuses.count(PostPlatformResult.Status.PUBLISHED) \
        if hasattr(PostPlatformResult, "Status") \
        else statuses.count(Post.Status.PUBLISHED)

    published = statuses.count("published")
    failed    = statuses.count("failed")
    if published == len(statuses):
        post.status = Post.Status.PUBLISHED
    elif failed == len(statuses):
        post.status = Post.Status.FAILED
    elif published:
        post.status = Post.Status.PARTIAL
    else:
        post.status = Post.Status.FAILED
    post.save(update_fields=["status", "updated_at"])


@shared_task
def scan_due_posts():
    """Periodic (Beat, every 60 s) — enqueue queued posts + rescue stuck ones."""
    now = timezone.now()
    stuck_cutoff = now - timedelta(minutes=15)

    queued = list(
        Post.objects.filter(status=Post.Status.QUEUED, scheduled_at__lte=now)
        .values_list("id", flat=True)
    )
    stuck = list(
        Post.objects.filter(
            status=Post.Status.PUBLISHING, updated_at__lte=stuck_cutoff
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
        status__in=[Post.Status.QUEUED, Post.Status.PUBLISHING]
    ).select_related("credential")

    if not pending.exists():
        _rollup(post)
        return {"status": "nothing-to-do"}

    post.status = Post.Status.PUBLISHING
    post.save(update_fields=["status", "updated_at"])

    retry_needed = False

    for result in pending:
        publisher = get_publisher(result.platform)
        payload   = _build_payload(post, result.platform)

        errors = publisher.validate(payload)
        if errors:
            result.status        = Post.Status.FAILED
            result.error_message = "; ".join(errors)
            result.save()
            continue

        result.status = Post.Status.PUBLISHING
        result.save(update_fields=["status", "updated_at"])

        try:
            out: PublishResult = publisher.publish(result.credential, payload)
            result.status           = Post.Status.PUBLISHED
            result.platform_post_id = out.platform_post_id
            result.published_at     = timezone.now()
            result.error_message    = ""
            result.save()

        except TransientError as exc:
            result.retry_count  += 1
            result.error_message = str(exc)
            result.status        = Post.Status.QUEUED
            result.save()
            retry_needed = True

        except PermanentError as exc:
            result.status        = Post.Status.FAILED
            result.error_message = str(exc)
            result.save()

        except Exception as exc:
            log.exception("Unexpected error in %s publisher", result.platform)
            result.status        = Post.Status.FAILED
            result.error_message = f"Unexpected: {exc!r}"
            result.save()

    if retry_needed and self.request.retries < MAX_RETRIES:
        countdown = RETRY_BACKOFF * (2 ** self.request.retries)
        raise self.retry(countdown=countdown)

    if retry_needed:   # retries exhausted → mark remaining as failed
        post.platform_results.filter(status=Post.Status.QUEUED).update(
            status=Post.Status.FAILED
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
        except Exception:
            log.exception("Failed to refresh credential for %s", cred.platform)
    return {"refreshed": refreshed}