from django.http import HttpResponse, JsonResponse
from rest_framework import generics, permissions, status
import zipfile

from api.file_processors.file_processor import ExportFile, FileProcessor
from api.models import Language, StringToken
from api.transport_models import TranslationModel


class ExportFormatsAPI(generics.GenericAPIView):

    def get(self, request):
        result = [{'type': file.value, 'name': file.vendor(), 'extension': file.file_extension()}
                  for file in ExportFile]
        return JsonResponse(result, safe=False)


class ExportAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            codes = request.GET.get('codes')
            project_id = request.GET['project_id']
            type = request.GET['type']
            tags_query = request.GET.get('tags')
            file_type = ExportFile(type)

            if not file_type:
                return JsonResponse({
                    'error': 'Unsupported file type'
                }, status=status.HTTP_400_BAD_REQUEST)

            if codes:
                lang_codes = codes.split(',')
            else:
                languages = Language.objects.filter(
                    project__pk=project_id
                )

                lang_codes = [lang.code for lang in languages]

            processor = FileProcessor(type=file_type)

            tokens = StringToken.objects.filter(
                project__pk=project_id,
                project__roles__user=user
            ).prefetch_related('translation', 'tags')

            if tags_query:
                tags = tags_query.split(',')
                tokens = tokens.filter(tags__tag__in=tags).distinct()

            for code in lang_codes:
                try:
                    records = [TranslationModel(token_model=token, code=code)
                               for token in tokens]

                    processor.append(records=records, code=code)
                except Exception as e:
                    print(e)

            return processor.http_response()
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)
