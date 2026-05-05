from django.db import models
from django.contrib.auth.models import User

from api.models.project import Project
from api.models.scope import Scope


class VerificationReport(models.Model):
    class Status(models.TextChoices):
        pending = 'pending'
        running = 'running'
        complete = 'complete'
        failed = 'failed'

    class Mode(models.TextChoices):
        source_quality = 'source_quality', 'Source Quality'
        translation_accuracy = 'translation_accuracy', 'Translation Accuracy'

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='verification_reports'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='verification_reports'
    )
    mode = models.CharField(max_length=30, choices=Mode.choices)
    target_language = models.CharField(max_length=10, blank=True, default='')
    scope = models.ForeignKey(
        Scope, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verification_reports'
    )
    tags = models.JSONField(default=list)
    new_only = models.BooleanField(default=False)
    checks = models.JSONField(default=list)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.pending
    )
    is_readonly = models.BooleanField(default=False)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    string_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Report {self.pk} — {self.project.name} ({self.status})'


class VerificationComment(models.Model):
    report = models.ForeignKey(
        VerificationReport, on_delete=models.CASCADE, related_name='comments'
    )
    token_id = models.IntegerField()
    token_key = models.CharField(max_length=200)
    plural_form = models.CharField(max_length=10, blank=True)
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='verification_comments'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on report {self.report_id}'
