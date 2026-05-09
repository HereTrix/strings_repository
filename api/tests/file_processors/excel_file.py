# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import io

from django.test import TestCase

from api.file_processors.excel_file import ExcelFileWriter, ExcelSingleSheetFileWriter, FileConstants
from api.models.transport_models import TranslationModel


def _write_bytes(writer) -> bytes:
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class ExcelFileWriterTestCase(TestCase):

    def test_content_type_attribute(self):
        writer = ExcelFileWriter()
        self.assertIn('excel', writer.content_type)

    def test_write_non_empty(self):
        writer = ExcelFileWriter()
        writer.append(records=[TranslationModel.create('key', 'val')], code='en')
        self.assertGreater(len(_write_bytes(writer)), 0)

    def test_filename_attribute(self):
        writer = ExcelFileWriter()
        self.assertIn('translations.xlsx', writer.filename)

    def test_plural_forms_do_not_raise(self):
        records = [TranslationModel.create('item', '', plural_forms={'one': 'one', 'other': 'many'})]
        writer = ExcelFileWriter()
        writer.append(records=records, code='en')
        self.assertGreater(len(_write_bytes(writer)), 0)


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

    def test_content_type_attribute(self):
        writer = ExcelSingleSheetFileWriter()
        self.assertIn('excel', writer.content_type)

    def test_write_non_empty(self):
        writer = ExcelSingleSheetFileWriter()
        writer.append(records=[TranslationModel.create('key', 'val')], code='en')
        self.assertGreater(len(_write_bytes(writer)), 0)
