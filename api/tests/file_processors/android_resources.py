import io
import zipfile
from xml.dom import minidom

from django.test import TestCase

from api.file_processors.android_resources import AndroidResourceFileReader, AndroidResourceFileWriter
from api.models.transport_models import TranslationModel


def _make_file(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode())


def _zip_xml(response, code: str) -> str:
    path = f'/values-{code.lower()}/strings.xml'
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return zf.read(path).decode()


class AndroidResourceReaderTestCase(TestCase):

    def setUp(self):
        self.reader = AndroidResourceFileReader()

    def test_basic_string(self):
        xml = '<resources><string name="key">value</string></resources>'
        result = self.reader.read(_make_file(xml))
        self.assertEqual(result, [TranslationModel.create('key', 'value')])

    def test_cdata_string(self):
        xml = '<resources><string name="key"><![CDATA[val<b>ue</b>]]></string></resources>'
        result = self.reader.read(_make_file(xml))
        self.assertEqual(result[0].token, 'key')
        self.assertIn('val', result[0].translation)

    def test_plural_element(self):
        xml = (
            '<resources>'
            '<plurals name="item">'
            '<item quantity="one">one item</item>'
            '<item quantity="other">many items</item>'
            '</plurals>'
            '</resources>'
        )
        result = self.reader.read(_make_file(xml))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'item')
        self.assertEqual(result[0].plural_forms.get('one'), 'one item')
        self.assertEqual(result[0].plural_forms.get('other'), 'many items')

    def test_empty_string_node(self):
        xml = '<resources><string name="empty"></string></resources>'
        result = self.reader.read(_make_file(xml))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'empty')
        self.assertEqual(result[0].translation, '')

    def test_mixed_strings_and_plurals(self):
        xml = (
            '<resources>'
            '<string name="greeting">Hello</string>'
            '<plurals name="item">'
            '<item quantity="one">one</item>'
            '<item quantity="other">many</item>'
            '</plurals>'
            '</resources>'
        )
        result = self.reader.read(_make_file(xml))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[1].token, 'item')


class AndroidResourceWriterTestCase(TestCase):

    def test_basic_string_in_zip(self):
        records = [TranslationModel.create('key', 'value')]
        writer = AndroidResourceFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_xml(writer.http_response(), 'en')
        dom = minidom.parseString(xml)
        nodes = dom.getElementsByTagName('string')
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].getAttribute('name'), 'key')

    def test_zip_path_uses_language_code(self):
        writer = AndroidResourceFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='DE')
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            self.assertIn('/values-de/strings.xml', zf.namelist())

    def test_html_entity_triggers_cdata(self):
        records = [TranslationModel.create('key', 'hello &amp; world')]
        writer = AndroidResourceFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_xml(writer.http_response(), 'en')
        self.assertIn('CDATA', xml)

    def test_comment_added_as_xml_comment(self):
        records = [TranslationModel.create('key', 'val', 'my comment')]
        writer = AndroidResourceFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_xml(writer.http_response(), 'en')
        self.assertIn('my comment', xml)

    def test_plural_entry(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one item', 'other': 'many'})]
        writer = AndroidResourceFileWriter()
        writer.append(records=records, code='en')
        xml = _zip_xml(writer.http_response(), 'en')
        dom = minidom.parseString(xml)
        plurals = dom.getElementsByTagName('plurals')
        self.assertEqual(len(plurals), 1)
        self.assertEqual(plurals[0].getAttribute('name'), 'item')
        items = plurals[0].getElementsByTagName('item')
        quantities = {item.getAttribute('quantity') for item in items}
        self.assertIn('one', quantities)
        self.assertIn('other', quantities)

    def test_http_response_content_disposition(self):
        writer = AndroidResourceFileWriter()
        writer.append(records=[], code='en')
        response = writer.http_response()
        self.assertIn('resources.zip', response['Content-Disposition'])
