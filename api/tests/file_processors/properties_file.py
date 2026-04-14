import io
import zipfile

from django.test import TestCase

from api.file_processors.properties_file import PropertiesFileReader, PropertiesFileWriter
from api.models.transport_models import TranslationModel


def _make_file(content) -> io.BytesIO:
    if isinstance(content, bytes):
        return io.BytesIO(content)
    return io.BytesIO(content.encode())


def _zip_properties(response, code: str) -> str:
    path = f'/{code.lower()}.properties'
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return zf.read(path).decode()


class PropertiesReaderTestCase(TestCase):

    def setUp(self):
        self.reader = PropertiesFileReader()

    def test_equals_separator(self):
        result = self.reader.read(_make_file(b'greeting=Hello'))
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')

    def test_colon_separator(self):
        result = self.reader.read(_make_file(b'greeting:Hello'))
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')

    def test_comment_attached_to_next_entry(self):
        content = b'# A note\ngreeting=Hello'
        result = self.reader.read(_make_file(content))
        self.assertIn('A note', result[0].comment)

    def test_plural_keys_grouped(self):
        content = b'item[one]=one item\nitem[other]=many items'
        result = self.reader.read(_make_file(content))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'item')
        self.assertEqual(result[0].plural_forms.get('one'), 'one item')
        self.assertEqual(result[0].plural_forms.get('other'), 'many items')

    def test_escaped_equals_in_key(self):
        # key\=name=value → token "key=name", value "value"
        result = self.reader.read(_make_file(b'key\\=name=value'))
        self.assertIn('key', result[0].token)
        self.assertIn('=', result[0].token)

    def test_multiple_entries(self):
        content = b'a=alpha\nb=beta'
        result = self.reader.read(_make_file(content))
        self.assertEqual(len(result), 2)

    def test_empty_file(self):
        result = self.reader.read(_make_file(b''))
        self.assertEqual(result, [])

    def test_process_line_prev_not_reset_after_escaped_delim(self):
        # After an escaped '=', prev remains '\\' until the next non-delimiter char.
        # A second consecutive '=' is therefore also skipped, leaving an empty token.
        # This documents the known parser limitation.
        result = self.reader.read(_make_file(b'key\\==value'))
        self.assertEqual(result[0].token, '')


class PropertiesWriterTestCase(TestCase):

    def test_basic_entry(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = PropertiesFileWriter()
        writer.append(records=records, code='en')
        content = _zip_properties(writer.http_response(), 'en')
        self.assertIn('greeting=Hello', content)

    def test_comment_prefixed_with_hash(self):
        records = [TranslationModel.create('key', 'val', 'my comment')]
        writer = PropertiesFileWriter()
        writer.append(records=records, code='en')
        content = _zip_properties(writer.http_response(), 'en')
        self.assertIn('# my comment', content)

    def test_multiline_comment(self):
        records = [TranslationModel.create('key', 'val', 'line1\nline2')]
        writer = PropertiesFileWriter()
        writer.append(records=records, code='en')
        content = _zip_properties(writer.http_response(), 'en')
        self.assertIn('# line1', content)
        self.assertIn('# line2', content)

    def test_special_chars_in_token_escaped(self):
        records = [TranslationModel.create('key=name', 'val')]
        writer = PropertiesFileWriter()
        writer.append(records=records, code='en')
        content = _zip_properties(writer.http_response(), 'en')
        self.assertIn(r'key\=name', content)

    def test_plural_emits_suffixed_lines(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        writer = PropertiesFileWriter()
        writer.append(records=records, code='en')
        content = _zip_properties(writer.http_response(), 'en')
        self.assertIn('item[one]=one item', content)
        self.assertIn('item[other]=many', content)

    def test_plural_comment_only_on_first_present_form(self):
        # Comment should appear exactly once, on the first form present in PLURAL_FORM_ORDER
        # ('one' here, since 'zero' is absent)
        records = [TranslationModel.create('item', '', comment='note', plural_forms={'one': 'one', 'other': 'many'})]
        writer = PropertiesFileWriter()
        writer.append(records=records, code='en')
        content = _zip_properties(writer.http_response(), 'en')
        self.assertEqual(content.count('# note'), 1)

    def test_zip_path_uses_language_code(self):
        writer = PropertiesFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='DE')
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            self.assertIn('/de.properties', zf.namelist())
