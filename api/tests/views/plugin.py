# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from api.models.project import ProjectAccessToken
from api.models.scope import Scope, ScopeImage
from api.models.tag import Tag
from api.tests.helpers import (
    make_access_token, make_language, make_project, make_token,
    make_translation, make_user,
)


def make_tag(name):
    return Tag.objects.create(tag=name)


def make_scope(project, name, tokens=None):
    scope = Scope.objects.create(project=project, name=name)
    if tokens:
        scope.tokens.set(tokens)
    return scope


def png_file(name='context.png'):
    # Minimal valid 1×1 white PNG
    data = (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx'
        b'\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7'
        b'\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return SimpleUploadedFile(name, data, content_type='image/png')


class TagsAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user()
        self.project = make_project(owner=self.user)
        self.access_token = make_access_token(self.project, self.user)
        self.client = APIClient()

    def _get(self, token=None):
        headers = {}
        if token is not None:
            headers['HTTP_ACCESS_TOKEN'] = token
        return self.client.get('/api/plugin/tags', **headers)

    def test_returns_empty_lists_when_no_tags_or_scopes(self):
        resp = self._get(self.access_token.token)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'tags': [], 'scopes': []})

    def test_returns_tags_for_project_tokens(self):
        tag = make_tag('ios')
        token = make_token(self.project, 'btn.ok')
        token.tags.add(tag)

        resp = self._get(self.access_token.token)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('ios', resp.json()['tags'])

    def test_does_not_return_tags_from_other_project(self):
        other_project = make_project('Other', owner=self.user)
        tag = make_tag('android')
        token = make_token(other_project, 'other.key')
        token.tags.add(tag)

        resp = self._get(self.access_token.token)
        self.assertNotIn('android', resp.json()['tags'])

    def test_returns_scopes_for_project(self):
        make_scope(self.project, 'Home')
        make_scope(self.project, 'Settings')

        resp = self._get(self.access_token.token)
        self.assertEqual(sorted(resp.json()['scopes']), ['Home', 'Settings'])

    def test_does_not_return_scopes_from_other_project(self):
        other_project = make_project('Other', owner=self.user)
        make_scope(other_project, 'Login')

        resp = self._get(self.access_token.token)
        self.assertNotIn('Login', resp.json()['scopes'])

    def test_no_token_returns_403(self):
        resp = self._get()
        self.assertEqual(resp.status_code, 403)

    def test_invalid_token_returns_403(self):
        resp = self._get('badtoken')
        self.assertEqual(resp.status_code, 403)


class PullAPIFilterTestCase(TestCase):

    def setUp(self):
        self.user = make_user()
        self.project = make_project(owner=self.user)
        self.lang = make_language(self.project, 'EN')
        self.access_token = make_access_token(self.project, self.user)
        self.client = APIClient()

        self.ios_tag = make_tag('ios')
        self.android_tag = make_tag('android')

        self.token_ios = make_token(self.project, 'btn.ios')
        self.token_ios.tags.add(self.ios_tag)
        make_translation(self.token_ios, self.lang, 'iOS button')

        self.token_android = make_token(self.project, 'btn.android')
        self.token_android.tags.add(self.android_tag)
        make_translation(self.token_android, self.lang, 'Android button')

        self.token_both = make_token(self.project, 'btn.both')
        self.token_both.tags.add(self.ios_tag)
        self.token_both.tags.add(self.android_tag)
        make_translation(self.token_both, self.lang, 'Both platforms')

        self.scope_home = make_scope(self.project, 'Home', tokens=[self.token_ios])

    def _post(self, **data):
        return self.client.post(
            '/api/plugin/pull',
            data,
            format='json',
            HTTP_ACCESS_TOKEN=self.access_token.token,
        )

    def test_no_filters_returns_all_requested_tokens(self):
        resp = self._post(
            code='en',
            tokens=['btn.ios', 'btn.android'],
        )
        self.assertEqual(resp.status_code, 200)
        keys = [t['token'] for t in resp.json()]
        self.assertIn('btn.ios', keys)
        self.assertIn('btn.android', keys)

    def test_tag_filter_returns_only_matching_tokens(self):
        resp = self._post(
            code='en',
            tokens=['btn.ios', 'btn.android', 'btn.both'],
            tags=['ios'],
        )
        self.assertEqual(resp.status_code, 200)
        keys = [t['token'] for t in resp.json()]
        self.assertIn('btn.ios', keys)
        self.assertIn('btn.both', keys)
        self.assertNotIn('btn.android', keys)

    def test_multiple_tags_are_anded(self):
        resp = self._post(
            code='en',
            tokens=['btn.ios', 'btn.android', 'btn.both'],
            tags=['ios', 'android'],
        )
        self.assertEqual(resp.status_code, 200)
        keys = [t['token'] for t in resp.json()]
        self.assertEqual(keys, ['btn.both'])

    def test_scope_filter_returns_only_tokens_in_scope(self):
        resp = self._post(
            code='en',
            tokens=['btn.ios', 'btn.android'],
            scope='Home',
        )
        self.assertEqual(resp.status_code, 200)
        keys = [t['token'] for t in resp.json()]
        self.assertIn('btn.ios', keys)
        self.assertNotIn('btn.android', keys)

    def test_scope_and_tag_filters_are_anded(self):
        # scope=Home contains btn.ios (has ios tag) but not btn.android
        resp = self._post(
            code='en',
            tokens=['btn.ios', 'btn.android'],
            scope='Home',
            tags=['android'],
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_unknown_scope_returns_empty_list(self):
        resp = self._post(
            code='en',
            tokens=['btn.ios'],
            scope='NonExistent',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_response_includes_tags_field(self):
        resp = self._post(code='en', tokens=['btn.ios'])
        self.assertEqual(resp.status_code, 200)
        item = next(t for t in resp.json() if t['token'] == 'btn.ios')
        self.assertEqual(item['tags'], ['ios'])

    def test_response_includes_scope_when_token_in_scope(self):
        resp = self._post(code='en', tokens=['btn.ios'])
        self.assertEqual(resp.status_code, 200)
        item = next(t for t in resp.json() if t['token'] == 'btn.ios')
        self.assertEqual(item['scope'], 'Home')

    def test_response_scope_is_none_when_token_not_in_any_scope(self):
        resp = self._post(code='en', tokens=['btn.android'])
        self.assertEqual(resp.status_code, 200)
        item = next(t for t in resp.json() if t['token'] == 'btn.android')
        self.assertIsNone(item['scope'])

    def test_missing_code_returns_400(self):
        resp = self._post(tokens=['btn.ios'])
        self.assertEqual(resp.status_code, 400)

    def test_missing_tokens_returns_400(self):
        resp = self._post(code='en')
        self.assertEqual(resp.status_code, 400)


class PushAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user()
        self.project = make_project(owner=self.user)
        self.lang = make_language(self.project, 'DE')
        self.write_token = make_access_token(self.project, self.user)
        self.client = APIClient()

    def _post(self, translations, code='de'):
        return self.client.post(
            '/api/plugin/push',
            {'code': code, 'translations': translations},
            format='json',
            HTTP_ACCESS_TOKEN=self.write_token.token,
        )

    def test_push_without_tags_or_scope_creates_translation(self):
        resp = self._post([{'token': 'home.title', 'translation': 'Willkommen'}])
        self.assertEqual(resp.status_code, 200)
        from api.models.string_token import StringToken
        self.assertTrue(StringToken.objects.filter(project=self.project, token='home.title').exists())

    def test_push_sets_tags_when_provided(self):
        resp = self._post([{
            'token': 'home.title',
            'translation': 'Willkommen',
            'tags': ['ios', 'onboarding'],
        }])
        self.assertEqual(resp.status_code, 200)
        from api.models.string_token import StringToken
        token = StringToken.objects.get(project=self.project, token='home.title')
        tag_names = set(token.tags.values_list('tag', flat=True))
        self.assertEqual(tag_names, {'ios', 'onboarding'})

    def test_push_replaces_existing_tags(self):
        existing = make_token(self.project, 'home.title')
        existing.tags.add(make_tag('old'))

        resp = self._post([{
            'token': 'home.title',
            'translation': 'Willkommen',
            'tags': ['ios'],
        }])
        self.assertEqual(resp.status_code, 200)
        tag_names = set(existing.tags.values_list('tag', flat=True))
        self.assertEqual(tag_names, {'ios'})

    def test_push_does_not_modify_tags_when_absent(self):
        existing = make_token(self.project, 'home.title')
        existing.tags.add(make_tag('ios'))

        resp = self._post([{'token': 'home.title', 'translation': 'Willkommen'}])
        self.assertEqual(resp.status_code, 200)
        tag_names = set(existing.tags.values_list('tag', flat=True))
        self.assertEqual(tag_names, {'ios'})

    def test_push_adds_token_to_scope_when_provided(self):
        resp = self._post([{
            'token': 'home.title',
            'translation': 'Willkommen',
            'scope': 'Home',
        }])
        self.assertEqual(resp.status_code, 200)
        scope = Scope.objects.get(project=self.project, name='Home')
        self.assertTrue(scope.tokens.filter(token='home.title').exists())

    def test_push_creates_scope_if_not_exists(self):
        self.assertFalse(Scope.objects.filter(project=self.project, name='Settings').exists())
        resp = self._post([{
            'token': 'settings.title',
            'translation': 'Einstellungen',
            'scope': 'Settings',
        }])
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Scope.objects.filter(project=self.project, name='Settings').exists())

    def test_push_does_not_modify_scope_when_absent(self):
        existing = make_token(self.project, 'home.title')
        scope = make_scope(self.project, 'Home', tokens=[existing])

        resp = self._post([{'token': 'home.title', 'translation': 'Willkommen'}])
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(scope.tokens.filter(token='home.title').exists())


class ContextAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user()
        self.project = make_project(owner=self.user)
        self.write_token = make_access_token(self.project, self.user, permission=ProjectAccessToken.AccessTokenPermissions.write)
        self.read_token = make_access_token(
            self.project, self.user,
            permission=ProjectAccessToken.AccessTokenPermissions.read,
        )
        self.client = APIClient()

    def _post(self, scope_name=None, image=None, access_token=None):
        token = access_token or self.write_token.token
        data = {}
        if scope_name is not None:
            data['scope'] = scope_name
        if image is not None:
            data['image'] = image
        return self.client.post(
            '/api/plugin/context',
            data,
            format='multipart',
            HTTP_ACCESS_TOKEN=token,
        )

    def test_creates_scope_and_image(self):
        resp = self._post(scope_name='Onboarding', image=png_file())
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Scope.objects.filter(project=self.project, name='Onboarding').exists())
        scope = Scope.objects.get(project=self.project, name='Onboarding')
        self.assertEqual(scope.images.count(), 1)

    def test_reuses_existing_scope(self):
        existing = make_scope(self.project, 'Settings')
        resp = self._post(scope_name='Settings', image=png_file())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Scope.objects.filter(project=self.project, name='Settings').count(), 1)

    def test_appends_image_to_existing_scope(self):
        scope = make_scope(self.project, 'Home')
        ScopeImage.objects.create(scope=scope, image=png_file('old.png'))
        self.assertEqual(scope.images.count(), 1)

        resp = self._post(scope_name='Home', image=png_file('new.png'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(scope.images.count(), 2)

    def test_missing_scope_returns_400(self):
        resp = self._post(image=png_file())
        self.assertEqual(resp.status_code, 400)

    def test_missing_image_returns_400(self):
        resp = self._post(scope_name='Home')
        self.assertEqual(resp.status_code, 400)

    def test_read_only_token_returns_403(self):
        resp = self._post(
            scope_name='Home',
            image=png_file(),
            access_token=self.read_token.token,
        )
        self.assertEqual(resp.status_code, 403)

    def test_no_token_returns_403(self):
        resp = self.client.post(
            '/api/plugin/context',
            {'scope': 'Home', 'image': png_file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 403)
