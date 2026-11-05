from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class PublishError(Exception):
    """Base for all publisher errors."""


class TransientError(PublishError):
    """Network / 5xx / rate-limit — safe to retry."""


class PermanentError(PublishError):
    """Bad token / invalid content / 4xx — do NOT retry."""


@dataclass
class Payload:
    content: str
    media_urls: list[str] = field(default_factory=list)
    title: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishResult:
    platform_post_id: str
    raw: dict[str, Any] = field(default_factory=dict)


class BasePublisher(ABC):
    platform: str = ""
    max_content_length: int | None = None
    requires_media: bool = False
    media_kind: str | None = None         # "image" | "video" | None
    max_media_count: int = 0              # 0 = unlimited / N/A

    def validate(self, payload: Payload) -> list[str]:
        """Return list of human-readable validation errors. Empty = OK."""
        errors: list[str] = []
        if self.max_content_length and len(payload.content) > self.max_content_length:
            errors.append(
                f"{self.platform}: content is {len(payload.content)} chars, "
                f"max {self.max_content_length}"
            )
        if self.requires_media and not payload.media_urls:
            errors.append(f"{self.platform}: requires at least one media URL")
        if self.max_media_count and len(payload.media_urls) > self.max_media_count:
            errors.append(
                f"{self.platform}: {len(payload.media_urls)} media, "
                f"max {self.max_media_count}"
            )
        return errors

    @abstractmethod
    def publish(self, credential, payload: Payload) -> PublishResult:
        """Do the actual API call. Raise Transient/PermanentError on failure."""

    def refresh(self, credential) -> None:
        """Override for OAuth platforms. Update credential in-memory; caller saves."""
        raise PermanentError(f"{self.platform}: refresh not implemented")

    # ── helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _token(credential) -> str:
        """EncryptedTextField decrypts transparently on read."""
        return str(credential.encrypted_token)

    @staticmethod
    def _secret(credential) -> str:
        return str(credential.encrypted_secret or "")