from rest_framework.views import exception_handler as drf_exception_handler

_2FA_CODE = "2fa_required"


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data.get("detail")
    if detail is not None:
        error = str(detail)
        response.data = {"error": error}
        if _2FA_CODE in str(getattr(detail, "code", "")) or "2FA" in error:
            response.data["code"] = _2FA_CODE

    return response
