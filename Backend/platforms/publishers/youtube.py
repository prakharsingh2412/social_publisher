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
        
        if "refresh_token" in new_tokens:
            credential.encrypted_secret = new_tokens["refresh_token"]
            
        credential.token_expires_at = timezone.now() + timedelta(seconds=new_tokens.get("expires_in", 3600))
        credential.save()

    def _get_authenticated_service(self, credential):
        """Refreshes token if needed and returns the YouTube API client."""
        if credential.token_expires_at and credential.token_expires_at <= timezone.now() + timedelta(minutes=5):
            self.refresh(credential)

        # FIXED: Provide ALL required fields so Google's library doesn't crash mid-upload
        creds = Credentials(
            token=credential.encrypted_token,
            refresh_token=credential.encrypted_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.YOUTUBE_CLIENT_ID,
            client_secret=settings.YOUTUBE_CLIENT_SECRET
        )
        return build("youtube", "v3", credentials=creds)

    def publish(self, credential, payload: Payload) -> PublishResult:
        if not payload.media_urls:
            raise PermanentError("YouTube requires a video URL.")
        
        video_url = payload.media_urls[0]
        youtube = self._get_authenticated_service(credential)

        tmp_file_path = None
        media = None # Keep a reference to explicitly delete it later

        # 1. Download the video from the provided URL to a temp file
        try:
            download_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            video_res = requests.get(video_url, headers=download_headers, stream=True, timeout=30)
            video_res.raise_for_status()
            
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp_file_path = tmp_file.name
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
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public", 
                "selfDeclaredMadeForKids": False
            }
        }

        # 3. Upload to YouTube
        try:
            media = MediaFileUpload(tmp_file_path, chunksize=-1, resumable=True)
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
            # FIXED: Safely delete the file on Windows
            if media:
                del media # Release the handle
            
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.remove(tmp_file_path)
                except PermissionError:
                    # Windows sometimes holds a lock on the file for a few seconds. 
                    # We ignore it; the OS will clean up the Temp folder eventually.
                    pass 