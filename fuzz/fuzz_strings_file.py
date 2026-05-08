#!/usr/bin/env python3
"""Fuzz target for AppleStringsFileReader."""
import atheris
import io
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

from api.file_processors.strings_file import AppleStringsFileReader


def TestOneInput(data):
    try:
        reader = AppleStringsFileReader()
        reader.read(io.BytesIO(data))
    except (UnicodeDecodeError, ValueError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
