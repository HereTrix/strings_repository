import io
import json
import zipfile

from django.test import TestCase

from api.file_processors.xcstrings_file import XCStringsFileReader, XCStringsFileWriter
from api.models.transport_models import TranslationModel


def _make_file(data: dict) -> io.BytesIO:
    return io.BytesIO(json.dumps(data).encode())


def _xcstrings_payload(strings: dict) -> dict:
    return {'version': '1.1', 'sourceLanguage': 'en', 'strings': strings}


class XCStringsReaderTestCase(TestCase):

    def setUp(self):
        self.reader = XCStringsFileReader()

    def test_basic_string_unit(self):
        payload = _xcstrings_payload({
            'greeting': {
                'localizations': {
                    'en': {'stringUnit': {'state': 'translated', 'value': 'Hello'}}
                }
            }
        })
        result = self.reader.read(_make_file(payload))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')
        self.assertEqual(result[0].code, 'en')

    def test_comment_extracted(self):
        payload = _xcstrings_payload({
            'key': {
                'comment': 'my note',
                'localizations': {
                    'en': {'stringUnit': {'state': 'translated', 'value': 'val'}}
                }
            }
        })
        result = self.reader.read(_make_file(payload))
        self.assertEqual(result[0].comment, 'my note')

    def test_plural_variations(self):
        payload = _xcstrings_payload({
            'item': {
                'localizations': {
                    'en': {
                        'variations': {
                            'plural': {
                                'one': {'stringUnit': {'state': 'translated', 'value': 'one item'}},
                                'other': {'stringUnit': {'state': 'translated', 'value': 'many'}},
                            }
                        }
                    }
                }
            }
        })
        result = self.reader.read(_make_file(payload))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'item')
        self.assertEqual(result[0].plural_forms.get('one'), 'one item')
        self.assertEqual(result[0].plural_forms.get('other'), 'many')

    def test_entry_without_localizations(self):
        payload = _xcstrings_payload({'bare_key': {}})
        result = self.reader.read(_make_file(payload))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'bare_key')
        self.assertEqual(result[0].translation, '')

    def test_needs_language_code_returns_false(self):
        self.assertFalse(self.reader.needs_language_code())

    def test_empty_strings(self):
        payload = _xcstrings_payload({})
        result = self.reader.read(_make_file(payload))
        self.assertEqual(result, [])


class XCStringsWriterTestCase(TestCase):

    def _get_output(self, writer) -> dict:
        response = writer.http_response()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            return json.loads(zf.read('Localizable.xcstrings').decode())

    def test_basic_translation(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = XCStringsFileWriter()
        writer.append(records=records, code='en')
        data = self._get_output(writer)
        unit = data['strings']['greeting']['localizations']['en']['stringUnit']
        self.assertEqual(unit['value'], 'Hello')
        self.assertEqual(unit['state'], 'translated')

    def test_comment_stored(self):
        records = [TranslationModel.create('key', 'val', 'my note')]
        writer = XCStringsFileWriter()
        writer.append(records=records, code='en')
        data = self._get_output(writer)
        self.assertEqual(data['strings']['key']['comment'], 'my note')

    def test_plural_forms_written_as_variations(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        writer = XCStringsFileWriter()
        writer.append(records=records, code='en')
        data = self._get_output(writer)
        plural = data['strings']['item']['localizations']['en']['variations']['plural']
        self.assertEqual(plural['one']['stringUnit']['value'], 'one item')
        self.assertEqual(plural['other']['stringUnit']['value'], 'many')

    def test_multiple_languages_accumulated(self):
        writer = XCStringsFileWriter()
        writer.append(records=[TranslationModel.create('key', 'Hello')], code='en')
        writer.append(records=[TranslationModel.create('key', 'Hola')], code='es')
        data = self._get_output(writer)
        locs = data['strings']['key']['localizations']
        self.assertIn('en', locs)
        self.assertIn('es', locs)

    def test_empty_translation_not_written(self):
        records = [TranslationModel.create('key', '')]
        writer = XCStringsFileWriter()
        writer.append(records=records, code='en')
        data = self._get_output(writer)
        self.assertNotIn('en', data['strings']['key'].get('localizations', {}))

    def test_duplicate_token_in_same_append_overwrites(self):
        # Two records with the same token in one append call — last one wins
        records = [
            TranslationModel.create('key', 'first'),
            TranslationModel.create('key', 'second'),
        ]
        writer = XCStringsFileWriter()
        writer.append(records=records, code='en')
        data = self._get_output(writer)
        unit = data['strings']['key']['localizations']['en']['stringUnit']
        self.assertEqual(unit['value'], 'second')
