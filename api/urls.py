from django.urls import path
from api.views.bundle import BundleActivateAPI, BundleCompareAPI, BundleCompareExportAPI, BundleDeactivateAPI, BundleDetailAPI, BundleExportAPI, BundleListCreateAPI
from api.views.export import ExportAPI, ExportFormatsAPI
from api.views.generic import *
from api.views.history import ProjectHistoryAPI, ProjectHistoryExportAPI
from api.views.import_api import ImportAPI
from api.views.language import LanguageAPI, SetDefaultLanguageAPI
from api.views.mcp import McpView
from api.views.plugin import FetchLanguagesAPI, PluginExportAPI, PullAPI, PushAPI
from api.views.plural_translation import PluralTranslationAPI
from api.views.project import *
from api.views.integration import IntegrationAPI, MachineTranslateAPI, VerifyIntegrationAPI
from api.views.roles import ProjectAccessTokenAPI, ProjectInvitationAPI, ProjectParticipantsAPI, RolesAPI
from api.views.translation import StringTokenAPI, StringTokenStatusAPI, StringTokenTagAPI, StringTokenTranslationsAPI, TranslationAPI, TranslationStatusAPI
from api.views.scope import ScopeDetailAPI, ScopeImageAPI, ScopeListCreateAPI, ScopeTokensAPI
from api.views.two_fa import TwoFASetupAPI, TwoFAVerifyAPI, TwoFADeleteAPI, TwoFALoginAPI
from api.views.webhook import WebhookDetailAPI, WebhookEventsAPI, WebhookListAPI, WebhookLogsAPI, WebhookVerifyAPI
from api.views.ai_provider import AIProviderAPI
from api.views.passkey import (
    PasskeyRegisterBeginAPI, PasskeyRegisterCompleteAPI,
    PasskeyAuthBeginAPI, PasskeyAuthCompleteAPI, PasskeyDeleteAPI,
)
from api.views.verification import (
    VerificationListCreateAPI,
    VerificationCountAPI,
    VerificationDetailAPI,
    VerificationApplyAPI,
    VerificationCommentAPI,
)
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
    path('project/<int:pk>/access_token', ProjectAccessTokenAPI.as_view()),
    path('project/<int:pk>/participants', ProjectParticipantsAPI.as_view()),
    path('project/<int:pk>/languages', LanguageListAPI.as_view()),
    path('project/<int:pk>/tokens', StringTokenListAPI.as_view()),
    path('project/<int:pk>/tags', ProjectTagsAPI.as_view()),
    path('project/<int:pk>/progress', LanguageProgressAPI.as_view()),
    path('project/<int:pk>/scopes', ScopeListCreateAPI.as_view()),
    path('project/<int:pk>/scopes/<int:scope_id>', ScopeDetailAPI.as_view()),
    path('project/<int:pk>/scopes/<int:scope_id>/tokens', ScopeTokensAPI.as_view()),
    path('project/<int:pk>/scopes/<int:scope_id>/image', ScopeImageAPI.as_view()),
    path('project/<int:pk>/invite', ProjectInvitationAPI.as_view()),
    path('project/<int:pk>/translations/<str:code>',
         TranslationsListAPI.as_view()),
    path('project/<int:pk>/integration', IntegrationAPI.as_view()),
    path('project/<int:pk>/machine-translate', MachineTranslateAPI.as_view()),
    path('project/<int:pk>/integration/verify', VerifyIntegrationAPI.as_view()),
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
    # Verification — count MUST be before <report_id> to avoid integer-match conflict
    path('project/<int:pk>/verify/count', VerificationCountAPI.as_view()),
    path('project/<int:pk>/verify', VerificationListCreateAPI.as_view()),
    path('project/<int:pk>/verify/<int:report_id>', VerificationDetailAPI.as_view()),
    path('project/<int:pk>/verify/<int:report_id>/apply', VerificationApplyAPI.as_view()),
    path('project/<int:pk>/verify/<int:report_id>/comments', VerificationCommentAPI.as_view()),
    path('project/<int:pk>', ProjectAPI.as_view()),
    path('projects/list', ProjectListAPI.as_view()),
    path('project', CreateProjectAPI.as_view()),
    # language
    path('language', LanguageAPI.as_view()),
    path('project/<int:pk>/language/<str:code>/default', SetDefaultLanguageAPI.as_view()),
    # tokens
    path('string_token', StringTokenAPI.as_view()),
    path('string_token/<int:pk>/status', StringTokenStatusAPI.as_view()),
    path('string_token/<int:pk>/tags', StringTokenTagAPI.as_view()),
    path('string_token/<int:pk>/translations',
         StringTokenTranslationsAPI.as_view()),
    path('translation', TranslationAPI.as_view()),
    path('translation/status', TranslationStatusAPI.as_view()),
    path('export', ExportAPI.as_view()),
    path('import', ImportAPI.as_view()),
    path('supported_formats', ExportFormatsAPI.as_view()),
    # plural translation
    path('plural', PluralTranslationAPI.as_view()),
    # 2FA
    path('2fa/setup', TwoFASetupAPI.as_view()),
    path('2fa/verify', TwoFAVerifyAPI.as_view()),
    path('2fa/login', TwoFALoginAPI.as_view()),
    path('2fa', TwoFADeleteAPI.as_view()),
    # passkeys
    path('passkey/register/begin', PasskeyRegisterBeginAPI.as_view()),
    path('passkey/register/complete', PasskeyRegisterCompleteAPI.as_view()),
    path('passkey/auth/begin', PasskeyAuthBeginAPI.as_view()),
    path('passkey/auth/complete', PasskeyAuthCompleteAPI.as_view()),
    path('passkey/<int:pk>', PasskeyDeleteAPI.as_view()),
    # mcp
    path('mcp', McpView.as_view()),
    # plugin
    path('plugin/export', PluginExportAPI.as_view()),
    path('plugin/pull', PullAPI.as_view()),
    path('plugin/push', PushAPI.as_view()),
    path('plugin/languages', FetchLanguagesAPI.as_view()),
]
