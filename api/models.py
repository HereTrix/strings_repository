from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, related_name='profile', unique=True, on_delete=models.CASCADE)


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

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=10, choices=Role.choices)

    def __str__(self):
        return self.user.username + ' ' + str(self.role)

    change_language_roles = [Role.owner, Role.admin]
    change_token_roles = [Role.owner, Role.admin, Role.editor]
    change_participants_roles = [Role.owner, Role.admin]


class Language(models.Model):
    id = models.AutoField('id', primary_key=True)
    code = models.CharField(max_length=2)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='languages')

    class Meta:
        unique_together = ['code', 'project']

    def __str__(self):
        return self.code


class Tag(models.Model):
    id = models.AutoField('id', primary_key=True)
    tag = models.CharField("Tag", max_length=40)

    def __str__(self) -> str:
        return self.tag


class StringToken(models.Model):
    id = models.AutoField('id', primary_key=True)
    token = models.CharField('Token', max_length=200, unique=True)
    comment = models.TextField('Comment', blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tokens')
    tags = models.ManyToManyField(Tag, related_name="tokens")

    class Meta:
        unique_together = ['token', 'project']

    def __str__(self):
        return self.token


class Translation(models.Model):
    id = models.AutoField('id', primary_key=True)
    translation = models.TextField("translation", blank=True)
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='translation')
    token = models.ForeignKey(
        StringToken, on_delete=models.CASCADE, related_name='translation')

    class Meta:
        unique_together = ['token', 'language']

    def __str__(self):
        return f"{self.id} {self.translation}"
