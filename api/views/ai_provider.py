import logging

from rest_framework.response import Response
from rest_framework import generics, status

from api.crypto import decrypt, encrypt
from api.models.project import Project, ProjectAIProvider, ProjectRole
from api.url_validation import validate_url_for_outbound

logger = logging.getLogger(__name__)

PROVIDER_LABELS = {
    ProjectAIProvider.ProviderType.openai: 'OpenAI-compatible',
    ProjectAIProvider.ProviderType.anthropic: 'Anthropic-compatible',
}
PROVIDERS_LIST = [
    {'value': v, 'label': l}
    for v, l in ProjectAIProvider.ProviderType.choices
]


def _serialize_provider(ai_provider: ProjectAIProvider) -> dict:
    return {
        'enabled': True,
        'provider_type': ai_provider.provider_type,
        'provider_label': PROVIDER_LABELS.get(ai_provider.provider_type, ai_provider.provider_type),
        'endpoint_url': ai_provider.endpoint_url,
        'model_name': ai_provider.model_name,
        'request_timeout': ai_provider.request_timeout,
        'translation_instructions': ai_provider.translation_instructions,
        'verification_instructions': ai_provider.verification_instructions,
        'glossary_extraction_instructions': ai_provider.glossary_extraction_instructions,
        'translation_memory_instructions': ai_provider.translation_memory_instructions,
        'providers': PROVIDERS_LIST,
    }


def _get_admin_project(pk: int, user) -> Project | None:
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
        roles__role__in=ProjectRole.change_participants_roles,
    ).first()


class AIProviderAPI(generics.GenericAPIView):

    def get(self, request, pk):
        project = Project.objects.filter(
            pk=pk, roles__user=request.user
        ).first()
        if not project:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            return Response(_serialize_provider(project.ai_provider))
        except ProjectAIProvider.DoesNotExist:
            return Response({'enabled': False, 'providers': PROVIDERS_LIST})

    def post(self, request, pk):
        project = _get_admin_project(pk, request.user)
        if not project:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        provider_type = request.data.get('provider_type', '').strip()
        api_key = request.data.get('api_key', '').strip()
        model_name = request.data.get('model_name', '').strip()
        endpoint_url = request.data.get('endpoint_url', '').strip()
        try:
            request_timeout = int(request.data.get('request_timeout', 120))
            if request_timeout < 1:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'error': 'request_timeout must be a positive integer'}, status=status.HTTP_400_BAD_REQUEST)

        translation_instructions = request.data.get(
            'translation_instructions', '').strip()
        verification_instructions = request.data.get(
            'verification_instructions', '').strip()
        glossary_extraction_instructions = request.data.get(
            'glossary_extraction_instructions', '').strip()
        translation_memory_instructions = request.data.get(
            'translation_memory_instructions', '').strip()

        if len(translation_instructions) > 4000:
            return Response({'error': 'translation_instructions must be 4000 characters or fewer'}, status=status.HTTP_400_BAD_REQUEST)
        if len(verification_instructions) > 4000:
            return Response({'error': 'verification_instructions must be 4000 characters or fewer'}, status=status.HTTP_400_BAD_REQUEST)
        if len(glossary_extraction_instructions) > 4000:
            return Response({'error': 'glossary_extraction_instructions must be 4000 characters or fewer'}, status=status.HTTP_400_BAD_REQUEST)
        if len(translation_memory_instructions) > 4000:
            return Response({'error': 'translation_memory_instructions must be 4000 characters or fewer'}, status=status.HTTP_400_BAD_REQUEST)

        if not provider_type:
            return Response({'error': 'provider_type is required'}, status=status.HTTP_400_BAD_REQUEST)
        if provider_type not in dict(ProjectAIProvider.ProviderType.choices):
            return Response({'error': 'Invalid provider_type'}, status=status.HTTP_400_BAD_REQUEST)
        if not model_name:
            return Response({'error': 'model_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        if endpoint_url:
            try:
                validate_url_for_outbound(endpoint_url)
            except ValueError as e:
                logger.error(e)
                return Response({'error': 'URL validation failed'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ai_provider = project.ai_provider
            ai_provider.provider_type = provider_type
            ai_provider.model_name = model_name
            ai_provider.endpoint_url = endpoint_url
            ai_provider.request_timeout = request_timeout
            ai_provider.translation_instructions = translation_instructions
            ai_provider.verification_instructions = verification_instructions
            ai_provider.glossary_extraction_instructions = glossary_extraction_instructions
            ai_provider.translation_memory_instructions = translation_memory_instructions
            if api_key:
                ai_provider.api_key = encrypt(api_key)
            ai_provider.save()
        except ProjectAIProvider.DoesNotExist:
            if not api_key:
                return Response({'error': 'api_key is required'}, status=status.HTTP_400_BAD_REQUEST)
            ai_provider = ProjectAIProvider(
                project=project,
                provider_type=provider_type,
                model_name=model_name,
                endpoint_url=endpoint_url,
                request_timeout=request_timeout,
                translation_instructions=translation_instructions,
                verification_instructions=verification_instructions,
                glossary_extraction_instructions=glossary_extraction_instructions,
                translation_memory_instructions=translation_memory_instructions,
                api_key=encrypt(api_key),
            )
            ai_provider.save()

        return Response(_serialize_provider(ai_provider))

    def delete(self, request, pk):
        project = _get_admin_project(pk, request.user)
        if not project:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        try:
            project.ai_provider.delete()
        except ProjectAIProvider.DoesNotExist:
            return Response({'error': 'No AI provider configured'}, status=status.HTTP_404_NOT_FOUND)

        return Response({}, status=status.HTTP_204_NO_CONTENT)
