import base64
import io
import logging

import qrcode
from django_otp import user_has_device
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.http import JsonResponse
from rest_framework import generics, permissions, status

from api.models.users import BackupCode, TwoFAVerification
from api.serializers.users import UserSerializer
from api.throttles import TwoFALoginRateThrottle

logger = logging.getLogger(__name__)


class TwoFASetupAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        if user_has_device(user, confirmed=True):
            return JsonResponse(
                {'error': '2FA already active; disable first'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        TOTPDevice.objects.filter(user=user, confirmed=False).delete()

        device = TOTPDevice.objects.create(
            user=user,
            name=user.email or user.username,
            confirmed=False,
        )

        otpauth_uri = device.config_url

        img = qrcode.make(otpauth_uri)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()

        backup_codes = BackupCode.generate(user)

        return JsonResponse({
            'otpauth_uri': otpauth_uri,
            'qr_code': qr_b64,
            'backup_codes': backup_codes,
        })


class TwoFAVerifyAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        code = request.data.get('code', '')

        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if not device:
            return JsonResponse(
                {'error': 'No pending 2FA device'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not device.verify_token(code):
            return JsonResponse(
                {'error': 'Invalid code'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.confirmed = True
        device.save(update_fields=['confirmed'])
        return JsonResponse({})


class TwoFADeleteAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        code = request.data.get('code', '')

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if not device:
            return JsonResponse(
                {'error': 'No active 2FA device'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp_valid = device.verify_token(code)
        backup_valid = not totp_valid and BackupCode.verify_and_consume(user, code)

        if not totp_valid and not backup_valid:
            return JsonResponse(
                {'error': 'Invalid code'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.delete()
        BackupCode.objects.filter(user=user).delete()

        from knox.models import AuthToken
        user_token_keys = AuthToken.objects.filter(
            user=user
        ).values_list('token_key', flat=True)
        TwoFAVerification.objects.filter(token_key__in=user_token_keys).delete()

        return JsonResponse({})


class TwoFALoginAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [TwoFALoginRateThrottle]

    def post(self, request):
        user = request.user
        code = request.data.get('code', '')

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if not device:
            return JsonResponse(
                {'error': 'No active 2FA device'},
                status=status.HTTP_403_FORBIDDEN,
            )

        totp_valid = device.verify_token(code)
        backup_valid = not totp_valid and BackupCode.verify_and_consume(user, code)

        if not totp_valid and not backup_valid:
            return JsonResponse(
                {'error': 'Invalid code'},
                status=status.HTTP_403_FORBIDDEN,
            )

        token_key = request.auth.token_key
        TwoFAVerification.objects.get_or_create(token_key=token_key)

        return JsonResponse({
            'user': UserSerializer(user).data,
            'expired': request.auth.expiry.isoformat() if request.auth.expiry else None,
        })
