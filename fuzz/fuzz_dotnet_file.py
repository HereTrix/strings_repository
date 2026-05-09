#!/usr/bin/env python3
# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

"""Fuzz target for DotNetFileReader."""
import atheris
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuzz.fuzz_settings')
import django
django.setup()

from api.file_processors.dotnet_file import DotNetFileReader

_reader = DotNetFileReader()


def TestOneInput(data):
    try:
        _reader.read(io.BytesIO(data))
    except RecursionError:
        raise
    except Exception:
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
