# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from api.models.project import Invitation, ProjectRole
from api.tests.helpers import authed_client, make_project, make_user


def make_invitation(project, role=ProjectRole.Role.translator):
    import secrets
    return Invitation.objects.create(
        project=project,
        code=secrets.token_hex(8),
        role=role,
    )


class SignInAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('signin_user', password='pass1234X')
        self.client = APIClient()

    def test_valid_credentials_returns_token(self):
        resp = self.client.post('/api/login', {'username': 'signin_user', 'password': 'pass1234X'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.json())
        self.assertIn('user', resp.json())

    def test_invalid_credentials_returns_401(self):
        resp = self.client.post('/api/login', {'username': 'signin_user', 'password': 'wrongpass'}, format='json')
        self.assertEqual(resp.status_code, 401)
        self.assertIn('error', resp.json())


class ChangePasswordAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('pw_user', password='OldPass1')
        self.client = authed_client(self.user)

    def test_change_password_success(self):
        resp = self.client.post('/api/password', {
            'password': 'OldPass1',
            'new_password': 'NewPass99',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass99'))

    def test_wrong_old_password_returns_400(self):
        resp = self.client.post('/api/password', {
            'password': 'WrongPass1',
            'new_password': 'NewPass99',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_weak_new_password_returns_400(self):
        resp = self.client.post('/api/password', {
            'password': 'OldPass1',
            'new_password': 'weak',
        }, format='json')
        self.assertEqual(resp.status_code, 400)


class ProfileAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('profile_user')
        self.user.first_name = 'Alice'
        self.user.last_name = 'Smith'
        self.user.email = 'alice@example.com'
        self.user.save()
        self.client = authed_client(self.user)

    def test_get_returns_user_data(self):
        resp = self.client.get('/api/profile')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['email'], 'alice@example.com')
        self.assertIn('has_2fa', data)
        self.assertIn('passkeys', data)

    def test_post_updates_profile(self):
        resp = self.client.post('/api/profile', {
            'email': 'new@example.com',
            'first_name': 'Bob',
            'last_name': 'Jones',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertEqual(self.user.first_name, 'Bob')


class ActivateProjectAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('activate_owner')
        self.project = make_project(owner=self.owner)
        self.user = make_user('activate_user')
        self.client = authed_client(self.user)

    def test_valid_code_adds_role(self):
        invite = make_invitation(self.project)
        resp = self.client.post('/api/activate', {'code': invite.code}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            ProjectRole.objects.filter(user=self.user, project=self.project).exists()
        )

    def test_wrong_code_returns_404(self):
        resp = self.client.post('/api/activate', {'code': 'no-such-code'}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_already_in_project_returns_error(self):
        invite = make_invitation(self.project)
        ProjectRole.objects.create(user=self.user, project=self.project, role=ProjectRole.Role.translator)
        resp = self.client.post('/api/activate', {'code': invite.code}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('error', resp.json())


class SignUpAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('signup_owner')
        self.project = make_project(owner=self.owner)
        self.client = APIClient()

    def _signup(self, **kwargs):
        data = {
            'login': 'newuser',
            'password': 'Secure12',
            'name': 'New',
            'surname': 'User',
        }
        data.update(kwargs)
        return self.client.post('/api/signup', data, format='json')

    def test_signup_with_valid_invite(self):
        invite = make_invitation(self.project)
        resp = self._signup(code=invite.code)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_missing_login_returns_400(self):
        invite = make_invitation(self.project)
        resp = self.client.post('/api/signup', {
            'password': 'Secure12', 'code': invite.code, 'name': 'A', 'surname': 'B',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_weak_password_returns_400(self):
        invite = make_invitation(self.project)
        resp = self._signup(code=invite.code, password='weak')
        self.assertEqual(resp.status_code, 400)

    def test_missing_code_returns_400(self):
        resp = self._signup()
        self.assertEqual(resp.status_code, 400)

    def test_missing_name_returns_400(self):
        invite = make_invitation(self.project)
        resp = self.client.post('/api/signup', {
            'login': 'u', 'password': 'Secure12', 'code': invite.code, 'surname': 'B',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_missing_surname_returns_400(self):
        invite = make_invitation(self.project)
        resp = self.client.post('/api/signup', {
            'login': 'u', 'password': 'Secure12', 'code': invite.code, 'name': 'A',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_invalid_code_returns_200_with_error(self):
        resp = self._signup(code='invalid-code')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('error', resp.json())

    def test_existing_username_returns_200_with_error(self):
        invite = make_invitation(self.project)
        make_user('newuser')
        resp = self._signup(code=invite.code)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('error', resp.json())
