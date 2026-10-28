from django.apps import AppConfig


class OwnershipFixtureConfig(AppConfig):
    """Test-only app proving the ownership foundation. Enabled only in settings_test."""

    name = "tests.ownership_fixture"
    label = "ownership_fixture"
    default_auto_field = "django.db.models.BigAutoField"
