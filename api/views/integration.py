import json
import logging

from django.http import JsonResponse
from rest_framework import generics, permissions, status

from api.crypto import encrypt
from api.models.project import Project, ProjectRole, TranslationIntegration
from api.translation_providers import get_provider

logger = logging.getLogger(__name__)


def _ai_fields_from_request(data: dict) -> dict:
    return {
        'endpoint_url': data.get('endpoint_url', ''),
        'payload_template': data.get('payload_template', ''),
        'response_path': data.get('response_path', '') or 'choices.0.message.content',
        'auth_header': data.get('auth_header', '') or 'Authorization',
    }


def _validate_ai_fields(data: dict):
    endpoint_url = data.get('endpoint_url', '').strip()
    payload_template = data.get('payload_template', '').strip()
    if not endpoint_url:
        return 'endpoint_url is required for Generic AI provider'
    if not payload_template:
        return 'payload_template is required for Generic AI provider'
    try:
        json.loads(payload_template)
    except json.JSONDecodeError:
        return 'payload_template must be valid JSON'
    if '{{text}}' not in payload_template:
        return 'payload_template must contain {{text}} placeholder'
    if '{{target_lang}}' not in payload_template:
        return 'payload_template must contain {{target_lang}} placeholder'
    return None


def _integration_response(integration: TranslationIntegration) -> dict:
    data = {
        'enabled': True,
        'provider': integration.provider,
        'provider_label': dict(TranslationIntegration.PROVIDER_CHOICES).get(
            integration.provider, integration.provider
        ),
        'providers': [{'value': v, 'label': l} for v, l in TranslationIntegration.PROVIDER_CHOICES],
    }
    if integration.provider == TranslationIntegration.PROVIDER_AI:
        data.update({
            'endpoint_url': integration.endpoint_url,
            'payload_template': integration.payload_template,
            'response_path': integration.response_path,
            'auth_header': integration.auth_header,
        })
    return data


class IntegrationAPI(generics.GenericAPIView):

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
            return JsonResponse(_integration_response(integration))
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

        if provider == TranslationIntegration.PROVIDER_AI:
            error = _validate_ai_fields(request.data)
            if error:
                return JsonResponse({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            integration = project.integration
            integration.provider = provider
            if api_key:
                integration.api_key = encrypt(api_key)
            if provider == TranslationIntegration.PROVIDER_AI:
                ai = _ai_fields_from_request(request.data)
                integration.endpoint_url = ai['endpoint_url']
                integration.payload_template = ai['payload_template']
                integration.response_path = ai['response_path']
                integration.auth_header = ai['auth_header']
            integration.save()
        except TranslationIntegration.DoesNotExist:
            if not api_key:
                return JsonResponse({'error': 'api_key is required'}, status=status.HTTP_400_BAD_REQUEST)
            ai = _ai_fields_from_request(request.data) if provider == TranslationIntegration.PROVIDER_AI else {}
            integration = TranslationIntegration(
                project=project,
                provider=provider,
                api_key=encrypt(api_key),
                **ai,
            )
            integration.save()

        return JsonResponse(_integration_response(integration))

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
