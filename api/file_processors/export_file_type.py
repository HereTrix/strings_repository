import enum


class ExportFile(enum.Enum):
    strings = 0
    android = 1
    excel = 2
    excel_single = 3

    def file_extension(self):
        match self:
            case ExportFile.strings:
                return '.strings'
            case ExportFile.android:
                return '.xml'
            case ExportFile.excel:
                return '.xlsx'
            case ExportFile.excel_single:
                return '.xlsx'

    def vendor(self):
        match self:
            case ExportFile.strings:
                return 'Apple'
            case ExportFile.android:
                return 'Android'
            case ExportFile.excel:
                return 'Excel with separate sheets'
            case ExportFile.excel_single:
                return 'Excel with single sheet'
