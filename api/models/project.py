from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    id = models.AutoField('id', primary_key=True)
    name = models.CharField("Name", max_length=200, unique=True)
    description = models.TextField("Description", blank=True)
    require_2fa = models.BooleanField(default=False)
    verification_cap = models.PositiveSmallIntegerField(default=10)

    def __str__(self):
        return self.name


class ProjectRole(models.Model):
    class Role(models.TextChoices):
        owner = 'owner'
        admin = 'admin'
        editor = 'editor'
        translator = 'translator'

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='roles')
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=10, choices=Role.choices)

    def __str__(self):
        return self.user.username + ' ' + str(self.role)

    change_language_roles = [Role.owner, Role.admin]
    change_token_roles = [Role.owner, Role.admin, Role.editor]
    change_participants_roles = [Role.owner, Role.admin]
    common_roles = [Role.admin, Role.editor, Role.translator]
    translator_roles = [Role.editor, Role.translator]


class Invitation(models.Model):
    id = models.AutoField('id', primary_key=True)
    code = models.CharField(max_length=64, unique=True)
    role = models.CharField(max_length=10, choices=ProjectRole.Role.choices)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='invitations')


class ProjectAccessToken(models.Model):
    class AccessTokenPermissions(models.TextChoices):
        write = 'write'
        read = 'read'

    token = models.CharField(max_length=64, unique=True)
    permission = models.CharField(
        max_length=10, choices=AccessTokenPermissions.choices)
    expiration = models.DateTimeField(null=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='access')
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='access_tokens')


class TranslationIntegration(models.Model):
    PROVIDER_DEEPL = 'deepl'
    PROVIDER_GOOGLE = 'google'
    PROVIDER_AI = 'ai'
    PROVIDER_CHOICES = [
        (PROVIDER_DEEPL, 'DeepL'),
        (PROVIDER_GOOGLE, 'Google Translate'),
        (PROVIDER_AI, 'Generic AI'),
    ]

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name='integration')
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    api_key = models.BinaryField()
    endpoint_url = models.CharField(max_length=500, blank=True, default='')
    payload_template = models.TextField(blank=True, default='')
    response_path = models.CharField(max_length=200, blank=True, default='')
    auth_header = models.CharField(max_length=100, blank=True, default='Authorization')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['provider', 'project']


class ProjectAIProvider(models.Model):
    class ProviderType(models.TextChoices):
        openai = 'openai', 'OpenAI-compatible'
        anthropic = 'anthropic', 'Anthropic-compatible'

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name='ai_provider'
    )
    provider_type = models.CharField(max_length=20, choices=ProviderType.choices)
    endpoint_url = models.CharField(max_length=500, blank=True, default='')
    api_key = models.BinaryField()
    model_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.project.name} ({self.provider_type})'

