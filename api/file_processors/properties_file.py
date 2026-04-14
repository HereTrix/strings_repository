import zipfile
from django.http import HttpResponse
from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.models.transport_models import TranslationModel
from api.models.translations import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()
PLURAL_FORMS_SET = set(PLURAL_FORM_ORDER)

# Suffix pattern used for plural keys: token[one], token[other], etc.


def _plural_suffix(form):
    return f'[{form}]'


def _split_plural_key(token):
    """Return (base_token, form) if token ends with a known plural suffix, else (token, None)."""
    for form in PLURAL_FORM_ORDER:
        suffix = _plural_suffix(form)
        if token.endswith(suffix):
            return token[:-len(suffix)], form
    return token, None


class PropertiesFileWriter(TranslationFileWriter):

    def __init__(self):
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/{code.lower()}{ExportFile.properties.file_extension()}'

    def append(self, records, code):
        lines = []
        for item in records:
            plural_forms = getattr(item, 'plural_forms', None) or {}
            if plural_forms:
                first_present_form = next((f for f in PLURAL_FORM_ORDER if f in plural_forms), None)
                for form in PLURAL_FORM_ORDER:
                    if form not in plural_forms:
                        continue
                    suffixed_token = item.token + _plural_suffix(form)
                    lines.append(self._convert_item_raw(
                        token=suffixed_token,
                        translation=plural_forms[form],
                        comment=item.comment if form == first_present_form else None,
                    ))
            else:
                lines.append(self._convert_item(item))
        self.zip_file.writestr(self.path(code=code), '\n'.join(lines))

    def _convert_item(self, item):
        return self._convert_item_raw(
            token=item.token,
            translation=item.translation if item.translation else '',
            comment=item.comment,
        )

    def _convert_item_raw(self, token, translation, comment):
        translation = self.clear(translation)
        token = self.prepare(token)
        if comment:
            comment = comment.replace('\n', '\n# ')
            return f'# {comment}\n{token}={translation}'
        else:
            return f'{token}={translation}'

    def prepare(self, text):
        text = text.replace('!', r'\!')
        text = text.replace('=', r'\=')
        text = text.replace(':', r'\:')
        text = text.replace('#', r'\#')
        text = text.replace(r'\"', r'\\"')
        text = text.replace(' ', r'\ ')
        return text

    def clear(self, text):
        if not text:
            return ''
        text = text.rstrip()
        text = text.replace(r'\!', '!')
        text = text.replace(r'\=', '=')
        text = text.replace(r'\:', ':')
        text = text.replace(r'\#', '#')
        text = text.replace(r'\\"', r'\"')
        text = text.replace(r'\ ', ' ')
        return text

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response


class PropertiesFileReader(TranslationFileReader):
    def read(self, file):
        file.seek(0)

        # Every line in the file must consist of either a comment
        # or a key-value pair. A key-value pair is a line consisting
        # of a key which is a combination of non-white space characters
        # The separator character between key-value pairs is a '=',
        # ':' or a whitespace character not including the newline.
        # If the '=' or ':' characters are found, in the line, even
        # keys containing whitespace chars are allowed.

        lines = file.readlines()

        # First pass: collect all raw key-value pairs
        raw = {}       # token -> TranslationModel (singular)
        raw_order = []  # preserve insertion order for output
        comment = ''
        for line in lines:
            str_line = line.decode()
            if len(str_line) > 0:
                if str_line[0] == '#':
                    comment += str_line
                else:
                    model = self.process_line(line=str_line, comment=comment)
                    raw[model.token] = model
                    raw_order.append(model.token)
                    comment = ''

        # Second pass: group plural-suffixed keys back into plural_forms
        result = []
        consumed = set()
        for token in raw_order:
            if token in consumed:
                continue
            base, form = _split_plural_key(token)
            if form is not None:
                # This is a plural entry — collect all forms for this base token
                plural_forms = {}
                for f in PLURAL_FORM_ORDER:
                    suffixed = base + _plural_suffix(f)
                    if suffixed in raw:
                        plural_forms[f] = raw[suffixed].translation
                        consumed.add(suffixed)
                # Use the comment from the first form's entry
                first_key = next(
                    (base + _plural_suffix(f)
                     for f in PLURAL_FORM_ORDER if base + _plural_suffix(f) in raw),
                    token
                )
                result.append(TranslationModel.create(
                    token=base,
                    translation='',
                    comment=raw[first_key].comment,
                    plural_forms=plural_forms,
                ))
            else:
                result.append(raw[token])

        return result

    def process_line(self, line, comment):
        prev = ''
        token = ''
        value = ''
        delim = -1
        for i, char in enumerate(line):
            if char == ':' or char == '=' or char == ' ':
                if prev == '\\':
                    continue
                else:
                    if delim == -1:
                        delim = i
                        token = self.clear(line[0:delim])
                    else:
                        if char == ':' or char == '=' or char == ' ':
                            continue
            else:
                if delim > -1:
                    value = line[i:]
                    value = self.clear(value)
                    break
            prev = char

        return TranslationModel.create(
            token=token,
            translation=value,
            comment=comment,
        )

    def clear(self, text):
        if not text:
            return ''
        text = text.rstrip()
        text = text.replace(r'\!', '!')
        text = text.replace(r'\=', '=')
        text = text.replace(r'\:', ':')
        text = text.replace(r'\#', '#')
        text = text.replace(r'\\"', r'\"')
        text = text.replace(r'\ ', ' ')
        return text
