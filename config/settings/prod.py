"""Production settings for Courpera.

Security-focused configuration. Expected to run behind a proxy with
ASGI server (e.g., Daphne) and a Redis service available for Channels.
"""

from .base import *  # noqa
import os


DEBUG = False

_sk = os.environ.get("DJANGO_SECRET_KEY")
if not _sk:
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")
SECRET_KEY: str = _sk  # type: ignore[no-redef]

_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", ".onrender.com,localhost,127.0.0.1")
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(",") if h.strip()]

# Static files via WhiteNoise in production
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Secure cookies and HSTS (tune for hosting environment)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days starter
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "1").lower() in ("1", "true")
SECURE_REFERRER_POLICY = "same-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = (
    os.environ.get("CSRF_TRUSTED_ORIGINS", "").split()
    if os.environ.get("CSRF_TRUSTED_ORIGINS")
    else []
)
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
