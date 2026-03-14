import zipfile
import json
from django.http import HttpResponse

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel
from api.models import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()


class JsonDictFileWriter(TranslationFileWriter):

    def __init__(self) -> None:
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/{code.lower()}{ExportFile.json_dict.file_extension()}'

    def append(self, records, code):
        data = {}
        for item in records:
            plural_forms = getattr(item, 'plural_forms', None) or {}
            entry = {}

            if item.translation:
                entry['value'] = item.translation
            if item.comment:
                entry['comment'] = item.comment
            if item.tags:
                entry['tags'] = item.tags
            if plural_forms:
                entry['plural'] = {
                    form: plural_forms[form]
                    for form in PLURAL_FORM_ORDER
                    if form in plural_forms
                }

            data[item.token] = entry

        self.zip_file.writestr(
            self.path(code=code),
            json.dumps(data, indent=4, ensure_ascii=False)
        )

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response


class JsonDictFileReader(TranslationFileReader):

    def read(self, file):
        file.seek(0)
        data = json.load(file)

        result = []
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue

            plural_forms = entry.get('plural') or {}
            model = TranslationModel.create(
                token=key,
                translation=entry.get('value', ''),
                comment=entry.get('comment'),
                tags=entry.get('tags'),
                plural_forms=plural_forms if isinstance(
                    plural_forms, dict) else {},
            )
            result.append(model)

        return result
