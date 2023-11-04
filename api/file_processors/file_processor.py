from api.file_processors.android_resources import AndroidResourceFileWriter, AndroidResourceFileReader
from api.file_processors.dotnet_file import DotNetFileWriter
from api.file_processors.excel_file import ExcelFileWriter, ExcelSingleSheetFileWriter
from api.file_processors.export_file_type import ExportFile
from api.file_processors.import_file_type import ImportFile
from api.file_processors.json_file import JsonFileWriter
from api.file_processors.strings_file import AppleStringsFileReader, AppleStringsFileWriter
from api.transport_models import TranslationModel
import tempfile


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


class FileImporter:

    class UnsupportedFile(Exception):
        pass

    def __init__(self, file):
        self.file = file
        extension = file.name.split('.')[-1]
        match extension:
            case ImportFile.strings.name:
                self.reader = AppleStringsFileReader()
            case ImportFile.xml.name:
                self.reader = AndroidResourceFileReader()
            case _:
                raise FileImporter.UnsupportedFile(
                    f"'.{extension}' is not supported file extension",
                )

    def parse(self) -> [TranslationModel]:
        with tempfile.NamedTemporaryFile(delete=True) as destination:
            for chunk in self.file.chunks():
                destination.write(chunk)

            return self.reader.read(file=destination)
