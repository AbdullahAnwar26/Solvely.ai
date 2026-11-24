from django.urls import path

from .views import AIStatusView

urlpatterns = [
    path("ai/status/", AIStatusView.as_view(), name="ai-status"),
]
