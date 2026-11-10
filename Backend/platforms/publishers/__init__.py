from django.conf import settings

from .base import (
    BasePublisher, Payload, PublishResult,
    PublishError, TransientError, PermanentError,
)

# ── active ──────────────────────────────────────────────────
from .facebook  import FacebookPublisher
from .instagram import InstagramPublisher
from .twitter   import TwitterPublisher
from .youtube   import YouTubePublisher
from .dry_run   import DryRunPublisher          # ← uncommented

# ── disabled for now (files not present yet) ────────────────
# from .discord   import DiscordPublisher
# from .reddit    import RedditPublisher
# from .linkedin  import LinkedInPublisher


PUBLISHERS: dict[str, type[BasePublisher]] = {
    p.platform: p for p in (
        FacebookPublisher,
        InstagramPublisher,
        TwitterPublisher,
        YouTubePublisher,
    )
}


def get_publisher(platform: str) -> BasePublisher:
    if settings.PUBLISH_DRY_RUN:
        return DryRunPublisher(platform)         # ← simplified, no try/except needed

    cls = PUBLISHERS.get(platform)
    if cls is None:
        raise PermanentError(f"No publisher registered for '{platform}'")
    return cls()


__all__ = [
    "BasePublisher", "Payload", "PublishResult",
    "PublishError", "TransientError", "PermanentError",
    "PUBLISHERS", "get_publisher",
]