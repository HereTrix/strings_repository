#!/usr/bin/env python3
"""Fuzz target for POFileReader and MOFileReader."""
import atheris
import io
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

import atheris.instrument_imports
with atheris.instrument_imports():
    from api.file_processors.po_file import POFileReader
    from api.file_processors.mo_file import MOFileReader

_po_reader = POFileReader()
_mo_reader = MOFileReader()


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 1)
    payload = fdp.ConsumeBytes(fdp.remaining_bytes())
    try:
        if choice == 0:
            _po_reader.read(io.BytesIO(payload))
        else:
            _mo_reader.read(io.BytesIO(payload))
    except (UnicodeDecodeError, ValueError, OSError, IOError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
