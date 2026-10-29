import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core import limits
from core.errors import ApiError

from .serializers import (
    EMAIL_TAKEN_MESSAGE,
    AccountDeleteSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PreferencesSerializer,
    RegisteredUserSerializer,
    RegisterSerializer,
    validate_new_password,
)
from .throttles import (
    AccountDeleteRateThrottle,
    AccountDeleteUserRateThrottle,
    LoginEmailRateThrottle,
    LoginRateThrottle,
    PasswordResetConfirmRateThrottle,
    PasswordResetRateThrottle,
    RegisterRateThrottle,
)

logger = logging.getLogger(__name__)

RESET_EMAIL_SUBJECT = "Reset your Whiteboard Tutor password"

ERROR = OpenApiResponse(description="Error envelope (see core.errors).")
EMPTY_204 = OpenApiResponse(description="No content.")
ACCEPTED_202 = OpenApiResponse(description="Accepted (empty object).")
OK_EMPTY_200 = OpenApiResponse(description="Password changed (empty object).")


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

    @extend_schema(request=None, responses={204: EMPTY_204})
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


# DRF marks API views csrf_exempt and only enforces CSRF for authenticated users,
# so anonymous registration needs Django's csrf_protect around dispatch.
@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegisteredUserSerializer, 400: ERROR, 429: ERROR},
    )
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

    @extend_schema(
        request=LoginSerializer,
        responses={200: RegisteredUserSerializer, 400: ERROR, 429: ERROR},
    )
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

    @extend_schema(request=None, responses={204: EMPTY_204, 403: ERROR})
    def post(self, request):
        # flush(): deletes the session row server-side and clears the cookie.
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: RegisteredUserSerializer, 403: ERROR})
    def get(self, request):
        return Response(RegisteredUserSerializer(request.user).data)


@method_decorator(csrf_protect, name="dispatch")
class PreferencesView(APIView):
    """Updates the signed-in Learner's preferences; the profile is always request.user's."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PreferencesSerializer,
        responses={200: PreferencesSerializer, 400: ERROR, 403: ERROR},
    )
    def patch(self, request):
        serializer = PreferencesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = request.user.profile
        profile.theme_preference = serializer.validated_data["theme_preference"]
        profile.save(update_fields=["theme_preference"])
        return Response(PreferencesSerializer(profile).data)


class IncorrectPassword(InvalidCredentials):
    """Same `invalid_credentials` code as sign-in, worded for a signed-in user."""

    default_detail = "The password is incorrect."


@method_decorator(csrf_protect, name="dispatch")
class AccountDeleteView(APIView):
    """Permanently deletes the signed-in user and everything they own (FR-18)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AccountDeleteRateThrottle, AccountDeleteUserRateThrottle]

    @extend_schema(
        request=AccountDeleteSerializer,
        responses={204: EMPTY_204, 400: ERROR, 403: ERROR, 429: ERROR},
    )
    def post(self, request):
        serializer = AccountDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["password"]):
            raise IncorrectPassword()

        # Profile and every OwnedModel row reference the user with on_delete=CASCADE
        # (guarded by tests), so one delete removes them all, all or nothing.
        with transaction.atomic():
            user.delete()
        # flush(): deletes this session row server-side and clears the cookie. Other
        # sessions of the user no longer resolve to an account, so they are anonymous.
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={202: ACCEPTED_202, 400: ERROR, 429: ERROR},
    )
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

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: OK_EMPTY_200, 400: ERROR, 429: ERROR},
    )
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
