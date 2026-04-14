import io
import zipfile

import polib
from django.test import TestCase

from api.file_processors.mo_file import MOFileReader, MOFileWriter
from api.models.transport_models import TranslationModel


def _records_to_mo_bytes(records) -> bytes:
    """Write records via MOFileWriter, extract the .mo bytes from the zip."""
    writer = MOFileWriter()
    writer.append(records=records, code='en')
    response = writer.http_response()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return zf.read('en.mo')


class MOFileWriterTestCase(TestCase):

    def test_basic_entry_produces_zip(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = MOFileWriter()
        writer.append(records=records, code='en')
        response = writer.http_response()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            self.assertIn('en.mo', zf.namelist())

    def test_zip_path_uses_language_code(self):
        writer = MOFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='FR')
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            self.assertIn('fr.mo', zf.namelist())

    def test_plural_entry_in_zip(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        writer = MOFileWriter()
        writer.append(records=records, code='en')
        response = writer.http_response()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            data = zf.read('en.mo')
        self.assertTrue(len(data) > 0)

    def test_http_response_content_disposition(self):
        writer = MOFileWriter()
        writer.append(records=[], code='en')
        response = writer.http_response()
        self.assertIn('resources.zip', response['Content-Disposition'])


class MOFileReaderTestCase(TestCase):

    def setUp(self):
        self.reader = MOFileReader()

    def test_round_trip_basic(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        mo_bytes = _records_to_mo_bytes(records)
        result = self.reader.read(io.BytesIO(mo_bytes))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')

    def test_round_trip_plural(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        mo_bytes = _records_to_mo_bytes(records)
        result = self.reader.read(io.BytesIO(mo_bytes))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'item')
        self.assertTrue(result[0].plural_forms)

    def test_round_trip_multiple_entries(self):
        records = [
            TranslationModel.create('a', 'alpha'),
            TranslationModel.create('b', 'beta'),
        ]
        mo_bytes = _records_to_mo_bytes(records)
        result = self.reader.read(io.BytesIO(mo_bytes))
        self.assertEqual(len(result), 2)
