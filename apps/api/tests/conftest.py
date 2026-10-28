import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    # Throttle history lives in the cache; keep tests independent.
    cache.clear()
    yield
    cache.clear()
