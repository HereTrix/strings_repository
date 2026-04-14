from django.http import JsonResponse
from rest_framework import generics, permissions, status

from api.models.language import Language
from api.models.translations import PluralTranslation, StringToken, Translation


PLURAL_FORMS = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()


class PluralTranslationAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        user = request.user
        project_id = request.data.get('project_id')
        code = request.data.get('code')
        token_key = request.data.get('token')
        plural_forms = request.data.get('plural_forms')

        if not all([project_id, code, token_key]):
            return JsonResponse(
                {'error': 'project_id, code and token are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(plural_forms, dict):
            return JsonResponse(
                {'error': 'plural_forms must be an object'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invalid = [f for f in plural_forms if f not in PLURAL_FORMS]
        if invalid:
            return JsonResponse(
                {'error': f'Unknown plural forms: {invalid}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = StringToken.objects.filter(
            project__pk=project_id,
            project__roles__user=user,
            token=token_key,
        ).first()
        if not token:
            return JsonResponse(
                {'error': 'Token not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            language = Language.objects.get(
                code=code.upper(), project__pk=project_id
            )
        except Language.DoesNotExist:
            return JsonResponse(
                {'error': 'Language not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        translation, _ = Translation.objects.get_or_create(
            token=token,
            language=language,
            defaults={'translation': '', 'status': Translation.Status.new},
        )

        for form, value in plural_forms.items():
            PluralTranslation.objects.update_or_create(
                translation=translation,
                plural_form=form,
                defaults={'value': value},
            )

        translation.status = Translation.Status.in_review
        translation.save()

        return JsonResponse({}, status=status.HTTP_200_OK)
