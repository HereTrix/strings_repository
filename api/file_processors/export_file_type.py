import enum


class ExportFile(enum.Enum):
    strings = 0
    android = 1
    excel = 2
    excel_single = 3
    json = 4
    resx = 5
    properties = 6

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
            case ExportFile.json:
                return '.json'
            case ExportFile.resx:
                return '.resx'
            case ExportFile.properties:
                return '.properties'

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
            case ExportFile.json:
                return 'Key and Value'
            case ExportFile.resx:
                return 'ASP.NET'
            case ExportFile.properties:
                return 'Java'
