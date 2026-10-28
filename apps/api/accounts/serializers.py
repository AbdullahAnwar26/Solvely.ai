from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from core import limits

from .models import Profile

EMAIL_TAKEN_MESSAGE = "This email is already registered."
ADULT_REQUIRED_MESSAGE = "You must confirm that you are 18 or older."


def normalize_email(value):
    return value.strip().lower()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=limits.EMAIL_MAX_LENGTH)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=limits.PASSWORD_MAX_LENGTH,
        style={"input_type": "password"},
    )
    confirm_adult = serializers.BooleanField(write_only=True)

    def validate_email(self, value):
        email = normalize_email(value)
        if get_user_model().objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError(EMAIL_TAKEN_MESSAGE)
        return email

    def validate_password(self, value):
        # Compare against the submitted email too (UserAttributeSimilarityValidator).
        raw_email = self.initial_data.get("email")
        email = normalize_email(raw_email) if isinstance(raw_email, str) else ""
        candidate = get_user_model()(username=email, email=email)
        try:
            validate_password(value, user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from None
        return value

    def validate_confirm_adult(self, value):
        if value is not True:
            raise serializers.ValidationError(ADULT_REQUIRED_MESSAGE)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username=email, email=email, password=validated_data["password"]
            )
            Profile.objects.create(user=user, adult_confirmed_at=timezone.now())
        return user


def _password_field():
    return serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=limits.PASSWORD_MAX_LENGTH,
        style={"input_type": "password"},
    )


class LoginSerializer(serializers.Serializer):
    # Plain CharField: a malformed email is simply an unknown account (invalid_credentials).
    email = serializers.CharField(max_length=limits.EMAIL_MAX_LENGTH)
    password = _password_field()

    def validate_email(self, value):
        return normalize_email(value)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=limits.EMAIL_MAX_LENGTH)

    def validate_email(self, value):
        return normalize_email(value)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=128)
    new_password = _password_field()


def validate_new_password(value, user):
    """Run the registration password validators against an existing user."""
    try:
        validate_password(value, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"new_password": list(exc.messages)}) from None


class RegisteredUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    adult_confirmed_at = serializers.DateTimeField(source="profile.adult_confirmed_at")
