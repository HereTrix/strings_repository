import csv
import io
import zipfile

from django.test import TestCase

from api.file_processors.csv_file import CSVFileReader, CSVFileWriter, _KEY_COL, _TRANSLATION_COL, _TAGS_COL, _COMMENT_COL, _COMMENT_COL_ALT
from api.models.transport_models import TranslationModel


def _make_file(rows: list[dict], fieldnames: list[str] | None = None) -> io.BytesIO:
    """Build an in-memory CSV file from a list of row dicts."""
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else [_KEY_COL, _TRANSLATION_COL]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return io.BytesIO(buf.getvalue().encode('utf-8'))


def _zip_csv(response, code: str) -> list[dict]:
    """Extract and parse the CSV for a given language code from the ZIP response."""
    path = f'/{code.lower()}/strings.csv'
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        content = zf.read(path).decode('utf-8')
    return list(csv.DictReader(io.StringIO(content)))


class CSVFileReaderTestCase(TestCase):

    def setUp(self):
        self.reader = CSVFileReader()

    def test_basic_key_value(self):
        f = _make_file([{_KEY_COL: 'greeting', _TRANSLATION_COL: 'Hello'}])
        result = self.reader.read(f)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'greeting')
        self.assertEqual(result[0].translation, 'Hello')

    def test_multiple_rows(self):
        rows = [
            {_KEY_COL: 'a', _TRANSLATION_COL: 'alpha'},
            {_KEY_COL: 'b', _TRANSLATION_COL: 'beta'},
        ]
        result = self.reader.read(_make_file(rows))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].token, 'a')
        self.assertEqual(result[1].token, 'b')

    def test_empty_file(self):
        f = _make_file([], fieldnames=[_KEY_COL, _TRANSLATION_COL])
        result = self.reader.read(f)
        self.assertEqual(result, [])

    def test_row_with_blank_key_skipped(self):
        rows = [
            {_KEY_COL: '', _TRANSLATION_COL: 'orphan'},
            {_KEY_COL: 'real', _TRANSLATION_COL: 'value'},
        ]
        result = self.reader.read(_make_file(rows))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'real')

    def test_tags_parsed_from_comma_list(self):
        rows = [{_KEY_COL: 'k', _TRANSLATION_COL: 'v', _TAGS_COL: 'ui,onboarding'}]
        fieldnames = [_KEY_COL, _TRANSLATION_COL, _TAGS_COL]
        result = self.reader.read(_make_file(rows, fieldnames=fieldnames))
        self.assertEqual(result[0].tags, ['ui', 'onboarding'])

    def test_empty_tags_returns_none(self):
        rows = [{_KEY_COL: 'k', _TRANSLATION_COL: 'v', _TAGS_COL: ''}]
        fieldnames = [_KEY_COL, _TRANSLATION_COL, _TAGS_COL]
        result = self.reader.read(_make_file(rows, fieldnames=fieldnames))
        self.assertIsNone(result[0].tags)

    def test_comment_populated(self):
        rows = [{_KEY_COL: 'k', _TRANSLATION_COL: 'v', _COMMENT_COL: 'Do not translate brand name'}]
        fieldnames = [_KEY_COL, _TRANSLATION_COL, _COMMENT_COL]
        result = self.reader.read(_make_file(rows, fieldnames=fieldnames))
        self.assertEqual(result[0].comment, 'Do not translate brand name')

    def test_empty_comment_returns_none(self):
        rows = [{_KEY_COL: 'k', _TRANSLATION_COL: 'v', _COMMENT_COL: ''}]
        fieldnames = [_KEY_COL, _TRANSLATION_COL, _COMMENT_COL]
        result = self.reader.read(_make_file(rows, fieldnames=fieldnames))
        self.assertIsNone(result[0].comment)

    def test_singular_comment_column_accepted(self):
        rows = [{_KEY_COL: 'k', _TRANSLATION_COL: 'v', _COMMENT_COL_ALT: 'note'}]
        fieldnames = [_KEY_COL, _TRANSLATION_COL, _COMMENT_COL_ALT]
        result = self.reader.read(_make_file(rows, fieldnames=fieldnames))
        self.assertEqual(result[0].comment, 'note')

    def test_plural_forms_read_from_bracketed_columns(self):
        rows = [{_KEY_COL: 'items', _TRANSLATION_COL: '', '[one]': 'One item', '[other]': 'Many items'}]
        fieldnames = [_KEY_COL, _TRANSLATION_COL, '[one]', '[other]']
        result = self.reader.read(_make_file(rows, fieldnames=fieldnames))
        self.assertEqual(result[0].plural_forms.get('one'), 'One item')
        self.assertEqual(result[0].plural_forms.get('other'), 'Many items')

    def test_empty_plural_columns_not_included(self):
        rows = [{_KEY_COL: 'items', _TRANSLATION_COL: '', '[one]': 'One item', '[other]': ''}]
        fieldnames = [_KEY_COL, _TRANSLATION_COL, '[one]', '[other]']
        result = self.reader.read(_make_file(rows, fieldnames=fieldnames))
        self.assertIn('one', result[0].plural_forms)
        self.assertNotIn('other', result[0].plural_forms)

    def test_missing_plural_columns_ignored(self):
        rows = [{_KEY_COL: 'k', _TRANSLATION_COL: 'v'}]
        result = self.reader.read(_make_file(rows))
        self.assertEqual(result[0].plural_forms, {})

    def test_unicode_preserved(self):
        rows = [{_KEY_COL: 'greeting', _TRANSLATION_COL: '日本語'}]
        result = self.reader.read(_make_file(rows))
        self.assertEqual(result[0].translation, '日本語')

    def test_bom_stripped(self):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[_KEY_COL, _TRANSLATION_COL])
        writer.writeheader()
        writer.writerow({_KEY_COL: 'k', _TRANSLATION_COL: 'v'})
        f = io.BytesIO(('﻿' + buf.getvalue()).encode('utf-8'))
        result = self.reader.read(f)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, 'k')

    def test_seek_resets_on_repeated_read(self):
        f = _make_file([{_KEY_COL: 'k', _TRANSLATION_COL: 'v'}])
        self.reader.read(f)
        result = self.reader.read(f)
        self.assertEqual(len(result), 1)

    def test_needs_language_code(self):
        self.assertTrue(self.reader.needs_language_code())


class CSVFileWriterTestCase(TestCase):

    def test_zip_content_type(self):
        writer = CSVFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='en')
        response = writer.http_response()
        self.assertIn('zip', response['Content-Type'])

    def test_content_disposition(self):
        writer = CSVFileWriter()
        writer.append(records=[], code='en')
        response = writer.http_response()
        self.assertIn('resources.zip', response['Content-Disposition'])

    def test_zip_path_uses_lowercase_language_code(self):
        writer = CSVFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='DE')
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            self.assertIn('/de/strings.csv', zf.namelist())

    def test_basic_record_round_trips(self):
        records = [TranslationModel.create('greeting', 'Hello')]
        writer = CSVFileWriter()
        writer.append(records=records, code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        self.assertEqual(rows[0][_KEY_COL], 'greeting')
        self.assertEqual(rows[0][_TRANSLATION_COL], 'Hello')

    def test_multiple_records(self):
        records = [
            TranslationModel.create('a', 'alpha'),
            TranslationModel.create('b', 'beta'),
        ]
        writer = CSVFileWriter()
        writer.append(records=records, code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][_KEY_COL], 'a')
        self.assertEqual(rows[1][_KEY_COL], 'b')

    def test_tags_joined_with_comma(self):
        records = [TranslationModel.create('k', 'v', tags=['ui', 'onboarding'])]
        writer = CSVFileWriter()
        writer.append(records=records, code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        self.assertEqual(rows[0][_TAGS_COL], 'ui,onboarding')

    def test_comment_written(self):
        records = [TranslationModel.create('k', 'v', comment='Do not translate brand name')]
        writer = CSVFileWriter()
        writer.append(records=records, code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        self.assertEqual(rows[0][_COMMENT_COL], 'Do not translate brand name')

    def test_plural_forms_written_to_bracketed_columns(self):
        records = [TranslationModel.create('items', '', plural_forms={'one': 'One item', 'other': 'Many items'})]
        writer = CSVFileWriter()
        writer.append(records=records, code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        self.assertEqual(rows[0]['[one]'], 'One item')
        self.assertEqual(rows[0]['[other]'], 'Many items')

    def test_missing_plural_forms_written_as_empty(self):
        records = [TranslationModel.create('items', '', plural_forms={'one': 'One item'})]
        writer = CSVFileWriter()
        writer.append(records=records, code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        self.assertEqual(rows[0]['[other]'], '')

    def test_all_six_plural_columns_always_present(self):
        writer = CSVFileWriter()
        writer.append(records=[TranslationModel.create('k', 'v')], code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        for form in ('zero', 'one', 'two', 'few', 'many', 'other'):
            self.assertIn(f'[{form}]', rows[0])

    def test_multiple_languages_produce_separate_files(self):
        writer = CSVFileWriter()
        writer.append(records=[TranslationModel.create('k', 'Hello')], code='en')
        writer.append(records=[TranslationModel.create('k', 'Hola')], code='es')
        response = writer.http_response()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            names = zf.namelist()
        self.assertIn('/en/strings.csv', names)
        self.assertIn('/es/strings.csv', names)

    def test_unicode_preserved(self):
        records = [TranslationModel.create('greeting', '日本語')]
        writer = CSVFileWriter()
        writer.append(records=records, code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        self.assertEqual(rows[0][_TRANSLATION_COL], '日本語')

    def test_empty_records_produces_header_only(self):
        writer = CSVFileWriter()
        writer.append(records=[], code='en')
        rows = _zip_csv(writer.http_response(), 'en')
        self.assertEqual(rows, [])


class CSVRoundTripTestCase(TestCase):
    """Write then re-read — verify lossless round-trip for all field types."""

    def _round_trip(self, records, code='en'):
        writer = CSVFileWriter()
        writer.append(records=records, code=code)
        path = f'/{code.lower()}/strings.csv'
        with zipfile.ZipFile(io.BytesIO(writer.http_response().content)) as zf:
            content = zf.read(path)
        return CSVFileReader().read(io.BytesIO(content))

    def test_singular_string(self):
        original = TranslationModel.create('btn_ok', 'OK')
        result = self._round_trip([original])
        self.assertEqual(result[0].token, 'btn_ok')
        self.assertEqual(result[0].translation, 'OK')

    def test_plural_forms(self):
        original = TranslationModel.create('items', '', plural_forms={'one': 'One item', 'other': 'Many items'})
        result = self._round_trip([original])
        self.assertEqual(result[0].plural_forms.get('one'), 'One item')
        self.assertEqual(result[0].plural_forms.get('other'), 'Many items')
        self.assertNotIn('zero', result[0].plural_forms)

    def test_tags_and_comment(self):
        original = TranslationModel.create('k', 'v', tags=['ui', 'nav'], comment='Context note')
        result = self._round_trip([original])
        self.assertEqual(result[0].tags, ['ui', 'nav'])
        self.assertEqual(result[0].comment, 'Context note')

    def test_unicode(self):
        original = TranslationModel.create('msg', '日本語テスト')
        result = self._round_trip([original])
        self.assertEqual(result[0].translation, '日本語テスト')

    def test_translation_with_comma(self):
        original = TranslationModel.create('msg', 'Hello, world')
        result = self._round_trip([original])
        self.assertEqual(result[0].translation, 'Hello, world')

    def test_translation_with_newline(self):
        original = TranslationModel.create('msg', 'Line one\nLine two')
        result = self._round_trip([original])
        self.assertEqual(result[0].translation, 'Line one\nLine two')

    def test_translation_with_quotes(self):
        original = TranslationModel.create('msg', 'She said "hello"')
        result = self._round_trip([original])
        self.assertEqual(result[0].translation, 'She said "hello"')
