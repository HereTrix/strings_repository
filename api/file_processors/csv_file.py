import csv
import io
import zipfile

from django.http import HttpResponse

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.models.transport_models import TranslationModel
from api.models.translations import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()

_KEY_COL = 'Localization key'
_TRANSLATION_COL = 'Translation'
_TAGS_COL = 'Tags'
_COMMENT_COL = 'Comments'
_COMMENT_COL_ALT = 'Comment'


def _plural_col(form):
    return f'[{form}]'


class CSVFileReader(TranslationFileReader):

    def read(self, file):
        file.seek(0)
        content = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        result = []
        for row in reader:
            token = row.get(_KEY_COL, '').strip()
            if not token:
                continue
            plural_forms = {
                form: row[_plural_col(form)]
                for form in PLURAL_FORM_ORDER
                if row.get(_plural_col(form), '').strip()
            }
            tags_raw = row.get(_TAGS_COL, '') or ''
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
            result.append(TranslationModel.create(
                token=token,
                translation=row.get(_TRANSLATION_COL, '') or '',
                comment=row.get(_COMMENT_COL) or row.get(_COMMENT_COL_ALT) or None,
                tags=tags or None,
                plural_forms=plural_forms,
            ))
        return result

    def needs_language_code(self):
        return True


class CSVFileWriter(TranslationFileWriter):
    def __init__(self):
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/{code.lower()}/strings{ExportFile.csv.file_extension()}'

    def append(self, records, code):
        output = io.StringIO()
        plural_cols = [_plural_col(f) for f in PLURAL_FORM_ORDER]
        fieldnames = [_KEY_COL, _TRANSLATION_COL,
                      *plural_cols, _TAGS_COL, _COMMENT_COL]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            plural_forms = record.plural_forms or {}
            row = {
                _KEY_COL: record.token,
                _TRANSLATION_COL: record.translation or '',
                _TAGS_COL: ','.join(record.tags or []),
                _COMMENT_COL: record.comment or '',
                **{_plural_col(f): plural_forms.get(f, '') for f in PLURAL_FORM_ORDER},
            }
            writer.writerow(row)
        self.zip_file.writestr(self.path(code=code), output.getvalue())

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response
