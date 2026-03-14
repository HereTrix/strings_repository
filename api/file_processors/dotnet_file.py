from xml.dom import minidom
import zipfile

from django.http import HttpResponse

from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel
from api.models import PluralTranslation

PLURAL_FORM_ORDER = PluralTranslation.PluralForm.PLURAL_FORM_ORDER()


def _plural_suffix(form):
    return f'[{form}]'


def _split_plural_key(token):
    """Return (base_token, form) if token ends with a known plural suffix, else (token, None)."""
    for form in PLURAL_FORM_ORDER:
        if token.endswith(_plural_suffix(form)):
            return token[:-len(_plural_suffix(form))], form
    return token, None


def _xml_escape(text):
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('"', '&quot;')
            .replace('>', '&gt;'))


class DotNetFileWriter(TranslationFileWriter):

    def __init__(self) -> None:
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/WebResources.{code.lower()}{ExportFile.resx.file_extension()}'

    def append(self, records, code):
        data = '<?xml version="1.0" encoding="utf-8"?>\n<root>\n' + self.__header

        for record in records:
            plural_forms = getattr(record, 'plural_forms', None) or {}
            if plural_forms:
                for form in plural_forms.keys():
                    suffixed_token = record.token + _plural_suffix(form)
                    # Only attach the comment to the first form
                    comment = record.comment if form == PLURAL_FORM_ORDER[0] else None
                    data += self._convert_raw(
                        token=suffixed_token,
                        translation=plural_forms[form],
                        comment=comment,
                    )
            else:
                data += self.convert(record)

        data += '</root>'
        self.zip_file.writestr(self.path(code=code), data)

    def convert(self, record):
        return self._convert_raw(
            token=record.token,
            translation=record.translation,
            comment=record.comment,
        )

    def _convert_raw(self, token, translation, comment):
        text = ''
        if comment:
            text += f'<!--\n    {comment}\n-->\n'
        cleared = _xml_escape(translation or '')
        return text + f'    <data name="{token}" xml:space="preserve">\n        <value>{cleared}</value>\n    </data>\n'

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
              <xsd:attribute name="name" type="xsd:string" use="required" />
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


class DotNetFileReader(TranslationFileReader):

    def read(self, file):
        file.seek(0)
        dom = minidom.parse(file=file)
        result = []

        # Collect all raw data entries preserving document order
        raw = {}       # name -> (translation, comment)
        raw_order = []
        for resource in dom.getElementsByTagName('data'):
            token = resource.getAttribute('name')
            translation = ''
            if resource.childNodes:
                value_nodes = resource.getElementsByTagName('value')
                if value_nodes:
                    value = value_nodes[0]
                    if value.childNodes:
                        text_node = value.childNodes[0]
                        if text_node.nodeType == text_node.TEXT_NODE:
                            translation = text_node.data
            raw[token] = translation
            raw_order.append(token)

        # Group plural-suffixed keys back into plural_forms
        consumed = set()
        for token in raw_order:
            if token in consumed:
                continue
            base, form = _split_plural_key(token)
            if form is not None:
                plural_forms = {}
                for f in PLURAL_FORM_ORDER:
                    suffixed = base + _plural_suffix(f)
                    if suffixed in raw:
                        plural_forms[f] = raw[suffixed]
                        consumed.add(suffixed)
                result.append(TranslationModel.create(
                    token=base,
                    translation='',
                    plural_forms=plural_forms,
                ))
            else:
                result.append(TranslationModel.create(
                    token=token,
                    translation=raw[token],
                ))

        return result
