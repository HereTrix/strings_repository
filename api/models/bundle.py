from django.db import models
from api.models.translations import Translation
from api.models.language import Language
from api.models.users import User


class TranslationBundle(models.Model):
    id = models.AutoField('id', primary_key=True)
    version_name = models.CharField(max_length=50, unique=True, null=True)
    created_at = models.DateTimeField('created_at', auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='bundles')


class TranslationBundleMap(models.Model):
    bundle = models.ForeignKey(
        TranslationBundle, on_delete=models.CASCADE, related_name='maps')
    translation = models.ForeignKey(
        Translation, on_delete=models.CASCADE, related_name='bundles')
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='bundles')
    value = models.TextField('value', blank=True)
