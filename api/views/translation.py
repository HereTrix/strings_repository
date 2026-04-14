from api import dispatcher
from api.models.history import HistoryRecord
from api.models.language import Language
from api.models.project import Project, ProjectRole
from django.http import JsonResponse
import django.core.exceptions as exception
from rest_framework import generics, permissions, status
from datetime import datetime

from api.models.tag import Tag
from api.models.translations import Translation, StringToken
from api.languages.langcoder import Langcoder
from api.serializers.translation import StringTokenSerializer, TranslationSerializer


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

        dispatcher.dispatch_event(
            project_id=project.pk,
            event_type='token.created',
            payload={'token': token.token, 'comment': token.comment},
            actor=user.email,
        )

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

        dispatcher.dispatch_event(
            project_id=project.pk,
            event_type='token.deleted',
            payload={'token': token_name},
            actor=user.email,
        )

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

        is_new = not Translation.objects.filter(
            token=token, language__code=code.upper()
        ).exists()

        try:
            translation = Translation.create_or_update_translation(
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

        dispatcher.dispatch_event(
            project_id=project_id,
            event_type='translation.created' if is_new else 'translation.updated',
            payload={
                'token': token.token,
                'language': code.upper(),
                'value': text,
            },
            actor=user.email,
        )

        return JsonResponse({
            'code': code,
            'img': Langcoder.flag(code),
            'translation': translation.translation if translation else '',
            'status': translation.status if translation else Translation.Status.new,
            'plural_forms': {
                pf.plural_form: pf.value
                for pf in translation.plural_forms.all()
            } if translation else {},
        }, status=status.HTTP_200_OK)


class TranslationStatusAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
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

        status_value = request.data.get('status')

        if status_value is None:
            return JsonResponse({
                'error': 'Status is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if status_value not in Translation.Status.values or status_value == Translation.Status.new:
            return JsonResponse({
                'error': 'Invalid status value'
            }, status=status.HTTP_400_BAD_REQUEST)

        token = StringToken.objects.get(
            project__pk=project_id,
            token=token_key,
            project__roles__user=user,
        )
        language = Language.objects.get(
            code=code.upper(), project__pk=project_id)

        translation, _ = Translation.objects.get_or_create(
            token=token,
            language=language,
            defaults={
                'status': Translation.Status.new,
                'translation': '',
            }
        )

        translation.status = status_value
        translation.save()

        dispatcher.dispatch_event(
            project_id=project_id,
            event_type='translation.status_changed',
            payload={
                'token': token_key,
                'language': code.upper(),
                'status': status_value,
            },
            actor=user.email,
        )

        serializer = TranslationSerializer(translation)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)


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

        dispatcher.dispatch_event(
            project_id=token.project_id,
            event_type='token.status_changed',
            payload={'token': token.token, 'status': status_value},
            actor=user.email,
        )

        serializer = StringTokenSerializer(token)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)


class StringTokenTranslationsAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

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

        data = []
        for lang in token.project.languages.all():
            translation = token.translation.filter(language=lang).first()
            data.append({
                'code': lang.code,
                'img': Langcoder.flag(lang.code),
                'translation': translation.translation if translation else '',
                'status': translation.status if translation else Translation.Status.new,
                'plural_forms': {
                    pf.plural_form: pf.value
                    for pf in translation.plural_forms.all()
                } if translation else {},
            })

        return JsonResponse(data, safe=False)
