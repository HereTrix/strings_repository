import secrets

from django.db import models

from api.models.project import Project


class WebhookEndpoint(models.Model):
    EVENTS = [
        'translation.created',
        'translation.updated',
        'translation.status_changed',
        'token.created',
        'token.deleted',
        'token.status_changed',
        'language.added',
        'language.removed',
        'import.completed',
        'member.invited',
        'member.role_changed',
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='webhooks')
    title = models.CharField(max_length=255)
    # Encrypted at rest — may contain secrets (e.g. Slack webhook tokens in URL path).
    url = models.BinaryField()
    # Optional auth token sent as Authorization: Bearer <token>. Encrypted at rest.
    auth_token = models.BinaryField(null=True, blank=True)
    # HMAC-SHA256 signing secret. Generated once, shown to user on creation.
    signing_secret = models.CharField(max_length=64, default=secrets.token_hex)
    # Optional Jinja-style template: "New translation: {{token}} ({{language}})"
    template = models.TextField(blank=True, default='')
    # List of subscribed event type strings from EVENTS above.
    events = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.title} ({self.project_id})'


class WebhookDeliveryLog(models.Model):
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='logs')
    event_type = models.CharField(max_length=100)
    payload_sent = models.JSONField()
    status_code = models.IntegerField(null=True, blank=True)
    delivered_at = models.DateTimeField(auto_now_add=True)
    error = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-delivered_at']
