import logging

from django.http import JsonResponse
from rest_framework import generics, permissions, status

from api.crypto import encrypt
from api.models.project import Project, ProjectRole, TranslationIntegration
from api.translation_providers import get_provider

logger = logging.getLogger(__name__)


class IntegrationAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        project = Project.objects.filter(
            pk=pk,
            roles__user=request.user,
        ).first()
        if not project:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        providers = [{'value': v, 'label': l} for v, l in TranslationIntegration.PROVIDER_CHOICES]
        try:
            integration = project.integration
            return JsonResponse({
                'enabled': True,
                'provider': integration.provider,
                'provider_label': dict(TranslationIntegration.PROVIDER_CHOICES).get(integration.provider, integration.provider),
                'providers': providers,
            })
        except TranslationIntegration.DoesNotExist:
            return JsonResponse({'enabled': False, 'providers': providers})

    def post(self, request, pk):
        project = Project.objects.filter(
            pk=pk,
            roles__user=request.user,
            roles__role__in=ProjectRole.change_participants_roles,
        ).first()
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        provider = request.data.get('provider')
        api_key = request.data.get('api_key')

        if not provider:
            return JsonResponse({'error': 'provider is required'}, status=status.HTTP_400_BAD_REQUEST)
        if provider not in dict(TranslationIntegration.PROVIDER_CHOICES):
            return JsonResponse({'error': 'Invalid provider'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            integration = project.integration
            integration.provider = provider
            if api_key:
                integration.api_key = encrypt(api_key)
            integration.save()
        except TranslationIntegration.DoesNotExist:
            if not api_key:
                return JsonResponse({'error': 'api_key is required'}, status=status.HTTP_400_BAD_REQUEST)
            integration = TranslationIntegration(
                project=project,
                provider=provider,
                api_key=encrypt(api_key),
            )
            integration.save()

        return JsonResponse({
            'enabled': True,
            'provider': integration.provider,
            'provider_label': dict(TranslationIntegration.PROVIDER_CHOICES).get(integration.provider, integration.provider),
            'providers': [{'value': v, 'label': l} for v, l in TranslationIntegration.PROVIDER_CHOICES],
        })

    def delete(self, request, pk):
        project = Project.objects.filter(
            pk=pk,
            roles__user=request.user,
            roles__role__in=ProjectRole.change_participants_roles,
        ).first()
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        try:
            project.integration.delete()
        except TranslationIntegration.DoesNotExist:
            return JsonResponse({'error': 'No integration configured'}, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)


class VerifyIntegrationAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        project = Project.objects.filter(
            pk=pk,
            roles__user=request.user,
            roles__role__in=ProjectRole.change_participants_roles,
        ).first()
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        try:
            integration = project.integration
        except TranslationIntegration.DoesNotExist:
            return JsonResponse({'error': 'No integration configured'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            provider = get_provider(integration)
            provider.translate('Hello', 'FR')
        except Exception as e:
            logger.exception('Integration verification failed for project %s: %s', pk, e)
            return JsonResponse({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return JsonResponse({'ok': True})


class MachineTranslateAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        project = Project.objects.filter(
            pk=pk,
            roles__user=request.user,
        ).first()
        if not project:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            integration = project.integration
        except TranslationIntegration.DoesNotExist:
            return JsonResponse(
                {'error': 'No translation integration configured'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = request.data.get('text')
        target_lang = request.data.get('target_language')
        source_lang = request.data.get('source_language')

        if not text or not target_lang:
            return JsonResponse(
                {'error': 'text and target_language are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            provider = get_provider(integration)
            translation = provider.translate(text, target_lang, source_lang)
        except Exception as e:
            logger.exception('Machine translation failed for project %s: %s', pk, e)
            return JsonResponse({'error': 'Translation failed'}, status=status.HTTP_502_BAD_GATEWAY)

        return JsonResponse({'translation': translation})
