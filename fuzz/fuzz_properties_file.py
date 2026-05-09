#!/usr/bin/env python3
"""Fuzz target for PropertiesFileReader."""
import atheris
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

from api.file_processors.properties_file import PropertiesFileReader


def TestOneInput(data):
    try:
        reader = PropertiesFileReader()
        reader.read(io.BytesIO(data))
    except (UnicodeDecodeError, ValueError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
