from xml.dom import minidom
import zipfile

from django.http import HttpResponse

from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel


class DotNetFileWriter:

    def __init__(self) -> None:
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/WebResources.{code.lower()}{ExportFile.resx.file_extension()}'

    def append(self, records, code):

        data = '<?xml version="1.0" encoding="utf-8"?>\n<root>\n' + self.__header

        for record in records:
            data += self.convert(record=record)

        data += '</root>'

        self.zip_file.writestr(
            self.path(code=code),
            data
        )

    def convert(self, record):
        text = ''
        if record.comment:
            text += f'''<!--
    {record.comment}
-->
'''
        cleared = record.translation \
            .replace('&', '&amp;') \
            .replace('<', '&lt;') \
            .replace('"', '&quot;') \
            .replace('>', '&gt;')
        return text + f'''    <data name="{record.token}" xml:space="preserve">
        <value>{cleared}</value>
    </data>
'''

    def http_response(self):
        self.response['Content-Disposition'] = 'attachment; filename="resources.zip"'
        self.zip_file.close()
        return self.response

    __header = '''     <xsd:schema id="root" xmlns="" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:msdata="urn:schemas-microsoft-com:xml-msdata">
    <xsd:import namespace="http://www.w3.org/XML/1998/namespace" />
    <xsd:element name="root" msdata:IsDataSet="true">
      <xsd:complexType>
        <xsd:choice maxOccurs="unbounded">
          <xsd:element name="metadata">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="value" type="xsd:string" minOccurs="0" />
              </xsd:sequence>
              <xsd:attribute name="name" use="required" type="xsd:string" />
              <xsd:attribute name="type" type="xsd:string" />
              <xsd:attribute name="mimetype" type="xsd:string" />
              <xsd:attribute ref="xml:space" />
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="assembly">
            <xsd:complexType>
              <xsd:attribute name="alias" type="xsd:string" />
              <xsd:attribute name="name" type="xsd:string" />
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="data">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="value" type="xsd:string" minOccurs="0" msdata:Ordinal="1" />
                <xsd:element name="comment" type="xsd:string" minOccurs="0" msdata:Ordinal="2" />
              </xsd:sequence>
              <xsd:attribute name="name" type="xsd:string" use="required" msdata:Ordinal="1" />
              <xsd:attribute name="type" type="xsd:string" msdata:Ordinal="3" />
              <xsd:attribute name="mimetype" type="xsd:string" msdata:Ordinal="4" />
              <xsd:attribute ref="xml:space" />
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="resheader">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="value" type="xsd:string" minOccurs="0" msdata:Ordinal="1" />
              </xsd:sequence>
              <xsd:attribute name="name" type="xsd:string" use="required" />
            </xsd:complexType>
          </xsd:element>
        </xsd:choice>
      </xsd:complexType>
    </xsd:element>
  </xsd:schema>
    <resheader name="resmimetype">
        <value>text/microsoft-resx</value>
    </resheader>
    <resheader name="version">
        <value>2.0</value>
    </resheader>
    <resheader name="reader">
        <value>System.Resources.ResXResourceReader, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089</value>
    </resheader>
    <resheader name="writer">
        <value>System.Resources.ResXResourceWriter, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089</value>
    </resheader>
'''


class DotNetFileReader:

    def read(self, file):
        file.seek(0)
        dom = minidom.parse(file=file)
        result = []

        resources = dom.getElementsByTagName('data')
        for resource in resources:
            token = resource.getAttribute('name')
            translation = ''
            if resource.childNodes:
                value = resource.getElementsByTagName("value")[0]
                if value.childNodes:
                    text_node = value.childNodes[0]
                    if text_node.nodeType == text_node.TEXT_NODE:
                        translation = text_node.data

            model = TranslationModel.create(
                token=token,
                translation=translation
            )
            result.append(model)

        return result
