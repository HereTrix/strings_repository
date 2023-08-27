import enum
from api.transport_models import TranslationModel


class AppleStringsFileReader:

    class State(enum.Enum):
        scan = 0
        token = 1
        delimiter = 2
        value = 3
        single_line_comment = 4
        multi_line_comment = 5

    def __init__(self, content):
        self.content = content

    def read(self):
        state = AppleStringsFileReader.State.scan
        prev_symbol = None
        is_completed = False
        records = []
        record = TranslationModel('', '')
        comment = None
        for char in self.content:
            match state:
                # Scan is emitted when
                case AppleStringsFileReader.State.scan:
                    if is_completed:
                        record.comment = comment
                        records.append(record)
                        record = TranslationModel('', '')
                        # All comments before key = value belongs to this pair
                        comment = None
                        is_completed = False
                        prev_symbol = None
                    if prev_symbol is None:
                        match char:
                            case '"':
                                state = AppleStringsFileReader.State.token
                                prev_symbol = None
                            case '/':
                                prev_symbol = char
                    else:
                        if char == '*':
                            state = AppleStringsFileReader.State.multi_line_comment
                            if comment is not None:
                                comment += '\n'
                            prev_symbol = None
                        if char == '/':
                            state = AppleStringsFileReader.State.single_line_comment
                            if comment is not None:
                                comment += '\n'
                            prev_symbol = None
                case AppleStringsFileReader.State.multi_line_comment:
                    if comment is None:
                        comment = ''
                    if prev_symbol is None:
                        if char == '*':
                            prev_symbol = char
                        else:
                            comment += char
                    else:
                        if prev_symbol == '/' or prev_symbol == '*':
                            if char == '/':
                                state = AppleStringsFileReader.State.scan
                            else:
                                comment += prev_symbol + char
                            prev_symbol = None
                        else:
                            if char == '/' or char == '*':
                                prev_symbol = char
                            else:
                                comment += char
                case AppleStringsFileReader.State.single_line_comment:
                    if comment is None:
                        comment = ''
                    if char == '\n':
                        state = AppleStringsFileReader.State.scan
                    else:
                        comment += char
                # Token should ends on "
                case AppleStringsFileReader.State.token:
                    if char == '"':
                        state = AppleStringsFileReader.State.delimiter
                    else:
                        record.token += char
                case AppleStringsFileReader.State.delimiter:
                    # Skip until " found
                    if char == '"':
                        state = AppleStringsFileReader.State.value
                case AppleStringsFileReader.State.value:
                    # Translation ends on " without escaping
                    if char == '"' and prev_symbol != '\\':
                        state = AppleStringsFileReader.State.scan
                        is_completed = True
                    else:
                        prev_symbol = char
                        record.translation += char
        return records


class AppleStringsFileWriter:

    def __init__(self, records):
        self.records = records

    def convert_file(self):
        items = [self.convert_item(x) for x in self.records]
        return '\n'.join(items)

    def convert_item(self, item):
        translation = item.translation if item.translation else ''
        if item.comment:
            return f'/*{item.comment}*/\n"{item.token}" = "{translation}";'
        else:
            return f'"{item.token}" = "{translation}";'
