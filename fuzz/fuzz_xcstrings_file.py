#!/usr/bin/env python3
"""Fuzz target for XCStringsFileReader."""
import atheris
import io
import json
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

from api.file_processors.xcstrings_file import XCStringsFileReader


def TestOneInput(data):
    try:
        reader = XCStringsFileReader()
        reader.read(io.BytesIO(data))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError, AttributeError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
