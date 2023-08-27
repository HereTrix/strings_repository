from django.http import HttpResponse, JsonResponse
import django.core.exceptions as exception
from rest_framework import generics, permissions, status
from api.models import Language, Translation, StringToken, Project, ProjectRole
from api.serializers import StringTokenSerializer, TranslationSerializer


class StringTokenAPI(generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        project_id = request.data['project']
        key = request.data['token']
        if key is None:
            return JsonResponse({
                'error': 'Token is not defined'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            project = Project.objects.get(
                pk=project_id, roles__user=user, roles__role__in=ProjectRole.change_token_roles)
        except Project.DoesNotExist:
            return JsonResponse({
                'error': 'Project not fount'
            }, status=status.HTTP_404_NOT_FOUND)
        except exception.ValidationError as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)
        token = StringToken()
        token.token = key
        token.comment = request.data['comment']
        token.project = project
        token.save()
        serializer = StringTokenSerializer(token)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        user = request.user
        token = request.data['id']
        if token is None:
            return JsonResponse({
                'error': 'id is not defined'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            object = StringToken.objects.get(
                pk=token, project__roles__user=user, project__roles__role__in=ProjectRole.change_token_roles)
            object.delete()
            return JsonResponse({}, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_404_NOT_FOUND)


class TranslationAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        project_id = request.data['project_id']
        if project_id is None:
            return JsonResponse({
                'error': 'project_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        code = request.data['code']
        if code is None:
            return JsonResponse({
                'error': 'code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        token = request.data['token']
        if token is None:
            return JsonResponse({
                'error': 'token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        text = request.data['translation']

        translations = Translation.objects.filter(
            token__project__pk=project_id,
            token__project__roles__user=user,
            token__token=token,
            language__code=code.upper(),
        )
        translation = translations.first()

        if translation is None:
            try:
                tokens = StringToken.objects.filter(
                    project__pk=project_id,
                    project__roles__user=user,
                    token=token
                )
                token = tokens.first()

                languages = Language.objects.filter(
                    project__pk=project_id,
                    code=code.upper()
                )
                language = languages.first()

                translation = Translation()
                translation.language = language
                translation.token = token
            except StringToken.DoesNotExist:
                return JsonResponse({
                    'error': 'Token not found'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Language.DoesNotExist:
                return JsonResponse({
                    'error': 'Language not found'
                }, status=status.HTTP_400_BAD_REQUEST)

        translation.translation = text
        translation.save()

        return JsonResponse({}, status=status.HTTP_200_OK)
