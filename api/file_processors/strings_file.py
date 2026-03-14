import enum
import zipfile

from django.http import HttpResponse
from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel

PLURAL_FORM_ORDER = ['zero', 'one', 'two', 'few', 'many', 'other']


def _split_plural_key(token):
    """Return (base_token, form) if token ends with a known _form suffix, else (token, None)."""
    for form in PLURAL_FORM_ORDER:
        if token.endswith(f'_{form}'):
            return token[:-len(f'_{form}')], form
    return token, None


class AppleStringsFileReader(TranslationFileReader):

    class State(enum.Enum):
        scan = 0
        token = 1
        delimiter = 2
        value = 3
        single_line_comment = 4
        multi_line_comment = 5

    def read(self, file):
        file.seek(0)
        content = file.read().decode()
        return self.read_string(content=content)

    def read_string(self, content):
        state = AppleStringsFileReader.State.scan
        prev_symbol = None
        is_completed = False
        raw = []
        record = TranslationModel.create('', '')
        comment = None

        for char in content:
            match state:
                # Scan is emitted when
                case AppleStringsFileReader.State.scan:
                    if is_completed:
                        record.comment = comment
                        raw.append(record)
                        record = TranslationModel.create('', '')
                        # All comments before key = value belongs to this pair
                        comment = None
                        is_completed = False
                        prev_symbol = None
                    if prev_symbol is None:
                        match char:
                            case '"':
                                state = AppleStringsFileReader.State.token
                                prev_symbol = None
                            case '/':
                                prev_symbol = char
                    else:
                        if char == '*':
                            state = AppleStringsFileReader.State.multi_line_comment
                            prev_symbol = None
                        elif char == '/':
                            state = AppleStringsFileReader.State.single_line_comment
                            prev_symbol = None
                        else:
                            prev_symbol = None
                case AppleStringsFileReader.State.single_line_comment:
                    if char == '\n':
                        state = AppleStringsFileReader.State.scan
                        prev_symbol = None
                    else:
                        if comment is None:
                            comment = ''
                        comment += char
                case AppleStringsFileReader.State.multi_line_comment:
                    if prev_symbol == '*' and char == '/':
                        state = AppleStringsFileReader.State.scan
                        prev_symbol = None
                        if comment:
                            comment = comment[:-1].strip()
                    else:
                        prev_symbol = char
                        if comment is None:
                            comment = ''
                        comment += char
                case AppleStringsFileReader.State.token:
                    if char == '"':
                        state = AppleStringsFileReader.State.delimiter
                    else:
                        record.token += char
                case AppleStringsFileReader.State.delimiter:
                    # Skip until " found
                    if char == '"':
                        state = AppleStringsFileReader.State.value
                case AppleStringsFileReader.State.value:
                    # Translation ends on " without escaping
                    if char == '"' and prev_symbol != '\\':
                        state = AppleStringsFileReader.State.scan
                        is_completed = True
                    else:
                        prev_symbol = char
                        record.translation += char

        # Group plural-suffixed keys (e.g. token_one, token_other) into one model
        plural_buckets = {}
        seen_plural_bases = set()
        records = []

        for r in raw:
            base, form = _split_plural_key(r.token)
            if form is not None:
                if base not in plural_buckets:
                    plural_buckets[base] = {}
                plural_buckets[base][form] = r.translation

        for r in raw:
            base, form = _split_plural_key(r.token)
            if form is not None:
                if base not in seen_plural_bases:
                    seen_plural_bases.add(base)
                    records.append(TranslationModel.create(
                        token=base,
                        translation='',
                        comment=r.comment,
                        plural_forms=plural_buckets[base],
                    ))
            else:
                records.append(r)

        return records


class AppleStringsFileWriter(TranslationFileWriter):

    def __init__(self):
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/{code.lower()}.lproj/Localizable{ExportFile.strings.file_extension()}'

    def append(self, records, code):
        data = '\n'.join([self.convert_item(x) for x in records])

        self.zip_file.writestr(
            self.path(code=code),
            data
        )

    def convert_item(self, item):
        plural_forms = getattr(item, 'plural_forms', None) or {}
        if plural_forms:
            lines = []
            for form in PLURAL_FORM_ORDER:
                if form not in plural_forms:
                    continue
                suffixed_token = f'{item.token}_{form}'
                value = plural_forms[form].replace(
                    '&nbsp;', ' ').replace('"', '\\"').replace('%s', '%@')
                if item.comment and form == next(f for f in PLURAL_FORM_ORDER if f in plural_forms):
                    lines.append(
                        f'/*{item.comment}*/\n"{suffixed_token}" = "{value}";')
                else:
                    lines.append(f'"{suffixed_token}" = "{value}";')
            return '\n'.join(lines)

        translation = item.translation if item.translation else ''
        translation = translation.replace(
            '&nbsp;', ' '
        ).replace(
            '"', '\\"'
        ).replace('%s', '%@')
        if item.comment:
            return f'/*{item.comment}*/\n"{item.token}" = "{translation}";'
        else:
            return f'"{item.token}" = "{translation}";'

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response
