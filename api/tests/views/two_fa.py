import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django_otp.plugins.otp_totp.models import TOTPDevice
from knox.models import AuthToken

from api.models.users import BackupCode, TwoFAVerification
from api.tests.helpers import authed_client, make_project, make_user, add_role
from api.models.project import ProjectRole


def _make_confirmed_device(user):
    return TOTPDevice.objects.create(user=user, name='default', confirmed=True)


def _make_pending_device(user):
    return TOTPDevice.objects.create(user=user, name='default', confirmed=False)


class TwoFASetupAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('setup_user')
        self.client = authed_client(self.user)

    def test_setup_creates_pending_device_and_backup_codes(self):
        resp = self.client.post('/api/2fa/setup', format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('otpauth_uri', data)
        self.assertIn('qr_code', data)
        self.assertIn('backup_codes', data)
        self.assertEqual(len(data['backup_codes']), 10)
        self.assertEqual(TOTPDevice.objects.filter(user=self.user, confirmed=False).count(), 1)
        self.assertEqual(BackupCode.objects.filter(user=self.user).count(), 10)

    def test_setup_blocked_if_device_already_confirmed(self):
        _make_confirmed_device(self.user)
        resp = self.client.post('/api/2fa/setup', format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('2FA already active', resp.json()['error'])

    def test_setup_replaces_unconfirmed_device(self):
        self.client.post('/api/2fa/setup', format='json')
        self.client.post('/api/2fa/setup', format='json')
        self.assertEqual(TOTPDevice.objects.filter(user=self.user, confirmed=False).count(), 1)


class TwoFAVerifyAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('verify_user')
        self.client = authed_client(self.user)

    def test_verify_activates_device(self):
        device = _make_pending_device(self.user)
        with patch.object(TOTPDevice, 'verify_token', return_value=True):
            resp = self.client.post('/api/2fa/verify', {'code': '123456'}, format='json')
        self.assertEqual(resp.status_code, 200)
        device.refresh_from_db()
        self.assertTrue(device.confirmed)

    def test_verify_returns_400_on_wrong_code(self):
        _make_pending_device(self.user)
        with patch.object(TOTPDevice, 'verify_token', return_value=False):
            resp = self.client.post('/api/2fa/verify', {'code': '000000'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_verify_returns_404_if_no_pending_device(self):
        resp = self.client.post('/api/2fa/verify', {'code': '123456'}, format='json')
        self.assertEqual(resp.status_code, 404)


class TwoFADeleteAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('delete_user')
        self.device = _make_confirmed_device(self.user)
        self.client = authed_client(self.user)

    def test_delete_requires_valid_code(self):
        with patch.object(TOTPDevice, 'verify_token', return_value=False):
            resp = self.client.delete('/api/2fa', {'code': '000000'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_delete_succeeds_with_totp_code(self):
        with patch.object(TOTPDevice, 'verify_token', return_value=True):
            resp = self.client.delete('/api/2fa', {'code': '123456'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())
        self.assertFalse(BackupCode.objects.filter(user=self.user).exists())

    def test_delete_succeeds_with_backup_code(self):
        codes = BackupCode.generate(self.user)
        with patch.object(TOTPDevice, 'verify_token', return_value=False):
            resp = self.client.delete('/api/2fa', {'code': codes[0]}, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_delete_clears_2fa_verifications(self):
        _, token = AuthToken.objects.create(self.user)
        token_key = AuthToken.objects.get(user=self.user).token_key
        TwoFAVerification.objects.create(token_key=token_key)
        with patch.object(TOTPDevice, 'verify_token', return_value=True):
            resp = self.client.delete('/api/2fa', {'code': '123456'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(TwoFAVerification.objects.filter(token_key=token_key).exists())


class LoginTwoFATestCase(TestCase):

    def setUp(self):
        self.user = make_user('login_user', password='testpass123')

    def test_login_returns_200_without_2fa(self):
        resp = self.client.post('/api/login', {
            'username': 'login_user',
            'password': 'testpass123',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('token', data)
        self.assertIn('user', data)

    def test_login_returns_202_with_2fa(self):
        _make_confirmed_device(self.user)
        resp = self.client.post('/api/login', {
            'username': 'login_user',
            'password': 'testpass123',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertTrue(data.get('2fa_required'))
        self.assertIn('token', data)


class TwoFALoginAPITestCase(TestCase):

    def setUp(self):
        cache.clear()
        self.user = make_user('fa_login_user')
        self.device = _make_confirmed_device(self.user)
        self.client = authed_client(self.user)

    def _get_token_key(self):
        return AuthToken.objects.filter(user=self.user).order_by('-created').first().token_key

    def test_2fa_login_success(self):
        with patch.object(TOTPDevice, 'verify_token', return_value=True):
            resp = self.client.post('/api/2fa/login', {'code': '123456'}, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('user', data)
        self.assertIn('expired', data)

    def test_2fa_login_success_with_backup_code(self):
        codes = BackupCode.generate(self.user)
        with patch.object(TOTPDevice, 'verify_token', return_value=False):
            resp = self.client.post('/api/2fa/login', {'code': codes[0]}, format='json')
        self.assertEqual(resp.status_code, 200)
        used = BackupCode.objects.filter(user=self.user, used=True)
        self.assertEqual(used.count(), 1)

    def test_2fa_login_wrong_code_returns_403(self):
        with patch.object(TOTPDevice, 'verify_token', return_value=False):
            resp = self.client.post('/api/2fa/login', {'code': '000000'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_backup_code_single_use(self):
        codes = BackupCode.generate(self.user)
        with patch.object(TOTPDevice, 'verify_token', return_value=False):
            r1 = self.client.post('/api/2fa/login', {'code': codes[0]}, format='json')
            r2 = self.client.post('/api/2fa/login', {'code': codes[0]}, format='json')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 403)


class ProjectTwoFAGateTestCase(TestCase):

    def setUp(self):
        self.user = make_user('gate_user')

    def _make_verified_client(self, user):
        """Return an authed_client with a TwoFAVerification record for the forced token."""
        client = authed_client(user)
        # force_authenticate doesn't create a Knox token; use a stub token_key
        # Inject a TwoFAVerification for a synthetic token_key matching what Knox returns
        # Since force_authenticate bypasses Knox, we fake verification by patching.
        return client

    def test_project_gate_blocks_user_without_2fa_on_required_project(self):
        project = make_project('GatedProj', owner=self.user, require_2fa=True)
        resp = authed_client(self.user).get(f'/api/project/{project.pk}')
        self.assertEqual(resp.status_code, 403)
        self.assertIn('2FA', resp.json().get('detail', ''))

    def test_project_gate_allows_user_with_verified_2fa(self):
        project = make_project('GatedProj2', owner=self.user, require_2fa=True)
        _make_confirmed_device(self.user)
        _, raw_token = AuthToken.objects.create(self.user)
        token_key = AuthToken.objects.filter(user=self.user).order_by('-created').first().token_key
        TwoFAVerification.objects.create(token_key=token_key)

        from rest_framework.test import APIClient
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Token ' + raw_token)
        resp = c.get(f'/api/project/{project.pk}')
        self.assertEqual(resp.status_code, 200)

    def test_project_gate_blocks_unverified_knox_token(self):
        project = make_project('GatedProj3', owner=self.user, require_2fa=True)
        _make_confirmed_device(self.user)
        # User has device but no TwoFAVerification
        _, raw_token = AuthToken.objects.create(self.user)
        from rest_framework.test import APIClient
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Token ' + raw_token)
        resp = c.get(f'/api/project/{project.pk}')
        self.assertEqual(resp.status_code, 403)

    def test_project_gate_not_triggered_on_non_2fa_project(self):
        project = make_project('FreeProj', owner=self.user, require_2fa=False)
        resp = authed_client(self.user).get(f'/api/project/{project.pk}')
        self.assertEqual(resp.status_code, 200)

    def test_project_gate_not_triggered_on_profile_endpoint(self):
        resp = authed_client(self.user).get('/api/profile')
        self.assertEqual(resp.status_code, 200)


class ProjectRequire2FASerializerTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('proj_owner')
        self.project = make_project('TwoFAProject', owner=self.owner)

    def test_create_project_with_require_2fa(self):
        resp = authed_client(self.owner).post('/api/project', {
            'name': 'SecureProject',
            'description': '',
            'require_2fa': True,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        from api.models.project import Project
        proj = Project.objects.get(name='SecureProject')
        self.assertTrue(proj.require_2fa)

    def test_patch_require_2fa_by_owner(self):
        resp = authed_client(self.owner).patch(
            f'/api/project/{self.project.pk}',
            {'require_2fa': True},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.project.refresh_from_db()
        self.assertTrue(self.project.require_2fa)

    def test_patch_require_2fa_by_non_owner(self):
        admin = make_user('proj_admin')
        add_role(admin, self.project, ProjectRole.Role.admin)
        resp = authed_client(admin).patch(
            f'/api/project/{self.project.pk}',
            {'require_2fa': True},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('Only project owners', str(data))
