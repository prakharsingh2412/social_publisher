# platforms/oauth_utils.py
import secrets
import urllib.parse

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect

GRAPH = "https://graph.facebook.com/v19.0"
STATE_TTL = 600  # 10 minutes — same as Step 1


class OAuthError(Exception):
    """Raised for any failure during the callback handshake."""


# ── state (CSRF) ──────────────────────────────────────────────────────────────

def issue_state(user_id: int, **extra) -> str:
    """Generate a random state, bind it to a user + arbitrary extras in Redis."""
    state = secrets.token_urlsafe(32)
    cache.set(f"oauth_state_{state}", {"user_id": user_id, **extra}, timeout=STATE_TTL)
    return state


def consume_state(state: str | None) -> dict | None:
    """Fetch-and-delete. State is single-use; replaying it fails."""
    if not state:
        return None
    key = f"oauth_state_{state}"
    data = cache.get(key)
    if data is not None:
        cache.delete(key)
    return data


# ── graph helpers ─────────────────────────────────────────────────────────────

def _graph_get(path: str, params: dict) -> dict:
    try:
        r = requests.get(f"{GRAPH}/{path.lstrip('/')}", params=params, timeout=20)
    except requests.RequestException as e:
        raise OAuthError(f"network error talking to Meta: {e}") from e
    if r.status_code >= 400:
        raise OAuthError(f"Meta API {r.status_code}: {r.text[:300]}")
    return r.json()


def exchange_code_for_user_token(code: str, redirect_uri: str) -> str:
    """Short-lived user token (~1 hour)."""
    data = _graph_get("oauth/access_token", {
        "client_id": settings.FACEBOOK_APP_ID,
        "client_secret": settings.FACEBOOK_APP_SECRET,
        "redirect_uri": redirect_uri,
        "code": code,
    })
    token = data.get("access_token")
    if not token:
        raise OAuthError("Meta did not return an access_token")
    return token


def exchange_for_long_lived_token(short_token: str) -> tuple[str, int | None]:
    """Long-lived user token (~60 days). Page tokens derived from this don't expire."""
    data = _graph_get("oauth/access_token", {
        "grant_type": "fb_exchange_token",
        "client_id": settings.FACEBOOK_APP_ID,
        "client_secret": settings.FACEBOOK_APP_SECRET,
        "fb_exchange_token": short_token,
    })
    return data.get("access_token", short_token), data.get("expires_in")


def list_pages(user_token: str) -> list[dict]:
    """
    Returns every Page the user manages, each with its own page access token
    and (if linked) the Instagram Business account attached to it.
    """
    data = _graph_get("me/accounts", {
        "access_token": user_token,
        "fields": "id,name,access_token,instagram_business_account{id,username}",
        "limit": 100,
    })
    return data.get("data", [])


# ── response helper ───────────────────────────────────────────────────────────

def oauth_respond(platform: str, ok: bool, message: str = "", **extra):
    """
    Redirects the browser back to the frontend if FRONTEND_OAUTH_REDIRECT is set,
    otherwise returns JSON (handy for Postman / local testing).
    """
    payload = {
        "platform": platform,
        "status": "success" if ok else "error",
        "message": message,
        **extra,
    }
    base = getattr(settings, "FRONTEND_OAUTH_REDIRECT", None)
    if base:
        sep = "&" if "?" in base else "?"
        return redirect(f"{base}{sep}{urllib.parse.urlencode(payload)}")
    return JsonResponse(payload, status=200 if ok else 400)