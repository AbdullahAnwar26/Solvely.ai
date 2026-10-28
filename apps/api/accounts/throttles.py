import hashlib

from rest_framework.throttling import SimpleRateThrottle

from .serializers import normalize_email


class _PerIPThrottle(SimpleRateThrottle):
    """Counts requests per client IP, whether or not the caller is signed in."""

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class RegisterRateThrottle(_PerIPThrottle):
    scope = "register"


class LoginRateThrottle(_PerIPThrottle):
    scope = "login"


class PasswordResetRateThrottle(_PerIPThrottle):
    scope = "password_reset"


class PasswordResetConfirmRateThrottle(_PerIPThrottle):
    scope = "password_reset_confirm"


class AccountDeleteRateThrottle(_PerIPThrottle):
    scope = "account_delete"


class AccountDeleteUserRateThrottle(SimpleRateThrottle):
    """Account deletion attempts per signed-in user, across all IPs."""

    scope = "account_delete_user"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class LoginEmailRateThrottle(SimpleRateThrottle):
    """Sign-in attempts per submitted email (case-insensitive), across all IPs."""

    scope = "login_email"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if not isinstance(email, str) or not email.strip():
            return None
        # Hash so raw emails never become cache keys.
        ident = hashlib.sha256(normalize_email(email).encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
