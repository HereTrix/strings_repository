# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from django.test import TestCase
from rest_framework.test import APIClient

from api.models.project import ProjectRole
from api.models.scope import Scope, ScopeImage
from api.tests.helpers import add_role, authed_client, make_project, make_token, make_user
from api.tests.views.plugin import make_scope, png_file


class ScopeListCreateAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('scope_owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)

    def test_list_returns_empty_when_no_scopes(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/scopes')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_list_returns_existing_scopes(self):
        make_scope(self.project, 'Home')
        make_scope(self.project, 'Settings')
        resp = self.client.get(f'/api/project/{self.project.pk}/scopes')
        self.assertEqual(resp.status_code, 200)
        names = [s['name'] for s in resp.json()]
        self.assertIn('Home', names)
        self.assertIn('Settings', names)

    def test_list_not_found_for_other_project(self):
        other = make_project('Other')
        resp = self.client.get(f'/api/project/{other.pk}/scopes')
        self.assertEqual(resp.status_code, 404)

    def test_create_scope(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/scopes',
            {'name': 'Onboarding', 'description': 'Intro screens'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['name'], 'Onboarding')
        self.assertTrue(Scope.objects.filter(project=self.project, name='Onboarding').exists())

    def test_create_scope_missing_name_returns_400(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/scopes',
            {'description': 'No name'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_scope_not_allowed_for_non_admin(self):
        member = make_user('scope_member')
        add_role(member, self.project, ProjectRole.Role.translator)
        client = authed_client(member)
        resp = client.post(
            f'/api/project/{self.project.pk}/scopes',
            {'name': 'New'},
            format='json',
        )
        self.assertEqual(resp.status_code, 404)


class ScopeDetailAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('scope_detail_owner')
        self.project = make_project(owner=self.owner)
        self.scope = make_scope(self.project, 'Home')
        self.client = authed_client(self.owner)

    def test_patch_updates_description(self):
        resp = self.client.patch(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}',
            {'description': 'Updated desc'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.scope.refresh_from_db()
        self.assertEqual(self.scope.description, 'Updated desc')

    def test_patch_scope_not_found_returns_404(self):
        resp = self.client.patch(
            f'/api/project/{self.project.pk}/scopes/99999',
            {'description': 'x'},
            format='json',
        )
        self.assertEqual(resp.status_code, 404)

    def test_patch_not_allowed_for_non_admin(self):
        member = make_user('scope_detail_member')
        add_role(member, self.project, ProjectRole.Role.translator)
        resp = authed_client(member).patch(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}',
            {'description': 'x'},
            format='json',
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_removes_scope(self):
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}',
        )
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Scope.objects.filter(pk=self.scope.pk).exists())

    def test_delete_not_found_project_returns_404(self):
        other = make_project('Other')
        resp = self.client.delete(f'/api/project/{other.pk}/scopes/{self.scope.pk}')
        self.assertEqual(resp.status_code, 404)


class ScopeTokensAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('scope_tokens_owner')
        self.project = make_project(owner=self.owner)
        self.scope = make_scope(self.project, 'Home')
        self.token1 = make_token(self.project, 'home.title')
        self.token2 = make_token(self.project, 'home.subtitle')
        self.client = authed_client(self.owner)

    def test_add_tokens_to_scope(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}/tokens',
            {'token_ids': [self.token1.pk, self.token2.pk]},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.token1, self.scope.tokens.all())
        self.assertIn(self.token2, self.scope.tokens.all())

    def test_add_tokens_not_found_project_returns_404(self):
        other = make_project('Other')
        resp = self.client.post(
            f'/api/project/{other.pk}/scopes/{self.scope.pk}/tokens',
            {'token_ids': [self.token1.pk]},
            format='json',
        )
        self.assertEqual(resp.status_code, 404)

    def test_add_tokens_scope_not_found_returns_404(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/scopes/99999/tokens',
            {'token_ids': [self.token1.pk]},
            format='json',
        )
        self.assertEqual(resp.status_code, 404)

    def test_remove_tokens_from_scope(self):
        self.scope.tokens.add(self.token1)
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}/tokens',
            {'token_ids': [self.token1.pk]},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(self.token1, self.scope.tokens.all())

    def test_remove_tokens_scope_not_found_returns_404(self):
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/scopes/99999/tokens',
            {'token_ids': [self.token1.pk]},
            format='json',
        )
        self.assertEqual(resp.status_code, 404)


class ScopeImageAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('scope_image_owner')
        self.project = make_project(owner=self.owner)
        self.scope = make_scope(self.project, 'Home')
        self.client = authed_client(self.owner)

    def test_upload_image_returns_201(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}/image',
            {'image': png_file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(ScopeImage.objects.filter(scope=self.scope).count(), 1)

    def test_upload_image_missing_image_returns_400(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}/image',
            {},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 400)

    def test_upload_image_scope_not_found_returns_404(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/scopes/99999/image',
            {'image': png_file()},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_image(self):
        img = ScopeImage.objects.create(scope=self.scope, image=png_file())
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}/image',
            {'image_id': img.pk},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ScopeImage.objects.filter(pk=img.pk).exists())

    def test_delete_image_missing_image_id_returns_400(self):
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}/image',
            {},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 400)

    def test_delete_image_not_found_returns_404(self):
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/scopes/{self.scope.pk}/image',
            {'image_id': 99999},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_image_scope_not_found_returns_404(self):
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/scopes/99999/image',
            {'image_id': 1},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 404)
