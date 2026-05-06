from django.urls import path
from api.views.project import (
    ProjectAPI, CreateProjectAPI, ProjectListAPI,
    ProjectAvailableLanguagesAPI, LanguageListAPI, StringTokenListAPI,
    ProjectTagsAPI, LanguageProgressAPI, TranslationsListAPI,
)
from api.views.roles import ProjectAccessTokenAPI, ProjectInvitationAPI, ProjectParticipantsAPI, RolesAPI
from api.views.language import LanguageAPI, SetDefaultLanguageAPI
from api.views.integration import IntegrationAPI, MachineTranslateAPI, VerifyIntegrationAPI
from api.views.history import ProjectHistoryAPI, ProjectHistoryExportAPI
from api.views.scope import ScopeDetailAPI, ScopeImageAPI, ScopeListCreateAPI, ScopeTokensAPI
from api.views.webhook import WebhookDetailAPI, WebhookEventsAPI, WebhookListAPI, WebhookLogsAPI, WebhookVerifyAPI
from api.views.bundle import BundleActivateAPI, BundleCompareAPI, BundleCompareExportAPI, BundleDeactivateAPI, BundleDetailAPI, BundleExportAPI, BundleListCreateAPI
from api.views.ai_provider import AIProviderAPI
from api.views.glossary import (
    GlossaryTermListCreateAPI, GlossaryTermDetailAPI,
    GlossaryExtractionAPI, GlossarySuggestionsAPI,
    GlossaryExportAPI, GlossaryImportAPI,
)
from api.views.verification import (
    VerificationListCreateAPI, VerificationCountAPI, VerificationDetailAPI,
    VerificationApplyAPI, VerificationCommentAPI,
)
from api.views.translation_memory import TranslationMemoryAPI

urlpatterns = [
    path('projects/list', ProjectListAPI.as_view()),
    path('project', CreateProjectAPI.as_view()),
    path('project/<int:pk>', ProjectAPI.as_view()),
    # roles & access
    path('project/<int:pk>/roles', RolesAPI.as_view()),
    path('project/<int:pk>/access_token', ProjectAccessTokenAPI.as_view()),
    path('project/<int:pk>/participants', ProjectParticipantsAPI.as_view()),
    path('project/<int:pk>/invite', ProjectInvitationAPI.as_view()),
    # languages
    path('language', LanguageAPI.as_view()),
    path('project/<int:pk>/availableLanguages', ProjectAvailableLanguagesAPI.as_view()),
    path('project/<int:pk>/languages', LanguageListAPI.as_view()),
    path('project/<int:pk>/language/<str:code>/default', SetDefaultLanguageAPI.as_view()),
    # tokens & translations
    path('project/<int:pk>/tokens', StringTokenListAPI.as_view()),
    path('project/<int:pk>/tags', ProjectTagsAPI.as_view()),
    path('project/<int:pk>/progress', LanguageProgressAPI.as_view()),
    path('project/<int:pk>/translations/<str:code>', TranslationsListAPI.as_view()),
    # scopes
    path('project/<int:pk>/scopes', ScopeListCreateAPI.as_view()),
    path('project/<int:pk>/scopes/<int:scope_id>', ScopeDetailAPI.as_view()),
    path('project/<int:pk>/scopes/<int:scope_id>/tokens', ScopeTokensAPI.as_view()),
    path('project/<int:pk>/scopes/<int:scope_id>/image', ScopeImageAPI.as_view()),
    # integration
    path('project/<int:pk>/integration', IntegrationAPI.as_view()),
    path('project/<int:pk>/integration/verify', VerifyIntegrationAPI.as_view()),
    path('project/<int:pk>/machine-translate', MachineTranslateAPI.as_view()),
    # history
    path('project/<int:pk>/history/export', ProjectHistoryExportAPI.as_view()),
    path('project/<int:pk>/history', ProjectHistoryAPI.as_view()),
    # webhooks
    path('project/<int:pk>/webhooks', WebhookListAPI.as_view()),
    path('project/<int:pk>/webhooks/events', WebhookEventsAPI.as_view()),
    path('project/<int:pk>/webhooks/<int:webhook_id>', WebhookDetailAPI.as_view()),
    path('project/<int:pk>/webhooks/<int:webhook_id>/verify', WebhookVerifyAPI.as_view()),
    path('project/<int:pk>/webhooks/<int:webhook_id>/logs', WebhookLogsAPI.as_view()),
    # bundles
    path('project/<int:pk>/bundles', BundleListCreateAPI.as_view()),
    path('project/<int:pk>/bundles/compare', BundleCompareAPI.as_view()),
    path('project/<int:pk>/bundles/compare/export', BundleCompareExportAPI.as_view()),
    path('project/<int:pk>/bundles/<int:bundle_id>', BundleDetailAPI.as_view()),
    path('project/<int:pk>/bundles/<int:bundle_id>/activate', BundleActivateAPI.as_view()),
    path('project/<int:pk>/bundles/<int:bundle_id>/deactivate', BundleDeactivateAPI.as_view()),
    path('project/<int:pk>/bundles/<int:bundle_id>/export', BundleExportAPI.as_view()),
    # AI provider
    path('project/<int:pk>/ai-provider', AIProviderAPI.as_view()),
    # glossary — named sub-routes MUST precede <int:term_id>
    path('project/<int:pk>/glossary/export', GlossaryExportAPI.as_view()),
    path('project/<int:pk>/glossary/import', GlossaryImportAPI.as_view()),
    path('project/<int:pk>/glossary/extract', GlossaryExtractionAPI.as_view()),
    path('project/<int:pk>/glossary/suggestions', GlossarySuggestionsAPI.as_view()),
    path('project/<int:pk>/glossary/<int:term_id>', GlossaryTermDetailAPI.as_view()),
    path('project/<int:pk>/glossary', GlossaryTermListCreateAPI.as_view()),
    # verification — count MUST be before <report_id> to avoid integer-match conflict
    path('project/<int:pk>/verify/count', VerificationCountAPI.as_view()),
    path('project/<int:pk>/verify', VerificationListCreateAPI.as_view()),
    path('project/<int:pk>/verify/<int:report_id>', VerificationDetailAPI.as_view()),
    path('project/<int:pk>/verify/<int:report_id>/apply', VerificationApplyAPI.as_view()),
    path('project/<int:pk>/verify/<int:report_id>/comments', VerificationCommentAPI.as_view()),
    # translation memory
    path('project/<int:pk>/translation-memory', TranslationMemoryAPI.as_view()),
]
