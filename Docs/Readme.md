# 📄 `README.md`

Save the following as `Backend/README.md` (project root, next to `manage.py`). This is the clean file content — no code blocks wrapping it, no meta-notes.

```markdown
# Social Publisher API

A Django REST backend for scheduling and publishing content to multiple social media platforms — YouTube, Facebook, Twitter/X, Discord, Reddit, Instagram, and LinkedIn — from a single API.

> **Status:** Phase 1 — Auth + Posts API complete. Publishing engine (Celery + Discord publisher) in progress.

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

**Social Publisher** lets authenticated users compose a single post and publish it to multiple social platforms simultaneously. Unlike tools that require each user to connect their own OAuth accounts, this backend uses **app-owned credentials** configured once by an administrator — so end users just log in and publish.

### Key Design Decisions

| Decision | Rationale |
| :--- | :--- |
| **App-owned platform credentials** | Users don't need per-platform OAuth. Admins configure Twitter tokens, Discord webhooks, etc. once. |
| **Separate `accounts` and `platforms` apps** | Clean domain separation. Auth is independent of posting logic, so either can be replaced without touching the other. |
| **Encrypted token storage** | `EncryptedTextField` (Fernet) ensures platform credentials are encrypted at rest — never stored in plaintext. |
| **JWT authentication** | Stateless auth suits API-first design and scales horizontally. |
| **Queue-based publishing (planned)** | Celery + Redis decouples API response time from platform API latency. |

---

## 🏗️ Architecture

```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│   Frontend   │──JWT──▶│  Django API  │───────▶│    MySQL     │
│  (React/etc) │◀───────│   (DRF)      │        │  (posts,     │
└──────────────┘        └──────────────┘        │  credentials)│
                               │                 └──────────────┘
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
                        └──────────────┘        │ (Discord,    │
                               ▲                │  Twitter…)   │
                               │ schedule       └──────────────┘
                        ┌──────────────┐
                        │ Celery Beat  │
                        │ (every 60s)  │
                        └──────────────┘
```

**Flow:**
1. User creates a post via `POST /api/v1/posts/`
2. Post row saved with `status=queued` + one `PostPlatformResult` per target platform
3. Celery Beat fires `scan_due_posts()` every 60s
4. Due posts are enqueued as `publish_post_task(post_id)`
5. Worker iterates platform results, calls the appropriate publisher, updates statuses
6. Frontend polls `GET /api/v1/posts/{id}/` to see per-platform success/failure

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

## ✅ Prerequisites

Before you begin, install these on your machine:

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **MySQL 8.0+** — [dev.mysql.com](https://dev.mysql.com/downloads/mysql/) (or XAMPP/WAMP if you prefer)
- **Redis** *(Block B only)* — [Windows: Memurai or WSL](https://redis.io/docs/getting-started/install/install-on-windows/)
- **Git** — [git-scm.com](https://git-scm.com/)
- **VS Code** *(recommended)* — with the Python extension

Verify your installs:

```bash
python --version    # Python 3.11.x or higher
mysql --version     # mysql Ver 8.0.x
git --version
```

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone <your-repo-url> social_publisher
cd social_publisher/Backend
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> **Windows users:** if you see a *"running scripts is disabled"* error, run once:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If `requirements.txt` doesn't exist yet, generate it after installing:

```bash
pip freeze > requirements.txt
```

### 4. Create the MySQL database

```sql
CREATE DATABASE social_publisher
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 5. Create your `.env` file

Copy the template and edit:

```bash
cp .env.example .env
```

Then open `.env` and fill in your values (see [Configuration](#-configuration) below).

### 6. Run migrations

```bash
python manage.py makemigrations platforms
python manage.py migrate
```

### 7. Create a superuser

```bash
python manage.py createsuperuser
```

You'll be prompted for username, email, and password — use these to access the Django admin at `/admin/`.

### 8. Start the development server

```bash
python manage.py runserver
```

Your API is now live at **`http://127.0.0.1:8000/`**.

---

## ⚙️ Configuration

All configuration is via environment variables, loaded by `python-decouple`. Never commit `.env` — only `.env.example` is version-controlled.

### `.env.example`

```env
# Django
SECRET_KEY=your-super-secret-key-change-me-in-prod
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# MySQL
DB_NAME=social_publisher
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

# Fernet encryption key for OAuth tokens
# Generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key-change-me

# Publishing (Block B)
PUBLISH_DRY_RUN=True

# Celery (Block B)
REDIS_URL=redis://localhost:6379/0
```

### Required variables

| Variable | Required | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | ✅ | Django secret. Generate a fresh one for prod: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | ✅ | `True` in dev, `False` in prod |
| `ALLOWED_HOSTS` | ✅ | Comma-separated hostnames |
| `DB_*` | ✅ | MySQL connection details |
| `ENCRYPTION_KEY` | ✅ | Fernet key. **Keep this stable** — if it changes, stored tokens can no longer be decrypted |
| `PUBLISH_DRY_RUN` | ⬜ | `True` logs payloads without hitting real APIs (safe default) |
| `REDIS_URL` | ⬜ | Only needed once Block B is installed |

---

## 🖥️ Running the Project

### Terminal 1 — Django server

```bash
venv\Scripts\Activate.ps1        # Windows
python manage.py runserver
```

Server at `http://127.0.0.1:8000/`.

### Terminal 2 — Redis *(Block B)*

```bash
redis-server
```

Default port: `6379`.

### Terminal 3 — Celery Worker *(Block B)*

```bash
celery -A config worker --loglevel=info --pool=solo
```

`--pool=solo` is required on Windows.

### Terminal 4 — Celery Beat *(Block B)*

```bash
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Fires `scan_due_posts` every 60 seconds.

---

## 📡 API Reference

**Base URL:** `http://127.0.0.1:8000/api/v1/`

**Interactive docs:** [`http://127.0.0.1:8000/api/docs/`](http://127.0.0.1:8000/api/docs/)

### Authentication

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register/` | Public | Create a new user |
| `POST` | `/auth/login/` | Public | Obtain JWT access + refresh tokens |
| `POST` | `/auth/refresh/` | Public | Refresh an expired access token |
| `POST` | `/auth/logout/` | JWT | Blacklist the refresh token |
| `GET` | `/auth/me/` | JWT | Get current user's profile |

**Example: Register**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "StrongPass123!",
    "password2": "StrongPass123!"
  }'
```

**Example: Login**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "StrongPass123!"}'
```

Response:

```json
{
  "access":  "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Platforms

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/platforms/` | JWT | List platforms that have an active credential |

> ⚠️ **Note:** `encrypted_token` and `encrypted_secret` are **never** returned by this endpoint — only `platform`, `label`, and `is_active`.

### Posts

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/posts/` | JWT | List my posts (paginated later) |
| `POST` | `/posts/` | JWT | Create a post targeting one or more platforms |
| `GET` | `/posts/{id}/` | JWT | Post detail with per-platform results |
| `PATCH` | `/posts/{id}/` | JWT | Update a draft (only `status=draft`) |
| `DELETE` | `/posts/{id}/` | JWT | Delete a draft or queued post |
| `POST` | `/posts/{id}/publish-now/` | JWT | Publish immediately (bypasses schedule) |

**Example: Create a multi-platform post**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/posts/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello from Social Publisher!",
    "media_urls": [],
    "scheduled_at": "2026-12-01T10:00:00Z",
    "platforms": ["discord", "twitter"]
  }'
```

Response:

```json
{
  "id": 1,
  "author": "alice",
  "content": "Hello from Social Publisher!",
  "media_urls": [],
  "scheduled_at": "2026-12-01T10:00:00Z",
  "status": "queued",
  "platform_results": [
    { "platform": "discord", "status": "queued", "platform_post_id": null, "published_at": null, "error_message": null },
    { "platform": "twitter", "status": "queued", "platform_post_id": null, "published_at": null, "error_message": null }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

**HTTP Status Codes**

| Code | Meaning |
| :--- | :--- |
| `200` | OK |
| `201` | Created |
| `204` | No Content (DELETE) |
| `400` | Bad Request — validation failed |
| `401` | Unauthorized — missing/invalid JWT |
| `403` | Forbidden — not the owner |
| `404` | Not Found |
| `429` | Rate Limited |

---

## 📁 Project Structure

```
Backend/
├── manage.py
├── requirements.txt
├── .env                     # ❌ NOT committed
├── .env.example             # ✅ committed
├── .gitignore
├── README.md
│
├── config/                  # Project settings
│   ├── __init__.py         # Celery app import (Block B)
│   ├── settings.py         # All configuration
│   ├── urls.py             # Root URL router
│   ├── celery.py           # Celery app (Block B)
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/                # Identity / auth domain
│   ├── models.py           # (empty — Django User is built-in)
│   ├── serializers.py      # Register, User, Logout
│   ├── views.py            # Health, Register, Me, Logout
│   ├── urls.py             # /api/v1/auth/*
│   └── admin.py            # (empty — User is in admin by default)
│
├── platforms/               # Posting domain
│   ├── models.py           # Platform, PlatformCredential, Post, PostPlatformResult
│   ├── serializers.py      # Post CRUD + Platform listing
│   ├── views.py            # PlatformListView, PostViewSet
│   ├── urls.py             # /api/v1/posts/*, /api/v1/platforms/
│   ├── admin.py            # All 3 models registered
│   ├── publishers/         # (Block B)
│   │   ├── __init__.py     # get_publisher() factory
│   │   ├── base.py         # BasePublisher + TransientError
│   │   ├── discord.py      # Real Discord publisher
│   │   └── dry_run.py      # Stub for unintegrated platforms
│   ├── tasks.py            # (Block B) publish_post_task, scan_due_posts
│   └── migrations/
│
└── media/                   # User uploads (Block C)
```

### Why two apps?

| App | Responsibility | Replaceable? |
| :--- | :--- | :--- |
| `accounts` | User identity, JWT, profile | Yes — swap to a custom `User` later without touching posts |
| `platforms` | Credentials, posts, publishing | Yes — swap to a different publisher engine later without touching auth |

This separation is why you can **delete the entire `platforms/` app** and rewire it without breaking login.

---

## 🗄️ Data Models

### `Platform` (enum)

`youtube`, `facebook`, `twitter`, `discord`, `reddit`, `instagram`, `linkedin`

### `PlatformCredential`

App-owned API credentials. **Managed via Django admin only.**

| Field | Type | Notes |
| :--- | :--- | :--- |
| `platform` | enum | Which platform |
| `label` | string | Human label e.g. "Main Discord" |
| `encrypted_token` | EncryptedTextField | **Encrypted at rest** — never returned by API |
| `encrypted_secret` | EncryptedTextField (nullable) | For platforms needing secret |
| `extra_config` | JSON | e.g. `{"subreddit": "python"}` |
| `is_active` | bool | Disabled credentials are skipped |
| `token_expires_at` | datetime (nullable) | For refresh logic |

### `Post`

| Field | Type | Notes |
| :--- | :--- | :--- |
| `user` | FK → User | Owner (cascade delete) |
| `content` | text | Post body |
| `media_urls` | JSON array | Attached media (Block C) |
| `scheduled_at` | datetime (indexed) | When to publish |
| `status` | enum | `draft`, `queued`, `publishing`, `published`, `partial`, `failed` |

### `PostPlatformResult`

One row per (post, platform). Tracks each target independently so failures don't block successes.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `post` | FK → Post | Parent post |
| `platform` | enum | Target platform |
| `credential` | FK → PlatformCredential (nullable) | Which credential was used |
| `platform_post_id` | string | ID returned by the platform API |
| `status` | enum | Per-platform status |
| `error_message` | text | Populated on failure |
| `published_at` | datetime | When published successfully |

**Unique together:** `(post, platform)` — one result per platform per post.

---

## ⚙️ Publishing Pipeline *(Block B — planned)*

> This section describes the publishing engine that is **not yet implemented**. Once Block B is complete, this section becomes the operational reference.

### Components

| Component | Role |
| :--- | :--- |
| `scan_due_posts` | Periodic task (every 60s) — finds `status=queued` posts where `scheduled_at <= now` |
| `publish_post_task(post_id)` | Worker task — iterates platform results and calls publishers |
| `get_publisher(platform)` | Factory — returns a `BasePublisher` subclass |
| `BasePublisher.publish(credential, content, media_urls)` | Contract every publisher implements |
| `DryRunPublisher` | Logs the payload instead of calling the real API (when `PUBLISH_DRY_RUN=True`) |

### Retry policy

Failed publishes retry 3 times with exponential backoff:

```
attempt 1: immediate
attempt 2: +60s
attempt 3: +120s
```

Only **transient** errors (network, rate-limit) are retried. Permanent errors (invalid content, bad token) are marked `failed` immediately.

### Adding a new platform publisher

1. Create `platforms/publishers/<platform>.py`
2. Subclass `BasePublisher` and implement `publish()`
3. Register in `platforms/publishers/__init__.py`:

   ```python
   PUBLISHERS = {
       "discord": DiscordPublisher,
       "twitter": TwitterPublisher,
       ...
   }
   ```
4. Add a credential via Django admin
5. Test in dry-run mode first, then with `PUBLISH_DRY_RUN=False`

---

## 🧪 Testing

### Manual API testing via Swagger

Open `http://127.0.0.1:8000/api/docs/` and use the **Authorize 🔓** button (paste the `access` token from `/auth/login/`).

### Full flow test

| Step | Endpoint | Expect |
| :--- | :--- | :--- |
| 1 | `POST /api/v1/auth/register/` | `201` |
| 2 | `POST /api/v1/auth/login/` | `200` + tokens |
| 3 | `GET /api/v1/auth/me/` (authorized) | User details |
| 4 | Admin → add a Discord credential | Saved |
| 5 | `GET /api/v1/platforms/` | Discord appears |
| 6 | `POST /api/v1/posts/` with `platforms: ["discord"]` | `201` + nested results |
| 7 | `GET /api/v1/posts/{id}/` | Shows `platform_results` |
| 8 | `POST /api/v1/posts/{id}/publish-now/` | Status still `queued` (until Block B) |

### Unit tests *(planned)*

```bash
python manage.py test
```

---

## 🩺 Troubleshooting

### `ImportError: cannot import name 'force_text'`

You installed the abandoned `django-fernet-fields`. Fix:

```bash
pip uninstall django-fernet-fields -y
pip install djfernet-redux
```

### `ModuleNotFoundError: No module named 'MySQLdb'`

```bash
pip install mysqlclient
```

If that fails on Windows, install `pymysql` instead and add to `config/__init__.py`:

```python
import pymysql
pymysql.install_as_MySQLdb()
```

### `Access denied for user 'root'@'localhost'`

Your `DB_PASSWORD` in `.env` doesn't match MySQL's actual root password. Test with a MySQL client:

```bash
mysql -u root -p
```

### `Can't connect to MySQL server`

MySQL service isn't running:

```powershell
Get-Service MySQL*
Start-Service MySQL80
```

### `mysql: command not found` (Windows)

Add MySQL `bin/` to PATH, or use the Python-based DB reset script (see `reset_db.py` pattern in the project history).

### `venv\Scripts\Activate.ps1 cannot be loaded`

Execution policy blocks scripts:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### OneDrive is corrupting `venv/` or `.git/`

Move the project **outside** OneDrive:

```
C:\Users\You\Documents\social_publisher\
```

OneDrive's file sync interferes with Python's many small files and git's object storage.

### `django.db.utils.OperationalError: (1050, "Table already exists")`

Stale migration state. Reset:

```bash
python manage.py migrate platforms zero
python manage.py migrate
```

Or drop the DB entirely (dev only):

```python
# reset_db.py
from decouple import config
import MySQLdb
conn = MySQLdb.connect(host=config("DB_HOST"), user=config("DB_USER"),
                       passwd=config("DB_PASSWORD"))
cur = conn.cursor()
cur.execute(f"DROP DATABASE IF EXISTS `{config('DB_NAME')}`")
cur.execute(f"CREATE DATABASE `{config('DB_NAME')}` CHARACTER SET utf8mb4")
conn.commit()
print("✅ Reset")
```

---

## 🗺️ Roadmap

### ✅ Phase 1 — Foundation (complete)

- [x] Django project + `accounts` + `platforms` apps
- [x] MySQL database with utf8mb4
- [x] JWT auth (register, login, refresh, logout, me)
- [x] Models: `Platform`, `PlatformCredential`, `Post`, `PostPlatformResult`
- [x] Encrypted credential storage (`EncryptedTextField`)
- [x] Django admin for credentials + posts
- [x] Posts CRUD with per-user isolation
- [x] `publish-now` action
- [x] Swagger UI at `/api/docs/`

### 🚧 Block B — Publishing Engine (next)

- [ ] Celery + Redis setup
- [ ] `BasePublisher` abstraction
- [ ] `DiscordPublisher` (real webhook)
- [ ] `DryRunPublisher` for stubs
- [ ] `publish_post_task` worker
- [ ] `scan_due_posts` periodic task (Beat)
- [ ] Retry with exponential backoff
- [ ] End-to-end test: post → Discord message arrives

### ⏳ Block C — Media Upload

- [ ] `POST /api/v1/media/upload/` endpoint
- [ ] File type validation (jpg, png, gif, mp4, mov)
- [ ] Size limit (50 MB)
- [ ] Local storage via `MEDIA_ROOT`
- [ ] Return URL for `media_urls` field

### ⏳ Block D — Polish

- [ ] Pagination on `GET /posts/`
- [ ] Filtering by status, platform, date
- [ ] Search on content
- [ ] Per-user throttle on create
- [ ] Retry-failed-platform endpoint
- [ ] Unit + integration tests

### 🔮 Phase 2+ — Optional

- [ ] Real publishers: Twitter, Reddit, Instagram, Facebook, YouTube, LinkedIn
- [ ] Email verification + password reset
- [ ] Email notifications on publish success/failure
- [ ] Post templates
- [ ] Recurring posts
- [ ] Analytics (engagement per platform)
- [ ] 2FA

---

## 🤝 Contributing

### Branching

```
main          ← production
develop       ← integration
feature/*     ← individual features
fix/*         ← bug fixes
```

### Commit convention

```
feat: add Discord publisher
fix: correct refresh token expiry
docs: update API reference
refactor: split serializers by domain
test: add post isolation tests
```

### Pre-commit checklist

- [ ] `.env` is **not** staged
- [ ] `python manage.py check` passes
- [ ] `python manage.py makemigrations --check --dry-run` shows no missing migrations
- [ ] New endpoints appear in Swagger
- [ ] No secrets in the diff

---

## 📄 License

This project is licensed under the **MIT License** — see `LICENSE` for details.

---

## 📞 Support

- **Issues:** Open a GitHub issue with the traceback + the endpoint that failed
- **Security:** Report vulnerabilities privately (do not open a public issue)
- **Docs:** Swagger UI is always the source of truth — if `README.md` and Swagger disagree, Swagger wins

---

**Built with Django 4.2 · MySQL 8 · DRF · SimpleJWT · drf-spectacular**
```
