from django.http import HttpResponse, JsonResponse
from rest_framework import generics, status, permissions

from api.models import HistoryRecord, Language, ProjectAccessToken, StringToken, Translation
from api.serializers import StringTokenModelSerializer, TranslationSerializer


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
            token = ProjectAccessToken.objects.get(token=token)
            tokens = StringToken.objects.filter(
                project=token.project
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
                    print(e)
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
            token = ProjectAccessToken.objects.get(token=token)
            languages = token.project.languages.all()
            codes = [lang.code for lang in languages]
            return JsonResponse(codes, safe=False)
        except ProjectAccessToken.DoesNotExist:
            return JsonResponse({
                'error': 'No access'
            }, status=status.HTTP_403_FORBIDDEN)
