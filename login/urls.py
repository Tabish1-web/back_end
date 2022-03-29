from django.urls import path
from rest_framework_simplejwt import views as jwt_views
from .views import (GoogleView, LoginView, LogoutView, PasswordResetView, 
    PasswordTokenView, RegisterView, SetNewPasswordView, VerifyEmail, GetUserFromTokenView)

urlpatterns = [
    path('register', RegisterView.as_view(), name="register"),
    path('email-verify', VerifyEmail.as_view(), name="email-verify"),
    path('google', GoogleView.as_view(), name="google"),
    path('login', LoginView.as_view(), name="login"),
    path('user-lookups', GetUserFromTokenView.as_view(), name="get-user-from-token"),
    path('token', jwt_views.TokenObtainPairView.as_view(), name='token_pair'),
    path('token/refresh', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('logout', LogoutView.as_view(), name="logout"),
    path('reset-password', PasswordResetView.as_view(), name="password-reset"),
    path('password-reset/<uidb64>/<token>/', PasswordTokenView.as_view(), name='password-reset-confirm'),
    path('set-password', SetNewPasswordView.as_view(),name='password-reset-done')
]