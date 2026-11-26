import importlib
import ipaddress
import socket

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    # Throttle history lives in the cache; keep tests independent.
    cache.clear()
    yield
    cache.clear()


def _is_local(address):
    host = address[0] if isinstance(address, tuple) else address
    if not isinstance(host, str):
        return True
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _no_real_ai_client_or_network(request, monkeypatch):
    """AD-12 guard: no real google.genai client and no outbound socket unless marked `live`."""
    if request.node.get_closest_marker("live"):
        yield
        return

    # Imported by name so only gemini.py imports the SDK in application code.
    genai = importlib.import_module("google.genai")

    def refuse_client(*args, **kwargs):
        pytest.fail("A real google.genai.Client was constructed outside a `live` test.")

    monkeypatch.setattr(genai.Client, "__init__", refuse_client)

    real_connect = socket.socket.connect

    def guarded_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and not _is_local(address):
            pytest.fail(f"Outbound network connection attempted in a test: {address!r}")
        return real_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    yield
