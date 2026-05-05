from django.contrib import admin

from django_otp.plugins.otp_totp.models import TOTPDevice
from api.models.bundle import TranslationBundle
from api.models.language import Language
from api.models.project import Project, ProjectRole, ProjectAIProvider
from api.models.string_token import StringToken
from api.models.tag import Tag
from api.models.translations import Translation
from api.models.users import TwoFAVerification, BackupCode, PasskeyCredential, PasskeyChallenge
from api.models.verification import VerificationReport, VerificationComment

admin.site.register(ProjectRole)
admin.site.register(Project)
admin.site.register(StringToken)
admin.site.register(Tag)
admin.site.register(Language)
admin.site.register(Translation)
admin.site.register(TranslationBundle)
admin.site.register(TOTPDevice)


@admin.register(TwoFAVerification)
class TwoFAVerificationAdmin(admin.ModelAdmin):
    list_display = ['token_key', 'created_at']
    search_fields = ['token_key']


@admin.register(BackupCode)
class BackupCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'used', 'created_at']
    list_filter = ['used']
    search_fields = ['user__username', 'user__email']


@admin.register(ProjectAIProvider)
class ProjectAIProviderAdmin(admin.ModelAdmin):
    list_display = ['project', 'provider_type', 'model_name', 'created_at']
    search_fields = ['project__name']


@admin.register(VerificationReport)
class VerificationReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'mode', 'status', 'target_language', 'created_at']
    list_filter = ['status', 'mode']
    search_fields = ['project__name']


@admin.register(PasskeyCredential)
class PasskeyCredentialAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'sign_count', 'created_at']
    search_fields = ['user__username', 'name']
    list_filter = ['created_at']
    readonly_fields = ['credential_id', 'public_key', 'sign_count', 'created_at']


@admin.register(PasskeyChallenge)
class PasskeyChallengeAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['challenge', 'created_at']


@admin.register(VerificationComment)
class VerificationCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'token_key', 'author', 'created_at']
    search_fields = ['token_key', 'text']
