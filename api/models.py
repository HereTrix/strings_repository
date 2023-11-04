from datetime import datetime
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
        return f"{self.id} {self.token}"


class Translation(models.Model):
    id = models.AutoField('id', primary_key=True)
    translation = models.TextField('translation', blank=True)
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='translation')
    token = models.ForeignKey(
        StringToken, on_delete=models.CASCADE, related_name='translation')
    updated_at = models.DateTimeField('updated_at', auto_now_add=True)

    class Meta:
        unique_together = ['token', 'language']

    def __str__(self):
        return f"{self.id} {self.translation}"

    def create_translation(user: User, token: StringToken, code: str, project_id, text: str):
        old_value = ''
        try:
            translation = Translation.objects.get(
                token=token,
                language__code=code.upper(),
            )

            old_value = translation.translation

        except Translation.DoesNotExist:
            languages = Language.objects.filter(
                project__pk=project_id,
                code=code.upper()
            )
            language = languages.first()

            translation = Translation()
            translation.language = language
            translation.token = token

        translation.translation = text
        translation.updated_at = datetime.now()
        translation.save()

        # Add history
        if old_value != text:
            record = HistoryRecord()
            record.token = token
            record.old_value = old_value
            record.new_value = text
            record.updated_at = datetime.now()
            record.editor = user
            record.language = translation.language.code
            record.save()

    def import_record(user, project_id, code, record, tags):
        project = Project.objects.get(
            id=project_id
        )

        try:
            token = StringToken.objects.get(
                token=record.token,
                project=project
            )
        except StringToken.DoesNotExist:
            token = StringToken()
            token.token = record.token
            token.project = project

        if tags:
            token.tags.set(tags)

        token.save()

        language = Language.objects.get(
            code=code,
            project=project
        )

        old_value = ''
        try:
            translation = Translation.objects.get(
                language=language,
                token=token
            )
            old_value = translation.translation
        except Translation.DoesNotExist:
            translation = Translation()
            translation.language = language
            translation.token = token

        translation.translation = record.translation
        translation.updated_at = datetime.now()
        translation.save()
        # Add history
        if not old_value == record.translation:
            history = HistoryRecord()
            history.token = token
            history.old_value = old_value
            history.new_value = record.translation
            history.updated_at = datetime.now()
            history.editor = user
            history.language = code
            history.save()


class HistoryRecord(models.Model):
    id = models.AutoField('id', primary_key=True)
    token = models.ForeignKey(
        StringToken, on_delete=models.CASCADE, related_name='history')
    language = models.CharField(max_length=2)
    updated_at = models.DateTimeField('updated_at', auto_now_add=True)
    editor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='history')
    old_value = models.TextField('old_value', blank=True)
    new_value = models.TextField('new_value', blank=True)


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
