from api.file_processors.android_resources import AndroidResourceFileWriter
from api.file_processors.dotnet_file import DotNetFileWriter
from api.file_processors.excel_file import ExcelFileWriter, ExcelSingleSheetFileWriter
from api.file_processors.export_file_type import ExportFile
from api.file_processors.json_file import JsonFileWriter
from api.file_processors.strings_file import AppleStringsFileWriter


class FileProcessor():

    def __init__(self, type):
        self.type = type
        match type:
            case ExportFile.strings:
                self.writer = AppleStringsFileWriter()
            case ExportFile.android:
                self.writer = AndroidResourceFileWriter()
            case ExportFile.excel:
                self.writer = ExcelFileWriter()
            case ExportFile.excel_single:
                self.writer = ExcelSingleSheetFileWriter()
            case ExportFile.json:
                self.writer = JsonFileWriter()
            case ExportFile.resx:
                self.writer = DotNetFileWriter()

    def append(self, records, code):
        self.writer.append(records=records, code=code)

    def http_response(self):
        return self.writer.http_response()
