import zipfile
from django.http import HttpResponse
import json

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel
from api.models import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()


def _plural_suffix(form):
    return f'_{form}'


def _split_plural_key(token):
    """Return (base_token, form) if token ends with a known plural suffix, else (token, None)."""
    for form in PLURAL_FORM_ORDER:
        if token.endswith(_plural_suffix(form)):
            return token[:-len(_plural_suffix(form))], form
    return token, None


class JsonFileWriter(TranslationFileWriter):

    def __init__(self) -> None:
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/{code.lower()}{ExportFile.json.file_extension()}'

    def append(self, records, code):
        data = {}
        for item in records:
            plural_forms = getattr(item, 'plural_forms', None) or {}
            if plural_forms:
                # Emit each plural form as a suffixed flat key: token_one, token_other, ...
                for form in PLURAL_FORM_ORDER:
                    if form in plural_forms:
                        data[item.token +
                             _plural_suffix(form)] = plural_forms[form]
            else:
                data[item.token] = item.translation
        self.zip_file.writestr(
            self.path(code=code),
            json.dumps(data, indent=4, ensure_ascii=False)
        )

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response


class JsonFileReader(TranslationFileReader):

    def read(self, file):
        file.seek(0)
        data = json.load(file)

        # Two-pass: collect all keys first, then group plural-suffixed ones.
        plural_buckets = {}  # base_token -> {form: value}
        singular_keys = []   # keys that are not plural-suffixed

        for key, value in data.items():
            base, form = _split_plural_key(key)
            if form is not None:
                if base not in plural_buckets:
                    plural_buckets[base] = {}
                plural_buckets[base][form] = value
            else:
                singular_keys.append(key)

        # Rebuild in document order, emitting one model per base token.
        result = []
        seen_plural_bases = set()
        for key in data.keys():
            base, form = _split_plural_key(key)
            if form is not None:
                if base not in seen_plural_bases:
                    seen_plural_bases.add(base)
                    result.append(TranslationModel.create(
                        token=base,
                        translation='',
                        plural_forms=plural_buckets[base],
                    ))
            else:
                value = data[key]
                result.append(TranslationModel.create(
                    token=key,
                    translation=value,
                ))

        return result
