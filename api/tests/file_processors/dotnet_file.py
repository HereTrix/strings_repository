import io
import zipfile
from xml.dom import minidom

from django.test import TestCase

from api.file_processors.dotnet_file import DotNetFileReader, DotNetFileWriter
from api.models.transport_models import TranslationModel


def _make_file(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode())


def _resx(data_entries: str) -> str:
    return f'<?xml version="1.0" encoding="utf-8"?><root>{data_entries}</root>'


def _data(name: str, value: str) -> str:
    return f'<data name="{name}" xml:space="preserve"><value>{value}</value></data>'


def _zip_resx(response, code: str) -> str:
    path = f'/WebResources.{code.lower()}.resx'
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return zf.read(path).decode()


class DotNetReaderTestCase(TestCase):

    def setUp(self):
        self.reader = DotNetFileReader()

    def test_basic_entry(self):
        xml = _resx(_data('greeting', 'Hello'))
        result = self.reader.read(_make_file(xml))
        self.assertEqual(result, [TranslationModel.create('greeting', 'Hello')])

    def test_multiple_entries_order_preserved(self):
        xml = _resx(_data('z', 'last') + _data('a', 'first'))
        result = self.reader.read(_make_file(xml))
        self.assertEqual(result[0].token, 'z')
        self.assertEqual(result[1].token, 'a')

    def test_plural_keys_grouped(self):
        xml = _resx(_data('item[one]', 'one item') + _data('item[other]', 'many'))
        result = self.reader.read(_make_file(xml))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'item')
        self.assertEqual(result[0].plural_forms.get('one'), 'one item')
        self.assertEqual(result[0].plural_forms.get('other'), 'many')

    def test_empty_document(self):
        xml = _resx('')
        result = self.reader.read(_make_file(xml))
        self.assertEqual(result, [])


class DotNetWriterTestCase(TestCase):

    def test_basic_entry_in_zip(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = DotNetFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_resx(writer.http_response(), 'en')
        self.assertIn('name="greeting"', xml)
        self.assertIn('<value>Hello</value>', xml)

    def test_xml_special_chars_escaped(self):
        records = [TranslationModel.create('key', '<b>bold</b> & more')]
        writer = DotNetFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_resx(writer.http_response(), 'en')
        self.assertIn('&lt;b&gt;', xml)
        self.assertIn('&amp;', xml)

    def test_comment_included(self):
        records = [TranslationModel.create('key', 'val', 'my comment')]
        writer = DotNetFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_resx(writer.http_response(), 'en')
        self.assertIn('my comment', xml)

    def test_plural_emits_suffixed_keys(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        writer = DotNetFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_resx(writer.http_response(), 'en')
        self.assertIn('name="item[one]"', xml)
        self.assertIn('name="item[other]"', xml)

    def test_plural_comment_on_first_present_form(self):
        # Comment should appear once, on the first form present in PLURAL_FORM_ORDER
        # ('one' here, since 'zero' is absent)
        records = [TranslationModel.create('item', '', comment='note', plural_forms={'one': 'one', 'other': 'many'})]
        writer = DotNetFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_resx(writer.http_response(), 'en')
        self.assertEqual(xml.count('note'), 1)

    def test_plural_forms_emitted_in_canonical_order(self):
        # Forms must appear in PLURAL_FORM_ORDER regardless of insertion order in dict
        records = [TranslationModel.create('item', '', plural_forms={'other': 'many', 'one': 'one'})]
        writer = DotNetFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_resx(writer.http_response(), 'en')
        one_pos = xml.index('item[one]')
        other_pos = xml.index('item[other]')
        self.assertLess(one_pos, other_pos)

    def test_zip_path_uses_language_code(self):
        writer = DotNetFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='DE')
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            self.assertIn('/WebResources.de.resx', zf.namelist())

    def test_http_response_content_disposition(self):
        writer = DotNetFileWriter()
        writer.append(records=[], code='en')
        response = writer.http_response()
        self.assertIn('resources.zip', response['Content-Disposition'])
