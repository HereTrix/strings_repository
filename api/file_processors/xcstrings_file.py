import zipfile
import json
from django.http import HttpResponse

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.models.transport_models import TranslationModel
from api.models.translations import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()


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
                    variations = node.get('variations', {})
                    plural_node = variations.get('plural', {})
                    if plural_node:
                        plural_forms = {}
                        for form in PLURAL_FORM_ORDER:
                            form_node = plural_node.get(form, {})
                            unit = form_node.get('stringUnit', {})
                            v = unit.get('value')
                            if v is not None:
                                plural_forms[form] = v
                        model = TranslationModel.create(
                            token=key,
                            comment=comment,
                            code=lang_code,
                            translation='',
                            plural_forms=plural_forms,
                        )
                    else:
                        unit = node.get('stringUnit', {})
                        translation = unit.get('value', '')
                        model = TranslationModel.create(
                            token=key,
                            comment=comment,
                            code=lang_code,
                            translation=translation,
                        )
                    result.append(model)
            else:
                result.append(TranslationModel.create(
                    token=key,
                    comment=comment,
                    translation=''
                ))
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

            if item.plural_forms:
                plural_node = {}
                for form in PLURAL_FORM_ORDER:
                    if form not in item.plural_forms:
                        continue
                    plural_node[form] = {
                        'stringUnit': {
                            'state': 'translated',
                            'value': item.plural_forms[form],
                        }
                    }
                if plural_node:
                    localizations[lang] = {
                        'variations': {
                            'plural': plural_node
                        }
                    }
            elif item.translation:
                localizations[lang] = {
                    'stringUnit': {
                        'state': 'translated',
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
