from django.urls import path
from auth.views import LoginView, LogoutView, RefreshTokenView

# Endpoints de autenticación JWT con cookies seguras
urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
]
