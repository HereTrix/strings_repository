import io
from unittest.mock import MagicMock

from django.test import TestCase

from api.file_processors.export_file_type import ExportFile
from api.file_processors.file_processor import FileImporter, FileProcessor
from api.file_processors.strings_file import AppleStringsFileReader
from api.file_processors.xcstrings_file import XCStringsFileReader
from api.file_processors.android_resources import AndroidResourceFileReader
from api.file_processors.common_json_file import CommonJSONFileReader
from api.file_processors.dotnet_file import DotNetFileReader
from api.file_processors.properties_file import PropertiesFileReader
from api.file_processors.po_file import POFileReader
from api.file_processors.mo_file import MOFileReader


class FileProcessorTestCase(TestCase):

    def test_valid_type_instantiates_writer(self):
        fp = FileProcessor(ExportFile.strings)
        self.assertIsNotNone(fp.writer)

    def test_unsupported_type_raises(self):
        with self.assertRaises(FileProcessor.UnsupportedFile):
            FileProcessor('unsupported_format')

    def test_append_delegates_to_writer(self):
        from api.models.transport_models import TranslationModel
        fp = FileProcessor(ExportFile.json)
        fp.append(records=[TranslationModel.create('key', 'val')], code='en')
        response = fp.http_response()
        self.assertIsNotNone(response)


class FileImporterTestCase(TestCase):

    def _mock_file(self, name: str, content: bytes = b''):
        f = MagicMock()
        f.name = name
        f.chunks.return_value = [content]
        return f

    def test_strings_extension_uses_apple_reader(self):
        importer = FileImporter(self._mock_file('test.strings'))
        self.assertIsInstance(importer.reader, AppleStringsFileReader)

    def test_xcstrings_extension_uses_xcstrings_reader(self):
        importer = FileImporter(self._mock_file('test.xcstrings'))
        self.assertIsInstance(importer.reader, XCStringsFileReader)

    def test_xml_extension_uses_android_reader(self):
        importer = FileImporter(self._mock_file('test.xml'))
        self.assertIsInstance(importer.reader, AndroidResourceFileReader)

    def test_json_extension_uses_common_json_reader(self):
        importer = FileImporter(self._mock_file('test.json'))
        self.assertIsInstance(importer.reader, CommonJSONFileReader)

    def test_resx_extension_uses_dotnet_reader(self):
        importer = FileImporter(self._mock_file('test.resx'))
        self.assertIsInstance(importer.reader, DotNetFileReader)

    def test_properties_extension_uses_properties_reader(self):
        importer = FileImporter(self._mock_file('test.properties'))
        self.assertIsInstance(importer.reader, PropertiesFileReader)

    def test_po_extension_uses_po_reader(self):
        importer = FileImporter(self._mock_file('test.po'))
        self.assertIsInstance(importer.reader, POFileReader)

    def test_mo_extension_uses_mo_reader(self):
        importer = FileImporter(self._mock_file('test.mo'))
        self.assertIsInstance(importer.reader, MOFileReader)

    def test_unsupported_extension_raises(self):
        with self.assertRaises(FileImporter.UnsupportedFile):
            FileImporter(self._mock_file('test.docx'))

    def test_needs_language_code_delegates_to_reader(self):
        importer = FileImporter(self._mock_file('test.strings'))
        self.assertTrue(importer.needs_language_code())

    def test_xcstrings_does_not_need_language_code(self):
        importer = FileImporter(self._mock_file('test.xcstrings'))
        self.assertFalse(importer.needs_language_code())

    def test_parse_json_file_returns_translation_models(self):
        import json as _json
        content = _json.dumps({'greeting': 'Hello'}).encode()
        mock_file = self._mock_file('test.json', content)
        importer = FileImporter(mock_file)
        result = importer.parse()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')

    def test_parse_strings_file_returns_translation_models(self):
        content = b'"key" = "value";'
        mock_file = self._mock_file('test.strings', content)
        importer = FileImporter(mock_file)
        result = importer.parse()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'key')
