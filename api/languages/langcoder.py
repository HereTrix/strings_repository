import os

LANGUAGE_KEY = 'Subtag'
LANGUAGE_DESC_KEY = 'Description'

LANGUAGE_CODE_KEY = 'code'
LANGUAGE_NAME_KEY = 'name'

languages = {}
code_name = []


class Langcoder:  # Languages file processor

    def load():
        if languages:
            return

        dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir, 'languages.txt')

        with open(
            file_path, encoding='utf-8'
        ) as data_file:
            Langcoder.parse_file(data_file)

    def parse_file(file):
        lines = []
        for line in file:
            line = line.rstrip('\n')
            if line == '%%':
                data = Langcoder.parse_item(lines)
                languages[data[LANGUAGE_KEY].upper()] = data[LANGUAGE_DESC_KEY]
                code_name.append({
                    LANGUAGE_CODE_KEY: data[LANGUAGE_KEY],
                    LANGUAGE_NAME_KEY: data[LANGUAGE_DESC_KEY]
                })
                lines.clear()
            else:
                lines.append(line)

    def parse_item(lines):
        data = {}
        for line in lines:
            key, value = line.split(': ')
            data[key] = value
        return data

    def language(code):
        Langcoder.load()
        return languages[code.upper()]

    def all_languages():
        Langcoder.load()
        return code_name
