import openpyxl


class HistoryFileWriter:

    def __init__(self, data, languages):
        self.data = data
        self.languages = languages

    def write(self, response):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Report'

        key_item = 'Localization key'

        header = [key_item] + self.languages

        indexes = {k: v + 1 for v, k in enumerate(header)}

        for idx in range(len(header)):
            cell = ws.cell(row=1, column=idx+1)
            cell.value = header[idx]

        row = 2

        for token in self.data:
            cell = ws.cell(row=row, column=indexes[key_item])
            cell.value = token.token
            for translation in token.translation.all():
                cell = ws.cell(row=row,
                               column=indexes[translation.language.code]
                               )
                cell.value = translation.translation
            row += 1

        wb.save(response)
