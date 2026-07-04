# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import json
import shutil
import tempfile
from urllib.parse import unquote

from django.test import TestCase, override_settings

from api.models.bundle import TranslationBundle, TranslationBundleMap
from api.models.live_bundle import LiveBundleSettings
from api.models.project import ProjectRole
from api.models.scope import Scope
from api.models.tag import Tag
from api.tests.helpers import (
    add_role, authed_client, make_language, make_project, make_token,
    make_translation, make_user,
)


def make_live_bundle_settings(project, token=None):
    return LiveBundleSettings.objects.create(project=project, token=token)


#
# LiveBundleSettingsAPI
#

class LiveBundleSettingsAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)

    def test_get_returns_disabled_when_never_configured(self):
        client = authed_client(self.owner)
        response = client.get(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'enabled': False, 'token': None})

    def test_get_includes_token_for_owner(self):
        make_live_bundle_settings(self.project, token='tok-owner')
        client = authed_client(self.owner)
        response = client.get(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.json()['token'], 'tok-owner')

    def test_get_includes_token_for_admin(self):
        admin = make_user('admin')
        add_role(admin, self.project, ProjectRole.Role.admin)
        make_live_bundle_settings(self.project, token='tok-admin')
        client = authed_client(admin)
        response = client.get(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.json()['token'], 'tok-admin')

    def test_get_includes_token_for_editor(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        make_live_bundle_settings(self.project, token='tok-editor')
        client = authed_client(editor)
        response = client.get(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.json()['token'], 'tok-editor')

    def test_get_excludes_token_for_translator(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        make_live_bundle_settings(self.project, token='tok-secret')
        client = authed_client(translator)
        response = client.get(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.json(), {'enabled': True, 'token': None})

    def test_get_returns_404_for_non_member(self):
        outsider = make_user('outsider')
        client = authed_client(outsider)
        response = client.get(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 404)

    def test_post_enables_and_generates_token_for_owner(self):
        client = authed_client(self.owner)
        response = client.post(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['enabled'])
        self.assertTrue(response.json()['token'])

    def test_post_enables_and_generates_token_for_admin(self):
        admin = make_user('admin')
        add_role(admin, self.project, ProjectRole.Role.admin)
        client = authed_client(admin)
        response = client.post(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['enabled'])
        self.assertTrue(response.json()['token'])

    def test_post_returns_409_when_already_enabled(self):
        client = authed_client(self.owner)
        first = client.post(f'/api/project/{self.project.id}/live-bundle')
        token = first.json()['token']

        second = client.post(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(second.status_code, 409)

        settings_obj = LiveBundleSettings.objects.get(project=self.project)
        self.assertEqual(settings_obj.token, token)

    def test_post_forbidden_for_editor_returns_404(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        client = authed_client(editor)
        response = client.post(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 404)

    def test_post_forbidden_for_translator_returns_404(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        client = authed_client(translator)
        response = client.post(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 404)

    def test_delete_disables_and_clears_token(self):
        make_live_bundle_settings(self.project, token='tok-1')
        client = authed_client(self.owner)
        response = client.delete(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'enabled': False, 'token': None})
        settings_obj = LiveBundleSettings.objects.get(project=self.project)
        self.assertIsNone(settings_obj.token)

    def test_delete_is_idempotent_when_never_enabled(self):
        client = authed_client(self.owner)
        response = client.delete(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'enabled': False, 'token': None})

    def test_delete_forbidden_for_editor_returns_404(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        make_live_bundle_settings(self.project, token='tok-1')
        client = authed_client(editor)
        response = client.delete(f'/api/project/{self.project.id}/live-bundle')
        self.assertEqual(response.status_code, 404)

    def test_disabled_token_no_longer_authenticates(self):
        client = authed_client(self.owner)
        enable_response = client.post(f'/api/project/{self.project.id}/live-bundle')
        token = enable_response.json()['token']

        client.delete(f'/api/project/{self.project.id}/live-bundle')

        version_response = self.client.get(
            '/api/live-bundle/version', HTTP_ACCESS_TOKEN=token)
        # DRF downgrades AuthenticationFailed to 403 when the authenticator has no
        # authenticate_header() — same behavior as the existing AccessTokenAuth in plugin.py.
        self.assertEqual(version_response.status_code, 403)


#
# LiveBundleRegenerateAPI
#

class LiveBundleRegenerateAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)

    def test_regenerate_returns_new_token_and_invalidates_old(self):
        client = authed_client(self.owner)
        enable_response = client.post(f'/api/project/{self.project.id}/live-bundle')
        token_a = enable_response.json()['token']

        regenerate_response = client.post(f'/api/project/{self.project.id}/live-bundle/regenerate')
        self.assertEqual(regenerate_response.status_code, 200)
        token_b = regenerate_response.json()['token']

        self.assertNotEqual(token_a, token_b)

        old_token_response = self.client.get(
            '/api/live-bundle/version', HTTP_ACCESS_TOKEN=token_a)
        # DRF downgrades AuthenticationFailed to 403 when the authenticator has no
        # authenticate_header() — same behavior as the existing AccessTokenAuth in plugin.py.
        self.assertEqual(old_token_response.status_code, 403)

        new_token_response = self.client.get(
            '/api/live-bundle/version', HTTP_ACCESS_TOKEN=token_b)
        self.assertEqual(new_token_response.status_code, 200)

    def test_regenerate_returns_409_when_not_enabled(self):
        client = authed_client(self.owner)
        response = client.post(f'/api/project/{self.project.id}/live-bundle/regenerate')
        self.assertEqual(response.status_code, 409)

    def test_regenerate_forbidden_for_editor_returns_404(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        make_live_bundle_settings(self.project, token='tok-1')
        client = authed_client(editor)
        response = client.post(f'/api/project/{self.project.id}/live-bundle/regenerate')
        self.assertEqual(response.status_code, 404)

    def test_regenerate_forbidden_for_translator_returns_404(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        make_live_bundle_settings(self.project, token='tok-1')
        client = authed_client(translator)
        response = client.post(f'/api/project/{self.project.id}/live-bundle/regenerate')
        self.assertEqual(response.status_code, 404)


#
# Public version/content API factories
#

def make_bundle(project, version_name='v1', is_active=False):
    return TranslationBundle.objects.create(
        project=project, version_name=version_name, is_active=is_active)


def make_bundle_map(bundle, token, language, value='Hello'):
    return TranslationBundleMap.objects.create(
        bundle=bundle, token=token, token_name=token.token,
        language=language, value=value)


class LiveBundlePublicAPITestCase(TestCase):

    def setUp(self):
        self.cache_dir = tempfile.mkdtemp()
        self.override = override_settings(LIVE_BUNDLE_CACHE_ROOT=self.cache_dir)
        self.override.enable()

        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.language = make_language(self.project, 'EN')
        self.settings_obj = LiveBundleSettings.objects.create(
            project=self.project, token='live-token-123')

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def get_version(self, token='live-token-123', **kwargs):
        return self.client.get('/api/live-bundle/version', HTTP_ACCESS_TOKEN=token, **kwargs)

    def get_content(self, token='live-token-123', **params):
        return self.client.get('/api/live-bundle/content', data=params, HTTP_ACCESS_TOKEN=token)

    def body(self, response):
        # FileResponse is streaming — .content isn't available, unlike a regular Response.
        return b''.join(response.streaming_content)


#
# LiveBundleVersionAPI
#

class LiveBundleVersionAPITestCase(LiveBundlePublicAPITestCase):

    def test_no_token_returns_403(self):
        response = self.client.get('/api/live-bundle/version')
        self.assertEqual(response.status_code, 403)

    def test_invalid_token_returns_403(self):
        response = self.get_version(token='not-a-real-token')
        self.assertEqual(response.status_code, 403)

    def test_no_active_bundle_returns_empty_dict(self):
        response = self.get_version()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    def test_returns_active_bundle_version_and_created_at(self):
        make_bundle(self.project, version_name='v1', is_active=True)
        response = self.get_version()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['version_name'], 'v1')
        self.assertIn('created_at', response.json())


#
# LiveBundleContentAPI
#

class LiveBundleContentAPITestCase(LiveBundlePublicAPITestCase):

    def test_no_token_returns_403(self):
        response = self.client.get('/api/live-bundle/content')
        self.assertEqual(response.status_code, 403)

    def test_invalid_token_returns_403(self):
        response = self.get_content(token='not-a-real-token')
        self.assertEqual(response.status_code, 403)

    def test_no_active_bundle_returns_404(self):
        response = self.get_content()
        self.assertEqual(response.status_code, 404)

    def test_matching_version_returns_204_with_empty_body(self):
        make_bundle(self.project, version_name='v3', is_active=True)
        response = self.get_content(version_name='v3')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')

    def test_omitted_version_returns_full_content_and_header(self):
        bundle = make_bundle(self.project, version_name='v3', is_active=True)
        token = make_token(self.project, key='greeting')
        make_bundle_map(bundle, token, self.language, value='Hello')

        response = self.get_content()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(self.body(response)) > 0)
        self.assertIn('X-Bundle-Version', response)
        self.assertEqual(unquote(response['X-Bundle-Version']), 'v3')

    def test_stale_version_returns_full_content_not_404(self):
        bundle = make_bundle(self.project, version_name='v3', is_active=True)
        token = make_token(self.project, key='greeting')
        make_bundle_map(bundle, token, self.language, value='Hello')

        response = self.get_content(version_name='v1')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(self.body(response)) > 0)
        self.assertEqual(unquote(response['X-Bundle-Version']), 'v3')

    def _json_body(self, response):
        # json export type zips one file per language; read the single EN entry.
        import io
        import zipfile
        zf = zipfile.ZipFile(io.BytesIO(self.body(response)))
        return json.loads(zf.read('/en.json'))

    def test_tag_filter_restricts_translations(self):
        bundle = make_bundle(self.project, version_name='v1', is_active=True)
        mobile_tag = Tag.objects.create(tag='mobile')
        tagged = make_token(self.project, key='mobile.greeting')
        tagged.tags.add(mobile_tag)
        untagged = make_token(self.project, key='other.greeting')
        make_bundle_map(bundle, tagged, self.language, value='Hi mobile')
        make_bundle_map(bundle, untagged, self.language, value='Hi other')

        response = self.get_content(tags='mobile')
        body = self._json_body(response)
        self.assertIn('mobile.greeting', body)
        self.assertNotIn('other.greeting', body)

    def test_multiple_tags_are_anded(self):
        bundle = make_bundle(self.project, version_name='v1', is_active=True)
        mobile_tag = Tag.objects.create(tag='mobile')
        ios_tag = Tag.objects.create(tag='ios')
        both = make_token(self.project, key='both.greeting')
        both.tags.add(mobile_tag, ios_tag)
        mobile_only = make_token(self.project, key='mobile_only.greeting')
        mobile_only.tags.add(mobile_tag)
        make_bundle_map(bundle, both, self.language, value='Hi both')
        make_bundle_map(bundle, mobile_only, self.language, value='Hi mobile only')

        response = self.get_content(tags='mobile,ios')
        body = self._json_body(response)
        self.assertIn('both.greeting', body)
        self.assertNotIn('mobile_only.greeting', body)

    def test_scope_filter_restricts_translations(self):
        bundle = make_bundle(self.project, version_name='v1', is_active=True)
        scope = Scope.objects.create(project=self.project, name='checkout')
        in_scope = make_token(self.project, key='checkout.button')
        scope.tokens.add(in_scope)
        out_of_scope = make_token(self.project, key='home.button')
        make_bundle_map(bundle, in_scope, self.language, value='Pay')
        make_bundle_map(bundle, out_of_scope, self.language, value='Home')

        response = self.get_content(scope=str(scope.id))
        body = self._json_body(response)
        self.assertIn('checkout.button', body)
        self.assertNotIn('home.button', body)

    def test_invalid_scope_returns_empty_not_error(self):
        bundle = make_bundle(self.project, version_name='v1', is_active=True)
        token = make_token(self.project, key='greeting')
        make_bundle_map(bundle, token, self.language, value='Hello')

        response = self.get_content(scope='not-a-number')
        self.assertEqual(response.status_code, 200)
        # No token matches the invalid scope, so no per-language entry is written at all
        # (not an empty en.json — an empty result set, per BA: invalid filter -> empty, not an error).
        import io
        import zipfile
        zf = zipfile.ZipFile(io.BytesIO(self.body(response)))
        self.assertEqual(zf.namelist(), [])

    def test_unsupported_type_returns_400(self):
        make_bundle(self.project, version_name='v1', is_active=True)
        response = self.get_content(type='bogus')
        self.assertEqual(response.status_code, 400)

    def test_default_type_is_json_when_omitted(self):
        bundle = make_bundle(self.project, version_name='v1', is_active=True)
        token = make_token(self.project, key='greeting')
        make_bundle_map(bundle, token, self.language, value='Hello')

        response = self.get_content()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')

    def test_response_has_no_content_disposition_header(self):
        bundle = make_bundle(self.project, version_name='v1', is_active=True)
        token = make_token(self.project, key='greeting')
        make_bundle_map(bundle, token, self.language, value='Hello')

        response = self.get_content()
        self.assertNotIn('Content-Disposition', response)

    def test_header_is_percent_encoded_for_special_characters(self):
        bundle = make_bundle(self.project, version_name='v 1', is_active=True)
        token = make_token(self.project, key='greeting')
        make_bundle_map(bundle, token, self.language, value='Hello')

        response = self.get_content()
        raw_header = response['X-Bundle-Version']
        self.assertNotIn(' ', raw_header)
        self.assertEqual(unquote(raw_header), 'v 1')

    def test_second_request_is_served_from_cache(self):
        import os

        bundle = make_bundle(self.project, version_name='v1', is_active=True)
        token = make_token(self.project, key='greeting')
        make_bundle_map(bundle, token, self.language, value='Hello')

        first = self.get_content()
        self.assertEqual(first.status_code, 200)

        cache_root = list(__import__('pathlib').Path(self.cache_dir).rglob('*'))
        cache_files = [p for p in cache_root if p.is_file()]
        self.assertEqual(len(cache_files), 1)
        mtime_after_first = os.path.getmtime(cache_files[0])

        second = self.get_content()
        self.assertEqual(second.status_code, 200)
        mtime_after_second = os.path.getmtime(cache_files[0])

        self.assertEqual(mtime_after_first, mtime_after_second)

    def test_different_bundle_versions_do_not_share_cache(self):
        bundle_a = make_bundle(self.project, version_name='v1', is_active=True)
        token = make_token(self.project, key='greeting')
        make_bundle_map(bundle_a, token, self.language, value='Hello from A')

        response_a = self.get_content()
        body_a = self._json_body(response_a)
        self.assertEqual(body_a['greeting'], 'Hello from A')

        bundle_a.is_active = False
        bundle_a.save(update_fields=['is_active'])
        bundle_b = make_bundle(self.project, version_name='v2', is_active=True)
        make_bundle_map(bundle_b, token, self.language, value='Hello from B')

        response_b = self.get_content()
        body_b = self._json_body(response_b)
        self.assertEqual(body_b['greeting'], 'Hello from B')
