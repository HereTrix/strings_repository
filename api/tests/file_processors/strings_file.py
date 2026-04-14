import io
import zipfile

from django.test import TestCase

from api.file_processors.strings_file import AppleStringsFileReader, AppleStringsFileWriter
from api.models.transport_models import TranslationModel


def _make_file(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode())


def _zip_content(response, path: str) -> str:
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return zf.read(path).decode()


class AppleStringsReaderTestCase(TestCase):

    def setUp(self):
        self.reader = AppleStringsFileReader()

    def test_basic_key_value(self):
        result = self.reader.read_string('"key" = "value";')
        self.assertEqual(result, [TranslationModel.create('key', 'value')])

    def test_single_line_comment(self):
        result = self.reader.read_string('//My comment\n"key" = "value";')
        self.assertEqual(result, [TranslationModel.create('key', 'value', 'My comment')])

    def test_multi_line_comment(self):
        result = self.reader.read_string('/*Some\ncomment*/\n"key" = "value";')
        self.assertEqual(result, [TranslationModel.create('key', 'value', 'Some\ncomment')])

    def test_multiple_entries(self):
        content = '"a" = "alpha";\n"b" = "beta";'
        result = self.reader.read_string(content)
        self.assertEqual(result, [
            TranslationModel.create('a', 'alpha'),
            TranslationModel.create('b', 'beta'),
        ])

    def test_escaped_quote_in_value(self):
        result = self.reader.read_string('"key" = "val\\"ue";')
        self.assertEqual(result[0].translation, 'val\\"ue')

    def test_plural_keys_grouped(self):
        content = '"item_one" = "one item";\n"item_other" = "many items";'
        result = self.reader.read_string(content)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'item')
        self.assertEqual(result[0].plural_forms, {'one': 'one item', 'other': 'many items'})

    def test_empty_content(self):
        result = self.reader.read_string('')
        self.assertEqual(result, [])

    def test_read_file_object(self):
        f = _make_file('"key" = "value";')
        result = self.reader.read(f)
        self.assertEqual(result, [TranslationModel.create('key', 'value')])


class AppleStringsWriterTestCase(TestCase):

    def test_basic_entry_in_zip(self):
        records = [TranslationModel.create('key', 'value')]
        writer = AppleStringsFileWriter()
        writer.append(records=records, code='en')
        response = writer.http_response()
        content = _zip_content(response, '/en.lproj/Localizable.strings')
        self.assertIn('"key" = "value";', content)

    def test_zip_path_uses_language_code(self):
        writer = AppleStringsFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='FR')
        response = writer.http_response()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            self.assertIn('/fr.lproj/Localizable.strings', zf.namelist())

    def test_entry_with_comment(self):
        records = [TranslationModel.create('key', 'value', 'My comment')]
        writer = AppleStringsFileWriter()
        writer.append(records=records, code='en')
        content = _zip_content(writer.http_response(), '/en.lproj/Localizable.strings')
        self.assertIn('/*My comment*/', content)
        self.assertIn('"key" = "value";', content)

    def test_nbsp_and_percent_substitution(self):
        records = [TranslationModel.create('key', 'hello&nbsp;%s')]
        writer = AppleStringsFileWriter()
        writer.append(records=records, code='en')
        content = _zip_content(writer.http_response(), '/en.lproj/Localizable.strings')
        self.assertIn('hello %@', content)

    def test_plural_entry(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        writer = AppleStringsFileWriter()
        writer.append(records=records, code='en')
        content = _zip_content(writer.http_response(), '/en.lproj/Localizable.strings')
        self.assertIn('"item_one" = "one item";', content)
        self.assertIn('"item_other" = "many";', content)

    def test_http_response_content_disposition(self):
        writer = AppleStringsFileWriter()
        writer.append(records=[], code='en')
        response = writer.http_response()
        self.assertIn('resources.zip', response['Content-Disposition'])
