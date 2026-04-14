import io
import json
from unittest.mock import MagicMock, call, patch

from django.test import TestCase

from api.crypto import decrypt, encrypt
from api.models.project import ProjectRole
from api.models.webhook import WebhookDeliveryLog, WebhookEndpoint
from api.tests.helpers import (
    add_role, authed_client, make_language, make_project, make_token,
    make_translation, make_user,
)


def make_webhook(project, title='My Hook', url='https://example.com/hook', events=None):
    endpoint = WebhookEndpoint.objects.create(
        project=project,
        title=title,
        url=encrypt(url),
        events=events or ['translation.created'],
        is_active=True,
    )
    return endpoint


class WebhookListAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.client = authed_client(self.user)

    def test_list_empty(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/webhooks')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_list_returns_webhooks(self):
        make_webhook(self.project, title='Hook A')
        make_webhook(self.project, title='Hook B')
        resp = self.client.get(f'/api/project/{self.project.pk}/webhooks')
        self.assertEqual(resp.status_code, 200)
        titles = [w['title'] for w in resp.json()]
        self.assertIn('Hook A', titles)
        self.assertIn('Hook B', titles)

    def test_list_decrypts_url(self):
        make_webhook(self.project, url='https://hooks.slack.com/secret/path')
        resp = self.client.get(f'/api/project/{self.project.pk}/webhooks')
        self.assertEqual(resp.json()[0]['url'], 'https://hooks.slack.com/secret/path')

    def test_list_masks_signing_secret(self):
        make_webhook(self.project)
        resp = self.client.get(f'/api/project/{self.project.pk}/webhooks')
        self.assertEqual(resp.json()[0]['signing_secret'], '••••••••')

    def test_list_forbidden_for_editor(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).get(f'/api/project/{self.project.pk}/webhooks')
        self.assertEqual(resp.status_code, 404)

    def test_list_forbidden_for_translator(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).get(f'/api/project/{self.project.pk}/webhooks')
        self.assertEqual(resp.status_code, 404)

    def test_list_unauthenticated_returns_401(self):
        from rest_framework.test import APIClient
        resp = APIClient().get(f'/api/project/{self.project.pk}/webhooks')
        self.assertEqual(resp.status_code, 401)

    def test_create_webhook(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/webhooks', {
            'title': 'Slack',
            'url': 'https://hooks.slack.com/T/B/xxx',
            'events': ['translation.created', 'token.deleted'],
            'template': 'New: {{token}}',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['title'], 'Slack')
        self.assertEqual(data['url'], 'https://hooks.slack.com/T/B/xxx')
        self.assertIn('translation.created', data['events'])
        # Signing secret is revealed on creation.
        self.assertNotEqual(data['signing_secret'], '••••••••')
        self.assertTrue(len(data['signing_secret']) > 8)

    def test_create_encrypts_url_at_rest(self):
        self.client.post(f'/api/project/{self.project.pk}/webhooks', {
            'title': 'Hook',
            'url': 'https://secret.example.com/endpoint',
            'events': [],
        }, format='json')
        endpoint = WebhookEndpoint.objects.get(project=self.project, title='Hook')
        # Stored bytes must not equal the plaintext URL.
        self.assertNotEqual(bytes(endpoint.url), b'https://secret.example.com/endpoint')
        # But decryption must round-trip correctly.
        self.assertEqual(decrypt(endpoint.url), 'https://secret.example.com/endpoint')

    def test_create_with_auth_token_encrypts_it(self):
        self.client.post(f'/api/project/{self.project.pk}/webhooks', {
            'title': 'Hook',
            'url': 'https://example.com',
            'events': [],
            'auth_token': 'supersecrettoken',
        }, format='json')
        endpoint = WebhookEndpoint.objects.get(project=self.project, title='Hook')
        self.assertTrue(endpoint.auth_token)
        self.assertEqual(decrypt(endpoint.auth_token), 'supersecrettoken')

    def test_create_without_url_returns_400(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/webhooks', {
            'title': 'Hook',
            'events': [],
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_create_without_title_returns_400(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/webhooks', {
            'url': 'https://example.com',
            'events': [],
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_create_with_unknown_event_returns_400(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/webhooks', {
            'title': 'Hook',
            'url': 'https://example.com',
            'events': ['not.a.real.event'],
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_create_forbidden_for_editor(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).post(f'/api/project/{self.project.pk}/webhooks', {
            'title': 'Hook', 'url': 'https://example.com', 'events': [],
        }, format='json')
        self.assertEqual(resp.status_code, 404)


class WebhookDetailAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.endpoint = make_webhook(self.project)
        self.client = authed_client(self.user)
        self.url = f'/api/project/{self.project.pk}/webhooks/{self.endpoint.pk}'

    def test_get_returns_webhook(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['title'], self.endpoint.title)

    def test_get_nonexistent_returns_404(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/webhooks/99999')
        self.assertEqual(resp.status_code, 404)

    def test_update_title(self):
        resp = self.client.put(self.url, {'title': 'Updated'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.endpoint.refresh_from_db()
        self.assertEqual(self.endpoint.title, 'Updated')

    def test_update_url_re_encrypts(self):
        resp = self.client.put(self.url, {'url': 'https://new-url.example.com'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.endpoint.refresh_from_db()
        self.assertEqual(decrypt(self.endpoint.url), 'https://new-url.example.com')

    def test_update_events(self):
        resp = self.client.put(self.url, {
            'events': ['token.created', 'language.added'],
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.endpoint.refresh_from_db()
        self.assertEqual(self.endpoint.events, ['token.created', 'language.added'])

    def test_update_with_invalid_event_returns_400(self):
        resp = self.client.put(self.url, {'events': ['fake.event']}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_update_deactivate(self):
        resp = self.client.put(self.url, {'is_active': False}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.endpoint.refresh_from_db()
        self.assertFalse(self.endpoint.is_active)

    def test_update_clear_auth_token(self):
        self.endpoint.auth_token = encrypt('old-token')
        self.endpoint.save()
        resp = self.client.put(self.url, {'auth_token': ''}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.endpoint.refresh_from_db()
        self.assertFalse(self.endpoint.auth_token)

    def test_delete(self):
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(WebhookEndpoint.objects.filter(pk=self.endpoint.pk).exists())

    def test_cannot_access_other_projects_webhook(self):
        other_user = make_user('other')
        other_project = make_project('Other', owner=other_user)
        other_hook = make_webhook(other_project)
        resp = self.client.get(
            f'/api/project/{other_project.pk}/webhooks/{other_hook.pk}'
        )
        self.assertEqual(resp.status_code, 404)


class WebhookEventsAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.client = authed_client(self.user)

    def test_returns_event_list(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/webhooks/events')
        self.assertEqual(resp.status_code, 200)
        events = resp.json()
        self.assertIn('translation.created', events)
        self.assertIn('import.completed', events)
        self.assertIn('token.deleted', events)


class WebhookLogsAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.endpoint = make_webhook(self.project)
        self.client = authed_client(self.user)

    def test_returns_empty_logs(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/webhooks/{self.endpoint.pk}/logs'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_returns_logs(self):
        WebhookDeliveryLog.objects.create(
            endpoint=self.endpoint,
            event_type='translation.created',
            payload_sent={'event': 'translation.created'},
            status_code=200,
        )
        resp = self.client.get(
            f'/api/project/{self.project.pk}/webhooks/{self.endpoint.pk}/logs'
        )
        self.assertEqual(resp.status_code, 200)
        logs = resp.json()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['event_type'], 'translation.created')
        self.assertEqual(logs[0]['status_code'], 200)


class DispatcherTestCase(TestCase):
    """Unit tests for dispatch_event() — no real HTTP calls."""

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)

    def _make_thread_sync(self):
        """Patch threading.Thread so target runs synchronously in tests."""
        def sync_thread(target, args=(), kwargs=None, daemon=False):
            m = MagicMock()
            m.start = lambda: target(*args)
            return m
        return patch('api.dispatcher.threading.Thread', side_effect=sync_thread)

    @patch('api.dispatcher.urllib.request.urlopen')
    def test_dispatch_delivers_to_subscribed_endpoint(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        endpoint = make_webhook(self.project, events=['translation.created'])

        with self._make_thread_sync():
            from api.dispatcher import dispatch_event
            dispatch_event(
                project_id=self.project.pk,
                event_type='translation.created',
                payload={'token': 'hello', 'language': 'EN', 'value': 'Hello'},
            )

        mock_urlopen.assert_called_once()
        log = WebhookDeliveryLog.objects.get(endpoint=endpoint)
        self.assertEqual(log.status_code, 200)
        self.assertEqual(log.event_type, 'translation.created')

    def test_dispatch_skips_inactive_endpoint(self):
        make_webhook(self.project, events=['translation.created'])
        WebhookEndpoint.objects.update(is_active=False)

        with patch('api.dispatcher.urllib.request.urlopen') as mock_urlopen:
            from api.dispatcher import dispatch_event
            dispatch_event(
                project_id=self.project.pk,
                event_type='translation.created',
                payload={},
            )
        mock_urlopen.assert_not_called()

    def test_dispatch_skips_unsubscribed_endpoint(self):
        make_webhook(self.project, events=['token.created'])

        with patch('api.dispatcher.urllib.request.urlopen') as mock_urlopen:
            from api.dispatcher import dispatch_event
            dispatch_event(
                project_id=self.project.pk,
                event_type='translation.created',
                payload={},
            )
        mock_urlopen.assert_not_called()

    def test_dispatch_no_endpoints_does_nothing(self):
        with patch('api.dispatcher.urllib.request.urlopen') as mock_urlopen:
            from api.dispatcher import dispatch_event
            dispatch_event(
                project_id=self.project.pk,
                event_type='translation.created',
                payload={},
            )
        mock_urlopen.assert_not_called()

    @patch('api.dispatcher.urllib.request.urlopen')
    def test_dispatch_logs_http_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='https://example.com', code=500, msg='Server Error', hdrs=None, fp=None
        )
        endpoint = make_webhook(self.project, events=['translation.created'])

        with self._make_thread_sync():
            from api.dispatcher import dispatch_event
            dispatch_event(
                project_id=self.project.pk,
                event_type='translation.created',
                payload={},
            )

        log = WebhookDeliveryLog.objects.get(endpoint=endpoint)
        self.assertEqual(log.status_code, 500)
        self.assertIsNotNone(log.error)

    @patch('api.dispatcher.urllib.request.urlopen')
    def test_dispatch_logs_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError('refused')
        endpoint = make_webhook(self.project, events=['translation.created'])

        with self._make_thread_sync():
            from api.dispatcher import dispatch_event
            dispatch_event(
                project_id=self.project.pk,
                event_type='translation.created',
                payload={},
            )

        log = WebhookDeliveryLog.objects.get(endpoint=endpoint)
        self.assertIsNone(log.status_code)
        self.assertIn('refused', log.error)

    @patch('api.dispatcher.urllib.request.urlopen')
    def test_dispatch_renders_template(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        endpoint = make_webhook(self.project, events=['translation.created'])
        endpoint.template = 'New: {{token}} ({{language}})'
        endpoint.save()

        captured = {}

        def capture_call(req, timeout=None):
            captured['body'] = json.loads(req.data)
            return mock_resp

        mock_urlopen.side_effect = capture_call

        with self._make_thread_sync():
            from api.dispatcher import dispatch_event
            dispatch_event(
                project_id=self.project.pk,
                event_type='translation.created',
                payload={'token': 'welcome', 'language': 'EN', 'value': 'Hi'},
            )

        self.assertEqual(captured['body'], {'text': 'New: welcome (EN)'})

    @patch('api.dispatcher.urllib.request.urlopen')
    def test_dispatch_sends_hmac_signature_header(self, mock_urlopen):
        import hashlib
        import hmac

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        endpoint = make_webhook(self.project, events=['token.created'])
        captured = {}

        def capture(req, timeout=None):
            captured['headers'] = dict(req.headers)
            captured['body'] = req.data
            return mock_resp

        mock_urlopen.side_effect = capture

        with self._make_thread_sync():
            from api.dispatcher import dispatch_event
            dispatch_event(
                project_id=self.project.pk,
                event_type='token.created',
                payload={'token': 'key'},
            )

        sig_header = captured['headers'].get('X-signature') or captured['headers'].get('X-Signature')
        self.assertIsNotNone(sig_header)
        expected = 'sha256=' + hmac.new(
            endpoint.signing_secret.encode(),
            captured['body'],
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(sig_header, expected)


class ViewEventDispatchTestCase(TestCase):
    """Assert that view actions call dispatch_event with the expected event type."""

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.lang = make_language(self.project, 'EN')
        self.client = authed_client(self.user)

    def _patch(self):
        return patch('api.dispatcher.dispatch_event')

    # --- Tokens ---

    def test_token_create_dispatches_token_created(self):
        with self._patch() as mock_dispatch:
            self.client.post('/api/string_token', {
                'project': self.project.pk,
                'token': 'new_key',
                'comment': '',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('token.created', event_types)

    def test_token_delete_dispatches_token_deleted(self):
        from api.models.translations import StringToken
        token = StringToken.objects.create(token='bye', project=self.project)
        with self._patch() as mock_dispatch:
            self.client.delete('/api/string_token', {'id': token.pk}, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('token.deleted', event_types)

    def test_token_status_change_dispatches_token_status_changed(self):
        from api.models.translations import StringToken
        token = StringToken.objects.create(token='k', project=self.project)
        with self._patch() as mock_dispatch:
            self.client.put(f'/api/string_token/{token.pk}/status', {
                'status': 'deprecated',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('token.status_changed', event_types)

    # --- Translations ---

    def test_translation_create_dispatches_translation_created(self):
        from api.models.translations import StringToken
        StringToken.objects.create(token='k', project=self.project)
        with self._patch() as mock_dispatch:
            self.client.post('/api/translation', {
                'project_id': self.project.pk,
                'code': 'EN',
                'token': 'k',
                'translation': 'Hello',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('translation.created', event_types)

    def test_translation_update_dispatches_translation_updated(self):
        from api.models.translations import StringToken, Translation
        token = StringToken.objects.create(token='k', project=self.project)
        Translation.objects.create(token=token, language=self.lang, translation='Old')
        with self._patch() as mock_dispatch:
            self.client.post('/api/translation', {
                'project_id': self.project.pk,
                'code': 'EN',
                'token': 'k',
                'translation': 'New',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('translation.updated', event_types)

    def test_translation_status_change_dispatches_status_changed(self):
        from api.models.translations import StringToken, Translation
        token = StringToken.objects.create(token='k', project=self.project)
        Translation.objects.create(token=token, language=self.lang, translation='Hi')
        with self._patch() as mock_dispatch:
            self.client.put('/api/translation/status', {
                'project_id': self.project.pk,
                'code': 'EN',
                'token': 'k',
                'status': 'approved',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('translation.status_changed', event_types)

    # --- Languages ---

    def test_language_add_dispatches_language_added(self):
        with self._patch() as mock_dispatch:
            self.client.post('/api/language', {
                'project': self.project.pk,
                'code': 'FR',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('language.added', event_types)

    def test_language_remove_dispatches_language_removed(self):
        make_language(self.project, 'DE')
        with self._patch() as mock_dispatch:
            self.client.delete('/api/language', {
                'project': self.project.pk,
                'code': 'DE',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('language.removed', event_types)

    # --- Import ---

    def test_import_dispatches_import_completed_once(self):
        content = '"a" = "A";\n"b" = "B";\n"c" = "C";\n'
        buf = io.BytesIO(content.encode())
        buf.name = 'en.strings'
        with self._patch() as mock_dispatch:
            self.client.post('/api/import', {
                'project_id': self.project.pk,
                'code': 'EN',
                'file': buf,
            }, format='multipart')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        # Exactly one import.completed event — not one per record.
        self.assertEqual(event_types.count('import.completed'), 1)
        self.assertNotIn('translation.created', event_types)

    def test_import_completed_payload_contains_count(self):
        content = '"x" = "X";\n"y" = "Y";\n'
        buf = io.BytesIO(content.encode())
        buf.name = 'en.strings'
        with self._patch() as mock_dispatch:
            self.client.post('/api/import', {
                'project_id': self.project.pk,
                'code': 'EN',
                'file': buf,
            }, format='multipart')
        import_call = next(
            c for c in mock_dispatch.call_args_list
            if (c.kwargs.get('event_type') or c.args[1]) == 'import.completed'
        )
        payload = import_call.kwargs.get('payload') or import_call.args[2]
        self.assertEqual(payload['count'], 2)

    # --- Members ---

    def test_invite_dispatches_member_invited(self):
        with self._patch() as mock_dispatch:
            self.client.post(f'/api/project/{self.project.pk}/invite', {
                'role': 'translator',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('member.invited', event_types)

    def test_role_change_dispatches_member_role_changed(self):
        member = make_user('member')
        add_role(member, self.project, ProjectRole.Role.translator)
        with self._patch() as mock_dispatch:
            self.client.post(f'/api/project/{self.project.pk}/participants', {
                'user_id': member.pk,
                'role': 'editor',
            }, format='json')
        event_types = [c.kwargs.get('event_type') or c.args[1] for c in mock_dispatch.call_args_list]
        self.assertIn('member.role_changed', event_types)
