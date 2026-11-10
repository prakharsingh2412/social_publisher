import logging
from .base import BasePublisher, Payload, PublishResult

log = logging.getLogger(__name__)


class DryRunPublisher(BasePublisher):
    """Logs the payload instead of hitting a real API. Used when PUBLISH_DRY_RUN=True.

    Inherits validation rules from the real publisher for `platform`, so
    dry-run catches the same content/media violations production would.
    """

    def __init__(self, platform: str):
        self.platform = platform

        from . import PUBLISHERS                    # local import — avoids circular
        cls = PUBLISHERS.get(platform)
        if cls is not None:
            real = cls()
            self.max_content_length = real.max_content_length
            self.requires_media     = real.requires_media
            self.max_media_count    = real.max_media_count
            self.media_kind         = real.media_kind

    def publish(self, credential, payload: Payload) -> PublishResult:
        log.info(
            "[DRY-RUN %s] content=%r media=%d title=%r",
            self.platform, payload.content[:80], len(payload.media_urls), payload.title,
        )
        return PublishResult(platform_post_id=f"dryrun-{self.platform}")