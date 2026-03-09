import os

LANGUAGE_KEY = 'Subtag'
LANGUAGE_DESC_KEY = 'Description'
LANGUAGE_FLAG_KEY = 'Flag'

LANGUAGE_CODE_KEY = 'code'
LANGUAGE_NAME_KEY = 'name'
LANGUAGE_FLAG_CODE_KEY = 'flag'

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
                if not lines:
                    continue
                data = Langcoder.parse_item(lines)
                languages[data[LANGUAGE_KEY].upper()] = {
                    LANGUAGE_DESC_KEY: data[LANGUAGE_DESC_KEY],
                    LANGUAGE_FLAG_KEY: data.get(LANGUAGE_FLAG_KEY, ''),
                }
                code_name.append({
                    LANGUAGE_CODE_KEY: data[LANGUAGE_KEY],
                    LANGUAGE_NAME_KEY: data[LANGUAGE_DESC_KEY],
                    LANGUAGE_FLAG_CODE_KEY: data.get(LANGUAGE_FLAG_KEY, ''),
                })
                lines.clear()
            else:
                lines.append(line)

    def parse_item(lines):
        data = {}
        for line in lines:
            key, value = line.split(': ', 1)
            data[key] = value
        return data

    def language(code):
        Langcoder.load()
        return languages[code.upper()][LANGUAGE_DESC_KEY]

    def flag(code):
        Langcoder.load()
        flag_code = languages[code.upper()][LANGUAGE_FLAG_KEY]
        return f'/static/flags/{flag_code}.svg' if flag_code else None

    def all_languages():
        Langcoder.load()
        return code_name
