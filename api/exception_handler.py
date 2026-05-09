# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from rest_framework.views import exception_handler as drf_exception_handler

_2FA_CODE = "2fa_required"
_2FA_LOGIN_CODE = "2fa_login_required"


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data.get("detail")
    if detail is not None:
        error = str(detail)
        detail_code = str(getattr(detail, "code", ""))
        response.data = {"error": error}
        if _2FA_LOGIN_CODE in detail_code:
            response.data["code"] = _2FA_LOGIN_CODE
        elif _2FA_CODE in detail_code or "2FA" in error:
            response.data["code"] = _2FA_CODE

    return response
