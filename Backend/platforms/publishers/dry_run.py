import logging
from .base import BasePublisher, Payload, PublishResult

log = logging.getLogger(__name__)


class DryRunPublisher(BasePublisher):
    """Logs the payload instead of hitting a real API. Used when PUBLISH_DRY_RUN=True."""

    def __init__(self, platform: str):
        self.platform = platform

    def publish(self, credential, payload: Payload) -> PublishResult:
        log.info(
            "[DRY-RUN %s] content=%r media=%d title=%r",
            self.platform, payload.content[:80], len(payload.media_urls), payload.title,
        )
        return PublishResult(platform_post_id=f"dryrun-{self.platform}")