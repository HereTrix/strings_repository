import enum
from api.file_processors.android_resources import AndroidResourceFileWriter
from api.file_processors.strings_file import AppleStringsFileWriter


class ExportFile(enum.Enum):
    strings = 0
    android = 1

    def file_extension(self):
        match self:
            case ExportFile.strings:
                return '.strings'
            case ExportFile.android:
                return '.xml'


class FileProcessor():

    def __init__(self, type):
        self.type = type

    def export(self, records):
        match self.type:
            case ExportFile.strings:
                writer = AppleStringsFileWriter(records=records)
                return writer.convert_file()
            case ExportFile.android:
                writer = AndroidResourceFileWriter(records=records)
                return writer.convert_file()

    def path(self, code):
        match self.type:
            case ExportFile.strings:
                return f'/{code.lower()}.lproj/Localizable{self.type.file_extension()}'
            case ExportFile.android:
                return f'/values-{code.lower()}/strings{self.type.file_extension()}'
