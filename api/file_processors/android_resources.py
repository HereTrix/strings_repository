from xml.dom import minidom


class AndroidResourceFileWriter:

    def __init__(self, records):
        self.records = records

    def convert_file(self):
        root = minidom.Document()
        xml = root.createElement('resources')
        root.appendChild(xml)

        for record in self.records:
            if record.comment:
                comment = root.createComment(record.comment)
                xml.appendChild(comment)
            item = root.createElement('string')
            item.setAttribute('name', record.token)
            if record.translation:
                text = root.createTextNode(record.translation)
                item.appendChild(text)
            xml.appendChild(item)

        return root.toxml()
