import io
from django.http import HttpResponse
import xlsxwriter

from api.file_processors.common import TranslationFileWriter
from api.models.translations import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()


class FileConstants:
    key_item = 'Localization key'
    tags_item = 'Tags'
    comment_item = 'Comments'
    translation_item = 'Translation'

    @staticmethod
    def plural_col(form):
        return f'[{form}]'


class ExcelFileWriter(TranslationFileWriter):

    def __init__(self):
        self.output = io.BytesIO()
        self.wb = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.has_data = False

    def append(self, records, code):
        if self.has_data:
            ws = self.wb.get_worksheet_by_name(code)
        else:
            ws = self.wb.add_worksheet(code)
            self.has_data = True

        plural_cols = [FileConstants.plural_col(f) for f in PLURAL_FORM_ORDER]
        header = [
            FileConstants.key_item,
            FileConstants.translation_item,
            *plural_cols,
            FileConstants.tags_item,
            FileConstants.comment_item,
        ]
        indexes = {k: v for v, k in enumerate(header)}

        for idx, col in enumerate(header):
            ws.write(0, idx, col)

        row = 1
        for record in records:
            ws.write(row, indexes[FileConstants.key_item], record.token)
            ws.write(
                row, indexes[FileConstants.translation_item], record.translation or '')
            ws.write(
                row, indexes[FileConstants.comment_item], record.comment or '')
            ws.write(row, indexes[FileConstants.tags_item],
                     ','.join(record.tags or []))
            for form in PLURAL_FORM_ORDER:
                col = FileConstants.plural_col(form)
                ws.write(row, indexes[col], record.plural_forms.get(
                    form, '') if record.plural_forms else '')
            row += 1

    def http_response(self):
        self.wb.close()
        self.output.seek(0)

        response = HttpResponse(
            content=self.output.read(),
            content_type='application/ms-excel'
        )
        response['Content-Disposition'] = 'attachment; filename=translations.xlsx'
        return response


class ExcelSingleSheetFileWriter:

    def __init__(self) -> None:
        self.records = {}
        self.languages = []

    def append(self, records, code):
        for item in records:
            record = self.records.get(item.token)
            if not record:
                record = {
                    FileConstants.key_item: item.token,
                    FileConstants.comment_item: item.comment or '',
                    FileConstants.tags_item: ','.join(item.tags or []),
                }
            if item.plural_forms:
                # Store each plural form as "<code>[form]"
                for form in PLURAL_FORM_ORDER:
                    col = f'{code}{FileConstants.plural_col(form)}'
                    record[col] = item.plural_forms.get(form, '')
            else:
                record[code] = item.translation or ''
            self.records[item.token] = record
        if code not in self.languages:
            self.languages.append(code)

    def http_response(self):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet()

        lang_cols = []
        for code in self.languages:
            lang_cols.append(code)
            for form in PLURAL_FORM_ORDER:
                lang_cols.append(f'{code}{FileConstants.plural_col(form)}')

        header = [FileConstants.key_item] + lang_cols + \
                 [FileConstants.tags_item, FileConstants.comment_item]
        indexes = {k: v for v, k in enumerate(header)}

        for idx, col in enumerate(header):
            ws.write(0, idx, col)

        row = 1
        for key, record in self.records.items():
            ws.write(row, indexes[FileConstants.key_item], key)
            ws.write(row, indexes[FileConstants.comment_item],
                     record.get(FileConstants.comment_item, ''))
            ws.write(row, indexes[FileConstants.tags_item],
                     record.get(FileConstants.tags_item, ''))
            for col in lang_cols:
                ws.write(row, indexes[col], record.get(col, ''))
            row += 1

        wb.close()
        output.seek(0)

        response = HttpResponse(
            content=output.read(),
            content_type='application/ms-excel'
        )
        response['Content-Disposition'] = 'attachment; filename=translations.xlsx'
        return response
