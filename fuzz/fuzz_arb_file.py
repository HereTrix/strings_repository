#!/usr/bin/env python3
"""Fuzz target for ARBFileReader."""
import atheris
import io
import json
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

from api.file_processors.arb_file import ARBFileReader


def TestOneInput(data):
    try:
        reader = ARBFileReader()
        reader.read(io.BytesIO(data))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, AttributeError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
