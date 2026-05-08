import io

import xlsxwriter


class CompareFileWriter:
    """
    Writes a compare diff to an xlsx file.

    mode='diff'    — one row per entry: Token | Language | From | To | Change
    mode='changes' — only new/changed values: Token | Language | Value
    """
    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def __init__(self, diff: dict, mode: str = 'diff'):
        self.diff = diff
        self.mode = mode

    @property
    def filename(self):
        return f'compare_{self.mode}.xlsx'

    def write(self, buf) -> None:
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})

        if self.mode == 'diff':
            self._write_diff(wb)
        else:
            self._write_changes(wb)

        wb.close()
        output.seek(0)
        buf.write(output.read())

    def _write_diff(self, wb):
        ws = wb.add_worksheet('Diff')
        bold = wb.add_format({'bold': True})
        for col, header in enumerate(['Token', 'Language', 'From', 'To', 'Change']):
            ws.write(0, col, header, bold)

        row = 1
        for entry in self.diff['changed']:
            ws.write(row, 0, entry['token'])
            ws.write(row, 1, entry['language'])
            ws.write(row, 2, entry.get('from', ''))
            ws.write(row, 3, entry.get('to', ''))
            ws.write(row, 4, 'changed')
            row += 1

        for entry in self.diff['added']:
            ws.write(row, 0, entry['token'])
            ws.write(row, 1, entry['language'])
            ws.write(row, 2, '')
            ws.write(row, 3, entry.get('value', ''))
            ws.write(row, 4, 'added')
            row += 1

        for entry in self.diff['removed']:
            ws.write(row, 0, entry['token'])
            ws.write(row, 1, entry['language'])
            ws.write(row, 2, entry.get('from', ''))
            ws.write(row, 3, '')
            ws.write(row, 4, 'removed')
            row += 1

        for token in self.diff['new_tokens']:
            ws.write(row, 0, token)
            ws.write(row, 1, '')
            ws.write(row, 2, '')
            ws.write(row, 3, '')
            ws.write(row, 4, 'new key')
            row += 1

        for token in self.diff['deleted_tokens']:
            ws.write(row, 0, token)
            ws.write(row, 1, '')
            ws.write(row, 2, '')
            ws.write(row, 3, '')
            ws.write(row, 4, 'deleted key')
            row += 1

    def _write_changes(self, wb):
        ws = wb.add_worksheet('Changes')
        bold = wb.add_format({'bold': True})
        for col, header in enumerate(['Token', 'Language', 'Value']):
            ws.write(0, col, header, bold)

        row = 1
        for entry in self.diff['changed']:
            ws.write(row, 0, entry['token'])
            ws.write(row, 1, entry['language'])
            ws.write(row, 2, entry.get('to', ''))
            row += 1

        for entry in self.diff['added']:
            ws.write(row, 0, entry['token'])
            ws.write(row, 1, entry['language'])
            ws.write(row, 2, entry.get('value', ''))
            row += 1

        for token in self.diff['new_tokens']:
            ws.write(row, 0, token)
            ws.write(row, 1, '')
            ws.write(row, 2, '')
            row += 1
