import requests
from .base import BasePublisher, Payload, PublishResult, TransientError, PermanentError

GRAPH = "https://graph.facebook.com/v19.0"


class FacebookPublisher(BasePublisher):
    platform = "facebook"
    max_content_length = 63_206
    max_media_count = 10
    media_kind = "image"

    def publish(self, credential, payload: Payload) -> PublishResult:
        cfg = credential.extra_config or {}
        page_id = cfg.get("page_id")
        if not page_id:
            raise PermanentError("facebook credential missing extra_config.page_id")

        token = self._token(credential)

        if not payload.media_urls:
            # Text-only feed post
            try:
                r = requests.post(
                    f"{GRAPH}/{page_id}/feed",
                    data={"message": payload.content, "access_token": token},
                    timeout=20,
                )
            except requests.RequestException as e:
                raise TransientError(f"facebook network: {e}") from e
        else:
            # One photo post; extra media can be attached later.
            try:
                r = requests.post(
                    f"{GRAPH}/{page_id}/photos",
                    data={
                        "url": payload.media_urls[0],
                        "caption": payload.content,
                        "access_token": token,
                    },
                    timeout=30,
                )
            except requests.RequestException as e:
                raise TransientError(f"facebook photo network: {e}") from e

        if r.status_code == 429 or (r.status_code >= 500):
            raise TransientError(f"facebook {r.status_code}: {r.text[:200]}")
        if r.status_code >= 400:
            raise PermanentError(f"facebook {r.status_code}: {r.text[:300]}")

        body = r.json()
        return PublishResult(platform_post_id=str(body.get("id", "")), raw=body)

    def refresh(self, credential) -> None:
        # Long-lived Page token exchange. Requires app_id + app_secret in extra_config,
        # and the current short-lived user token in encrypted_token.
        import datetime, requests
        from django.utils import timezone
        cfg = credential.extra_config or {}
        try:
            r = requests.get(
                f"{GRAPH}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": cfg["app_id"],
                    "client_secret": cfg["app_secret"],
                    "fb_exchange_token": self._token(credential),
                },
                timeout=15,
            )
        except requests.RequestException as e:
            raise TransientError(f"facebook refresh network: {e}") from e
        if r.status_code >= 400:
            raise PermanentError(f"facebook refresh: {r.status_code} {r.text[:200]}")
        j = r.json()
        credential.encrypted_token = j["access_token"]
        credential.token_expires_at = timezone.now() + datetime.timedelta(
            seconds=j.get("expires_in", 60 * 24 * 3600)
        )