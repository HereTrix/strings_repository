import io
import json
import zipfile

from django.test import TestCase

from api.file_processors.json_dict_file import JsonDictFileReader, JsonDictFileWriter
from api.models.transport_models import TranslationModel


def _make_file(data: dict) -> io.BytesIO:
    return io.BytesIO(json.dumps(data).encode())


def _zip_json(response, code: str) -> dict:
    path = f'/{code.lower()}.json'
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return json.loads(zf.read(path).decode())


class JsonDictReaderTestCase(TestCase):

    def setUp(self):
        self.reader = JsonDictFileReader()

    def test_basic_entry(self):
        data = {'greeting': {'value': 'Hello'}}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')

    def test_comment_and_tags(self):
        data = {'key': {'value': 'val', 'comment': 'note', 'tags': ['t1', 't2']}}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].comment, 'note')
        self.assertEqual(result[0].tags, ['t1', 't2'])

    def test_plural_forms(self):
        data = {'item': {'plural': {'one': 'one item', 'other': 'many'}}}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].token, 'item')
        self.assertEqual(result[0].plural_forms.get('one'), 'one item')
        self.assertEqual(result[0].plural_forms.get('other'), 'many')

    def test_non_dict_entry_skipped(self):
        data = {'bad': 'just a string', 'good': {'value': 'ok'}}
        result = self.reader.read(_make_file(data))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'good')

    def test_missing_optional_fields(self):
        data = {'key': {}}
        result = self.reader.read(_make_file(data))
        self.assertEqual(result[0].translation, '')
        self.assertIsNone(result[0].comment)

    def test_empty_object(self):
        result = self.reader.read(_make_file({}))
        self.assertEqual(result, [])


class JsonDictWriterTestCase(TestCase):

    def test_basic_entry_in_zip(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = JsonDictFileWriter()
        writer.append(records=records, code='en')
        data = _zip_json(writer.http_response(), 'en')
        self.assertEqual(data['greeting']['value'], 'Hello')

    def test_comment_and_tags_serialized(self):
        records = [TranslationModel.create('key', 'val', comment='note', tags=['t1'])]
        writer = JsonDictFileWriter()
        writer.append(records=records, code='en')
        data = _zip_json(writer.http_response(), 'en')
        self.assertEqual(data['key']['comment'], 'note')
        self.assertEqual(data['key']['tags'], ['t1'])

    def test_plural_forms_serialized(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one', 'other': 'many'})]
        writer = JsonDictFileWriter()
        writer.append(records=records, code='en')
        data = _zip_json(writer.http_response(), 'en')
        self.assertEqual(data['item']['plural']['one'], 'one')
        self.assertEqual(data['item']['plural']['other'], 'many')

    def test_empty_translation_omits_value_key(self):
        records = [TranslationModel.create('key', '')]
        writer = JsonDictFileWriter()
        writer.append(records=records, code='en')
        data = _zip_json(writer.http_response(), 'en')
        self.assertNotIn('value', data['key'])

    def test_zip_path_uses_language_code(self):
        writer = JsonDictFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='DE')
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            self.assertIn('/de.json', zf.namelist())
