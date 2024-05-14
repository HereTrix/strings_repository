from django.http import HttpResponse, JsonResponse
import django.core.exceptions as exception
from rest_framework import generics, permissions, status
from api.models import HistoryRecord, Language, Tag, Translation, StringToken, Project, ProjectRole
from api.serializers import StringTokenSerializer, TranslationSerializer
from datetime import datetime


class StringTokenAPI(generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        project_id = request.data['project']
        key = request.data['token']
        tags = request.data.get('tags')
        if key is None:
            return JsonResponse({
                'error': 'Token is not defined'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            project = Project.objects.get(
                pk=project_id,
                roles__user=user,
                roles__role__in=ProjectRole.change_token_roles
            )
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

        if tags:
            for tag in tags:
                token_tag, _ = Tag.objects.get_or_create(
                    tag=tag
                )
                token.tags.add(token_tag)
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

        try:
            token = StringToken.objects.filter(
                project__pk=project_id,
                project__roles__user=user,
                token=token
            ).first()

            Translation.create_translation(
                user=user,
                token=token,
                code=code,
                project_id=project_id,
                text=text
            )
        except StringToken.DoesNotExist:
            return JsonResponse({
                'error': 'Token not found'
            })
        except Language.DoesNotExist:
            return JsonResponse({
                'error': 'Language not found'
            }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({}, status=status.HTTP_200_OK)


class StringTokenTagAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        tags = request.data['tags']
        try:
            token = StringToken.objects.get(
                pk=pk,
                project__roles__user=user,
                project__roles__role__in=ProjectRole.change_token_roles
            )
            token.tags.clear()
            for tag in tags:
                token_tag, _ = Tag.objects.get_or_create(
                    tag=tag
                )
                token.tags.add(token_tag)

            token.save()
            return JsonResponse({})
        except StringToken.DoesNotExist:
            return JsonResponse({
                'error': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)


class StringTokenTranslationsAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_or_empty(self, translation, language):
        try:
            return translation.get(language=language).translation
        except Translation.DoesNotExist:
            return ''

    def get(self, request, pk):
        user = request.user
        try:
            # TODO: Need to refactor
            token = StringToken.objects.get(
                pk=pk,
                project__roles__user=user,
            )

            data = [{'code': lang.code, 'translation': self.get_or_empty(token.translation, lang)}
                    for lang in token.project.languages.all()]

            return JsonResponse(data, safe=False)
        except StringToken.DoesNotExist:
            return JsonResponse({
                'error': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)
