import zipfile
import json
from django.http import HttpResponse

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.transport_models import TranslationModel


class XCStringsFileReader(TranslationFileReader):
    def read(self, file):
        file.seek(0)
        data = json.load(file)
        result = []
        strings = data.get('strings', {})
        for (key, value) in strings.items():
            comment = value.get('comment')
            localizations = value.get('localizations')
            if localizations:
                for (lang_code, node) in localizations.items():
                    unit = node.get('stringUnit', {})
                    translation = unit.get('value')
                    model = TranslationModel.create(
                        token=key,
                        comment=comment,
                        code=lang_code,
                        translation=translation
                    )
            else:
                model = TranslationModel.create(
                    token=key,
                    comment=comment,
                    translation=''
                )
            result.append(model)
        return result

    def needs_language_code(self):
        return False


class XCStringsFileWriter(TranslationFileWriter):
    def __init__(self):
        self.data = {
            "version": "1.1",
            "sourceLanguage": "en",
            'strings': {}
        }

    def append(self, records, code):
        lang = code.lower()
        for item in records:
            entry = self.data['strings'].setdefault(item.token, {})
            if item.comment:
                entry['comment'] = item.comment

            localizations = entry.setdefault('localizations', {})
            if item.translation:
                localizations[lang] = {
                    'stringUnit': {
                        "state": "translated",
                        'value': item.translation,
                    }
                }
            self.data['strings'][item.token] = entry

    def http_response(self):
        response = HttpResponse(content_type='application/zip')
        zip_file = zipfile.ZipFile(response, 'w')
        zip_file.writestr(
            'Localizable.xcstrings',
            json.dumps(self.data, indent=4, ensure_ascii=False)
        )
        response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        zip_file.close()
        return response
