from django.db import models
from api.models.translations import Translation
from api.models.language import Language
from api.models.project import Project
from api.models.string_token import StringToken
from api.models.users import User


class TranslationBundle(models.Model):
    id = models.AutoField('id', primary_key=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='bundles', null=True)
    version_name = models.CharField(max_length=50, null=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField('created_at', auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='bundles')

    class Meta:
        unique_together = [['project', 'version_name']]


class TranslationBundleMap(models.Model):
    bundle = models.ForeignKey(
        TranslationBundle, on_delete=models.CASCADE, related_name='maps')
    token = models.ForeignKey(
        StringToken, on_delete=models.SET_NULL, related_name='bundle_maps', null=True)
    token_name = models.CharField(max_length=200, default='')
    translation = models.ForeignKey(
        Translation, on_delete=models.SET_NULL, related_name='bundles', null=True, blank=True)
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='bundles')
    value = models.TextField('value', blank=True)
