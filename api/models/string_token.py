from api.models.project import Project
from api.models.tag import Tag


from django.db import models


class StringToken(models.Model):
    class Status(models.TextChoices):
        active = 'active'
        deprecated = 'deprecated'

    id = models.AutoField('id', primary_key=True)
    token = models.CharField('Token', max_length=200)
    comment = models.TextField('Comment', blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tokens')
    tags = models.ManyToManyField(Tag, related_name="tokens")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.active)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        unique_together = ['token', 'project']

    def __str__(self):
        return f"{self.id} {self.token}"
