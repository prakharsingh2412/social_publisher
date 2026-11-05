import requests
from .base import BasePublisher, Payload, PublishResult, TransientError, PermanentError

TWEET_URL = "https://api.twitter.com/2/tweets"

class TwitterPublisher(BasePublisher):
    platform = "twitter"
    max_content_length = 280
    max_media_count = 4
    media_kind = "image"

    def publish(self, credential, payload: Payload) -> PublishResult:
        # OAuth 2.0 uses Bearer token authentication
        token = self._token(credential)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Basic text tweet (Media upload via OAuth 2.0 is different, skipping for now)
        body = {"text": payload.content}
        
        if payload.media_urls:
            # NOTE: X v2 media upload requires a different flow. 
            # For now, we block media to prevent silent failures.
            raise PermanentError("Twitter media upload is not yet implemented for OAuth 2.0.")

        try:
            r = requests.post(TWEET_URL, json=body, headers=headers, timeout=15)
        except requests.RequestException as e:
            raise TransientError(f"twitter tweet network: {e}") from e

        if r.status_code == 429:
            raise TransientError("twitter rate limit")
        if r.status_code >= 500:
            raise TransientError(f"twitter {r.status_code}")
        if r.status_code >= 400:
            raise PermanentError(f"twitter {r.status_code}: {r.text[:300]}")

        data = r.json()
        return PublishResult(
            platform_post_id=data["data"]["id"], raw=data
        )

    def refresh(self, credential) -> None:
        """Refresh the OAuth 2.0 token using the refresh token."""
        import base64, requests
        from django.conf import settings
        from django.utils import timezone
        
        refresh_token = self._secret(credential)
        if not refresh_token:
            raise PermanentError("No refresh token available.")

        token_url = "https://api.twitter.com/2/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.TWITTER_CLIENT_ID,
        }
        
        auth_str = f"{settings.TWITTER_CLIENT_ID}:{settings.TWITTER_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            r = requests.post(token_url, data=data, headers=headers, timeout=15)
        except requests.RequestException as e:
            raise TransientError(f"twitter refresh network: {e}") from e
            
        if r.status_code >= 400:
            raise PermanentError(f"twitter refresh failed: {r.text[:200]}")

        tokens = r.json()
        credential.encrypted_token = tokens["access_token"]
        if "refresh_token" in tokens:
            credential.encrypted_secret = tokens["refresh_token"]
        
        expires_in = tokens.get("expires_in", 7200)
        credential.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)