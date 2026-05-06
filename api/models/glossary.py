from django.db import models
from django.contrib.auth.models import User

from api.models.project import Project


class GlossaryTerm(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='glossary_terms'
    )
    term = models.CharField(max_length=500)
    definition = models.TextField(blank=True, default='')
    case_sensitive = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='created_glossary_terms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['term']

    def __str__(self):
        return f'{self.term} ({self.project.name})'


class GlossaryTranslation(models.Model):
    term = models.ForeignKey(
        GlossaryTerm, on_delete=models.CASCADE, related_name='translations'
    )
    language_code = models.CharField(max_length=10)
    preferred_translation = models.CharField(max_length=500)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='updated_glossary_translations'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['language_code']
        unique_together = ['term', 'language_code']

    def __str__(self):
        return f'{self.term.term} [{self.language_code}] → {self.preferred_translation}'


class GlossaryExtractionJob(models.Model):
    class Status(models.TextChoices):
        pending = 'pending'
        running = 'running'
        complete = 'complete'
        failed = 'failed'

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='glossary_extraction_jobs'
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.pending
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='glossary_extraction_jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    suggestions = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Extraction job {self.pk} — {self.project.name} ({self.status})'
