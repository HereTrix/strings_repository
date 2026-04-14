from django.db import models
from api.models.project import Project
from api.models.users import User


class HistoryRecord(models.Model):
    class Status(models.TextChoices):
        created = 'created'
        updated = 'updated'
        deleted = 'deleted'

    id = models.AutoField('id', primary_key=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, related_name='history')
    token = models.CharField(max_length=200)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.updated)
    language = models.CharField(max_length=2)
    updated_at = models.DateTimeField('updated_at', auto_now_add=True)
    editor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='history')
    old_value = models.TextField('old_value', blank=True)
    new_value = models.TextField('new_value', blank=True)
