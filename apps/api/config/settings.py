"""Environment-driven settings. Secrets come only from environment variables."""
from pathlib import Path

import environ

from core import limits

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DJANGO_DEBUG")
# No insecure fallback in production: DEBUG-only default.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key" if DEBUG else None)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "core",
    "accounts",
]

MIDDLEWARE = [
    "core.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# PostgreSQL is the target; SQLite fallback is for local unit tests only.
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
USE_TZ = True
TIME_ZONE = "UTC"

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": limits.PASSWORD_MIN_LENGTH},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Session cookie auth (AD-6). HttpOnly session cookie; the CSRF cookie stays readable
# by the SPA so it can echo it in X-CSRFToken. Secure flags are set below when not DEBUG.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "core.errors.csrf_failure"

# Password reset: single-use tokens from default_token_generator, valid for one hour.
PASSWORD_RESET_TIMEOUT = limits.RESET_TIMEOUT_SECONDS
# Reset links point at the SPA, which posts uid + token back to the API.
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:5173").rstrip("/")

# Email: console in development, SMTP from the environment otherwise.
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@localhost")
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="localhost")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "register": limits.REGISTER_RATE,
        "login": limits.LOGIN_RATE,
        "login_email": limits.LOGIN_EMAIL_RATE,
        "password_reset": limits.RESET_RATE,
        "password_reset_confirm": limits.RESET_RATE,
        "account_delete": limits.ACCOUNT_DELETE_RATE,
        "account_delete_user": limits.ACCOUNT_DELETE_RATE,
    },
    # 0 = throttle on REMOTE_ADDR only, so a spoofed X-Forwarded-For cannot dodge limits.
    # Set to the number of trusted reverse proxies in production.
    "NUM_PROXIES": env.int("DJANGO_NUM_PROXIES", default=0),
    "EXCEPTION_HANDLER": "core.errors.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
SPECTACULAR_SETTINGS = {"TITLE": "Whiteboard Tutor API", "VERSION": "0.1.0"}

# AI provider config (consumed by the AI service in Phase 4).
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="")

if not DEBUG:
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = env.bool("DJANGO_SECURE_COOKIES", default=True)
    SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=0)
    SECURE_CONTENT_TYPE_NOSNIFF = True
