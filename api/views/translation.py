from api.models import StringToken, ProjectRole
from django.http import JsonResponse
import django.core.exceptions as exception
from rest_framework import generics, permissions, status
from datetime import datetime

from api.models import HistoryRecord, Language, Tag, Translation, StringToken, Project, ProjectRole
from api.serializers import StringTokenSerializer, TranslationSerializer


def create_history_record(project, token_name, record_status, user):
    record = HistoryRecord()
    record.project = project
    record.token = token_name
    record.status = record_status
    record.updated_at = datetime.now()
    record.editor = user
    record.save()


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
                'error': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except exception.ValidationError as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        token = StringToken()
        token.token = key
        token.comment = request.data['comment']
        token.project = project
        token.save()

        create_history_record(token.project, token.token,
                              HistoryRecord.Status.created, user)

        if tags:
            for tag in tags:
                token_tag, _ = Tag.objects.get_or_create(tag=tag)
                token.tags.add(token_tag)
            token.save()

        serializer = StringTokenSerializer(token)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        user = request.user
        token_id = request.data['id']

        if token_id is None:
            return JsonResponse({
                'error': 'id is not defined'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = StringToken.objects.get(
                pk=token_id,
                project__roles__user=user,
                project__roles__role__in=ProjectRole.change_token_roles
            )
        except StringToken.DoesNotExist:
            return JsonResponse({
                'error': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except exception.ValidationError as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        token_name = token.token
        project = token.project
        token.delete()

        create_history_record(project, token_name,
                              HistoryRecord.Status.deleted, user)

        return JsonResponse({}, status=status.HTTP_200_OK)


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

        token_key = request.data['token']
        if token_key is None:
            return JsonResponse({
                'error': 'token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        text = request.data['translation']

        token = StringToken.objects.filter(
            project__pk=project_id,
            project__roles__user=user,
            token=token_key
        ).first()

        if token is None:
            return JsonResponse({
                'error': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            Translation.create_translation(
                user=user,
                token=token,
                code=code,
                project_id=project_id,
                text=text
            )
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
        except StringToken.DoesNotExist:
            return JsonResponse({
                'error': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)

        token.tags.clear()
        for tag in tags:
            token_tag, _ = Tag.objects.get_or_create(tag=tag)
            token.tags.add(token_tag)
        token.save()

        return JsonResponse({})


class StringTokenStatusAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        user = request.user
        status_value = request.data.get('status')

        if status_value is None:
            return JsonResponse({
                'error': 'Status is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if status_value not in StringToken.Status.values:
            return JsonResponse({
                'error': 'Invalid status value'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = StringToken.objects.get(
                pk=pk,
                project__roles__user=user,
                project__roles__role__in=ProjectRole.change_token_roles
            )
        except StringToken.DoesNotExist:
            return JsonResponse({
                'error': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)

        token.status = status_value
        token.save()

        serializer = StringTokenSerializer(token)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)


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
            token = StringToken.objects.get(
                pk=pk,
                project__roles__user=user,
            )
        except StringToken.DoesNotExist:
            return JsonResponse({
                'error': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)

        data = [
            {'code': lang.code, 'translation': self.get_or_empty(
                token.translation, lang)}
            for lang in token.project.languages.all()
        ]

        return JsonResponse(data, safe=False)
