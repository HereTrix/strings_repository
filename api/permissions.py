# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import logging

from django_otp import user_has_device
from rest_framework.permissions import BasePermission

from api.models.project import Project
from api.models.users import TwoFAVerification

logger = logging.getLogger(__name__)

_GATE_MESSAGE = (
    "This project requires 2FA. "
    "Enable two-factor authentication to access it."
)

_SESSION_MESSAGE = "Complete 2FA login to access this resource."


class TwoFASessionPermission(BasePermission):
    """
    Global permission applied via DEFAULT_PERMISSION_CLASSES.

    If the authenticated user has a confirmed 2FA device, their current Knox
    token must have a TwoFAVerification record (i.e. they completed the 2FA
    login step). Otherwise the request is denied with code "2fa_login_required"
    so the frontend can redirect to /2fa-login.

    Views that declare explicit permission_classes override DEFAULT_PERMISSION_CLASSES
    entirely, so they bypass this check automatically:
      - Plugin/MCP views (AllowAny or custom token auth)
      - TwoFALoginAPI and other 2fa/* endpoints (IsAuthenticated only)
      - Login, signup, passkey auth (AllowAny)
    """

    message = _SESSION_MESSAGE
    code = "2fa_login_required"

    def has_permission(self, request, _view):
        user = request.user
        if not user or not user.is_authenticated:
            return True  # Deferred to IsAuthenticated

        if not user_has_device(user, confirmed=True):
            return True  # No 2FA device configured

        token_key = getattr(request.auth, 'token_key', None)
        if not token_key:
            return False

        return TwoFAVerification.objects.filter(token_key=token_key).exists()


class ProjectTwoFAPermission(BasePermission):
    """
    Global permission applied via DEFAULT_PERMISSION_CLASSES.

    For any DRF view that has `pk` in its URL kwargs, checks whether the
    referenced project requires 2FA. If it does, the requesting user must:
      1. Have a confirmed TOTP device on their account, AND
      2. Have a TwoFAVerification record for their current Knox token key.

    Views with explicit permission_classes (e.g. AllowAny on plugin views)
    override DEFAULT_PERMISSION_CLASSES entirely and bypass this check —
    which is correct, since those views use ProjectAccessToken auth, not Knox.

    Views without `pk` in kwargs (login, signup, 2fa/* endpoints, etc.) pass
    through immediately.
    """

    message = _GATE_MESSAGE

    def has_permission(self, request, view):
        pk = view.kwargs.get('pk')
        if not pk:
            return True

        try:
            project = Project.objects.only('require_2fa').get(pk=pk)
        except Project.DoesNotExist:
            return True  # Let the view return 404

        if not project.require_2fa:
            return True

        # Project requires 2FA: user must have an active confirmed device
        if not user_has_device(request.user, confirmed=True):
            return False

        # AND the current Knox token must have completed the 2FA login step
        token_key = getattr(request.auth, 'token_key', None)
        if not token_key:
            return False

        return TwoFAVerification.objects.filter(token_key=token_key).exists()
