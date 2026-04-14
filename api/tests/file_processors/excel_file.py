from django.test import TestCase

from api.file_processors.excel_file import ExcelFileWriter, ExcelSingleSheetFileWriter, FileConstants
from api.models.transport_models import TranslationModel


class ExcelFileWriterTestCase(TestCase):

    def test_http_response_returns_xlsx_content_type(self):
        writer = ExcelFileWriter()
        writer.append(records=[TranslationModel.create('key', 'val')], code='en')
        response = writer.http_response()
        self.assertIn('excel', response['Content-Type'])

    def test_http_response_non_empty(self):
        writer = ExcelFileWriter()
        writer.append(records=[TranslationModel.create('key', 'val')], code='en')
        response = writer.http_response()
        self.assertGreater(len(response.content), 0)

    def test_content_disposition(self):
        writer = ExcelFileWriter()
        writer.append(records=[], code='en')
        response = writer.http_response()
        self.assertIn('translations.xlsx', response['Content-Disposition'])

    def test_plural_forms_do_not_raise(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one', 'other': 'many'})]
        writer = ExcelFileWriter()
        writer.append(records=records, code='en')
        response = writer.http_response()
        self.assertGreater(len(response.content), 0)


class ExcelSingleSheetWriterTestCase(TestCase):

    def test_records_accumulated_across_languages(self):
        writer = ExcelSingleSheetFileWriter()
        writer.append(records=[TranslationModel.create('key', 'Hello')], code='en')
        writer.append(records=[TranslationModel.create('key', 'Hola')], code='es')
        self.assertIn('key', writer.records)
        self.assertEqual(writer.records['key']['en'], 'Hello')
        self.assertEqual(writer.records['key']['es'], 'Hola')

    def test_languages_list_populated(self):
        writer = ExcelSingleSheetFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='en')
        writer.append(records=[TranslationModel.create('k', 'w')], code='fr')
        self.assertEqual(writer.languages, ['en', 'fr'])

    def test_plural_forms_stored_with_suffixed_columns(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one', 'other': 'many'})]
        writer = ExcelSingleSheetFileWriter()
        writer.append(records=records, code='en')
        record = writer.records['item']
        self.assertEqual(record['en[one]'], 'one')
        self.assertEqual(record['en[other]'], 'many')

    def test_http_response_returns_xlsx_content_type(self):
        writer = ExcelSingleSheetFileWriter()
        writer.append(records=[TranslationModel.create('key', 'val')], code='en')
        response = writer.http_response()
        self.assertIn('excel', response['Content-Type'])

    def test_http_response_non_empty(self):
        writer = ExcelSingleSheetFileWriter()
        writer.append(records=[TranslationModel.create('key', 'val')], code='en')
        response = writer.http_response()
        self.assertGreater(len(response.content), 0)
