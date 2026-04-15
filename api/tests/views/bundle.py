import io
import zipfile

from django.test import TestCase
from rest_framework.test import APIClient

from api.models.bundle import TranslationBundle, TranslationBundleMap
from api.models.project import ProjectAccessToken, ProjectRole
from api.tests.helpers import (
    add_role, authed_client, make_language, make_project, make_token,
    make_translation, make_user,
)


#
# Factories
#

def make_bundle(project, version_name=None, is_active=False, created_by=None):
    return TranslationBundle.objects.create(
        project=project,
        version_name=version_name or 'v1',
        is_active=is_active,
        created_by=created_by,
    )


def make_bundle_map(bundle, translation, value=None):
    return TranslationBundleMap.objects.create(
        bundle=bundle,
        token=translation.token,
        token_name=translation.token.token,
        translation=translation,
        language=translation.language,
        value=value if value is not None else translation.translation,
    )


def make_access_token(user, project, permission='read'):
    return ProjectAccessToken.objects.create(
        token='testtoken12345x',
        permission=permission,
        expiration=None,
        user=user,
        project=project,
    )


#
# BundleListCreateAPI
#

class BundleListAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.client = authed_client(self.owner)

    def test_list_empty(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/bundles')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_list_returns_bundles_for_project(self):
        make_bundle(self.project, 'v1')
        make_bundle(self.project, 'v2')
        resp = self.client.get(f'/api/project/{self.project.pk}/bundles')
        self.assertEqual(resp.status_code, 200)
        names = [b['version_name'] for b in resp.json()]
        self.assertIn('v1', names)
        self.assertIn('v2', names)

    def test_list_excludes_other_project_bundles(self):
        other_owner = make_user('other')
        other_project = make_project('Other', owner=other_owner)
        make_bundle(other_project, 'v1')
        resp = self.client.get(f'/api/project/{self.project.pk}/bundles')
        self.assertEqual(resp.json(), [])

    def test_list_unauthenticated_returns_401(self):
        resp = APIClient().get(f'/api/project/{self.project.pk}/bundles')
        self.assertEqual(resp.status_code, 401)

    def test_list_forbidden_for_non_member(self):
        stranger = make_user('stranger')
        resp = authed_client(stranger).get(
            f'/api/project/{self.project.pk}/bundles')
        self.assertEqual(resp.status_code, 404)

    def test_list_allowed_for_translator(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).get(
            f'/api/project/{self.project.pk}/bundles')
        self.assertEqual(resp.status_code, 200)


class BundleCreateAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.lang = make_language(self.project, 'EN')
        self.token = make_token(self.project, 'greeting')
        make_translation(self.token, self.lang, 'Hello')
        self.client = authed_client(self.owner)

    def test_create_snapshots_all_translations(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json')
        self.assertEqual(resp.status_code, 201)
        bundle = TranslationBundle.objects.get(id=resp.json()['id'])
        self.assertEqual(bundle.maps.count(), 1)
        self.assertEqual(bundle.maps.first().value, 'Hello')

    def test_create_auto_generates_version_name(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['version_name'], 'v1')

    def test_create_sequential_version_names(self):
        self.client.post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json')
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json')
        self.assertEqual(resp.json()['version_name'], 'v2')

    def test_create_uses_provided_version_name(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles',
            {'version_name': 'release-1.0'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['version_name'], 'release-1.0')

    def test_create_reserved_name_active_returns_400(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles',
            {'version_name': 'active'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_reserved_name_live_returns_400(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles',
            {'version_name': 'live'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_reserved_name_case_insensitive(self):
        for name in ('Active', 'ACTIVE', 'Live', 'LIVE'):
            with self.subTest(name=name):
                resp = self.client.post(
                    f'/api/project/{self.project.pk}/bundles',
                    {'version_name': name},
                    format='json',
                )
                self.assertEqual(resp.status_code, 400)

    def test_create_duplicate_version_name_returns_409(self):
        make_bundle(self.project, 'v1')
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles',
            {'version_name': 'v1'},
            format='json',
        )
        self.assertEqual(resp.status_code, 409)

    def test_create_empty_project_creates_empty_bundle(self):
        empty_project = make_project('Empty', owner=self.owner)
        resp = self.client.post(
            f'/api/project/{empty_project.pk}/bundles', {}, format='json')
        self.assertEqual(resp.status_code, 201)
        bundle = TranslationBundle.objects.get(id=resp.json()['id'])
        self.assertEqual(bundle.maps.count(), 0)

    def test_create_captures_multiple_languages(self):
        lang_de = make_language(self.project, 'DE')
        make_translation(self.token, lang_de, 'Hallo')
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json')
        self.assertEqual(resp.status_code, 201)
        bundle = TranslationBundle.objects.get(id=resp.json()['id'])
        self.assertEqual(bundle.maps.count(), 2)

    def test_create_bundle_is_inactive_by_default(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json')
        self.assertFalse(resp.json()['is_active'])

    def test_create_forbidden_for_translator(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json'
        )
        self.assertEqual(resp.status_code, 404)

    def test_create_allowed_for_editor(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json'
        )
        self.assertEqual(resp.status_code, 201)

    def test_create_snapshots_value_not_live(self):
        """Bundle must capture the value at creation time, not reflect later edits."""
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles', {}, format='json')
        self.assertEqual(resp.status_code, 201)
        bundle_id = resp.json()['id']

        # Edit live translation after bundle creation
        translation = self.token.translation.get(language=self.lang)
        translation.translation = 'Hi'
        translation.save()

        bundle = TranslationBundle.objects.get(id=bundle_id)
        self.assertEqual(bundle.maps.first().value, 'Hello')


#
# BundleDetailAPI
#

class BundleDetailAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.bundle = make_bundle(self.project, 'v1')
        self.client = authed_client(self.owner)

    def test_get_returns_bundle(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/bundles/{self.bundle.pk}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['version_name'], 'v1')

    def test_get_not_found_for_wrong_project(self):
        other_owner = make_user('other')
        other_project = make_project('Other', owner=other_owner)
        resp = self.client.get(
            f'/api/project/{other_project.pk}/bundles/{self.bundle.pk}')
        self.assertEqual(resp.status_code, 404)

    def test_delete_removes_bundle(self):
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/bundles/{self.bundle.pk}')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(TranslationBundle.objects.filter(
            pk=self.bundle.pk).exists())

    def test_delete_active_bundle_returns_409(self):
        self.bundle.is_active = True
        self.bundle.save()
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/bundles/{self.bundle.pk}')
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(TranslationBundle.objects.filter(
            pk=self.bundle.pk).exists())

    def test_delete_forbidden_for_editor(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).delete(
            f'/api/project/{self.project.pk}/bundles/{self.bundle.pk}'
        )
        self.assertEqual(resp.status_code, 404)


#
# BundleActivateAPI / BundleDeactivateAPI
#

class BundleActivateAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.client = authed_client(self.owner)

    def test_activate_sets_is_active(self):
        bundle = make_bundle(self.project, 'v1')
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles/{bundle.pk}/activate'
        )
        self.assertEqual(resp.status_code, 200)
        bundle.refresh_from_db()
        self.assertTrue(bundle.is_active)

    def test_activate_deactivates_previous_active(self):
        old = make_bundle(self.project, 'v1', is_active=True)
        new = make_bundle(self.project, 'v2')
        self.client.post(
            f'/api/project/{self.project.pk}/bundles/{new.pk}/activate')
        old.refresh_from_db()
        new.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertTrue(new.is_active)

    def test_only_one_active_bundle_per_project(self):
        b1 = make_bundle(self.project, 'v1')
        b2 = make_bundle(self.project, 'v2')
        b3 = make_bundle(self.project, 'v3')
        self.client.post(
            f'/api/project/{self.project.pk}/bundles/{b1.pk}/activate')
        self.client.post(
            f'/api/project/{self.project.pk}/bundles/{b2.pk}/activate')
        self.client.post(
            f'/api/project/{self.project.pk}/bundles/{b3.pk}/activate')
        active_count = TranslationBundle.objects.filter(
            project=self.project, is_active=True).count()
        self.assertEqual(active_count, 1)

    def test_activate_does_not_affect_other_projects(self):
        other_owner = make_user('other')
        other_project = make_project('Other', owner=other_owner)
        other_bundle = make_bundle(other_project, 'v1', is_active=True)

        my_bundle = make_bundle(self.project, 'v1')
        self.client.post(
            f'/api/project/{self.project.pk}/bundles/{my_bundle.pk}/activate')

        other_bundle.refresh_from_db()
        self.assertTrue(other_bundle.is_active)

    def test_activate_forbidden_for_editor(self):
        bundle = make_bundle(self.project, 'v1')
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).post(
            f'/api/project/{self.project.pk}/bundles/{bundle.pk}/activate'
        )
        self.assertEqual(resp.status_code, 404)

    def test_activate_not_found_returns_404(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles/9999/activate')
        self.assertEqual(resp.status_code, 404)


class BundleDeactivateAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.client = authed_client(self.owner)

    def test_deactivate_clears_is_active(self):
        bundle = make_bundle(self.project, 'v1', is_active=True)
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles/{bundle.pk}/deactivate'
        )
        self.assertEqual(resp.status_code, 200)
        bundle.refresh_from_db()
        self.assertFalse(bundle.is_active)

    def test_deactivate_already_inactive_is_idempotent(self):
        bundle = make_bundle(self.project, 'v1', is_active=False)
        resp = self.client.post(
            f'/api/project/{self.project.pk}/bundles/{bundle.pk}/deactivate'
        )
        self.assertEqual(resp.status_code, 200)
        bundle.refresh_from_db()
        self.assertFalse(bundle.is_active)

    def test_deactivate_forbidden_for_editor(self):
        bundle = make_bundle(self.project, 'v1', is_active=True)
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).post(
            f'/api/project/{self.project.pk}/bundles/{bundle.pk}/deactivate'
        )
        self.assertEqual(resp.status_code, 404)


#
# BundleCompareAPI
#

class BundleCompareAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.lang = make_language(self.project, 'EN')
        self.client = authed_client(self.owner)

    def _url(self, **params):
        from urllib.parse import urlencode
        qs = urlencode(params)
        return f'/api/project/{self.project.pk}/bundles/compare?{qs}'

    def test_missing_params_returns_400(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/bundles/compare')
        self.assertEqual(resp.status_code, 400)

    def test_missing_to_returns_400(self):
        bundle = make_bundle(self.project, 'v1')
        resp = self.client.get(self._url(**{'from': bundle.pk}))
        self.assertEqual(resp.status_code, 400)

    def test_invalid_from_id_returns_404(self):
        bundle = make_bundle(self.project, 'v1')
        resp = self.client.get(self._url(**{'from': 9999, 'to': bundle.pk}))
        self.assertEqual(resp.status_code, 404)

    def test_compare_identical_bundles_all_unchanged(self):
        token = make_token(self.project, 'hello')
        translation = make_translation(token, self.lang, 'Hello')

        b1 = make_bundle(self.project, 'v1')
        make_bundle_map(b1, translation, 'Hello')
        b2 = make_bundle(self.project, 'v2')
        make_bundle_map(b2, translation, 'Hello')

        resp = self.client.get(self._url(**{'from': b1.pk, 'to': b2.pk}))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['added'], [])
        self.assertEqual(data['removed'], [])
        self.assertEqual(data['changed'], [])
        self.assertEqual(data['unchanged_count'], 1)

    def test_compare_detects_changed_value(self):
        token = make_token(self.project, 'hello')
        translation = make_translation(token, self.lang, 'Hello')

        b1 = make_bundle(self.project, 'v1')
        make_bundle_map(b1, translation, 'Hello')
        b2 = make_bundle(self.project, 'v2')
        make_bundle_map(b2, translation, 'Hi')

        resp = self.client.get(self._url(**{'from': b1.pk, 'to': b2.pk}))
        data = resp.json()
        self.assertEqual(len(data['changed']), 1)
        self.assertEqual(data['changed'][0]['from'], 'Hello')
        self.assertEqual(data['changed'][0]['to'], 'Hi')
        self.assertEqual(data['changed'][0]['token'], 'hello')

    def test_compare_detects_added_key(self):
        t1 = make_token(self.project, 'existing')
        t2 = make_token(self.project, 'new_key')
        tr1 = make_translation(t1, self.lang, 'Existing')
        tr2 = make_translation(t2, self.lang, 'New')

        b1 = make_bundle(self.project, 'v1')
        make_bundle_map(b1, tr1, 'Existing')
        b2 = make_bundle(self.project, 'v2')
        make_bundle_map(b2, tr1, 'Existing')
        make_bundle_map(b2, tr2, 'New')

        resp = self.client.get(self._url(**{'from': b1.pk, 'to': b2.pk}))
        data = resp.json()
        self.assertEqual(len(data['added']), 1)
        self.assertEqual(data['added'][0]['token'], 'new_key')

    def test_compare_detects_removed_key(self):
        t1 = make_token(self.project, 'existing')
        t2 = make_token(self.project, 'old_key')
        tr1 = make_translation(t1, self.lang, 'Existing')
        tr2 = make_translation(t2, self.lang, 'Old')

        b1 = make_bundle(self.project, 'v1')
        make_bundle_map(b1, tr1, 'Existing')
        make_bundle_map(b1, tr2, 'Old')
        b2 = make_bundle(self.project, 'v2')
        make_bundle_map(b2, tr1, 'Existing')

        resp = self.client.get(self._url(**{'from': b1.pk, 'to': b2.pk}))
        data = resp.json()
        self.assertEqual(len(data['removed']), 1)
        self.assertEqual(data['removed'][0]['token'], 'old_key')

    def test_compare_bundle_to_live(self):
        token = make_token(self.project, 'greeting')
        translation = make_translation(token, self.lang, 'Hello')

        bundle = make_bundle(self.project, 'v1')
        make_bundle_map(bundle, translation, 'Hello')

        # Edit live value after bundle
        translation.translation = 'Hi'
        translation.save()

        resp = self.client.get(self._url(**{'from': bundle.pk, 'to': 'live'}))
        data = resp.json()
        self.assertEqual(len(data['changed']), 1)
        self.assertEqual(data['changed'][0]['from'], 'Hello')
        self.assertEqual(data['changed'][0]['to'], 'Hi')

    def test_compare_forbidden_for_non_member(self):
        b1 = make_bundle(self.project, 'v1')
        b2 = make_bundle(self.project, 'v2')
        stranger = make_user('stranger')
        resp = authed_client(stranger).get(
            self._url(**{'from': b1.pk, 'to': b2.pk}))
        self.assertEqual(resp.status_code, 404)


#
# BundleCompareExportAPI
#

class BundleCompareExportAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.lang = make_language(self.project, 'EN')
        self.token_a = make_token(self.project, 'greeting')
        self.token_b = make_token(self.project, 'farewell')
        self.tr_a = make_translation(self.token_a, self.lang, 'Hello')
        self.tr_b = make_translation(self.token_b, self.lang, 'Goodbye')
        self.bundle = make_bundle(self.project, 'v1')
        make_bundle_map(self.bundle, self.tr_a, 'Hello')
        make_bundle_map(self.bundle, self.tr_b, 'Goodbye')
        self.client = authed_client(self.owner)

    def _url(self, **params):
        from urllib.parse import urlencode
        qs = urlencode(params)
        return f'/api/project/{self.project.pk}/bundles/compare/export?{qs}'

    def _xlsx_text(self, content):
        """Extract all text from xlsx shared strings XML."""
        import zipfile, re
        zf = zipfile.ZipFile(io.BytesIO(content))
        try:
            xml = zf.read('xl/sharedStrings.xml').decode()
        except KeyError:
            return ''
        return re.sub(r'<[^>]+>', ' ', xml)

    def test_missing_params_returns_400(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/bundles/compare/export')
        self.assertEqual(resp.status_code, 400)

    def test_invalid_mode_returns_400(self):
        resp = self.client.get(self._url(**{
            'from': self.bundle.pk, 'to': 'live', 'mode': 'invalid'}))
        self.assertEqual(resp.status_code, 400)

    def test_invalid_bundle_returns_404(self):
        resp = self.client.get(self._url(**{
            'from': 9999, 'to': 'live', 'mode': 'diff'}))
        self.assertEqual(resp.status_code, 404)

    def test_forbidden_for_non_member(self):
        stranger = make_user('stranger')
        resp = authed_client(stranger).get(self._url(**{
            'from': self.bundle.pk, 'to': 'live', 'mode': 'diff'}))
        self.assertEqual(resp.status_code, 404)

    def test_export_diff_returns_xlsx(self):
        resp = self.client.get(self._url(**{
            'from': self.bundle.pk, 'to': 'live', 'mode': 'diff'}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.get('Content-Type'),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('compare_diff.xlsx', resp.get('Content-Disposition', ''))

    def test_export_changes_returns_xlsx(self):
        resp = self.client.get(self._url(**{
            'from': self.bundle.pk, 'to': 'live', 'mode': 'changes'}))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('compare_changes.xlsx', resp.get('Content-Disposition', ''))

    def test_export_diff_default_mode(self):
        """Omitting mode defaults to diff."""
        resp = self.client.get(self._url(**{
            'from': self.bundle.pk, 'to': 'live'}))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('compare_diff.xlsx', resp.get('Content-Disposition', ''))

    def test_export_diff_contains_changed_token(self):
        self.tr_a.translation = 'Hi'
        self.tr_a.save()

        resp = self.client.get(self._url(**{
            'from': self.bundle.pk, 'to': 'live', 'mode': 'diff'}))
        self.assertEqual(resp.status_code, 200)
        text = self._xlsx_text(resp.content)
        self.assertIn('greeting', text)
        self.assertIn('Hello', text)
        self.assertIn('Hi', text)

    def test_export_changes_contains_changed_token(self):
        self.tr_a.translation = 'Hi'
        self.tr_a.save()

        resp = self.client.get(self._url(**{
            'from': self.bundle.pk, 'to': 'live', 'mode': 'changes'}))
        self.assertEqual(resp.status_code, 200)
        text = self._xlsx_text(resp.content)
        self.assertIn('greeting', text)
        self.assertIn('Hi', text)

    def test_export_diff_contains_new_token(self):
        new_tok = make_token(self.project, 'new_key')
        make_translation(new_tok, self.lang, 'New value')

        resp = self.client.get(self._url(**{
            'from': self.bundle.pk, 'to': 'live', 'mode': 'diff'}))
        text = self._xlsx_text(resp.content)
        self.assertIn('new_key', text)

    def test_export_bundle_to_bundle(self):
        b2 = make_bundle(self.project, 'v2')
        make_bundle_map(b2, self.tr_a, 'Hi')

        resp = self.client.get(self._url(**{
            'from': self.bundle.pk, 'to': b2.pk, 'mode': 'diff'}))
        self.assertEqual(resp.status_code, 200)
        text = self._xlsx_text(resp.content)
        self.assertIn('greeting', text)


#
# BundleExportAPI
#

class BundleExportAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.lang = make_language(self.project, 'EN')
        self.str_token = make_token(self.project, 'greeting')
        self.translation = make_translation(self.str_token, self.lang, 'Hello')
        self.bundle = make_bundle(self.project, 'v1')
        make_bundle_map(self.bundle, self.translation, 'Hello')
        self.client = authed_client(self.owner)

    def _url(self, bundle_id=None, **params):
        from urllib.parse import urlencode
        bid = bundle_id or self.bundle.pk
        qs = urlencode(params)
        return f'/api/project/{self.project.pk}/bundles/{bid}/export?{qs}'

    def test_export_returns_zip(self):
        resp = self.client.get(self._url(type='strings'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('zip', resp.get('Content-Type', ''))

    def test_export_contains_snapshotted_value(self):
        # Change live translation — export must still reflect bundle snapshot
        self.translation.translation = 'Changed'
        self.translation.save()

        resp = self.client.get(self._url(type='strings'))
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        content = zf.read(zf.namelist()[0]).decode()
        self.assertIn('Hello', content)
        self.assertNotIn('Changed', content)

    def test_export_filters_by_codes(self):
        lang_de = make_language(self.project, 'DE')
        tr_de = make_translation(self.str_token, lang_de, 'Hallo')
        make_bundle_map(self.bundle, tr_de, 'Hallo')

        resp = self.client.get(self._url(type='strings', codes='EN'))
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = [n.lower() for n in zf.namelist()]
        self.assertTrue(any('en' in n for n in names))
        self.assertFalse(any('de' in n for n in names))

    def test_export_invalid_type_returns_400(self):
        resp = self.client.get(self._url(type='nosuchformat'))
        self.assertEqual(resp.status_code, 400)

    def test_export_bundle_not_found_returns_404(self):
        resp = self.client.get(self._url(bundle_id=9999, type='strings'))
        self.assertEqual(resp.status_code, 404)

    def test_export_forbidden_for_non_member(self):
        stranger = make_user('stranger')
        resp = authed_client(stranger).get(self._url(type='strings'))
        self.assertEqual(resp.status_code, 404)


#
# PluginExportAPI — bundle_version modes
#

class PluginExportBundleTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.lang = make_language(self.project, 'EN')
        self.str_token = make_token(self.project, 'greeting')
        self.translation = make_translation(self.str_token, self.lang, 'Hello')
        self.access_token = make_access_token(self.owner, self.project)
        self.client = APIClient()

    def _post(self, **data):
        return self.client.post(
            '/api/plugin/export',
            data,
            HTTP_ACCESS_TOKEN=self.access_token.token,
        )

    def test_default_serves_live_translations(self):
        """Omitting bundle_version returns live data, even when an active bundle exists."""
        bundle = make_bundle(self.project, 'v1', is_active=True)
        make_bundle_map(bundle, self.translation, 'Bundled')

        resp = self._post(type='strings', codes='EN')
        self.assertEqual(resp.status_code, 200)
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        content = zf.read(zf.namelist()[0]).decode()
        self.assertIn('Hello', content)
        self.assertNotIn('Bundled', content)

    def test_explicit_live_serves_live_translations(self):
        bundle = make_bundle(self.project, 'v1', is_active=True)
        make_bundle_map(bundle, self.translation, 'Bundled')

        resp = self._post(type='strings', codes='EN', bundle_version='live')
        self.assertEqual(resp.status_code, 200)
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        content = zf.read(zf.namelist()[0]).decode()
        self.assertIn('Hello', content)
        self.assertNotIn('Bundled', content)

    def test_active_serves_active_bundle(self):
        bundle = make_bundle(self.project, 'v1', is_active=True)
        make_bundle_map(bundle, self.translation, 'Bundled')

        resp = self._post(type='strings', codes='EN', bundle_version='active')
        self.assertEqual(resp.status_code, 200)
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        content = zf.read(zf.namelist()[0]).decode()
        self.assertIn('Bundled', content)

    def test_active_with_no_active_bundle_returns_404(self):
        resp = self._post(type='strings', codes='EN', bundle_version='active')
        self.assertEqual(resp.status_code, 404)
        self.assertIn('No active bundle', resp.json()['error'])

    def test_specific_version_served_when_requested(self):
        bundle_v1 = make_bundle(self.project, 'v1')
        make_bundle_map(bundle_v1, self.translation, 'V1 value')
        bundle_v2 = make_bundle(self.project, 'v2', is_active=True)
        make_bundle_map(bundle_v2, self.translation, 'V2 value')

        resp = self._post(type='strings', codes='EN', bundle_version='v1')
        self.assertEqual(resp.status_code, 200)
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        content = zf.read(zf.namelist()[0]).decode()
        self.assertIn('V1 value', content)
        self.assertNotIn('V2 value', content)

    def test_specific_version_not_found_returns_404(self):
        resp = self._post(type='strings', codes='EN', bundle_version='v99')
        self.assertEqual(resp.status_code, 404)

    def test_no_access_token_returns_403(self):
        resp = self.client.post('/api/plugin/export', {'type': 'strings'})
        self.assertEqual(resp.status_code, 403)
