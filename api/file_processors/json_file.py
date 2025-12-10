
import zipfile
from django.http import HttpResponse
import json

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel


class JsonFileWriter(TranslationFileWriter):

    def __init__(self) -> None:
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/{code.lower()}{ExportFile.json.file_extension()}'

    def append(self, records, code):
        data = {item.token: item.translation for item in records}
        self.zip_file.writestr(
            self.path(code=code),
            json.dumps(data, indent=4)
        )

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response


class JsonFileReader(TranslationFileReader):

    def read(self, file):
        file.seek(0)
        data = json.load(file)

        result = []
        for key in data:
            model = TranslationModel.create(
                token=key,
                translation=data[key]
            )
            result.append(model)
        return result
