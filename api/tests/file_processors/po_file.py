import io
import zipfile

import polib
from django.test import TestCase

from api.file_processors.po_file import POFileReader, POFileWriter
from api.models.transport_models import TranslationModel


def _make_po_file(entries: list[polib.POEntry]) -> io.BytesIO:
    po = polib.POFile()
    for entry in entries:
        po.append(entry)
    content = getattr(po, '__unicode__')()
    return io.BytesIO(content.encode())


def _zip_po(response, code: str) -> bytes:
    path = f'{code.lower()}.po'
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return zf.read(path)


class POFileReaderTestCase(TestCase):

    def setUp(self):
        self.reader = POFileReader()

    def test_basic_entry(self):
        f = _make_po_file([polib.POEntry(msgid='greeting', msgstr='Hello')])
        result = self.reader.read(f)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')

    def test_entry_with_comment(self):
        f = _make_po_file([polib.POEntry(msgid='key', msgstr='val', comment='my note')])
        result = self.reader.read(f)
        self.assertIn('my note', result[0].comment)

    def test_plural_entry(self):
        entry = polib.POEntry(
            msgid='item',
            msgid_plural='item',
            msgstr_plural={0: 'one item', 1: 'many items'},
        )
        f = _make_po_file([entry])
        result = self.reader.read(f)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'item')
        self.assertFalse(result[0].translation)
        self.assertTrue(result[0].plural_forms)

    def test_multiple_entries(self):
        entries = [
            polib.POEntry(msgid='a', msgstr='alpha'),
            polib.POEntry(msgid='b', msgstr='beta'),
        ]
        result = self.reader.read(_make_po_file(entries))
        self.assertEqual(len(result), 2)


class POFileWriterTestCase(TestCase):

    def test_basic_entry_in_zip(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = POFileWriter()
        writer.append(records=records, code='en')
        raw = _zip_po(writer.http_response(), 'en')
        self.assertIn(b'msgid "greeting"', raw)
        self.assertIn(b'msgstr "Hello"', raw)

    def test_plural_entry_in_zip(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        writer = POFileWriter()
        writer.append(records=records, code='en')
        raw = _zip_po(writer.http_response(), 'en')
        self.assertIn(b'msgid_plural', raw)
        self.assertIn(b'msgstr[0]', raw)

    def test_comment_written(self):
        records = [TranslationModel.create('key', 'val', 'my note')]
        writer = POFileWriter()
        writer.append(records=records, code='en')
        raw = _zip_po(writer.http_response(), 'en')
        self.assertIn(b'my note', raw)

    def test_zip_path_uses_language_code(self):
        writer = POFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='FR')
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            self.assertIn('fr.po', zf.namelist())

    def test_http_response_content_disposition(self):
        writer = POFileWriter()
        writer.append(records=[], code='en')
        response = writer.http_response()
        self.assertIn('resources.zip', response['Content-Disposition'])
