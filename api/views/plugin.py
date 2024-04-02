import datetime
from django.http import JsonResponse
from rest_framework import generics, status, permissions
from api.file_processors.export_file_type import ExportFile
from api.file_processors.file_processor import FileProcessor

from api.models import Language, ProjectAccessToken, StringToken, Translation
from api.serializers import StringTokenModelSerializer
from api.transport_models import TranslationModel


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

        try:
            access = ProjectAccessToken.objects.get(token=token)

            if access.expiration and access.expiration < datetime.now():
                try:
                    access.delete()
                except Exception:
                    pass

                return JsonResponse({
                    'error': 'No access'
                }, status=status.HTTP_403_FORBIDDEN)

            tokens = StringToken.objects.filter(
                project=access.project
            ).prefetch_related('translation')

            if string_tokens:
                tokens = tokens.filter(
                    token__in=string_tokens
                ).distinct()

            result = [StringTokenModelSerializer(token=token, code=code).toSimplifiedJson()
                      for token in tokens]

            return JsonResponse(result, safe=False)
        except ProjectAccessToken.DoesNotExist:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)


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
            })

        if not data:
            return JsonResponse({
                'error': 'No translations provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            access = ProjectAccessToken.objects.get(token=token)

            if access.permission == ProjectAccessToken.AccessTokenPermissions.read:
                return JsonResponse({
                    'error': 'You do not have permissions to perform this action'
                }, status=status.HTTP_403_FORBIDDEN)

            if access.expiration and access.expiration < datetime.now():
                try:
                    access.delete()
                except Exception:
                    pass

                return JsonResponse({
                    'error': 'No access'
                }, status=status.HTTP_403_FORBIDDEN)

            project = access.project

            for item in data:
                try:
                    try:
                        string_token = StringToken.objects.get(
                            project=project,
                            token=item['token']
                        )
                    except StringToken.DoesNotExist:
                        string_token = StringToken()
                        string_token.project = project
                        string_token.token = item['token']
                        string_token.save()

                    Translation.create_translation(
                        user=access.user,
                        token=string_token,
                        code=code,
                        project_id=project.id,
                        text=item['translation']
                    )
                except Exception as e:
                    pass

            return JsonResponse({})
        except ProjectAccessToken.DoesNotExist:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)


class FetchLanguagesAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.META.get('HTTP_ACCESS_TOKEN')

        if not token:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            access = ProjectAccessToken.objects.get(token=token)

            if access.expiration and access.expiration < datetime.now():
                try:
                    access.delete()
                except Exception:
                    pass

                return JsonResponse({
                    'error': 'No access'
                }, status=status.HTTP_403_FORBIDDEN)

            languages = access.project.languages.all()
            codes = [lang.code for lang in languages]
            return JsonResponse(codes, safe=False)
        except ProjectAccessToken.DoesNotExist:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)


class PluginExportAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            token = request.META.get('HTTP_ACCESS_TOKEN')
            access = ProjectAccessToken.objects.get(token=token)
            if access.expiration and access.expiration < datetime.now():
                try:
                    access.delete()
                except Exception:
                    pass
                return JsonResponse({
                    'error': 'No access'
                }, status=status.HTTP_403_FORBIDDEN)

        except Exception:
            return JsonResponse({
                'error': 'No access'
            })

        try:
            user = access.user
            project_id = access.project.id

            codes = request.POST.getlist('codes')
            type = request.POST.get('type')
            tags = request.POST.getlist('tags')
            file_type = ExportFile(type)

            if not file_type:
                return JsonResponse({
                    'error': 'Unsupported file type'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not codes:
                languages = Language.objects.filter(
                    project__pk=project_id
                )

                codes = [lang.code for lang in languages]

            processor = FileProcessor(type=file_type)

            tokens = StringToken.objects.filter(
                project__pk=project_id,
                project__roles__user=user
            ).prefetch_related('translation', 'tags')

            if tags:
                tokens = tokens.filter(tags__tag__in=tags).distinct()

            if isinstance(codes, str):
                try:
                    records = [TranslationModel(token_model=token, code=codes)
                               for token in tokens]

                    processor.append(records=records, code=codes)
                except Exception as e:
                    pass
            else:
                for code in codes:
                    try:
                        records = [TranslationModel(token_model=token, code=code)
                                   for token in tokens]

                        processor.append(records=records, code=code)
                    except Exception as e:
                        pass
            return processor.http_response()
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)
