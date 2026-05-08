#!/usr/bin/env python3
"""Fuzz target for DotNetFileReader."""
import atheris
import io
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

from api.file_processors.dotnet_file import DotNetFileReader
from xml.parsers.expat import ExpatError


def TestOneInput(data):
    try:
        reader = DotNetFileReader()
        reader.read(io.BytesIO(data))
    except (ExpatError, UnicodeDecodeError, ValueError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
