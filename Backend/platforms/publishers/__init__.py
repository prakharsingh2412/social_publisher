from django.conf import settings

from .base import (
    BasePublisher, Payload, PublishResult,
    PublishError, TransientError, PermanentError,
)
from .discord import DiscordPublisher
from .reddit import RedditPublisher
from .twitter import TwitterPublisher
from .linkedin import LinkedInPublisher
from .facebook import FacebookPublisher
from .instagram import InstagramPublisher
from .dry_run import DryRunPublisher


PUBLISHERS: dict[str, type[BasePublisher]] = {
    p.platform: p for p in (
        DiscordPublisher, RedditPublisher, TwitterPublisher,
        LinkedInPublisher, FacebookPublisher, InstagramPublisher,
    )
}


def get_publisher(platform: str) -> BasePublisher:
    if settings.PUBLISH_DRY_RUN:
        return DryRunPublisher(platform)
    cls = PUBLISHERS.get(platform)
    if cls is None:
        raise PermanentError(f"No publisher registered for '{platform}'")
    return cls()


__all__ = [
    "BasePublisher", "Payload", "PublishResult",
    "PublishError", "TransientError", "PermanentError",
    "PUBLISHERS", "get_publisher",
]