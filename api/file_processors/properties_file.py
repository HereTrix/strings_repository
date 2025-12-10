from configparser import ConfigParser
import tempfile
import zipfile
from django.http import HttpResponse
from api.file_processors.common import TranslationFileReader, TranslationFileWriter
from api.file_processors.export_file_type import ExportFile
from api.transport_models import TranslationModel


class PropertiesFileWriter(TranslationFileWriter):

    def __init__(self):
        self.response = HttpResponse(content_type='application/zip')
        self.zip_file = zipfile.ZipFile(self.response, 'w')

    def path(self, code):
        return f'/{code.lower()}{ExportFile.properties.file_extension()}'

    def append(self, records, code):
        data = '\n'.join([self.convert_item(x) for x in records])
        self.zip_file.writestr(
            self.path(code=code),
            data
        )

    def convert_item(self, item):
        translation = item.translation if item.translation else ''
        translation = self.clear(translation)
        token = self.prepare(item.token)
        if item.comment:
            comment = item.comment.replace('\n', '\n# ')
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
        result = []

        comment = ''
        for line in lines:
            str_line = line.decode()
            if len(str_line) > 0:
                # Any line that starts with a '#' is considerered a comment
                if str_line[0] == '#':
                    comment += str_line
                else:
                    model = self.process_line(
                        line=str_line,
                        comment=comment
                    )
                    result.append(model)
                    comment = ''

        return result

    def process_line(self, line, comment):
        prev = ''
        token = ''
        value = ''
        delim = -1
        for i, char in enumerate(line):
            # separators are : = and space
            if char == ':' or char == '=' or char == ' ':
                if prev == '\\':
                    # escaping is part of key
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

        model = TranslationModel.create(
            token=token,
            translation=value,
            comment=comment
        )

        return model

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
