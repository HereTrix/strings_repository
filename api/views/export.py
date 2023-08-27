from django.http import HttpResponse, JsonResponse
from rest_framework import generics, permissions, status
import zipfile

from api.file_processors.file_processor import ExportFile, FileProcessor
from api.models import Language, StringToken
from api.transport_models import TranslationModel


class ExportFormatsAPI(generics.GenericAPIView):

    def get(self, request):
        result = [{'type': file.value, 'name': file.file_extension()}
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
            file_type = ExportFile(int(type))

            if codes:
                lang_codes = codes.split(',')
            else:
                languages = Language.objects.filter(
                    project__pk=project_id
                )

                lang_codes = [lang.code for lang in languages]

            print(f'codes: {lang_codes}')
            response = HttpResponse(content_type='application/zip')
            zip_file = zipfile.ZipFile(response, 'w')
            processor = FileProcessor(type=file_type)

            tokens = StringToken.objects.filter(
                project__pk=project_id,
                project__roles__user=user
            ).prefetch_related('translation')

            for code in lang_codes:
                try:
                    records = [TranslationModel(token_model=token, code=code)
                               for token in tokens]

                    zip_file.writestr(
                        processor.path(code=code), processor.export(records=records))
                except Exception as e:
                    print(e)

            response['Content-Disposition'] = 'attachment; filename="resources.zip"'
            zip_file.close()
            return response
        except Exception as e:
            print(e)
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
