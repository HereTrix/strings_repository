import io
import json
import zipfile

from django.test import TestCase

from api.file_processors.json_file import JsonFileReader, JsonFileWriter
from api.models.transport_models import TranslationModel


def _make_file(data: dict) -> io.BytesIO:
    return io.BytesIO(json.dumps(data).encode())


def _zip_json(response, code: str) -> dict:
    path = f'/{code.lower()}.json'
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return json.loads(zf.read(path).decode())


class JsonFileReaderTestCase(TestCase):

    def setUp(self):
        self.reader = JsonFileReader()

    def test_basic_key_value(self):
        result = self.reader.read(_make_file({'greeting': 'Hello'}))
        self.assertEqual(result, [TranslationModel.create('greeting', 'Hello')])

    def test_multiple_entries(self):
        data = {'a': 'alpha', 'b': 'beta'}
        result = self.reader.read(_make_file(data))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].token, 'a')
        self.assertEqual(result[1].token, 'b')

    def test_plural_keys_grouped(self):
        data = {'item_one': 'one item', 'item_other': 'many items'}
        result = self.reader.read(_make_file(data))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'item')
        self.assertEqual(result[0].plural_forms.get('one'), 'one item')
        self.assertEqual(result[0].plural_forms.get('other'), 'many items')

    def test_document_order_preserved(self):
        data = {'z': 'last', 'a': 'first'}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].token, 'z')
        self.assertEqual(result[1].token, 'a')

    def test_empty_object(self):
        result = self.reader.read(_make_file({}))
        self.assertEqual(result, [])

    def test_unicode_preserved(self):
        result = self.reader.read(_make_file({'key': '日本語'}))
        self.assertEqual(result[0].translation, '日本語')

    def test_non_string_value_passed_through(self):
        # Integer and boolean values from json.load are not coerced — translation
        # will be the raw Python value. Document this as known behaviour.
        result = self.reader.read(_make_file({'count': 42, 'flag': True}))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].token, 'count')
        self.assertEqual(result[0].translation, 42)
        self.assertEqual(result[1].token, 'flag')
        self.assertEqual(result[1].translation, True)


class JsonFileWriterTestCase(TestCase):

    def test_basic_entry_in_zip(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = JsonFileWriter()
        writer.append(records=records, code='en')
        data = _zip_json(writer.http_response(), 'en')
        self.assertEqual(data['greeting'], 'Hello')

    def test_zip_path_uses_language_code(self):
        writer = JsonFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='FR')
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            self.assertIn('/fr.json', zf.namelist())

    def test_plural_forms_expanded_as_suffixed_keys(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        writer = JsonFileWriter()
        writer.append(records=records, code='en')
        data = _zip_json(writer.http_response(), 'en')
        self.assertEqual(data['item_one'], 'one item')
        self.assertEqual(data['item_other'], 'many')

    def test_unicode_preserved(self):
        records = [TranslationModel.create('key', '日本語')]
        writer = JsonFileWriter()
        writer.append(records=records, code='en')
        data = _zip_json(writer.http_response(), 'en')
        self.assertEqual(data['key'], '日本語')

    def test_http_response_content_disposition(self):
        writer = JsonFileWriter()
        writer.append(records=[], code='en')
        response = writer.http_response()
        self.assertIn('resources.zip', response['Content-Disposition'])
