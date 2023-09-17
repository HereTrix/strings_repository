from xml.dom import minidom
import zipfile

from django.http import HttpResponse

from api.file_processors.export_file_type import ExportFile


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

        data = root.toxml()

        self.zip_file.writestr(
            self.path(code=code),
            data
        )

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response
