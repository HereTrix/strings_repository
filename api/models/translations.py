from datetime import datetime

from django.db import models

from api.models.string_token import StringToken
from api.models.project import Project
from api.models.language import Language
from api.models.history import HistoryRecord
from api.models.users import User


class Translation(models.Model):
    class Status(models.TextChoices):
        new = 'new'
        in_review = 'in_review'
        approved = 'approved'
        deprecated = 'deprecated'

    id = models.AutoField('id', primary_key=True)
    translation = models.TextField('translation', blank=True)
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='translation')
    token = models.ForeignKey(
        StringToken, on_delete=models.CASCADE, related_name='translation')
    updated_at = models.DateTimeField('updated_at', auto_now_add=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.new)

    class Meta:
        unique_together = ['token', 'language']

    def __str__(self):
        return f"{self.id} {self.translation}"

    def create_or_update_translation(user: User, token: StringToken, code: str, project_id, text: str) -> Translation:
        old_value = ''
        try:
            translation = Translation.objects.get(
                token=token,
                token__project__pk=project_id,
                language__code=code.upper(),
            )

            old_value = translation.translation
            translation.status = Translation.Status.in_review

        except Translation.DoesNotExist:
            languages = Language.objects.filter(
                project__pk=project_id,
                code=code.upper()
            )
            language = languages.first()
            if language is None:
                raise Language.DoesNotExist(f'Language {code} not found')

            translation = Translation()
            translation.language = language
            translation.token = token

        translation.translation = text
        translation.updated_at = datetime.now()
        translation.save()

        # Add history
        if old_value != text:
            record = HistoryRecord()
            record.project = token.project
            record.token = token.token
            record.status = HistoryRecord.Status.updated
            record.old_value = old_value
            record.new_value = text
            record.updated_at = datetime.now()
            record.editor = user
            record.language = translation.language.code
            record.save()
        return translation

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
            token.save()

        if tags:
            for tag in tags:
                token.tags.add(tag.id)

        token.save()
        old_value = ''
        if code:  # No code means no translation
            language = Language.objects.get(
                code=code.upper(),
                project=project
            )
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

            if record.translation:
                translation.translation = record.translation
            translation.updated_at = datetime.now()
            translation.save()
        # Add history
        if not old_value == record.translation:
            history = HistoryRecord()
            history.project = token.project
            history.token = token.token
            history.status = HistoryRecord.Status.updated
            history.old_value = old_value
            history.new_value = record.translation
            history.updated_at = datetime.now()
            history.editor = user
            if code:
                history.language = code
            history.save()


class PluralTranslation(models.Model):
    class PluralForm(models.TextChoices):
        zero = 'zero'
        one = 'one'
        two = 'two'
        few = 'few'
        many = 'many'
        other = 'other'

        @staticmethod
        def PLURAL_FORM_ORDER():
            return ['zero', 'one', 'two', 'few', 'many', 'other']

    translation = models.ForeignKey(
        Translation, on_delete=models.CASCADE, related_name='plural_forms'
    )
    plural_form = models.CharField(max_length=5, choices=PluralForm.choices)
    value = models.TextField()

    class Meta:
        unique_together = ['translation', 'plural_form']
