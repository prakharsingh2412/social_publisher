import base64
import requests
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

from .base import BasePublisher, Payload, PublishResult, TransientError, PermanentError

TWEET_URL = "https://api.twitter.com/2/tweets"
MEDIA_UPLOAD_URL = "https://api.twitter.com/2/media/upload"

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

        media_ids = []

        # Step 1: Upload media if present
        if payload.media_urls:
            # Twitter allows a max of 4 images
            for url in payload.media_urls[:self.max_media_count]:
                try:
                    # Download the image from the public URL
                    img_response = requests.get(url, timeout=30)
                    img_response.raise_for_status()
                    
                    # Base64 encode the image for Twitter's simple upload
                    media_payload = {
                        "media": base64.b64encode(img_response.content).decode('utf-8'),
                        "media_category": "tweet_image"
                    }
                    
                    upload_res = requests.post(
                        MEDIA_UPLOAD_URL,
                        json=media_payload,
                        headers=headers,
                        timeout=60
                    )
                    
                    if upload_res.status_code not in (200, 201):
                        raise PermanentError(
                            f"twitter media upload failed: {upload_res.status_code} - {upload_res.text[:200]}"
                        )
                    
                    # Extract the media_id
                    media_data = upload_res.json().get("data", {})
                    media_id = media_data.get("id") or media_data.get("media_id_string")
                    
                    if not media_id:
                        raise PermanentError(f"twitter media upload missing ID: {upload_res.text[:200]}")
                        
                    media_ids.append(str(media_id))

                except requests.RequestException as e:
                    raise TransientError(f"twitter media download/upload network: {e}") from e

        # Step 2: Create the tweet
        body = {"text": payload.content}
        
        # Attach the uploaded media IDs to the tweet
        if media_ids:
            body["media"] = {"media_ids": media_ids}

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
        credential.token_expires_at = timezone.now() + timedelta(seconds=expires_in)