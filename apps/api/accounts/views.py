import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import EmailMessage
from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core import limits
from core.errors import ApiError

from .serializers import (
    EMAIL_TAKEN_MESSAGE,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisteredUserSerializer,
    RegisterSerializer,
    validate_new_password,
)
from .throttles import (
    LoginEmailRateThrottle,
    LoginRateThrottle,
    PasswordResetConfirmRateThrottle,
    PasswordResetRateThrottle,
    RegisterRateThrottle,
)

logger = logging.getLogger(__name__)

RESET_EMAIL_SUBJECT = "Reset your Whiteboard Tutor password"


class InvalidCredentials(ApiError):
    status_code = 400
    default_code = "invalid_credentials"
    default_detail = "The email or password is incorrect."


class InvalidResetToken(ApiError):
    status_code = 400
    default_code = "invalid_reset_token"
    default_detail = "This password reset link is invalid or has expired. Request a new one."


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    """Sets the `csrftoken` cookie the SPA echoes in the X-CSRFToken header."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


# DRF marks API views csrf_exempt and only enforces CSRF for authenticated users,
# so anonymous registration needs Django's csrf_protect around dispatch.
@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
        except IntegrityError:
            # Lost a race with a concurrent registration of the same email.
            email = serializer.validated_data["email"]
            if get_user_model().objects.filter(username__iexact=email).exists():
                raise serializers.ValidationError({"email": [EMAIL_TAKEN_MESSAGE]}) from None
            raise
        login(request._request, user)
        return Response(RegisteredUserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle, LoginEmailRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Emails are stored lowercase as the username. ModelBackend hashes the password
        # even for unknown users and rejects inactive ones, so every failure looks alike.
        user = authenticate(
            request._request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise InvalidCredentials()
        # login() rotates the session key (no fixation) and the CSRF token.
        login(request._request, user)
        return Response(RegisteredUserSerializer(user).data, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # flush(): deletes the session row server-side and clears the cookie.
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(RegisteredUserSerializer(request.user).data)


def _reset_candidate(email):
    """The account that may receive a reset email, or None (mirrors PasswordResetForm)."""
    user = get_user_model().objects.filter(username__iexact=email, is_active=True).first()
    if user is None or not user.has_usable_password():
        return None
    return user


def _build_reset_email(user, to_email):
    query = urlencode(
        {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }
    )
    link = f"{settings.FRONTEND_BASE_URL}/reset-password?{query}"
    minutes = limits.RESET_TIMEOUT_SECONDS // 60
    body = (
        "Someone asked to reset the password for your Whiteboard Tutor account.\n\n"
        f"To choose a new password, open this link within {minutes} minutes:\n\n"
        f"{link}\n\n"
        "The link works once. If you did not ask for this, you can ignore this email.\n"
    )
    return EmailMessage(RESET_EMAIL_SUBJECT, body, to=[to_email])


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = _reset_candidate(email)
        # Build the token and message for unknown emails too, so both paths do the same
        # work; only a real account's message is sent.
        target = user or get_user_model()(username=email, email=email)
        message = _build_reset_email(target, email)
        if user is not None:
            message.to = [user.email]
            try:
                message.send()
            except Exception as exc:
                # A send failure must not reveal the account, so still answer 202.
                # Never log the message or exc_info: they can contain the reset link.
                logger.error(
                    "Password reset email failed request_id=%s exc_type=%s",
                    getattr(request, "request_id", None),
                    type(exc).__name__,
                )
        return Response({}, status=status.HTTP_202_ACCEPTED)


def _user_from_uid(uid):
    try:
        pk = urlsafe_base64_decode(uid).decode()
        return get_user_model().objects.get(pk=pk)
    except (ValueError, TypeError, OverflowError, DjangoValidationError,
            get_user_model().DoesNotExist):
        return None


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = _user_from_uid(data["uid"])
        # The token hashes the password and last login, so it is spent once the password
        # changes, and it expires after PASSWORD_RESET_TIMEOUT.
        if user is None or not default_token_generator.check_token(user, data["token"]):
            raise InvalidResetToken()

        validate_new_password(data["new_password"], user)
        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        # Existing sessions store a hash of the old password, so Django's session
        # verification now treats every one of them as signed out.
        return Response({}, status=status.HTTP_200_OK)
