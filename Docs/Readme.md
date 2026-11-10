# Social Publisher API

A Django REST backend for scheduling and publishing content to multiple social media platforms — YouTube, Facebook, Twitter/X, and Instagram — from a single API.

> **Status:** Phase 1 — Auth + Posts API complete. OAuth integrations and Publishing engine (Celery + publishers) in progress.

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Project](#-running-the-project)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Data Models](#-data-models)
- [Publishing Pipeline (planned)](#-publishing-pipeline-planned)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🎯 Overview

**Social Publisher** is a multi-tenant SaaS backend that lets authenticated users compose a single post and publish it simultaneously to **their own** social media accounts (YouTube, Facebook, Twitter/X, and Instagram).

### How it Works (User Flow)

1. **Sign Up**: A user registers and logs into your Django application via JWT.
2. **Connect Accounts (OAuth)**: The user goes to a settings page and clicks "Connect Facebook", "Connect Twitter", etc. They are redirected to the platform's official OAuth screen, log in, and grant your app permission to post on their behalf.
3. **Store Tokens**: Your backend receives the OAuth callback, exchanges the code for an Access Token, and securely saves it in the database **tied to that specific user**.
4. **Publish**: When the user creates a post via your API, your Celery workers retrieve *their* specific tokens and publish to *their* specific accounts.

> **⚠️ Important Platform Note:** To publish to Facebook or Instagram via the API, the user must connect a **Facebook Page** (or an Instagram Business Account linked to a Page). Personal Facebook profiles are blocked by Meta's API.

---

## 🏗️ Architecture

```
┌──────────────┐        ┌──────────────┐        ┌───────────────────┐
│   Frontend   │──JWT──▶│  Django API  │───────▶│      MySQL        │
│  (React/etc) │◀───────│   (DRF)      │        │ (users, posts,    │
└──────────────┘        └──────────────┘        │  user_credentials)│
                               │                 └───────────────────┘
                               │ create post
                               ▼
                        ┌──────────────┐
                        │    Redis     │◀── Queue
                        └──────────────┘
                               │
                               ▼
                        ┌──────────────┐        ┌──────────────┐
                        │   Celery     │───────▶│  Platform    │
                        │   Worker     │        │  APIs        │
                        └──────────────┘        │ (Using the   │
                               ▲                │  USER'S      │
                               │ schedule       │  tokens)     │
                        ┌──────────────┐        └──────────────┘
                        │ Celery Beat  │
                        │ (every 60s)  │
                        └──────────────┘
```

**Flow:**
1. User creates a post via `POST /api/v1/posts/`.
2. Post row is saved with `status=queued`.
3. Celery Beat fires `scan_due_posts()` every 60s.
4. Due posts are enqueued as `publish_post_task(post_id)`.
5. Worker looks up the `Post.user`, retrieves *that user's* `PlatformCredential`, and calls the appropriate publisher.
6. Frontend polls `GET /api/v1/posts/{id}/` to see per-platform success/failure.

---

## 🧰 Tech Stack

| Layer | Technology | Version |
| :--- | :--- | :--- |
| **Framework** | Django | 4.2+ |
| **API** | Django REST Framework | 3.14+ |
| **Auth** | djangorestframework-simplejwt | 5.x |
| **Database** | MySQL | 8.0+ (utf8mb4) |
| **Encryption** | djfernet-redux (maintained fork of django-fernet-fields) | latest |
| **Docs** | drf-spectacular (OpenAPI 3 + Swagger UI) | 0.27+ |
| **Config** | python-decouple | 3.x |
| **CORS** | django-cors-headers | 4.x |
| **Queue** *(planned)* | Celery + Redis | 5.x / 7.x |
| **Scheduler** *(planned)* | django-celery-beat | 2.x |

---

## ⚙️ Configuration (`.env.example`)

```env
# Django
SECRET_KEY=your-super-secret-key-change-me-in-prod
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,your-ngrok-subdomain.ngrok-free.app
PUBLIC_BASE_URL=https://your-ngrok-subdomain.ngrok-free.app

# MySQL
DB_NAME=social_publisher
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

# Fernet encryption key
ENCRYPTION_KEY=your-fernet-key-change-me

# OAuth Credentials (App-Level)
# Meta (Facebook & Instagram)
FACEBOOK_APP_ID=...
FACEBOOK_APP_SECRET=...
FACEBOOK_REDIRECT_URI=http://localhost:8000/oauth/facebook/callback/
INSTAGRAM_REDIRECT_URI=https://your-ngrok-subdomain.ngrok-free.app/oauth/instagram/callback/

# Twitter / X
TWITTER_CLIENT_ID=...
TWITTER_CLIENT_SECRET=...
TWITTER_REDIRECT_URI=http://localhost:8000/oauth/twitter/callback/

# YouTube (Google)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
YOUTUBE_REDIRECT_URI=http://localhost:8000/oauth/youtube/callback/

# Publishing
PUBLISH_DRY_RUN=True
REDIS_URL=redis://localhost:6379/0
```

---

## 🗄️ Data Models

### `PlatformCredential` (Updated for Multi-User)

This model now links directly to the User. **Each user has their own set of credentials for each platform.**

| Field | Type | Notes |
| :--- | :--- | :--- |
| `user` | FK → User | **CRITICAL:** Ties this credential to a specific user |
| `platform` | enum | Which platform (facebook, twitter, youtube, instagram) |
| `label` | string | Human label e.g. "User's Facebook Page" |
| `encrypted_token` | EncryptedTextField | **Encrypted at rest** |
| `encrypted_secret` | EncryptedTextField (nullable) | Used for Twitter OAuth 1.0a or refresh tokens |
| `extra_config` | JSON | e.g. `{"page_id": "12345"}` for FB, `{"channel_id": "abc"}` for YouTube |
| `is_active` | bool | Disabled credentials are skipped |
| `token_expires_at` | datetime (nullable) | For refresh logic |

**Unique together:** `(user, platform)` — A user should only have one active connection per platform.

---

## ⚙️ Publishing Pipeline *(Block B — planned)*

> The Celery worker dynamically fetches the correct user's token for each post.

### Adding a new platform publisher

```python
# platforms/tasks.py
@shared_task
def publish_post_task(post_id):
    post = Post.objects.get(id=post_id)
    
    for result in post.platform_results.all():
        # Look up the credential SPECIFIC to the user who made the post
        try:
            credential = PlatformCredential.objects.get(
                user=post.user, 
                platform=result.platform,
                is_active=True
            )
            publisher = get_publisher(result.platform)
            publisher.publish(credential, post.content, post.media_urls)
            # ... update result status to success ...
        except PlatformCredential.DoesNotExist:
            # Mark as failed: User hasn't connected this platform yet
            pass
```

---

## 🗺️ Roadmap

### ✅ Phase 1 — Foundation (complete)
- [x] Django project + `accounts` + `platforms` apps
- [x] MySQL database with utf8mb4
- [x] JWT auth (register, login, refresh, logout, me)
- [x] Models: `Platform`, `PlatformCredential`, `Post`, `PostPlatformResult`
- [x] Encrypted credential storage (`EncryptedTextField`)
- [x] Posts CRUD with per-user isolation

### 🚧 Block B — OAuth & Publishing Engine (Next)
- [ ] **OAuth Flows**: Endpoints for `/oauth/facebook/login/`, `/oauth/twitter/login/`, etc., to link user accounts.
- [ ] **Token Exchange**: Exchange short-lived codes for long-lived tokens and save to `PlatformCredential`.
- [ ] Celery + Redis setup
- [ ] `BasePublisher` abstraction
- [ ] `FacebookPublisher` (real API)
- [ ] `InstagramPublisher` (real API)
- [ ] `TwitterPublisher` (real API)
- [ ] `YouTubePublisher` (real API)
- [ ] `publish_post_task` worker (fetching user-specific tokens)
```

### 🔗 A quick note on Twitter and YouTube
Since you are adding Twitter and YouTube, you will also need to create Developer Apps for those platforms to get your App IDs and Secrets:
*   **Twitter/X**: Go to the [Twitter Developer Portal](https://developer.twitter.com/), create an app, and enable OAuth 2.0. You'll need to request "write" permissions.
*   **YouTube**: Go to the [Google Cloud Console](https://console.cloud.google.com/), create a project, enable the **YouTube Data API v3**, and configure the OAuth consent screen.

The beauty of your architecture is that the `PlatformCredential` model and the Celery task don't care which platform it is. They just look at `result.platform`, pull the user's token, and send it to the right publisher class. You are fully set up for all four!