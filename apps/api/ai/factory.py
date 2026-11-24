"""Provider selection from settings, so views and services never name a vendor."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .service import AIService

PROVIDERS = ("gemini", "fake")


def get_provider():
    name = settings.AI_PROVIDER
    if name == "gemini":
        # Imported lazily: loading the SDK is only needed when Gemini is the provider.
        from .providers.gemini import GeminiProvider

        return GeminiProvider.from_settings()
    if name == "fake":
        from .providers.fake import FakeProvider

        return FakeProvider()
    raise ImproperlyConfigured(f"AI_PROVIDER must be one of {', '.join(PROVIDERS)}.")


def get_ai_service(**kwargs):
    return AIService(get_provider(), **kwargs)


def provider_status():
    """Non-secret diagnostics: never the key or any part of it."""
    name = settings.AI_PROVIDER
    if name == "fake":
        from .providers.fake import FAKE_MODEL

        configured, model = True, FAKE_MODEL
    else:
        model = settings.GEMINI_MODEL or None
        configured = bool(settings.GEMINI_API_KEY and model)
    return {
        "configured": configured,
        "provider": name,
        "model": model,
        "max_attempts": settings.AI_MAX_ATTEMPTS,
        "max_concurrency": settings.AI_MAX_CONCURRENCY,
    }
