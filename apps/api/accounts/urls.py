from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.CsrfCookieView.as_view(), name="auth-csrf"),
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/preferences/", views.PreferencesView.as_view(), name="auth-preferences"),
    path(
        "auth/account/delete/", views.AccountDeleteView.as_view(), name="auth-account-delete"
    ),
    path(
        "auth/password-reset/",
        views.PasswordResetRequestView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "auth/password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
