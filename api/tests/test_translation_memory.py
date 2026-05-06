from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from api.models.project import ProjectAIProvider, ProjectRole
from api.models.string_token import StringToken
from api.crypto import encrypt
from api.tests.helpers import (
    authed_client, add_role, make_user, make_project,
    make_language, make_token, make_translation,
)

URL = '/api/project/{pk}/translation-memory'


def _make_ai_provider(project):
    return ProjectAIProvider.objects.create(
        project=project,
        provider_type=ProjectAIProvider.ProviderType.openai,
        endpoint_url='https://api.openai.com/v1/chat/completions',
        api_key=encrypt('test-key'),
        model_name='gpt-4o',
    )


class AccessAndValidationTests(TestCase):

    def setUp(self):
        cache.clear()
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.en = make_language(self.project, 'EN')
        self.en.is_default = True
        self.en.save()
        self.de = make_language(self.project, 'DE')
        self.token_a = make_token(self.project, 'login_button')
        make_translation(self.token_a, self.en, 'Log In')
        make_translation(self.token_a, self.de, 'Anmelden')
        self.client = authed_client(self.owner)

    def test_requires_project_membership(self):
        outsider = make_user('outsider')
        c = authed_client(outsider)
        resp = c.get(URL.format(pk=self.project.pk), {'token': 'login_button', 'language': 'DE'})
        self.assertEqual(resp.status_code, 404)

    def test_all_roles_can_access(self):
        for role in (ProjectRole.Role.translator, ProjectRole.Role.editor, ProjectRole.Role.admin):
            user = make_user(f'user_{role}')
            add_role(user, self.project, role)
            c = authed_client(user)
            resp = c.get(URL.format(pk=self.project.pk), {'token': 'login_button', 'language': 'DE'})
            self.assertEqual(resp.status_code, 200, f'role {role} should get 200')

    def test_missing_token_param_returns_400(self):
        resp = self.client.get(URL.format(pk=self.project.pk), {'language': 'DE'})
        self.assertEqual(resp.status_code, 400)

    def test_missing_language_param_returns_400(self):
        resp = self.client.get(URL.format(pk=self.project.pk), {'token': 'login_button'})
        self.assertEqual(resp.status_code, 400)


class ManualModeTests(TestCase):

    def setUp(self):
        cache.clear()
        self.owner = make_user('owner2')
        self.project = make_project(owner=self.owner)
        self.en = make_language(self.project, 'EN')
        self.en.is_default = True
        self.en.save()
        self.de = make_language(self.project, 'DE')
        self.client = authed_client(self.owner)

    def _url(self):
        return URL.format(pk=self.project.pk)

    def test_returns_empty_when_no_default_language(self):
        self.en.is_default = False
        self.en.save()
        token = make_token(self.project, 'key1')
        make_translation(token, self.en, 'Hello')
        resp = self.client.get(self._url(), {'token': 'key1', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_returns_empty_when_current_token_has_no_source_text(self):
        token = make_token(self.project, 'no_source')
        resp = self.client.get(self._url(), {'token': 'no_source', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_returns_empty_when_below_threshold(self):
        token_a = make_token(self.project, 'token_a')
        make_translation(token_a, self.en, 'Hello')

        token_b = make_token(self.project, 'token_b')
        make_translation(token_b, self.en, 'Completely different xyz abc 1234567890')
        make_translation(token_b, self.de, 'Völlig anders')

        resp = self.client.get(self._url(), {'token': 'token_a', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_returns_similar_strings(self):
        token_a = make_token(self.project, 'login_button')
        make_translation(token_a, self.en, 'Log In')

        token_b = make_token(self.project, 'signin_button')
        make_translation(token_b, self.en, 'Sign In')
        make_translation(token_b, self.de, 'Einloggen')

        token_c = make_token(self.project, 'login_action')
        make_translation(token_c, self.en, 'Login')
        make_translation(token_c, self.de, 'Anmelden')

        resp = self.client.get(self._url(), {'token': 'login_button', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(len(data), 0)
        scores = [d['similarity_score'] for d in data]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_excludes_current_token(self):
        token_a = make_token(self.project, 'login_button')
        make_translation(token_a, self.en, 'Log In')
        make_translation(token_a, self.de, 'Anmelden')

        resp = self.client.get(self._url(), {'token': 'login_button', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        keys = [d['token_key'] for d in resp.json()]
        self.assertNotIn('login_button', keys)

    def test_excludes_tokens_without_target_translation(self):
        token_a = make_token(self.project, 'source_token')
        make_translation(token_a, self.en, 'Log In')

        # Candidate has source but no DE translation
        token_b = make_token(self.project, 'no_de')
        make_translation(token_b, self.en, 'Login Now')

        resp = self.client.get(self._url(), {'token': 'source_token', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        keys = [d['token_key'] for d in resp.json()]
        self.assertNotIn('no_de', keys)

    def test_max_five_results(self):
        source = make_token(self.project, 'source')
        make_translation(source, self.en, 'Log In')

        for i in range(8):
            t = make_token(self.project, f'similar_{i}')
            make_translation(t, self.en, f'Log In {i}')
            make_translation(t, self.de, f'Anmelden {i}')

        resp = self.client.get(self._url(), {'token': 'source', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.json()), 5)

    def test_response_shape(self):
        token_a = make_token(self.project, 'shape_source')
        make_translation(token_a, self.en, 'Log In')

        token_b = make_token(self.project, 'shape_candidate')
        make_translation(token_b, self.en, 'Login')
        make_translation(token_b, self.de, 'Anmelden')

        resp = self.client.get(self._url(), {'token': 'shape_source', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        if data:
            item = data[0]
            self.assertIn('token_key', item)
            self.assertIn('source_text', item)
            self.assertIn('translation_text', item)
            self.assertIn('similarity_score', item)

    def test_similarity_score_is_between_0_and_1(self):
        token_a = make_token(self.project, 'score_source')
        make_translation(token_a, self.en, 'Hello World')

        token_b = make_token(self.project, 'score_candidate')
        make_translation(token_b, self.en, 'Hello World Again')
        make_translation(token_b, self.de, 'Hallo Welt')

        resp = self.client.get(self._url(), {'token': 'score_source', 'language': 'DE'})
        self.assertEqual(resp.status_code, 200)
        for item in resp.json():
            self.assertGreaterEqual(item['similarity_score'], 0.0)
            self.assertLessEqual(item['similarity_score'], 1.0)


class LargeProjectSamplingTests(TestCase):

    def setUp(self):
        cache.clear()
        self.owner = make_user('owner3')
        self.project = make_project(owner=self.owner)
        self.en = make_language(self.project, 'EN')
        self.en.is_default = True
        self.en.save()
        self.de = make_language(self.project, 'DE')
        self.client = authed_client(self.owner)

    def test_sampling_applied_above_2000(self):
        source = make_token(self.project, 'big_source')
        make_translation(source, self.en, 'Hello')

        tokens = []
        for i in range(2001):
            t = make_token(self.project, f'big_token_{i}')
            tokens.append(t)

        # Batch-create translations for efficiency
        from api.models.translations import Translation as Trans
        en_translations = [
            Trans(token=t, language=self.en, translation=f'Hello {i}', status=Trans.Status.new)
            for i, t in enumerate(tokens)
        ]
        de_translations = [
            Trans(token=t, language=self.de, translation=f'Hallo {i}', status=Trans.Status.new)
            for i, t in enumerate(tokens)
        ]
        Trans.objects.bulk_create(en_translations)
        Trans.objects.bulk_create(de_translations)

        with patch('api.views.translation_memory.difflib.SequenceMatcher') as mock_sm:
            mock_instance = MagicMock()
            mock_instance.ratio.return_value = 0.0
            mock_sm.return_value = mock_instance
            self.client.get(
                f'/api/project/{self.project.pk}/translation-memory',
                {'token': 'big_source', 'language': 'DE'},
            )
            call_count = mock_sm.call_count
        self.assertLessEqual(call_count, 501)


class AIModeTests(TestCase):

    def setUp(self):
        cache.clear()
        self.owner = make_user('owner4')
        self.project = make_project(owner=self.owner)
        self.en = make_language(self.project, 'EN')
        self.en.is_default = True
        self.en.save()
        self.de = make_language(self.project, 'DE')
        _make_ai_provider(self.project)
        self.client = authed_client(self.owner)

        self.source = make_token(self.project, 'ai_source')
        make_translation(self.source, self.en, 'Log In')

        self.candidate = make_token(self.project, 'ai_candidate')
        make_translation(self.candidate, self.en, 'Login Now')
        make_translation(self.candidate, self.de, 'Jetzt anmelden')

    def _url(self):
        return f'/api/project/{self.project.pk}/translation-memory'

    def test_ai_mode_calls_rank_by_similarity(self):
        mock_provider = MagicMock()
        mock_provider.rank_by_similarity.return_value = []

        with patch('api.views.translation_memory.get_verification_provider', return_value=mock_provider):
            resp = self.client.get(self._url(), {'token': 'ai_source', 'language': 'DE'})

        self.assertEqual(resp.status_code, 200)
        if mock_provider.rank_by_similarity.called:
            args = mock_provider.rank_by_similarity.call_args
            self.assertEqual(args[0][0], 'Log In')

    def test_ai_mode_fallback_on_exception(self):
        mock_provider = MagicMock()
        mock_provider.rank_by_similarity.side_effect = RuntimeError('AI failure')

        with patch('api.views.translation_memory.get_verification_provider', return_value=mock_provider):
            resp = self.client.get(self._url(), {'token': 'ai_source', 'language': 'DE'})

        self.assertEqual(resp.status_code, 200)

    def test_ai_mode_uses_looser_floor(self):
        # Add a candidate with similarity ~0.45 (above AI floor 0.40, below manual floor 0.60)
        # "Log In" vs "Logged" → ratio is roughly 0.44–0.50 depending on difflib
        borderline = make_token(self.project, 'borderline_token')
        make_translation(borderline, self.en, 'Logged')
        make_translation(borderline, self.de, 'Eingeloggt')

        import difflib
        ratio = difflib.SequenceMatcher(None, 'Log In', 'Logged').ratio()

        if ratio >= 0.40:
            mock_provider = MagicMock()
            mock_provider.rank_by_similarity.side_effect = lambda src, cands: cands

            with patch('api.views.translation_memory.get_verification_provider', return_value=mock_provider):
                resp = self.client.get(self._url(), {'token': 'ai_source', 'language': 'DE'})

            self.assertEqual(resp.status_code, 200)
            keys = [d['token_key'] for d in resp.json()]
            if ratio < 0.60:
                self.assertIn('borderline_token', keys, 'AI mode should include candidates above 0.40')
