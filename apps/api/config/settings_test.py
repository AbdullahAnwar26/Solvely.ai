"""Settings for automated tests: deterministic, no external services."""
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production-use-0123456789")

from .settings import *  # noqa: E402, F403

# Fast hasher keeps the auth tests quick; production uses Django's default PBKDF2.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
