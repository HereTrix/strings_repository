import json
from django.test import TestCase

from api.models.project import Project, ProjectRole
from api.tests.helpers import (
    add_role, authed_client, make_language, make_project, make_user,
)


class CreateProjectTestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.client = authed_client(self.user)

    def test_creates_project_and_owner_role(self):
        resp = self.client.post('/api/project', {'name': 'NewProj', 'description': 'desc'}, format='json')
        self.assertEqual(resp.status_code, 201)
        project = Project.objects.get(name='NewProj')
        self.assertTrue(ProjectRole.objects.filter(user=self.user, project=project, role=ProjectRole.Role.owner).exists())

    def test_duplicate_name_returns_400(self):
        make_project('Dup')
        resp = self.client.post('/api/project', {'name': 'Dup', 'description': ''}, format='json')
        self.assertEqual(resp.status_code, 400)


class DeleteProjectTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)

    def test_owner_can_delete(self):
        resp = authed_client(self.owner).delete(f'/api/project/{self.project.pk}')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_editor_cannot_delete(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).delete(f'/api/project/{self.project.pk}')
        self.assertEqual(resp.status_code, 204)
        # Project still exists because editor has no change_participants_roles
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())


class ProjectListTestCase(TestCase):

    def setUp(self):
        self.user = make_user('user')
        self.other = make_user('other')
        self.mine = make_project('Mine', owner=self.user)
        self.theirs = make_project('Theirs', owner=self.other)

    def test_returns_only_own_projects(self):
        resp = authed_client(self.user).get('/api/projects/list')
        self.assertEqual(resp.status_code, 200)
        names = [p['name'] for p in json.loads(resp.content)]
        self.assertIn('Mine', names)
        self.assertNotIn('Theirs', names)


class AvailableLanguagesTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        make_language(self.project, 'EN')

    def test_excludes_already_added_language(self):
        resp = authed_client(self.owner).get(f'/api/project/{self.project.pk}/availableLanguages')
        self.assertEqual(resp.status_code, 200)
        codes = [lang['code'] for lang in json.loads(resp.content)]
        self.assertNotIn('EN', codes)
