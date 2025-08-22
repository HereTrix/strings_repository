import xlsxwriter
import io
from datetime import datetime


class HistoryFileWriter:

    def __init__(self, data):
        self.data = data

    def write(self, response):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Report')

        key_item = 'Localization key'
        tags_item = 'Tags'
        comment_item = 'Comments'
        language_item = 'Language'
        translation_item = 'Translation'
        update_item = 'Updated at'

        header = [key_item, language_item,
                  translation_item, update_item]

        indexes = {k: v for v, k in enumerate(header)}

        for idx in range(len(header)):
            ws.write(0, idx, header[idx])

        row = 1
        for item in self.data:
            ws.write(row, indexes[key_item], item.token)
            ws.write(row, indexes[language_item], item.language)
            ws.write(row, indexes[translation_item], item.new_value)
            ws.write(row, indexes[update_item],
                     item.updated_at.strftime('%Y-%m-%d %H:%M'))
            row += 1

        wb.close()
        output.seek(0)
        response.headers['Content-Disposition'] = 'attachment; filename=history.xlsx'
        response.write(output.read())
