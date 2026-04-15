import datetime

from django.http import JsonResponse
from rest_framework import generics, status, permissions

from api.file_processors.export_file_type import ExportFile
from api.file_processors.file_processor import FileProcessor
from api.models.bundle import TranslationBundle, TranslationBundleMap
from api.models.language import Language
from api.models.project import ProjectAccessToken
from api.models.string_token import StringToken
from api.models.translations import Translation
from api.models.transport_models import TranslationModel
from api.serializers.translation import StringTokenModelSerializer


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

        project = access.project
        user = access.user

        codes = request.POST.getlist('codes')
        export_type = request.POST.get('type')
        tags = request.POST.getlist('tags')
        bundle_version = request.POST.get('bundle_version')

        try:
            file_type = ExportFile(export_type)
        except ValueError:
            return JsonResponse({
                'error': 'Unsupported file type'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not codes:
            codes = list(Language.objects.filter(
                project=project
            ).values_list('code', flat=True))

        # Resolve export source:
        # omitted or 'live' -> live translations  (default, development)
        # 'active' -> active bundle (production CI/CD)
        # '<version>' -> specific bundle (QA, rollback check)

        if bundle_version is None or bundle_version == 'live':
            return _export_live(project, user, codes, tags, file_type)

        if bundle_version == 'active':
            bundle = TranslationBundle.objects.filter(
                project=project, is_active=True).first()
            if not bundle:
                return JsonResponse({
                    'error': (
                        'No active bundle for this project. '
                        'Activate a bundle first or use a specific version name.'
                    )
                }, status=status.HTTP_404_NOT_FOUND)
            return _export_bundle(bundle, codes, file_type)

        # Specific version name
        try:
            bundle = TranslationBundle.objects.get(
                project=project, version_name=bundle_version)
        except TranslationBundle.DoesNotExist:
            return JsonResponse({
                'error': f"Bundle '{bundle_version}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        return _export_bundle(bundle, codes, file_type)


def _export_live(project, user, codes, tags, file_type):
    tokens = StringToken.objects.filter(
        project=project,
        project__roles__user=user,
    ).prefetch_related('translation', 'tags')

    for tag in tags:
        tokens = tokens.filter(tags__tag=tag)

    processor = FileProcessor(type=file_type)
    for code in codes:
        try:
            records = [TranslationModel(token_model=t, code=code)
                       for t in tokens]
            processor.append(records=records, code=code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return processor.http_response()


def _export_bundle(bundle, codes, file_type):
    upper_codes = [c.upper() for c in codes]
    maps = (
        bundle.maps
        .select_related('translation__token', 'language')
        .prefetch_related('translation__token__tags')
        .filter(language__code__in=upper_codes)
    )

    by_language = {}
    for m in maps:
        code = m.language.code.lower()
        by_language.setdefault(code, []).append(m)

    processor = FileProcessor(type=file_type)
    for code, bundle_maps in by_language.items():
        records = [TranslationModel.from_bundle_map(m) for m in bundle_maps]
        try:
            processor.append(records=records, code=code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return processor.http_response()
