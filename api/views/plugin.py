import datetime

from django.http import JsonResponse
from rest_framework import generics, status, permissions

from api.file_processors.export_file_type import ExportFile
from api.file_processors.file_processor import FileProcessor
from api.models import Language, ProjectAccessToken, StringToken, Translation
from api.transport_models import TranslationModel
from api.serializers import StringTokenModelSerializer


def validate_access_token(token):
    """
    Returns (access, error_response) tuple.
    If the token is invalid or expired, access is None and error_response is a JsonResponse.
    """
    try:
        access = ProjectAccessToken.objects.get(token=token)
    except ProjectAccessToken.DoesNotExist:
        return None, JsonResponse({
            'error': 'No access'
        }, status=status.HTTP_403_FORBIDDEN)

    if access.expiration and access.expiration < datetime.datetime.now():
        access.delete()
        return None, JsonResponse({
            'error': 'No access'
        }, status=status.HTTP_403_FORBIDDEN)

    return access, None


class PullAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.META.get('HTTP_ACCESS_TOKEN')
        string_tokens = request.data.get('tokens')
        code = request.data.get('code')

        if not token:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)
        if not code:
            return JsonResponse({
                'error': 'No language code'
            }, status=status.HTTP_400_BAD_REQUEST)
        if not string_tokens:
            return JsonResponse({
                'error': 'No localization keys to fetch'
            }, status=status.HTTP_400_BAD_REQUEST)

        access, error = validate_access_token(token)
        if error:
            return error

        tokens = StringToken.objects.filter(
            project=access.project
        ).prefetch_related('translation').filter(
            token__in=string_tokens
        ).distinct()

        serializer = StringTokenModelSerializer(tokens, many=True)
        return JsonResponse(serializer.data, safe=False)


class PushAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.META.get('HTTP_ACCESS_TOKEN')
        data = request.data.get('translations')
        code = request.data.get('code')

        if not token:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)
        if not code:
            return JsonResponse({
                'error': 'No language code'
            }, status=status.HTTP_400_BAD_REQUEST)
        if not data:
            return JsonResponse({
                'error': 'No translations provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        access, error = validate_access_token(token)
        if error:
            return error

        if access.permission == ProjectAccessToken.AccessTokenPermissions.read:
            return JsonResponse({
                'error': 'You do not have permissions to perform this action'
            }, status=status.HTTP_403_FORBIDDEN)

        project = access.project
        failed = []

        for item in data:
            try:
                string_token, _ = StringToken.objects.get_or_create(
                    project=project,
                    token=item['token']
                )
                Translation.create_translation(
                    user=access.user,
                    token=string_token,
                    code=code,
                    project_id=project.id,
                    text=item['translation']
                )
            except Exception as e:
                failed.append({'token': item.get('token'), 'error': str(e)})

        if failed:
            return JsonResponse({'failed': failed}, status=status.HTTP_207_MULTI_STATUS)

        return JsonResponse({})


class FetchLanguagesAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.META.get('HTTP_ACCESS_TOKEN')

        if not token:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)

        access, error = validate_access_token(token)
        if error:
            return error

        codes = [lang.code for lang in access.project.languages.all()]
        return JsonResponse(codes, safe=False)


class PluginExportAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.META.get('HTTP_ACCESS_TOKEN')

        if not token:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)

        access, error = validate_access_token(token)
        if error:
            return error

        project_id = access.project.id
        user = access.user

        codes = request.POST.getlist('codes')
        export_type = request.POST.get('type')
        tags = request.POST.getlist('tags')

        try:
            file_type = ExportFile(export_type)
        except ValueError:
            return JsonResponse({
                'error': 'Unsupported file type'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not codes:
            codes = list(Language.objects.filter(
                project__pk=project_id
            ).values_list('code', flat=True))

        tokens = StringToken.objects.filter(
            project__pk=project_id,
            project__roles__user=user
        ).prefetch_related('translation', 'tags')

        for tag in tags:
            tokens = tokens.filter(tags__tag=tag)

        processor = FileProcessor(type=file_type)

        for code in codes:
            try:
                records = [TranslationModel(
                    token_model=token, code=code) for token in tokens]
                processor.append(records=records, code=code)
            except Exception as e:
                return JsonResponse({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

        return processor.http_response()
