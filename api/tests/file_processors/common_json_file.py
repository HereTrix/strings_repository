import io
import json

from django.test import TestCase

from api.file_processors.common_json_file import CommonJSONFileReader
from api.file_processors.json_dict_file import JsonDictFileReader
from api.file_processors.json_file import JsonFileReader


def _make_file(data) -> io.BytesIO:
    return io.BytesIO(json.dumps(data).encode())


class CommonJSONFileReaderTestCase(TestCase):

    def setUp(self):
        self.reader = CommonJSONFileReader()

    def test_flat_json_delegates_to_json_file_reader(self):
        f = _make_file({'key': 'value'})
        reader = self.reader._make_reader(f)
        self.assertIsInstance(reader, JsonFileReader)

    def test_dict_json_delegates_to_json_dict_reader(self):
        f = _make_file({'key': {'value': 'hello'}})
        reader = self.reader._make_reader(f)
        self.assertIsInstance(reader, JsonDictFileReader)

    def test_invalid_json_falls_back_to_json_file_reader(self):
        f = io.BytesIO(b'{not valid json')
        reader = self.reader._make_reader(f)
        self.assertIsInstance(reader, JsonFileReader)

    def test_needs_language_code_returns_true(self):
        self.assertTrue(self.reader.needs_language_code())

    def test_read_flat_returns_translations(self):
        f = _make_file({'greeting': 'Hello'})
        result = self.reader.read(f)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')

    def test_read_dict_returns_translations(self):
        f = _make_file({'greeting': {'value': 'Hello'}})
        result = self.reader.read(f)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')
