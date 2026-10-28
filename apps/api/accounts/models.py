from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Per-user data kept beside Django's default User (no custom user model)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    # When the user confirmed they are 18 or older (required at registration).
    adult_confirmed_at = models.DateTimeField()

    def __str__(self):
        return f"Profile(user_id={self.user_id})"
