from datetime import datetime
from django.http import JsonResponse
from rest_framework.parsers import MultiPartParser
from rest_framework import generics, permissions, status, views

from api.file_processors.file_processor import FileImporter
from api.models import Language, Project, StringToken, Tag, Translation
from api.transport_models import TranslationModel


class ImportAPI(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        user = request.user
        code = request.POST.get('code')
        tags = request.POST.get('tags')
        project_id = request.POST.get('project_id')
        file = request.FILES.get('file')

        if not file:
            return JsonResponse({
                'error': 'No localization file'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not project_id:
            return JsonResponse({
                'error': 'No project_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not code:
            return JsonResponse({
                'error': 'No language code'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            importer = FileImporter(
                file=file
            )

            records = importer.parse()
        except FileImporter.UnsupportedFile as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)

        tag_models = []
        if tags:
            for tag in tags:
                tag_model = Tag.objects.get_or_create(
                    tag=tag
                )
                tag_models.append(tag_model)

        for record in records:
            try:
                project = Project.objects.get(
                    id=project_id
                )
            except Project.DoesNotExist:
                return JsonResponse({
                    'error': 'Unable to import'
                }, status=status.HTTP_404_NOT_FOUND)

            try:
                token = StringToken.objects.get(
                    token=record.token,
                    project=project
                )
            except StringToken.DoesNotExist:
                token = StringToken()
                token.token = record.token
                token.project = project

            if tag_models:
                token.tags = tag_models

            token.save()

            try:
                language = Language.objects.get(
                    code=code,
                    project=project
                )
            except Language.DoesNotExist:
                return JsonResponse({
                    'error': 'Unable to import'
                }, status=status.HTTP_404_NOT_FOUND)

            try:
                translation = Translation.objects.get(
                    language=language,
                    token=token
                )
            except Translation.DoesNotExist:
                translation = Translation()
                translation.language = language
                translation.token = token

            translation.translation = record.translation
            translation.updated_at = datetime.now()
            translation.save()

        return JsonResponse({})
