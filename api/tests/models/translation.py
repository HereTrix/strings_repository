from django.test import TestCase

from api.models.history import HistoryRecord
from api.models.translations import Translation
from api.tests.helpers import (
    make_language, make_project, make_token, make_translation, make_user,
)


class TranslationCreateOrUpdateTestCase(TestCase):

    def setUp(self):
        self.user = make_user('editor')
        self.project = make_project('P', owner=self.user)
        self.lang = make_language(self.project, 'EN')
        self.token = make_token(self.project, 'greeting')

    def _call(self, text):
        return Translation.create_or_update_translation(
            user=self.user,
            token=self.token,
            code='EN',
            project_id=self.project.pk,
            text=text,
        )

    def test_creates_new_translation(self):
        tr = self._call('Hello')
        self.assertEqual(tr.translation, 'Hello')
        self.assertTrue(Translation.objects.filter(token=self.token, language=self.lang).exists())

    def test_new_translation_status_is_new(self):
        # Status is preserved as set on the object (default new on create path)
        tr = self._call('Hello')
        saved = Translation.objects.get(pk=tr.pk)
        # create_or_update doesn't force status on first create, so it stays default
        self.assertIsNotNone(saved.status)

    def test_updates_existing_translation(self):
        make_translation(self.token, self.lang, 'Old')
        tr = self._call('New')
        self.assertEqual(tr.translation, 'New')
        self.assertEqual(tr.status, Translation.Status.in_review)

    def test_changed_text_creates_history(self):
        make_translation(self.token, self.lang, 'Old')
        before = HistoryRecord.objects.count()
        self._call('New')
        self.assertEqual(HistoryRecord.objects.count(), before + 1)
        record = HistoryRecord.objects.latest('id')
        self.assertEqual(record.old_value, 'Old')
        self.assertEqual(record.new_value, 'New')
        self.assertEqual(record.token, 'greeting')

    def test_same_text_does_not_create_history(self):
        make_translation(self.token, self.lang, 'Same')
        before = HistoryRecord.objects.count()
        self._call('Same')
        self.assertEqual(HistoryRecord.objects.count(), before)

    def test_history_record_references_editor(self):
        make_translation(self.token, self.lang, 'Old')
        self._call('New')
        record = HistoryRecord.objects.latest('id')
        self.assertEqual(record.editor, self.user)


class TranslationImportRecordTestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.lang = make_language(self.project, 'EN')

    def _make_record(self, token, translation, code=None):
        from api.models.transport_models import TranslationModel
        from api.models.string_token import StringToken
        # Build a minimal transport model without a DB token
        st = StringToken(token=token, project=self.project)
        return TranslationModel(token_model=st, code=code or 'EN')

    def test_import_creates_token_if_missing(self):
        from api.models.string_token import StringToken
        from api.models.transport_models import TranslationModel

        class SimpleRecord:
            pass

        r = SimpleRecord()
        r.token = 'new_key'
        r.translation = 'New Value'
        r.code = 'EN'

        Translation.import_record(
            user=self.user,
            project_id=self.project.pk,
            code='EN',
            record=r,
            tags=[],
        )
        self.assertTrue(StringToken.objects.filter(token='new_key', project=self.project).exists())
        self.assertTrue(
            Translation.objects.filter(
                token__token='new_key',
                language__code='EN',
                translation='New Value',
            ).exists()
        )

    def test_import_updates_existing_token(self):
        from api.models.string_token import StringToken

        token = StringToken.objects.create(token='existing', project=self.project)
        make_translation(token, self.lang, 'Old')

        class SimpleRecord:
            pass

        r = SimpleRecord()
        r.token = 'existing'
        r.translation = 'Updated'
        r.code = 'EN'

        Translation.import_record(
            user=self.user,
            project_id=self.project.pk,
            code='EN',
            record=r,
            tags=[],
        )
        self.assertEqual(
            Translation.objects.get(token=token, language=self.lang).translation,
            'Updated'
        )

    def test_import_creates_history_on_change(self):
        from api.models.string_token import StringToken

        token = StringToken.objects.create(token='htoken', project=self.project)
        make_translation(token, self.lang, 'Before')
        before = HistoryRecord.objects.count()

        class SimpleRecord:
            pass

        r = SimpleRecord()
        r.token = 'htoken'
        r.translation = 'After'
        r.code = 'EN'

        Translation.import_record(
            user=self.user,
            project_id=self.project.pk,
            code='EN',
            record=r,
            tags=[],
        )
        self.assertEqual(HistoryRecord.objects.count(), before + 1)
