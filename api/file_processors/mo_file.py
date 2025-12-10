import zipfile
from django.http import HttpResponse
import polib

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel


class MOFileWriter(TranslationFileWriter):

    def __init__(self):
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def append(self, records, code):
        po = polib.POFile()

        for record in records:
            entry = polib.POEntry(
                msgid=record.token,
                msgstr=record.translation,
                comment=record.comment
            )
            po.append(entry)

        contents = getattr(po, 'to_binary')()

        po.save_as_mofile
        self.zip_file.writestr(
            self.path(code=code),
            contents
        )

    def path(self, code):
        return f'{code.lower()}.{ExportFile.mo.file_extension()}'

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response


class MOFileReader(TranslationFileReader):

    def read(self, file):
        file.seek(0)
        content = file.read().decode()
        pofile = polib.mofile(content)
        result = [TranslationModel.create(entry.msgid, entry.msgstr, entry.comment)
                  for entry in pofile]
        return result
