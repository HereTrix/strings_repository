from django.http import JsonResponse


def error_response(message, status_code):
    return JsonResponse({'error': str(message)}, status=status_code)
