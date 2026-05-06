import base64
from datetime import timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
import webauthn
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    AttestationConveyancePreference,
)

from api.models.users import PasskeyCredential, PasskeyChallenge, TwoFAVerification
from api.throttles import PasskeyAuthRateThrottle


def _expected_origin():
    if settings.WEBAUTHN_ORIGIN:
        return settings.WEBAUTHN_ORIGIN
    if settings.WEBAUTHN_RP_ID == 'localhost':
        return 'https://localhost:8000'
    return f'https://{settings.WEBAUTHN_RP_ID}'


def _sweep_expired_challenges():
    PasskeyChallenge.objects.filter(
        created_at__lt=timezone.now() - timedelta(minutes=5)
    ).delete()


class PasskeyRegisterBeginAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if PasskeyCredential.objects.filter(user=request.user).count() >= 10:
            return Response({'error': 'Maximum number of passkeys reached'}, status=400)

        name = request.data.get('name', '')

        options = webauthn.generate_registration_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            rp_name=settings.WEBAUTHN_RP_NAME,
            user_id=str(request.user.pk).encode(),
            user_name=request.user.username,
            user_display_name=request.user.username,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED,
                resident_key=ResidentKeyRequirement.PREFERRED,
            ),
        )

        PasskeyChallenge.objects.create(
            user=request.user,
            challenge=bytes(options.challenge),
        )

        return Response({'publicKey': webauthn.options_to_json(options), 'name': name})


class PasskeyRegisterCompleteAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _sweep_expired_challenges()

        challenge_obj = PasskeyChallenge.objects.filter(
            user=request.user
        ).order_by('-created_at').first()
        if not challenge_obj:
            return Response({'error': 'Challenge expired or not found'}, status=400)

        try:
            registration_verification = webauthn.verify_registration_response(
                credential=request.data['credential'],
                expected_challenge=bytes(challenge_obj.challenge),
                expected_rp_id=settings.WEBAUTHN_RP_ID,
                expected_origin=_expected_origin(),
                require_user_verification=False,
            )
        except Exception as e:
            print(e)
            challenge_obj.delete()
            return Response({'error': 'Passkey verification failed'}, status=400)

        challenge_obj.delete()

        if PasskeyCredential.objects.filter(
            credential_id=registration_verification.credential_id
        ).exists():
            return Response({'error': 'This passkey is already registered'}, status=400)

        cred = PasskeyCredential.objects.create(
            user=request.user,
            credential_id=bytes(registration_verification.credential_id),
            public_key=bytes(registration_verification.credential_public_key),
            sign_count=registration_verification.sign_count,
            name=request.data.get('name', '')[:100],
        )

        return Response({
            'id': cred.pk,
            'name': cred.name,
            'created_at': cred.created_at.isoformat(),
        })


class PasskeyAuthBeginAPI(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasskeyAuthRateThrottle]

    def post(self, request):
        options = webauthn.generate_authentication_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            allow_credentials=[],
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        PasskeyChallenge.objects.create(
            user=None,
            challenge=bytes(options.challenge),
        )

        return Response({'publicKey': webauthn.options_to_json(options)})


class PasskeyAuthCompleteAPI(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasskeyAuthRateThrottle]

    def post(self, request):
        _sweep_expired_challenges()

        raw_id_b64 = request.data['credential']['rawId']
        padded = raw_id_b64 + '=' * (4 - len(raw_id_b64) % 4)
        raw_id = base64.urlsafe_b64decode(padded)

        cred = PasskeyCredential.objects.filter(credential_id=raw_id).first()
        if not cred:
            return Response({'error': 'Passkey not recognised'}, status=400)

        challenge_obj = PasskeyChallenge.objects.filter(
            user=None
        ).order_by('-created_at').first()
        if not challenge_obj:
            return Response({'error': 'Challenge expired or not found'}, status=400)

        origin = _expected_origin()

        try:
            auth_verification = webauthn.verify_authentication_response(
                credential=request.data['credential'],
                expected_challenge=bytes(challenge_obj.challenge),
                expected_rp_id=settings.WEBAUTHN_RP_ID,
                expected_origin=origin,
                credential_public_key=bytes(cred.public_key),
                credential_current_sign_count=cred.sign_count,
                require_user_verification=False,
            )
        except Exception:
            challenge_obj.delete()
            return Response({'error': 'Passkey verification failed'}, status=400)

        challenge_obj.delete()

        if auth_verification.new_sign_count < cred.sign_count and cred.sign_count > 0:
            return Response({'error': 'Passkey replay detected'}, status=400)

        cred.sign_count = auth_verification.new_sign_count
        cred.save(update_fields=['sign_count'])

        instance, token = AuthToken.objects.create(user=cred.user)
        TwoFAVerification.objects.get_or_create(token_key=instance.token_key)
        return Response({'token': token})


class PasskeyDeleteAPI(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        cred = get_object_or_404(PasskeyCredential, pk=pk)
        if cred.user != request.user:
            return Response({'error': 'Forbidden'}, status=403)
        cred.delete()
        return Response({})
