"""Development settings for Courpera.

Extends base settings with developer-friendly defaults.
"""

from .base import *  # noqa
import os


DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Development secret key fallback (safe only for local use)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")

# Keep static handling simple in development (WhiteNoise added in prod)
