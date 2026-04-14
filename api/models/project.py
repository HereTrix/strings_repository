from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    id = models.AutoField('id', primary_key=True)
    name = models.CharField("Name", max_length=200, unique=True)
    description = models.TextField("Description", blank=True)

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
    code = models.CharField(max_length=16, unique=True)
    role = models.CharField(max_length=10, choices=ProjectRole.Role.choices)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='invitations')


class ProjectAccessToken(models.Model):
    class AccessTokenPermissions(models.TextChoices):
        write = 'write'
        read = 'read'

    token = models.CharField(max_length=16, unique=True)
    permission = models.CharField(
        max_length=10, choices=AccessTokenPermissions.choices)
    expiration = models.DateTimeField(null=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='access')
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='access_tokens')
