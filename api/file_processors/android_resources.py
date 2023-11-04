import tempfile
from xml.dom import minidom
import zipfile

from django.http import HttpResponse

from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel


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
            item = root.createElement('string')
            item.setAttribute('name', record.token)
            if record.translation:
                text = root.createTextNode(record.translation)
                item.appendChild(text)
            xml.appendChild(item)

        data = root.toprettyxml()

        self.zip_file.writestr(
            self.path(code=code),
            data
        )

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response


class AndroidResourceFileReader:

    def read(self, file):
        file.seek(0)
        dom = minidom.parse(file=file)
        strings = dom.getElementsByTagName('string')
        result = []
        for node in strings:
            token = node.getAttribute('name')
            translation = ''
            if node.childNodes:
                text_node = node.childNodes[0]
                if text_node.nodeType == node.TEXT_NODE:
                    translation = text_node.data

            model = TranslationModel.create(
                token=token,
                translation=translation
            )
            result.append(model)

        return result
