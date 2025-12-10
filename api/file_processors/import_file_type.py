import enum


class ImportFile(enum.Enum):
    strings = 'strings'
    xml = 'xml'
    # excel = 'excel'
    json = 'json'
    resx = 'resx'
    properties = 'properties'
    po = 'po'
    mo = 'mo'
    xcstrings = 'xcstrings'
