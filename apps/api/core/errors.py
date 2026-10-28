"""Single API error envelope: {"error": {"code", "message", "retryable", "request_id", "fields"?}}.

Codes are stable strings. Responses never carry tracebacks; unexpected errors are
logged server-side with the request id.
"""
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, JsonResponse
from django.views.csrf import csrf_failure as django_csrf_failure
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

logger = logging.getLogger(__name__)

SERVER_ERROR_MESSAGE = "Something went wrong on our side. Please try again later."
CSRF_FAILED_MESSAGE = "Security check failed. Refresh the page and try again."

# (exception class, code, message, retryable); first match wins, so subclasses go first.
_MAPPING = [
    (exceptions.ValidationError, "validation_error", "Please correct the highlighted fields.",
     False),
    (exceptions.ParseError, "parse_error", "The request body could not be parsed.", False),
    (exceptions.NotAuthenticated, "not_authenticated", "Please sign in to continue.", False),
    (exceptions.AuthenticationFailed, "not_authenticated", "Please sign in to continue.", False),
    (exceptions.PermissionDenied, "permission_denied",
     "You do not have permission to do that.", False),
    (exceptions.NotFound, "not_found", "Not found.", False),
    (exceptions.MethodNotAllowed, "method_not_allowed", "Method not allowed.", False),
    (exceptions.NotAcceptable, "not_acceptable", "Requested format is not available.", False),
    (exceptions.UnsupportedMediaType, "unsupported_media_type", "Unsupported media type.",
     False),
    (exceptions.Throttled, "throttled", "Too many requests. Please try again later.", True),
]


class ApiError(exceptions.APIException):
    """Base for domain errors that carry their own stable code and user-safe message.

    Subclasses set `status_code`, `default_code`, `default_detail` and optionally `retryable`.
    """

    status_code = 400
    retryable = False


def error_body(code, message, retryable, request_id, fields=None):
    error = {"code": code, "message": message, "retryable": retryable, "request_id": request_id}
    if fields is not None:
        error["fields"] = fields
    return {"error": error}


def _flatten_fields(detail):
    """Turn DRF validation detail into {field: [message, ...]} with plain strings."""
    if isinstance(detail, dict):
        return {str(key): _messages(value) for key, value in detail.items()}
    return {"non_field_errors": _messages(detail)}


def _messages(value):
    if isinstance(value, dict):
        return [msg for nested in value.values() for msg in _messages(nested)]
    if isinstance(value, list | tuple):
        return [msg for item in value for msg in _messages(item)]
    return [str(value)]


def _is_csrf_denial(exc):
    # DRF's SessionAuthentication raises PermissionDenied("CSRF Failed: ...").
    return isinstance(exc, exceptions.PermissionDenied) and str(exc.detail).startswith(
        "CSRF Failed"
    )


def _classify(exc):
    if isinstance(exc, ApiError):
        return exc.default_code, str(exc.detail), exc.retryable
    for exc_class, code, message, retryable in _MAPPING:
        if isinstance(exc, exc_class):
            return code, message, retryable
    return getattr(exc, "default_code", "error"), "The request could not be completed.", False


def api_exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER producing the envelope for every API error."""
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        set_rollback()
        logger.error(
            "Unhandled API error request_id=%s exc_type=%s",
            request_id,
            type(exc).__name__,
            exc_info=exc,
        )
        return Response(
            error_body("server_error", SERVER_ERROR_MESSAGE, False, request_id), status=500
        )

    if _is_csrf_denial(exc):
        response.data = error_body("csrf_failed", CSRF_FAILED_MESSAGE, False, request_id)
        return response

    code, message, retryable = _classify(exc)
    fields = _flatten_fields(exc.detail) if isinstance(exc, exceptions.ValidationError) else None
    response.data = error_body(code, message, retryable, request_id, fields)
    return response


def csrf_failure(request, reason=""):
    """CSRF_FAILURE_VIEW: envelope for API paths, Django's default page elsewhere (admin)."""
    if not request.path.startswith("/api/"):
        return django_csrf_failure(request, reason=reason)
    body = error_body(
        "csrf_failed", CSRF_FAILED_MESSAGE, False, getattr(request, "request_id", None)
    )
    return JsonResponse(body, status=403)
