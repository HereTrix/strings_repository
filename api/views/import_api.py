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
            for tag in tags.split(','):
                try:
                    tag_model = Tag.objects.get(
                        tag=tag
                    )
                except Tag.DoesNotExist:
                    tag_model = Tag()
                    tag_model.tag = tag
                    tag_model.save()

                tag_models.append(tag_model)

        for record in records:
            try:
                Translation.import_record(
                    user=user,
                    project_id=project_id,
                    code=code,
                    record=record,
                    tags=tag_models
                )
            except Project.DoesNotExist:
                return JsonResponse({
                    'error': 'Unable to import'
                }, status=status.HTTP_404_NOT_FOUND)
            except Language.DoesNotExist:
                return JsonResponse({
                    'error': 'Unable to import'
                }, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({})
