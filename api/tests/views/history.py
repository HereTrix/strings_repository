import json
from django.test import TestCase

from api.models.history import HistoryRecord
from api.tests.helpers import (
    authed_client, make_language, make_project, make_token,
    make_translation, make_user,
)


def _make_history(project, user, token='k', status=HistoryRecord.Status.updated):
    record = HistoryRecord.objects.create(
        project=project,
        token=token,
        status=status,
        language='EN',
        editor=user,
        old_value='old',
        new_value='new',
    )
    return record


class ProjectHistoryAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        _make_history(self.project, self.owner)
        self.client = authed_client(self.owner)

    def test_returns_history_with_from_filter(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/history',
            {'from': '2000-01-01'}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_returns_history_with_to_filter(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/history',
            {'to': '2099-12-31'}
        )
        self.assertEqual(resp.status_code, 200)

    def test_missing_time_range_returns_400(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/history')
        self.assertEqual(resp.status_code, 400)

    def test_non_member_sees_no_records(self):
        other = make_user('other')
        resp = authed_client(other).get(
            f'/api/project/{self.project.pk}/history',
            {'from': '2000-01-01'}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(len(data), 0)

    def test_from_and_to_filter_combined(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/history',
            {'from': '2000-01-01', 'to': '2099-12-31'}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertGreaterEqual(len(data), 1)


class ProjectHistoryExportAPITestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        _make_history(self.project, self.owner)
        self.client = authed_client(self.owner)

    def test_export_returns_xlsx_content_type(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/history/export',
            {'from': '2000-01-01'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            'spreadsheetml',
            resp.get('Content-Type', '')
        )

    def test_missing_time_range_returns_400(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/history/export')
        self.assertEqual(resp.status_code, 400)
