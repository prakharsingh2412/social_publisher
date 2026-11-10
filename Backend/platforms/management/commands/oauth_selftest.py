# platforms/management/commands/oauth_selftest.py
"""
End-to-end OAuth self-test. Mocked at the Meta/Twitter boundary — no live API calls.

Run:
    python manage.py oauth_selftest
"""
import urllib.parse
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection
from rest_framework.test import APIClient


class Command(BaseCommand):
    help = "Self-test the OAuth pipeline end-to-end (mocked graph calls)."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = 0
        self.failed = 0

    def _check_one(self, name, cond, expected=None, actual=None):
        if cond:
            self.stdout.write(f"  [PASS] {name}")
            self.passed += 1
            return True
        self.stdout.write(f"  [FAIL] {name}")
        if expected is not None:
            self.stdout.write(f"         expected: {expected}")
        if actual is not None:
            self.stdout.write(f"         actual:   {actual}")
        self.failed += 1
        return False

    def _section(self, title):
        self.stdout.write(f"\n--- {title} ---")

    def handle(self, *args, **opts):
        self._test_settings()
        self._test_db()
        self._test_cache()
        self._test_state()

        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import RefreshToken

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username="oauth_selftest_user",
            defaults={"email": "selftest@example.com"},
        )
        token = str(RefreshToken.for_user(user).access_token)
        uid = user.id

        try:
            self._test_login_urls(token)
            self._test_anon_rejected()
            self._test_callback_bad_state()
            self._test_callback_happy_path(uid)
            self._test_credentials_persisted(uid)
            self._test_tenant_isolation(token)
            self._test_publishers(uid)
        finally:
            from platforms.models import PlatformCredential
            PlatformCredential.objects.filter(user=user).delete()
            User.objects.filter(username="oauth_selftest_user").delete()

        total = self.passed + self.failed
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"RESULT: {self.passed}/{total} passed, {self.failed} failed")
        self.stdout.write(f"{'=' * 60}")

    # ── BLOCK 1 ────────────────────────────────────────────────
    def _test_settings(self):
        self._section("BLOCK 1 — Settings loaded from .env")
        for name in [
            "FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET",
            "FACEBOOK_REDIRECT_URI", "INSTAGRAM_REDIRECT_URI",
            "TWITTER_REDIRECT_URI", "TWITTER_CLIENT_ID",
        ]:
            val = getattr(settings, name, None)
            self._check_one(name, bool(val), "non-empty string", repr(val))

        self._check_one(
            "ALLOWED_HOSTS includes 'testserver'",
            "testserver" in settings.ALLOWED_HOSTS,
            "'testserver' in ALLOWED_HOSTS",
            str(settings.ALLOWED_HOSTS),
        )

    # ── BLOCK 1b ───────────────────────────────────────────────
    def _test_db(self):
        self._section("BLOCK 1b — Model + migration")
        try:
            from platforms.models import PlatformCredential
        except Exception as e:
            self._check_one("import PlatformCredential", False, "import OK", str(e))
            return

        field_names = [f.name for f in PlatformCredential._meta.get_fields()]
        self._check_one(
            "PlatformCredential has 'user' field",
            "user" in field_names,
            "'user' present",
            str(field_names),
        )
        self._check_one(
            "unique_together == (user, platform)",
            PlatformCredential._meta.unique_together == (("user", "platform"),),
            "(('user','platform'),)",
            str(PlatformCredential._meta.unique_together),
        )
        try:
            PlatformCredential.objects.count()
            self._check_one("queryset works (migration applied)", True)
        except Exception as e:
            self._check_one(
                "queryset works (migration applied)",
                False, "query OK", str(e)[:150],
            )

    # ── BLOCK 2 ────────────────────────────────────────────────
    def _test_cache(self):
        self._section("BLOCK 2 — Cache / Redis")
        try:
            cache.set("_selftest_ping", "pong", 5)
            self._check_one(
                "cache round-trip",
                cache.get("_selftest_ping") == "pong",
                "pong", cache.get("_selftest_ping"),
            )
            cls_name = cache.__class__.__name__
            self._check_one(
                "cache is not LocMem (must be Redis)",
                "LocMem" not in cls_name,
                "Redis backend", cls_name,
            )
            cache.delete("_selftest_ping")
        except Exception as e:
            self._check_one("cache reachable", False, "Redis alive", str(e)[:150])

    # ── BLOCK 3 ────────────────────────────────────────────────
    def _test_state(self):
        self._section("BLOCK 3 — State issue / consume (single-use)")
        try:
            from platforms.oauth_utils import issue_state, consume_state
        except Exception as e:
            self._check_one("import oauth_utils", False, "import OK", str(e))
            return

        s = issue_state(999, platform="facebook")
        self._check_one(
            "issue_state returns long string",
            isinstance(s, str) and len(s) > 20,
            "str(len>20)",
            f"{type(s).__name__}({len(s) if isinstance(s, str) else '?'})",
        )
        first = consume_state(s)
        self._check_one(
            "first consume returns payload",
            first == {"user_id": 999, "platform": "facebook"},
            "{'user_id': 999, 'platform': 'facebook'}",
            str(first),
        )
        self._check_one(
            "second consume fails (single-use)",
            consume_state(s) is None,
            "None", str(consume_state(s)),
        )
        self._check_one("missing state fails", consume_state(None) is None)

    # ── BLOCKS 4–6 ─────────────────────────────────────────────
    def _test_login_urls(self, token):
        self._section("BLOCK 4-6 — Login URL generation")
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        targets = [
            ("facebook",  "/oauth/facebook/login/",
             getattr(settings, "FACEBOOK_REDIRECT_URI", None)),
            ("instagram", "/oauth/instagram/login/",
             getattr(settings, "INSTAGRAM_REDIRECT_URI", None)),
        ]

        for name, path, expected_redirect in targets:
            try:
                r = c.get(path)
            except Exception as e:
                self._check_one(f"{name} login request", False, "200", str(e)[:150])
                continue
            if not self._check_one(f"{name} login status",
                                   r.status_code == 200, "200", r.status_code):
                continue
            try:
                url = r.json()["auth_url"]
            except Exception as e:
                self._check_one(f"{name} returns auth_url", False,
                                "JSON with auth_url", str(e)[:150])
                continue

            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
            self._check_one(
                f"{name} client_id == FACEBOOK_APP_ID",
                q.get("client_id") == settings.FACEBOOK_APP_ID,
                settings.FACEBOOK_APP_ID, q.get("client_id"),
            )
            self._check_one(
                f"{name} redirect_uri == setting",
                q.get("redirect_uri") == expected_redirect,
                expected_redirect, q.get("redirect_uri"),
            )
            self._check_one(f"{name} response_type=code",
                            q.get("response_type") == "code",
                            "code", q.get("response_type"))
            self._check_one(f"{name} state present", "state" in q)
            self._check_one(f"{name} scope non-empty", bool(q.get("scope")),
                            "non-empty scope", q.get("scope"))

        # Twitter (PKCE)
        try:
            r = c.get("/oauth/twitter/login/")
            if self._check_one("twitter login status",
                               r.status_code == 200, "200", r.status_code):
                j = r.json()
                if self._check_one("twitter returns auth_url (not redirect)",
                                   "auth_url" in j, "'auth_url' key",
                                   list(j.keys())):
                    q = dict(urllib.parse.parse_qsl(
                        urllib.parse.urlparse(j["auth_url"]).query))
                    self._check_one("twitter PKCE S256",
                                    q.get("code_challenge_method") == "S256",
                                    "S256", q.get("code_challenge_method"))
                    self._check_one("twitter has state", "state" in q)
        except Exception as e:
            self._check_one("twitter login request", False, "200", str(e)[:150])

    # ── BLOCK 7 ────────────────────────────────────────────────
    def _test_anon_rejected(self):
        self._section("BLOCK 7 — Auth gating (no JWT → 401/403)")
        anon = APIClient()
        for path in [
            "/oauth/facebook/login/",
            "/oauth/instagram/login/",
            "/oauth/twitter/login/",
        ]:
            r = anon.get(path)
            self._check_one(
                f"anon {path.split('/')[-2]} → 401/403",
                r.status_code in (401, 403),
                "401 or 403", r.status_code,
            )

    # ── BLOCK 8 ────────────────────────────────────────────────
    def _test_callback_bad_state(self):
        self._section("BLOCK 8 — Callback rejects bad state / cancel")
        saved = getattr(settings, "FRONTEND_OAUTH_REDIRECT", None)
        settings.FRONTEND_OAUTH_REDIRECT = None
        try:
            cb = APIClient()
            r = cb.get("/oauth/facebook/callback/",
                       {"code": "x", "state": "bogus"})
            self._check_one("bad state → 400", r.status_code == 400,
                            400, r.status_code)
            if r.status_code == 400:
                try:
                    self._check_one("bad state returns status=error",
                                    r.json().get("status") == "error",
                                    "error", r.json().get("status"))
                except Exception:
                    self._check_one("bad state response is JSON", False,
                                    "application/json",
                                    r.get("Content-Type", "?"))

            r = cb.get("/oauth/facebook/callback/",
                       {"error": "access_denied"})
            self._check_one("user cancel → 400", r.status_code == 400,
                            400, r.status_code)
        finally:
            settings.FRONTEND_OAUTH_REDIRECT = saved

    # ── BLOCK 9 ────────────────────────────────────────────────
    def _test_callback_happy_path(self, uid):
        self._section("BLOCK 9 — Callback happy path (mocked Meta)")
        from platforms.oauth_utils import issue_state

        saved = getattr(settings, "FRONTEND_OAUTH_REDIRECT", None)
        settings.FRONTEND_OAUTH_REDIRECT = None
        cb = APIClient()

        fake_page = {
            "id": "PAGE_TEST_123",
            "name": "Self-Test Page",
            "access_token": "PAGE_TOKEN_SELFTEST",
            "instagram_business_account": {
                "id": "IG_TEST_999", "username": "selftest_ig",
            },
        }

        try:
            for platform, path in [
                ("facebook",  "/oauth/facebook/callback/"),
                ("instagram", "/oauth/instagram/callback/"),
            ]:
                state = issue_state(uid, platform=platform)
                with patch("platforms.views.exchange_code_for_user_token",
                           return_value="SHORT"), \
                     patch("platforms.views.exchange_for_long_lived_token",
                           return_value=("LONG", None)), \
                     patch("platforms.views.list_pages",
                           return_value=[fake_page]):
                    r = cb.get(path, {"code": "fake", "state": state})

                if self._check_one(f"{platform} callback → 200",
                                   r.status_code == 200, 200, r.status_code):
                    try:
                        j = r.json()
                        self._check_one(f"{platform} callback status=success",
                                        j.get("status") == "success",
                                        "success", j.get("status"))
                    except Exception as e:
                        self._check_one(f"{platform} callback returns JSON",
                                        False, "application/json",
                                        str(e)[:100])
        finally:
            settings.FRONTEND_OAUTH_REDIRECT = saved

    # ── BLOCK 10 ───────────────────────────────────────────────
    def _test_credentials_persisted(self, uid):
        self._section("BLOCK 10 — Credentials persisted + encrypted")
        from platforms.models import PlatformCredential, Platform

        creds = PlatformCredential.objects.filter(user_id=uid)
        self._check_one("2 credentials saved", creds.count() == 2,
                        "2", creds.count())

        fb = creds.filter(platform=Platform.FACEBOOK).first()
        ig = creds.filter(platform=Platform.INSTAGRAM).first()

        if fb:
            cfg = fb.extra_config or {}
            self._check_one("FB extra_config.page_id",
                            cfg.get("page_id") == "PAGE_TEST_123",
                            "PAGE_TEST_123", cfg.get("page_id"))
            self._check_one("FB token decrypts via model",
                            str(fb.encrypted_token) == "PAGE_TOKEN_SELFTEST",
                            "PAGE_TOKEN_SELFTEST", str(fb.encrypted_token))
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT encrypted_token "
                    "FROM platforms_platformcredential WHERE id=%s", [fb.id],
                )
                raw_row = cur.fetchone()
            raw = raw_row[0] if raw_row else None
            self._check_one(
                "FB token encrypted at rest (raw DB column != plaintext)",
                raw is not None and raw != "PAGE_TOKEN_SELFTEST",
                "ciphertext bytes", repr(raw)[:60],
            )
        else:
            self._check_one("FB credential exists", False, "1 row", "0 rows")

        if ig:
            cfg = ig.extra_config or {}
            self._check_one("IG extra_config.ig_user_id",
                            cfg.get("ig_user_id") == "IG_TEST_999",
                            "IG_TEST_999", cfg.get("ig_user_id"))
        else:
            self._check_one("IG credential exists", False, "1 row", "0 rows")

    # ── BLOCK 11 ───────────────────────────────────────────────
    def _test_tenant_isolation(self, token):
        self._section("BLOCK 11 — Tenant isolation on /platforms/")
        from django.contrib.auth import get_user_model
        from platforms.models import PlatformCredential, Platform

        User = get_user_model()
        other, _ = User.objects.get_or_create(username="oauth_selftest_other")
        PlatformCredential.objects.filter(user=other).delete()
        PlatformCredential.objects.create(
            user=other, platform=Platform.FACEBOOK,
            label="OTHER_TENANT_PAGE", encrypted_token="OTHER_TOKEN",
            is_active=True,
        )

        try:
            c = APIClient()
            c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            r = c.get("/api/v1/platforms/")
            if self._check_one("/platforms/ returns 200",
                               r.status_code == 200, 200, r.status_code):
                body = r.json()
                items = body if isinstance(body, list) else body.get("results", [])
                labels = [i.get("label") for i in items]
                self._check_one(
                    "no other-tenant label leaked",
                    all("OTHER_TENANT" not in (l or "") for l in labels),
                    "no cross-tenant rows", labels,
                )
        finally:
            PlatformCredential.objects.filter(user=other).delete()
            other.delete()

    # ── BLOCK 12 ───────────────────────────────────────────────
    def _test_publishers(self, uid):
        self._section("BLOCK 12 — Publishers validate + decrypt")
        try:
            from platforms.publishers import PUBLISHERS, get_publisher
            from platforms.publishers.base import Payload
        except Exception as e:
            self._check_one("import platforms.publishers", False,
                            "import OK", str(e)[:150])
            return

        self._check_one("PUBLISHERS has facebook", "facebook" in PUBLISHERS,
                        "facebook key", list(PUBLISHERS.keys()))
        self._check_one("PUBLISHERS has instagram", "instagram" in PUBLISHERS,
                        "instagram key", list(PUBLISHERS.keys()))

        from platforms.models import PlatformCredential, Platform

        fb_cred = PlatformCredential.objects.filter(
            user_id=uid, platform=Platform.FACEBOOK).first()
        ig_cred = PlatformCredential.objects.filter(
            user_id=uid, platform=Platform.INSTAGRAM).first()

        if fb_cred:
            try:
                from platforms.publishers.facebook import FacebookPublisher
                self._check_one(
                    "FB _token() decrypts",
                    FacebookPublisher._token(fb_cred) == "PAGE_TOKEN_SELFTEST",
                    "PAGE_TOKEN_SELFTEST",
                    FacebookPublisher._token(fb_cred),
                )
                fb = FacebookPublisher()
                self._check_one(
                    "FB validate empty media → no error",
                    fb.validate(Payload(content="hi", media_urls=[])) == [],
                    "[]", fb.validate(Payload(content="hi", media_urls=[])),
                )
                self._check_one(
                    "FB validate oversize content → error",
                    len(fb.validate(Payload(content="x" * 70000,
                                            media_urls=[]))) > 0,
                    "≥1 error",
                    len(fb.validate(Payload(content="x" * 70000,
                                            media_urls=[]))),
                )
            except Exception as e:
                self._check_one("FB publisher import", False, "OK", str(e)[:150])

        if ig_cred:
            try:
                from platforms.publishers.instagram import InstagramPublisher
                ig = InstagramPublisher()
                self._check_one(
                    "IG validate no media → error",
                    len(ig.validate(Payload(content="hi", media_urls=[]))) > 0,
                    "≥1 error",
                    ig.validate(Payload(content="hi", media_urls=[])),
                )
                good = Payload(content="hi", media_urls=["https://x/y.jpg"])
                self._check_one("IG validate good media → no error",
                                ig.validate(good) == [], "[]", ig.validate(good))
            except Exception as e:
                self._check_one("IG publisher import", False, "OK", str(e)[:150])

        # Dry-run dispatch
        try:
            saved = settings.PUBLISH_DRY_RUN
            settings.PUBLISH_DRY_RUN = True
            p = get_publisher("facebook")
            self._check_one("dry-run wraps publisher",
                            "DryRun" in type(p).__name__,
                            "DryRunPublisher", type(p).__name__)
            settings.PUBLISH_DRY_RUN = False
            p = get_publisher("facebook")
            self._check_one("live dispatch returns real publisher",
                            "Facebook" in type(p).__name__,
                            "FacebookPublisher", type(p).__name__)
            settings.PUBLISH_DRY_RUN = saved
        except Exception as e:
            self._check_one("publisher dispatch", False, "OK", str(e)[:150])