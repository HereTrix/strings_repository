import io
from django.http import HttpResponse
import xlsxwriter
import tempfile


class FileConstants:
    key_item = 'Localization key'
    tags_item = 'Tags'
    comment_item = 'Comments'
    translation_item = 'Translation'


class ExcelFileWriter:

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

        header = [FileConstants.key_item,
                  FileConstants.translation_item,
                  FileConstants.tags_item,
                  FileConstants.comment_item]
        indexes = {k: v for v, k in enumerate(header)}

        for idx in range(len(header)):
            ws.write(0, idx, header[idx])

        row = 1

        for record in records:
            ws.write(row, indexes[FileConstants.key_item], record.token)
            ws.write(
                row, indexes[FileConstants.translation_item], record.translation)
            ws.write(row, indexes[FileConstants.comment_item], record.comment)
            ws.write(row, indexes[FileConstants.tags_item],
                     ','.join(record.tags))
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
                    FileConstants.comment_item: item.comment,
                    FileConstants.tags_item: ','.join(item.tags)
                }
            record[code] = item.translation
            self.records[item.token] = record
        self.languages.append(code)

    def http_response(self):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet()

        header = [FileConstants.key_item] + \
            self.languages + \
            [FileConstants.tags_item, FileConstants.comment_item]
        indexes = {k: v for v, k in enumerate(header)}

        for idx in range(len(header)):
            ws.write(0, idx, header[idx])

        row = 1
        for key in self.records.keys():
            record = self.records[key]
            ws.write(
                row,
                indexes[FileConstants.key_item],
                key
            )
            ws.write(
                row,
                indexes[FileConstants.comment_item],
                record[FileConstants.comment_item]
            )
            ws.write(row, indexes[FileConstants.tags_item],
                     record[FileConstants.tags_item])

            for code in self.languages:
                ws.write(
                    row,
                    indexes[code],
                    record[code]
                )

            row += 1

        wb.close()
        output.seek(0)

        response = HttpResponse(
            content=output.read(),
            content_type='application/ms-excel'
        )
        response['Content-Disposition'] = 'attachment; filename=translations.xlsx'
        return response
