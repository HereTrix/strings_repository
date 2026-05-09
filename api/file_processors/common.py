# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import re
from typing import Protocol
from abc import abstractmethod

from api.models.transport_models import TranslationModel


def escape_quotes(text):
    text = re.sub(r"(?<!\\)’", r"\’", text)
    text = re.sub(r"(?<!\\)'", r"\'", text)
    return text


class TranslationFileReader(Protocol):
    @abstractmethod
    def read(self, file_path: str) -> list[TranslationModel]:
        ...

    def needs_language_code(self) -> bool:
        return True


class TranslationFileWriter(Protocol):
    content_type: str
    filename: str

    @abstractmethod
    def append(self, records: list[TranslationModel], code: str) -> None:
        ...

    @abstractmethod
    def write(self, buf) -> None:
        ...
