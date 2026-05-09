# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import io
import json
import re
import zipfile

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.models.transport_models import TranslationModel
from api.models.translations import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()

_ICU_PLURAL_RE = re.compile(r'^\{(\w+),\s*plural,\s*(.+)\}$', re.DOTALL)
_FORM_RE = re.compile(r'(zero|one|two|few|many|other)\s*\{((?:[^{}]|\{[^{}]*\})*)\}')


def _parse_icu_plural(value):
    if not isinstance(value, str):
        return None, None
    m = _ICU_PLURAL_RE.match(value.strip())
    if not m:
        return None, None
    var_name = m.group(1)
    forms = {fm.group(1): fm.group(2) for fm in _FORM_RE.finditer(m.group(2))}
    if not forms:
        return None, None
    return var_name, forms


def _build_icu_plural(plural_forms, var_name='count'):
    parts = [f'{form} {{{plural_forms[form]}}}' for form in PLURAL_FORM_ORDER if form in plural_forms]
    return '{' + var_name + ', plural, ' + ' '.join(parts) + '}'


class ARBFileWriter(TranslationFileWriter):
    content_type = 'application/zip'
    filename = 'resources.zip'

    def __init__(self):
        self._buf = io.BytesIO()
        self.zip_file = zipfile.ZipFile(self._buf, 'w')

    def _path(self, code):
        return f'/intl_{code.lower()}.arb'

    def append(self, records, code):
        data = {'@@locale': code.lower()}
        for item in records:
            plural_forms = getattr(item, 'plural_forms', None) or {}
            if plural_forms:
                data[item.token] = _build_icu_plural(plural_forms)
            else:
                data[item.token] = item.translation
            if item.comment:
                data[f'@{item.token}'] = {'description': item.comment}
        self.zip_file.writestr(
            self._path(code=code),
            json.dumps(data, indent=4, ensure_ascii=False)
        )

    def write(self, buf):
        self.zip_file.close()
        buf.write(self._buf.getvalue())


class ARBFileReader(TranslationFileReader):

    def read(self, file):
        file.seek(0)
        data = json.load(file)

        result = []
        for key, value in data.items():
            if key.startswith('@'):
                continue
            comment = None
            meta = data.get(f'@{key}')
            if isinstance(meta, dict):
                comment = meta.get('description')

            _, plural_forms = _parse_icu_plural(value)
            if plural_forms:
                result.append(TranslationModel.create(
                    token=key,
                    translation='',
                    comment=comment,
                    plural_forms=plural_forms,
                ))
            else:
                result.append(TranslationModel.create(
                    token=key,
                    translation=value,
                    comment=comment,
                ))

        return result
