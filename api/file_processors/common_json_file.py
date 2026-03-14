import json

from api.file_processors.json_dict_file import JsonDictFileReader
from api.file_processors.json_file import JsonFileReader


class CommonJSONFileReader:
    """
    Factory reader for .json files. Inspects the file structure and delegates
    to JsonDictFileReader (values are dicts) or JsonFileReader (values are strings).
    """

    def read(self, file):
        return self._make_reader(file).read(file)

    def needs_language_code(self):
        return True

    def _make_reader(self, file):
        file.seek(0)
        try:
            data = json.load(file)
            if isinstance(data, dict) and data:
                first_value = next(iter(data.values()))
                if isinstance(first_value, dict):
                    return JsonDictFileReader()
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        finally:
            file.seek(0)

        return JsonFileReader()
