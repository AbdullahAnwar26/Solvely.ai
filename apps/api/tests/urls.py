"""Test ROOT_URLCONF: production routes plus test-only fixture routes."""
from django.urls import include, path

from config.urls import urlpatterns as production_urlpatterns

urlpatterns = [
    *production_urlpatterns,
    path("api/v1/", include("tests.ownership_fixture.urls")),
]
