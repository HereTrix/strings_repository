#!/usr/bin/env python3
# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

"""Fuzz target for POFileReader and MOFileReader."""
import atheris
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

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
    except RecursionError:
        raise
    except Exception:
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
