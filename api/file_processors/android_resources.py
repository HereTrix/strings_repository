import re
import zipfile
from xml.dom import minidom

from django.http import HttpResponse

from api.file_processors.common import escape_quotes
from api.file_processors.export_file_type import ExportFile
from api.models.transport_models import TranslationModel
from api.models.translations import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()


class AndroidResourceFileWriter:

    def __init__(self):
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/values-{code.lower()}/strings{ExportFile.android.file_extension()}'

    def append(self, records, code):
        root = minidom.Document()
        xml = root.createElement('resources')
        root.appendChild(xml)

        for record in records:
            if record.comment:
                comment = root.createComment(record.comment)
                xml.appendChild(comment)

            if record.plural_forms:
                plurals_elem = root.createElement('plurals')
                plurals_elem.setAttribute('name', record.token)

                for form in PLURAL_FORM_ORDER:
                    if form not in record.plural_forms:
                        continue
                    item = root.createElement('item')
                    item.setAttribute('quantity', form)
                    text = escape_quotes(record.plural_forms[form])
                    res = re.search(
                        r'</?\s*[a-z-][^>]*\s*>|(\&(?:[\w\d]+|#\d+|#x[a-f\d]+);)',
                        record.plural_forms[form]
                    )
                    if res:
                        item.appendChild(root.createCDATASection(text))
                    else:
                        item.appendChild(root.createTextNode(text))
                    plurals_elem.appendChild(item)

                xml.appendChild(plurals_elem)
            else:
                item = root.createElement('string')
                item.setAttribute('name', record.token)
                text = escape_quotes(record.translation)
                if record.translation:
                    res = re.search(
                        r'</?\s*[a-z-][^>]*\s*>|(\&(?:[\w\d]+|#\d+|#x[a-f\d]+);)',
                        record.translation
                    )
                    if res:
                        text = root.createCDATASection(text)
                    else:
                        text = root.createTextNode(text)
                    item.appendChild(text)
                xml.appendChild(item)

        data = root.toprettyxml()
        self.zip_file.writestr(self.path(code=code), data)

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response


class AndroidResourceFileReader:

    def read(self, file):
        file.seek(0)
        dom = minidom.parse(file=file)
        result = []

        for node in dom.getElementsByTagName('string'):
            token = node.getAttribute('name')
            translation = ''
            if node.childNodes:
                text_node = node.childNodes[0]
                if text_node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
                    translation = text_node.data
            result.append(TranslationModel.create(
                token=token, translation=translation))

        for plurals_node in dom.getElementsByTagName('plurals'):
            token = plurals_node.getAttribute('name')
            plural_forms = {}
            for item in plurals_node.getElementsByTagName('item'):
                quantity = item.getAttribute('quantity')
                value = ''
                if item.childNodes:
                    text_node = item.childNodes[0]
                    if text_node.nodeType in (item.TEXT_NODE, item.CDATA_SECTION_NODE):
                        value = text_node.data
                if quantity:
                    plural_forms[quantity] = value
            result.append(TranslationModel.create(
                token=token,
                translation='',
                plural_forms=plural_forms,
            ))

        return result
