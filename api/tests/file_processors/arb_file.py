import io
import json
import zipfile

from django.test import TestCase

from api.file_processors.arb_file import ARBFileReader, ARBFileWriter
from api.models.transport_models import TranslationModel


def _make_file(data: dict) -> io.BytesIO:
    return io.BytesIO(json.dumps(data).encode())


def _write_bytes(writer) -> bytes:
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _zip_arb(data: bytes, code: str) -> dict:
    path = f'/intl_{code.lower()}.arb'
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return json.loads(zf.read(path).decode())


class ARBFileReaderTestCase(TestCase):

    def setUp(self):
        self.reader = ARBFileReader()

    def test_basic_key_value(self):
        result = self.reader.read(_make_file({'greeting': 'Hello'}))
        self.assertEqual(result, [TranslationModel.create('greeting', 'Hello')])

    def test_skips_locale_metadata(self):
        data = {'@@locale': 'en', 'greeting': 'Hello'}
        result = self.reader.read(_make_file(data))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'greeting')

    def test_skips_key_metadata(self):
        data = {'greeting': 'Hello', '@greeting': {'description': 'A greeting'}}
        result = self.reader.read(_make_file(data))
        self.assertEqual(len(result), 1)

    def test_description_becomes_comment(self):
        data = {'greeting': 'Hello', '@greeting': {'description': 'A greeting'}}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].comment, 'A greeting')

    def test_plural_icu_format_parsed(self):
        data = {'itemCount': '{count, plural, one {One item} other {{count} items}}'}
        result = self.reader.read(_make_file(data))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'itemCount')
        self.assertEqual(result[0].plural_forms.get('one'), 'One item')
        self.assertEqual(result[0].plural_forms.get('other'), '{count} items')

    def test_plural_translation_is_empty_string(self):
        data = {'itemCount': '{count, plural, one {One item} other {Many items}}'}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].translation, '')

    def test_non_plural_has_no_plural_forms(self):
        result = self.reader.read(_make_file({'key': 'value'}))
        self.assertEqual(result[0].plural_forms, {})

    def test_empty_file(self):
        result = self.reader.read(_make_file({}))
        self.assertEqual(result, [])

    def test_unicode_preserved(self):
        result = self.reader.read(_make_file({'key': '日本語'}))
        self.assertEqual(result[0].translation, '日本語')

    def test_multiple_entries_order_preserved(self):
        data = {'z': 'last', 'a': 'first'}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].token, 'z')
        self.assertEqual(result[1].token, 'a')

    def test_no_comment_when_no_metadata(self):
        result = self.reader.read(_make_file({'key': 'value'}))
        self.assertIsNone(result[0].comment)

    def test_plural_with_all_forms(self):
        data = {'n': '{count, plural, zero {none} one {one} other {many}}'}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].plural_forms.get('zero'), 'none')
        self.assertEqual(result[0].plural_forms.get('one'), 'one')
        self.assertEqual(result[0].plural_forms.get('other'), 'many')


class ARBFileWriterTestCase(TestCase):

    def test_basic_entry_in_zip(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = ARBFileWriter()
        writer.append(records=records, code='en')
        data = _zip_arb(_write_bytes(writer), 'en')
        self.assertEqual(data['greeting'], 'Hello')

    def test_locale_field_written(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = ARBFileWriter()
        writer.append(records=records, code='en')
        data = _zip_arb(_write_bytes(writer), 'en')
        self.assertEqual(data['@@locale'], 'en')

    def test_locale_lowercased(self):
        records = [TranslationModel.create('k', 'v')]
        writer = ARBFileWriter()
        writer.append(records=records, code='FR')
        data = _zip_arb(_write_bytes(writer), 'fr')
        self.assertEqual(data['@@locale'], 'fr')

    def test_zip_path_uses_language_code(self):
        writer = ARBFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='FR')
        with zipfile.ZipFile(io.BytesIO(_write_bytes(writer))) as zf:
            self.assertIn('/intl_fr.arb', zf.namelist())

    def test_plural_forms_written_as_icu(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'One item', 'other': '{count} items'})]
        writer = ARBFileWriter()
        writer.append(records=records, code='en')
        data = _zip_arb(_write_bytes(writer), 'en')
        value = data['item']
        self.assertIn('{count, plural,', value)
        self.assertIn('one {One item}', value)
        self.assertIn('other {{count} items}', value)

    def test_comment_written_as_description(self):
        records = [TranslationModel.create('greeting', 'Hello', comment='A greeting')]
        writer = ARBFileWriter()
        writer.append(records=records, code='en')
        data = _zip_arb(_write_bytes(writer), 'en')
        self.assertEqual(data['@greeting']['description'], 'A greeting')

    def test_no_metadata_key_when_no_comment(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = ARBFileWriter()
        writer.append(records=records, code='en')
        data = _zip_arb(_write_bytes(writer), 'en')
        self.assertNotIn('@greeting', data)

    def test_unicode_preserved(self):
        records = [TranslationModel.create('key', '日本語')]
        writer = ARBFileWriter()
        writer.append(records=records, code='en')
        data = _zip_arb(_write_bytes(writer), 'en')
        self.assertEqual(data['key'], '日本語')

    def test_multiple_languages_in_zip(self):
        writer = ARBFileWriter()
        writer.append(records=[TranslationModel.create('k', 'Hello')], code='en')
        writer.append(records=[TranslationModel.create('k', 'Hola')], code='es')
        with zipfile.ZipFile(io.BytesIO(_write_bytes(writer))) as zf:
            names = zf.namelist()
        self.assertIn('/intl_en.arb', names)
        self.assertIn('/intl_es.arb', names)

    def test_filename_attribute(self):
        writer = ARBFileWriter()
        self.assertIn('resources.zip', writer.filename)

    def test_content_type_is_zip(self):
        writer = ARBFileWriter()
        self.assertEqual(writer.content_type, 'application/zip')
