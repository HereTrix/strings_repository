#!/usr/bin/env python3
"""Fuzz target for AndroidResourceFileReader."""
import atheris
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

from api.file_processors.android_resources import AndroidResourceFileReader
from xml.parsers.expat import ExpatError


def TestOneInput(data):
    try:
        reader = AndroidResourceFileReader()
        reader.read(io.BytesIO(data))
    except (ExpatError, UnicodeDecodeError, ValueError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
