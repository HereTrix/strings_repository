from django.urls import path
from api.views.translation import StringTokenAPI, StringTokenStatusAPI, StringTokenTagAPI, StringTokenTranslationsAPI, TranslationAPI, TranslationStatusAPI
from api.views.plural_translation import PluralTranslationAPI
from api.views.export import ExportAPI, ExportFormatsAPI
from api.views.import_api import ImportAPI

urlpatterns = [
    path('string_token', StringTokenAPI.as_view()),
    path('string_token/<int:pk>/status', StringTokenStatusAPI.as_view()),
    path('string_token/<int:pk>/tags', StringTokenTagAPI.as_view()),
    path('string_token/<int:pk>/translations', StringTokenTranslationsAPI.as_view()),
    path('translation', TranslationAPI.as_view()),
    path('translation/status', TranslationStatusAPI.as_view()),
    path('plural', PluralTranslationAPI.as_view()),
    path('export', ExportAPI.as_view()),
    path('import', ImportAPI.as_view()),
    path('supported_formats', ExportFormatsAPI.as_view()),
]
