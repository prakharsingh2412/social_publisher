import time
import requests
from .base import BasePublisher, Payload, PublishResult, TransientError, PermanentError

GRAPH = "https://graph.facebook.com/v19.0"


class InstagramPublisher(BasePublisher):
    platform = "instagram"
    max_content_length = 2_200
    requires_media = True
    max_media_count = 10
    media_kind = "image"

    def publish(self, credential, payload: Payload) -> PublishResult:
        cfg = credential.extra_config or {}
        ig_user_id = cfg.get("ig_user_id")
        if not ig_user_id:
            raise PermanentError("instagram credential missing extra_config.ig_user_id")
        if not payload.media_urls:
            raise PermanentError("instagram requires at least one public image URL")

        token = self._token(credential)
        # Instagram only accepts a *publicly reachable* URL — no local files.
        # 1) Create media container
        try:
            r = requests.post(
                f"{GRAPH}/{ig_user_id}/media",
                data={
                    "image_url": payload.media_urls[0],
                    "caption": payload.content,
                    "access_token": token,
                },
                timeout=20,
            )
        except requests.RequestException as e:
            raise TransientError(f"instagram container network: {e}") from e
        if r.status_code == 429 or r.status_code >= 500:
            raise TransientError(f"instagram container {r.status_code}")
        if r.status_code >= 400:
            raise PermanentError(
                f"instagram container {r.status_code}: {r.text[:300]}"
            )
        container_id = r.json()["id"]

        # 2) Poll the container until it's FINISHED (usually < 5 s)
        for _ in range(6):
            time.sleep(2)
            try:
                s = requests.get(
                    f"{GRAPH}/{container_id}",
                    params={"fields": "status_code", "access_token": token},
                    timeout=10,
                )
            except requests.RequestException as e:
                raise TransientError(f"instagram status network: {e}") from e
            status = s.json().get("status_code")
            if status == "FINISHED":
                break
            if status == "ERROR":
                raise PermanentError(f"instagram container error: {s.text[:300]}")
        else:
            raise TransientError("instagram container not ready after 12 s")

        # 3) Publish the container
        try:
            pub = requests.post(
                f"{GRAPH}/{ig_user_id}/media_publish",
                data={"creation_id": container_id, "access_token": token},
                timeout=20,
            )
        except requests.RequestException as e:
            raise TransientError(f"instagram publish network: {e}") from e
        if pub.status_code == 429 or pub.status_code >= 500:
            raise TransientError(f"instagram publish {pub.status_code}")
        if pub.status_code >= 400:
            raise PermanentError(
                f"instagram publish {pub.status_code}: {pub.text[:300]}"
            )
        body = pub.json()
        return PublishResult(platform_post_id=str(body.get("id", "")), raw=body)