#!/usr/bin/env python3
"""Fuzz target for CSVFileReader."""
import atheris
import io
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

from api.file_processors.csv_file import CSVFileReader


def TestOneInput(data):
    try:
        reader = CSVFileReader()
        reader.read(io.BytesIO(data))
    except (UnicodeDecodeError, ValueError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
