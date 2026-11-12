import os
import tempfile
import requests
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from .base import BasePublisher, Payload, PublishResult, TransientError, PermanentError

class YouTubePublisher(BasePublisher):
    platform = "youtube"
    max_content_length = 5000
    requires_media = True
    media_kind = "video"

    def refresh(self, credential) -> None:
        """Refreshes the OAuth token using the refresh token."""
        refresh_token = credential.encrypted_secret
        if not refresh_token:
            raise PermanentError("YouTube refresh token missing. Please reconnect.")

        res = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        
        if res.status_code != 200:
            raise PermanentError(f"Failed to refresh YouTube token: {res.text}")

        new_tokens = res.json()
        credential.encrypted_token = new_tokens["access_token"]
        
        # Google sometimes returns a new refresh token, keep it if so
        if "refresh_token" in new_tokens:
            credential.encrypted_secret = new_tokens["refresh_token"]
            
        credential.token_expires_at = timezone.now() + timedelta(seconds=new_tokens.get("expires_in", 3600))
        credential.save()

    def _get_authenticated_service(self, credential):
        """Refreshes token if needed and returns the YouTube API client."""
        # Check if token is expired (or expires in the next 5 minutes)
        if credential.token_expires_at and credential.token_expires_at <= timezone.now() + timedelta(minutes=5):
            self.refresh(credential)

        creds = Credentials(token=credential.encrypted_token)
        return build("youtube", "v3", credentials=creds)

    def publish(self, credential, payload: Payload) -> PublishResult:
        if not payload.media_urls:
            raise PermanentError("YouTube requires a video URL.")
        
        video_url = payload.media_urls[0]
        youtube = self._get_authenticated_service(credential)

        # 1. Download the video from the provided URL to a temp file
        try:
            video_res = requests.get(video_url, stream=True, timeout=30)
            video_res.raise_for_status()
            
            # Create a temporary file
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            for chunk in video_res.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_file.close()
        except Exception as e:
            raise TransientError(f"Failed to download video from URL: {e}")

        # 2. Prepare metadata
        lines = payload.content.strip().split("\n")
        title = lines[0][:100] if lines else "New Video"
        description = payload.content

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22" # 22 is 'People & Blogs'
            },
            "status": {
                "privacyStatus": "public", 
                "selfDeclaredMadeForKids": False
            }
        }

        # 3. Upload to YouTube
        try:
            media = MediaFileUpload(tmp_file.name, chunksize=-1, resumable=True)
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                
            video_id = response.get("id")
            return PublishResult(platform_post_id=video_id, raw=response)

        except HttpError as e:
            raise PermanentError(f"YouTube API error: {e.content.decode()}")
        except Exception as e:
            raise TransientError(f"YouTube upload failed: {str(e)}")
        finally:
            # Always clean up the temp file
            if os.path.exists(tmp_file.name):
                os.remove(tmp_file.name)