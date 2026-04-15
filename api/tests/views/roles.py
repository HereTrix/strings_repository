import json
from django.test import TestCase

from api.models.project import Invitation, ProjectAccessToken, ProjectRole
from api.tests.helpers import (
    add_role, authed_client, make_project, make_user,
)


class RolesAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)

    def test_owner_sees_all_roles(self):
        resp = authed_client(self.owner).get(f'/api/project/{self.project.pk}/roles')
        self.assertEqual(resp.status_code, 200)
        roles = json.loads(resp.content)
        self.assertIn('owner', roles)
        self.assertIn('admin', roles)
        self.assertIn('editor', roles)
        self.assertIn('translator', roles)

    def test_admin_sees_common_roles(self):
        admin = make_user('admin')
        add_role(admin, self.project, ProjectRole.Role.admin)
        resp = authed_client(admin).get(f'/api/project/{self.project.pk}/roles')
        self.assertEqual(resp.status_code, 200)
        roles = json.loads(resp.content)
        self.assertNotIn('owner', roles)
        self.assertIn('editor', roles)

    def test_editor_sees_editor_and_translator(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).get(f'/api/project/{self.project.pk}/roles')
        self.assertEqual(resp.status_code, 200)
        roles = json.loads(resp.content)
        self.assertIn('editor', roles)
        self.assertIn('translator', roles)
        self.assertNotIn('owner', roles)
        self.assertNotIn('admin', roles)

    def test_translator_gets_403(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).get(f'/api/project/{self.project.pk}/roles')
        self.assertEqual(resp.status_code, 403)

    def test_non_member_gets_403(self):
        other = make_user('other')
        resp = authed_client(other).get(f'/api/project/{self.project.pk}/roles')
        self.assertEqual(resp.status_code, 403)


class ProjectParticipantsAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.editor = make_user('editor')
        add_role(self.editor, self.project, ProjectRole.Role.editor)

    def test_owner_can_list_participants(self):
        resp = authed_client(self.owner).get(f'/api/project/{self.project.pk}/participants')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        ids = [p['id'] for p in data]
        self.assertIn(self.owner.pk, ids)
        self.assertIn(self.editor.pk, ids)

    def test_editor_cannot_list_participants(self):
        resp = authed_client(self.editor).get(f'/api/project/{self.project.pk}/participants')
        self.assertEqual(resp.status_code, 403)

    def test_owner_can_change_participant_role(self):
        resp = authed_client(self.owner).post(
            f'/api/project/{self.project.pk}/participants',
            {'user_id': self.editor.pk, 'role': 'translator'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            ProjectRole.objects.get(user=self.editor, project=self.project).role,
            'translator'
        )

    def test_changing_nonexistent_user_returns_404(self):
        resp = authed_client(self.owner).post(
            f'/api/project/{self.project.pk}/participants',
            {'user_id': 99999, 'role': 'translator'},
            format='json'
        )
        self.assertEqual(resp.status_code, 404)

    def test_owner_can_remove_participant(self):
        resp = authed_client(self.owner).delete(
            f'/api/project/{self.project.pk}/participants',
            {'user_id': self.editor.pk},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ProjectRole.objects.filter(user=self.editor, project=self.project).exists())

    def test_removing_nonexistent_user_returns_404(self):
        resp = authed_client(self.owner).delete(
            f'/api/project/{self.project.pk}/participants',
            {'user_id': 99999},
            format='json'
        )
        self.assertEqual(resp.status_code, 404)


class ProjectInvitationAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)

    def test_owner_can_generate_invitation(self):
        resp = authed_client(self.owner).post(
            f'/api/project/{self.project.pk}/invite',
            {'role': 'editor'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('code', data)
        self.assertTrue(Invitation.objects.filter(code=data['code'], project=self.project).exists())

    def test_editor_can_invite_translator(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).post(
            f'/api/project/{self.project.pk}/invite',
            {'role': 'translator'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('code', resp.json())

    def test_editor_cannot_invite_admin(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).post(
            f'/api/project/{self.project.pk}/invite',
            {'role': 'admin'},
            format='json'
        )
        self.assertEqual(resp.status_code, 400)

    def test_translator_cannot_generate_invitation(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).post(
            f'/api/project/{self.project.pk}/invite',
            {'role': 'translator'},
            format='json'
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_cannot_invite_owner(self):
        admin = make_user('admin')
        add_role(admin, self.project, ProjectRole.Role.admin)
        resp = authed_client(admin).post(
            f'/api/project/{self.project.pk}/invite',
            {'role': 'owner'},
            format='json'
        )
        self.assertEqual(resp.status_code, 400)


class ProjectAccessTokenAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.client = authed_client(self.owner)

    def test_create_access_token(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/access_token',
            {'permission': 'read'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('token', data)
        self.assertTrue(ProjectAccessToken.objects.filter(token=data['token'], project=self.project).exists())

    def test_missing_permission_returns_400(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/access_token',
            {},
            format='json'
        )
        self.assertEqual(resp.status_code, 400)

    def test_list_access_tokens(self):
        self.client.post(
            f'/api/project/{self.project.pk}/access_token',
            {'permission': 'write'},
            format='json'
        )
        resp = self.client.get(f'/api/project/{self.project.pk}/access_token')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(len(data), 1)

    def test_delete_access_token(self):
        create_resp = self.client.post(
            f'/api/project/{self.project.pk}/access_token',
            {'permission': 'read'},
            format='json'
        )
        token_value = json.loads(create_resp.content)['token']
        del_resp = self.client.delete(
            f'/api/project/{self.project.pk}/access_token',
            {'token': token_value},
            format='json'
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(ProjectAccessToken.objects.filter(token=token_value).exists())

    def test_delete_missing_token_returns_400(self):
        resp = self.client.delete(
            f'/api/project/{self.project.pk}/access_token',
            {'token': 'doesnotexist'},
            format='json'
        )
        self.assertEqual(resp.status_code, 400)
