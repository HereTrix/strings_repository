from django.contrib import admin

from django_otp.plugins.otp_totp.models import TOTPDevice
from api.models.bundle import TranslationBundle
from api.models.language import Language
from api.models.project import Project, ProjectRole
from api.models.string_token import StringToken
from api.models.tag import Tag
from api.models.translations import Translation
from api.models.users import TwoFAVerification, BackupCode

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
