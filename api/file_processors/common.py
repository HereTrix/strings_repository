import re


def escape_quotes(text):
    text = re.sub(r"(?<!\\)’", r"\’", text)
    text = re.sub(r"(?<!\\)'", r"\'", text)
    return text
