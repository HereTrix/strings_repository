from django.urls import path
from api.views.generic import SignUpAPI, SignInAPI, ProfileAPI, ChangePasswordAPI, ActivateProjectAPI
from api.views.two_fa import TwoFASetupAPI, TwoFAVerifyAPI, TwoFADeleteAPI, TwoFALoginAPI
from api.views.passkey import (
    PasskeyRegisterBeginAPI, PasskeyRegisterCompleteAPI,
    PasskeyAuthBeginAPI, PasskeyAuthCompleteAPI, PasskeyDeleteAPI,
)
from knox.views import LogoutView

urlpatterns = [
    path('signup', SignUpAPI.as_view()),
    path('login', SignInAPI.as_view()),
    path('logout', LogoutView.as_view()),
    path('profile', ProfileAPI.as_view()),
    path('password', ChangePasswordAPI.as_view()),
    path('activate', ActivateProjectAPI.as_view()),
    # 2FA
    path('2fa/setup', TwoFASetupAPI.as_view()),
    path('2fa/verify', TwoFAVerifyAPI.as_view()),
    path('2fa/login', TwoFALoginAPI.as_view()),
    path('2fa', TwoFADeleteAPI.as_view()),
    # passkeys
    path('passkey/register/begin', PasskeyRegisterBeginAPI.as_view()),
    path('passkey/register/complete', PasskeyRegisterCompleteAPI.as_view()),
    path('passkey/auth/begin', PasskeyAuthBeginAPI.as_view()),
    path('passkey/auth/complete', PasskeyAuthCompleteAPI.as_view()),
    path('passkey/<int:pk>', PasskeyDeleteAPI.as_view()),
]
