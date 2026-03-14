import zipfile
from django.http import HttpResponse
import polib

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel
from api.models import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()


class POFileWriter(TranslationFileWriter):

    def __init__(self):
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def append(self, records, code):
        po = polib.POFile()

        for record in records:
            if record.plural_forms:
                ordered = sorted(
                    record.plural_forms.items(),
                    key=lambda kv: PLURAL_FORM_ORDER.index(kv[0])
                    if kv[0] in PLURAL_FORM_ORDER else len(PLURAL_FORM_ORDER)
                )
                msgstr_plural = {i: v for i, (_, v) in enumerate(ordered)}
                entry = polib.POEntry(
                    msgid=record.token,
                    msgid_plural=record.token,
                    msgstr_plural=msgstr_plural,
                    comment=record.comment or '',
                )
            else:
                entry = polib.POEntry(
                    msgid=record.token,
                    msgstr=record.translation or '',
                    comment=record.comment or '',
                )
            po.append(entry)

        contents = getattr(po, '__unicode__')()

        self.zip_file.writestr(
            self.path(code=code),
            contents
        )

    def path(self, code):
        return f'{code.lower()}.{ExportFile.po.file_extension()}'

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response


class POFileReader(TranslationFileReader):

    def read(self, file):
        file.seek(0)
        content = file.read().decode()
        pofile = polib.pofile(content)
        result = []
        for entry in pofile:
            if entry.msgstr_plural:
                # Map numeric indices back to CLDR plural-form names.
                plural_forms = {
                    PLURAL_FORM_ORDER[i] if i < len(PLURAL_FORM_ORDER) else str(i): v
                    for i, v in entry.msgstr_plural.items()
                }
                model = TranslationModel.create(
                    token=entry.msgid,
                    translation='',
                    comment=entry.comment,
                    plural_forms=plural_forms,
                )
            else:
                model = TranslationModel.create(
                    token=entry.msgid,
                    translation=entry.msgstr,
                    comment=entry.comment,
                )
            result.append(model)
        return result
