from django.db import models

from api.models.project import Project


class Language(models.Model):
    id = models.AutoField('id', primary_key=True)
    code = models.CharField(max_length=2)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='languages')
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ['code', 'project']

    def __str__(self):
        return self.code
