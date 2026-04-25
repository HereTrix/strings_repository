from django.db import models
from api.models.project import Project
from api.models.string_token import StringToken


class Scope(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='scopes')
    tokens = models.ManyToManyField(StringToken, related_name='scopes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['name', 'project']

    def __str__(self):
        return f"{self.id} {self.name}"


class ScopeImage(models.Model):
    scope = models.ForeignKey(Scope, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='scope_images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image {self.id} for scope {self.scope_id}"
