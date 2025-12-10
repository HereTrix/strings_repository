import enum


class ExportFile(enum.Enum):
    strings = 'strings'
    xcstrings = 'xcstrings'
    android = 'xml'
    excel = 'excel'
    excel_single = 'xlsx'
    json = 'json'
    resx = 'resx'
    properties = 'properties'
    po = 'po'
    mo = 'mo'

    def file_extension(self):
        match self:
            case ExportFile.strings:
                return '.strings'
            case ExportFile.xcstrings:
                return '.xcstrings'
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
            case ExportFile.po:
                return '.po'
            case ExportFile.mo:
                return '.mo'

    def vendor(self):
        match self:
            case ExportFile.strings:
                return 'Apple'
            case ExportFile.xcstrings:
                return 'Apple Xcode'
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
            case ExportFile.po:
                return 'Portable Object'
            case ExportFile.mo:
                return 'Binary MO'
