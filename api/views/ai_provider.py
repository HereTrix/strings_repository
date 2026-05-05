import logging

from django.http import JsonResponse
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
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            return JsonResponse(_serialize_provider(project.ai_provider))
        except ProjectAIProvider.DoesNotExist:
            return JsonResponse({'enabled': False, 'providers': PROVIDERS_LIST})

    def post(self, request, pk):
        project = _get_admin_project(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        provider_type = request.data.get('provider_type', '').strip()
        api_key = request.data.get('api_key', '').strip()
        model_name = request.data.get('model_name', '').strip()
        endpoint_url = request.data.get('endpoint_url', '').strip()

        if not provider_type:
            return JsonResponse({'error': 'provider_type is required'}, status=status.HTTP_400_BAD_REQUEST)
        if provider_type not in dict(ProjectAIProvider.ProviderType.choices):
            return JsonResponse({'error': 'Invalid provider_type'}, status=status.HTTP_400_BAD_REQUEST)
        if not model_name:
            return JsonResponse({'error': 'model_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        if endpoint_url:
            try:
                validate_url_for_outbound(endpoint_url)
            except ValueError as e:
                return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ai_provider = project.ai_provider
            ai_provider.provider_type = provider_type
            ai_provider.model_name = model_name
            ai_provider.endpoint_url = endpoint_url
            if api_key:
                ai_provider.api_key = encrypt(api_key)
            ai_provider.save()
        except ProjectAIProvider.DoesNotExist:
            if not api_key:
                return JsonResponse({'error': 'api_key is required'}, status=status.HTTP_400_BAD_REQUEST)
            ai_provider = ProjectAIProvider(
                project=project,
                provider_type=provider_type,
                model_name=model_name,
                endpoint_url=endpoint_url,
                api_key=encrypt(api_key),
            )
            ai_provider.save()

        return JsonResponse(_serialize_provider(ai_provider))

    def delete(self, request, pk):
        project = _get_admin_project(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        try:
            project.ai_provider.delete()
        except ProjectAIProvider.DoesNotExist:
            return JsonResponse({'error': 'No AI provider configured'}, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)
