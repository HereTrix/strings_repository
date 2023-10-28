from django.urls import path
from api.views.export import ExportAPI, ExportFormatsAPI
from api.views.generic import *
from api.views.history import ProjectHistoryAPI, ProjectHistoryExportAPI
from api.views.language import LanguageAPI
from api.views.project import *
from api.views.roles import ProjectInvitationAPI, ProjectParticipantsAPI, RolesAPI
from api.views.translation import StringTokenAPI, StringTokenTagAPI, StringTokenTranslationsAPI, TranslationAPI
from knox.views import LogoutView

urlpatterns = [
    path('signup', SignUpAPI.as_view()),
    path('login', SignInAPI.as_view()),
    path('logout', LogoutView.as_view()),
    path('profile', ProfileAPI.as_view()),
    path('password', ChangePasswordAPI.as_view()),
    path('activate', ActivateProjectAPI.as_view()),
    # roles
    path('project/<int:pk>/roles', RolesAPI.as_view()),
    # project
    path('project/<int:pk>/availableLanguages',
         ProjectAvailableLanguagesAPI.as_view()),
    path('project/<int:pk>/participants', ProjectParticipantsAPI.as_view()),
    path('project/<int:pk>/languages', LanguageListAPI.as_view()),
    path('project/<int:pk>/tokens', StringTokenListAPI.as_view()),
    path('project/<int:pk>/tags', ProjectTagsAPI.as_view()),
    path('project/<int:pk>/invite', ProjectInvitationAPI.as_view()),
    path('project/<int:pk>/translations/<str:code>',
         TranslationsListAPI.as_view()),
    path('project/<int:pk>/history/export', ProjectHistoryExportAPI.as_view()),
    path('project/<int:pk>/history', ProjectHistoryAPI.as_view()),
    path('project/<int:pk>', ProjectAPI.as_view()),
    path('projects/list', ProjectListAPI.as_view()),
    path('project', CreateProjectAPI.as_view()),
    # language
    path('language', LanguageAPI.as_view()),
    # tokens
    path('string_token', StringTokenAPI.as_view()),
    path('string_token/<int:pk>/tags', StringTokenTagAPI.as_view()),
    path('string_token/<int:pk>/translations',
         StringTokenTranslationsAPI.as_view()),
    path('translation', TranslationAPI.as_view()),
    path('export', ExportAPI.as_view()),
    path('supported_formats', ExportFormatsAPI.as_view())
]
