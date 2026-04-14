from django.contrib import admin

from api.models.bundle import TranslationBundle
from api.models.language import Language
from api.models.string_token import StringToken
from api.models.tag import Tag
from api.models.translations import Translation

from api.models.project import Project, ProjectRole

admin.site.register(ProjectRole)
admin.site.register(Project)
admin.site.register(StringToken)
admin.site.register(Tag)
admin.site.register(Language)
admin.site.register(Translation)
admin.site.register(TranslationBundle)
