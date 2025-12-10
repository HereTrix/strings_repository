from api.file_processors.android_resources import AndroidResourceFileWriter, AndroidResourceFileReader
from api.file_processors.dotnet_file import DotNetFileReader, DotNetFileWriter
from api.file_processors.excel_file import ExcelFileWriter, ExcelSingleSheetFileWriter
from api.file_processors.export_file_type import ExportFile
from api.file_processors.import_file_type import ImportFile
from api.file_processors.json_file import JsonFileReader, JsonFileWriter
from api.file_processors.mo_file import MOFileReader, MOFileWriter
from api.file_processors.po_file import POFileReader, POFileWriter
from api.file_processors.properties_file import PropertiesFileReader, PropertiesFileWriter
from api.file_processors.strings_file import AppleStringsFileReader, AppleStringsFileWriter
from api.file_processors.xcstrings_file import XCStringsFileReader, XCStringsFileWriter
from api.transport_models import TranslationModel
import tempfile

WRITER_MAP = {
    ExportFile.strings: AppleStringsFileWriter,
    ExportFile.xcstrings: XCStringsFileWriter,
    ExportFile.android: AndroidResourceFileWriter,
    ExportFile.excel: ExcelFileWriter,
    ExportFile.excel_single: ExcelSingleSheetFileWriter,
    ExportFile.json: JsonFileWriter,
    ExportFile.resx: DotNetFileWriter,
    ExportFile.properties: PropertiesFileWriter,
    ExportFile.po: POFileWriter,
    ExportFile.mo: MOFileWriter,
}


class FileProcessor():

    class UnsupportedFile(Exception):
        pass

    def __init__(self, type: ExportFile):
        self.type = type
        try:
            self.writer = WRITER_MAP[type]()
        except KeyError:
            raise FileProcessor.UnsupportedFile(
                f"Export file type '{type}' is not supported")

    def append(self, records, code):
        self.writer.append(records=records, code=code)

    def http_response(self):
        return self.writer.http_response()


READER_MAP = {
    ImportFile.strings.name: AppleStringsFileReader,
    ImportFile.xcstrings.name: XCStringsFileReader,
    ImportFile.xml.name: AndroidResourceFileReader,
    ImportFile.json.name: JsonFileReader,
    ImportFile.resx.name: DotNetFileReader,
    ImportFile.properties.name: PropertiesFileReader,
    ImportFile.po.name: POFileReader,
    ImportFile.mo.name: MOFileReader,
}


class FileImporter:

    class UnsupportedFile(Exception):
        pass

    def __init__(self, file):
        self.file = file
        extension = file.name.split('.')[-1]
        try:
            self.reader = READER_MAP[extension]()
        except KeyError:
            raise FileImporter.UnsupportedFile(
                f"'.{extension}' is not supported file extension")

    def parse(self) -> list[TranslationModel]:
        with tempfile.NamedTemporaryFile(delete=True) as destination:
            for chunk in self.file.chunks():
                destination.write(chunk)

            return self.reader.read(file=destination)

    def needs_language_code(self) -> bool:
        return self.reader.needs_language_code()
