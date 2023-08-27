from django.contrib import admin
from .models import *

admin.site.register(ProjectRole)
admin.site.register(Project)
admin.site.register(StringToken)
admin.site.register(Tag)
admin.site.register(Language)
admin.site.register(Translation)