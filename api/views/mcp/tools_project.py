# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from api.models.language import Language


def get_project(args, access):
    p = access.project
    return {"id": p.id, "name": p.name, "description": p.description}


def get_languages(args, access):
    codes = list(Language.objects.filter(
        project=access.project).values_list('code', flat=True))
    return {"languages": codes}
