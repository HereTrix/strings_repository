# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import json
from unittest.mock import patch

from django.test import TestCase, Client

from api.models.language import Language
from api.models.project import ProjectAccessToken
from api.tests.helpers import (
    make_access_token, make_glossary_term, make_glossary_translation,
    make_language, make_project, make_token, make_translation, make_user,
)
from .helpers import get_error, get_result, make_ai_provider, mcp_call


# ── search_similar_tokens ─────────────────────────────────────────────────────

class SearchSimilarTokensTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev')
        self.project = make_project('SearchApp', owner=self.user)
        self.lang_en = make_language(self.project, 'EN')
        self.access = make_access_token(self.project, self.user)
        self.client = Client()
        token_a = make_token(self.project, 'onboarding.title')
        token_b = make_token(self.project, 'onboarding.subtitle')
        token_c = make_token(self.project, 'settings.profile')
        make_translation(token_a, self.lang_en, 'Welcome to the app')
        make_translation(token_b, self.lang_en, 'Get started here')
        make_translation(token_c, self.lang_en, 'Edit your profile')

    def _call(self, arguments):
        return mcp_call(self.client, self.access, 'search_similar_tokens', arguments)

    def test_search_finds_by_translation_text(self):
        result = get_result(self._call({'text': 'Welcome'}))
        self.assertIn('onboarding.title', [r['token'] for r in result['results']])

    def test_search_finds_by_key_name(self):
        result = get_result(self._call({'text': 'settings'}))
        self.assertIn('settings.profile', [r['token'] for r in result['results']])

    def test_search_respects_limit(self):
        result = get_result(self._call({'text': 'onboarding', 'limit': 1}))
        self.assertLessEqual(len(result['results']), 1)

    def test_search_returns_translations(self):
        result = get_result(self._call({'text': 'Welcome'}))
        first = result['results'][0]
        self.assertIn('translations', first)
        self.assertIn('EN', [t['language'] for t in first['translations']])


# ── suggest_token_key ─────────────────────────────────────────────────────────

class SuggestTokenKeyTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev')
        self.project = make_project('SuggestApp', owner=self.user)
        self.access = make_access_token(self.project, self.user)
        self.client = Client()

    def _call(self, arguments):
        return mcp_call(self.client, self.access, 'suggest_token_key', arguments)

    def test_suggest_basic(self):
        result = get_result(self._call({'source_text': 'Sign in to your account'}))
        self.assertEqual(result['suggested_key'], 'sign_in_to_your_account')

    def test_suggest_strips_punctuation(self):
        key = get_result(self._call({'source_text': "Don't miss out!"}))['suggested_key']
        self.assertNotIn("'", key)
        self.assertNotIn('!', key)

    def test_suggest_avoids_collision(self):
        result = get_result(self._call({
            'source_text': 'Hello world',
            'existing_tokens': ['hello_world'],
        }))
        self.assertEqual(result['suggested_key'], 'hello_world_2')

    def test_suggest_increments_collision_counter(self):
        result = get_result(self._call({
            'source_text': 'Hello world',
            'existing_tokens': ['hello_world', 'hello_world_2'],
        }))
        self.assertEqual(result['suggested_key'], 'hello_world_3')

    def test_suggest_truncates_to_five_words(self):
        result = get_result(self._call({'source_text': 'one two three four five six seven'}))
        self.assertLessEqual(len(result['suggested_key'].split('_')), 5)


# ── get_token_naming_patterns ─────────────────────────────────────────────────

class TokenNamingPatternsTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev')
        self.project = make_project('NamingApp', owner=self.user)
        self.lang_en = make_language(self.project, 'EN')
        self.access = make_access_token(self.project, self.user)
        self.client = Client()
        make_token(self.project, 'onboarding.title')
        make_token(self.project, 'onboarding.subtitle')
        make_token(self.project, 'settings.profile')

    def _call(self, arguments):
        return mcp_call(self.client, self.access, 'get_token_naming_patterns', arguments)

    def test_detects_dot_separator(self):
        result = get_result(self._call({}))
        self.assertEqual(result['separator'], 'dot')

    def test_returns_common_prefixes(self):
        result = get_result(self._call({'sample_size': 10}))
        self.assertIn('onboarding', result['common_prefixes'])

    def test_returns_examples(self):
        result = get_result(self._call({}))
        self.assertGreater(len(result['examples']), 0)

    def test_detects_underscore_separator(self):
        project2 = make_project('UnderscoreApp', owner=self.user)
        make_language(project2, 'EN')
        for key in ('home_title', 'home_subtitle', 'profile_name'):
            make_token(project2, key)
        access2 = make_access_token(project2, self.user)
        result = get_result(mcp_call(self.client, access2, 'get_token_naming_patterns', {}))
        self.assertEqual(result['separator'], 'underscore')


# ── check_glossary ────────────────────────────────────────────────────────────

class CheckGlossaryTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev')
        self.project = make_project('GlossaryApp', owner=self.user)
        self.access = make_access_token(self.project, self.user)
        self.read_access = make_access_token(
            self.project, self.user,
            permission=ProjectAccessToken.AccessTokenPermissions.read,
        )
        self.client = Client()

    def _call(self, arguments, token=None):
        return mcp_call(self.client, token or self.access, 'check_glossary', arguments)

    def test_appears_in_tools_list(self):
        resp = self.client.post(
            '/api/mcp',
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=self.access.token,
        )
        self.assertIn('check_glossary', [t['name'] for t in resp.json()['result']['tools']])

    def test_empty_source_returns_empty(self):
        self.assertEqual(get_result(self._call({'source_text': ''})), {'matches': []})

    def test_no_terms_returns_empty(self):
        self.assertEqual(
            get_result(self._call({'source_text': 'Click Login to continue'})),
            {'matches': []},
        )

    def test_match_case_insensitive(self):
        make_glossary_term(self.project, term='Login', case_sensitive=False)
        result = get_result(self._call({'source_text': 'Click login button'}))
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['matches'][0]['term'], 'Login')

    def test_no_match(self):
        make_glossary_term(self.project, term='Submit', case_sensitive=False)
        self.assertEqual(
            get_result(self._call({'source_text': 'Click login button'})),
            {'matches': []},
        )

    def test_case_sensitive_no_match(self):
        make_glossary_term(self.project, term='Login', case_sensitive=True)
        self.assertEqual(
            get_result(self._call({'source_text': 'Click login button'})),
            {'matches': []},
        )

    def test_case_sensitive_match(self):
        make_glossary_term(self.project, term='Login', case_sensitive=True)
        result = get_result(self._call({'source_text': 'Click Login button'}))
        self.assertEqual(len(result['matches']), 1)

    def test_with_language_code_includes_preferred_translation(self):
        term = make_glossary_term(self.project, term='Login', case_sensitive=False)
        make_glossary_translation(term, language_code='DE', preferred_translation='Anmelden')
        result = get_result(self._call({'source_text': 'Click Login to continue', 'language_code': 'DE'}))
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['matches'][0]['preferred_translation'], 'Anmelden')

    def test_without_language_code_returns_null_preferred_translation(self):
        term = make_glossary_term(self.project, term='Login', case_sensitive=False)
        make_glossary_translation(term, language_code='DE', preferred_translation='Anmelden')
        result = get_result(self._call({'source_text': 'Click Login to continue'}))
        self.assertIsNone(result['matches'][0]['preferred_translation'])

    def test_language_with_no_preferred_translation(self):
        term = make_glossary_term(self.project, term='Login', case_sensitive=False)
        make_glossary_translation(term, language_code='FR', preferred_translation='Connexion')
        result = get_result(self._call({'source_text': 'Click Login to continue', 'language_code': 'DE'}))
        self.assertIsNone(result['matches'][0]['preferred_translation'])

    def test_multiple_terms_multiple_matches(self):
        make_glossary_term(self.project, term='Login', case_sensitive=False)
        make_glossary_term(self.project, term='Submit', case_sensitive=False)
        make_glossary_term(self.project, term='Register', case_sensitive=False)
        result = get_result(self._call({'source_text': 'Click Login and Submit form'}))
        self.assertEqual(len(result['matches']), 2)

    def test_read_token_allowed(self):
        make_glossary_term(self.project, term='Login', case_sensitive=False)
        result = get_result(self._call({'source_text': 'Click Login'}, token=self.read_access))
        self.assertEqual(len(result['matches']), 1)


# ── suggest_translation ───────────────────────────────────────────────────────

class SuggestTranslationTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev2')
        self.project = make_project('TMApp', owner=self.user)
        self.lang_en = Language.objects.create(code='EN', project=self.project, is_default=True)
        self.lang_de = make_language(self.project, 'DE')
        self.access = make_access_token(self.project, self.user)
        self.read_access = make_access_token(
            self.project, self.user,
            permission=ProjectAccessToken.AccessTokenPermissions.read,
        )
        self.client = Client()

    def _call(self, arguments, token=None):
        return mcp_call(self.client, token or self.access, 'suggest_translation', arguments)

    def _make_similar_tokens(self):
        for i, (src, de) in enumerate([
            ('Sign In to continue', 'Anmelden um fortzufahren'),
            ('Sign In now', 'Jetzt anmelden'),
            ('Sign In please', 'Bitte anmelden'),
        ]):
            t = make_token(self.project, f'btn.signin{i}')
            make_translation(t, self.lang_en, src)
            make_translation(t, self.lang_de, de)

    def test_appears_in_tools_list(self):
        resp = self.client.post(
            '/api/mcp',
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=self.access.token,
        )
        self.assertIn('suggest_translation', [t['name'] for t in resp.json()['result']['tools']])

    def test_invalid_language_returns_error(self):
        self.assertIn('Item not found', get_error(self._call({'source_text': 'Sign In', 'language_code': 'XX'})))

    def test_empty_source_returns_empty(self):
        self.assertEqual(
            get_result(self._call({'source_text': '', 'language_code': 'DE'})),
            {'suggestions': []},
        )

    def test_no_default_language_returns_empty(self):
        project2 = make_project('NoDefault', owner=self.user)
        make_language(project2, 'DE')
        access2 = make_access_token(project2, self.user)
        result = get_result(mcp_call(self.client, access2, 'suggest_translation', {
            'source_text': 'Sign In', 'language_code': 'DE',
        }))
        self.assertEqual(result, {'suggestions': []})

    def test_no_candidates_above_threshold(self):
        token = make_token(self.project, 'btn.cancel')
        make_translation(token, self.lang_en, 'XXXXXXXXXXXXXXXXXXXXXXXXXXX')
        make_translation(token, self.lang_de, 'Abbrechen')
        self.assertEqual(
            get_result(self._call({'source_text': 'Sign In', 'language_code': 'DE'})),
            {'suggestions': []},
        )

    def test_returns_similar_strings(self):
        self._make_similar_tokens()
        result = get_result(self._call({'source_text': 'Sign In to continue', 'language_code': 'DE'}))
        self.assertGreater(len(result['suggestions']), 0)

    def test_sorted_by_similarity_desc(self):
        self._make_similar_tokens()
        scores = [s['similarity_score'] for s in get_result(
            self._call({'source_text': 'Sign In to continue', 'language_code': 'DE'})
        )['suggestions']]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_max_5_results(self):
        for i in range(8):
            t = make_token(self.project, f'btn.signin{i}')
            make_translation(t, self.lang_en, f'Sign In button {i}')
            make_translation(t, self.lang_de, f'Anmelden Schaltfläche {i}')
        result = get_result(self._call({'source_text': 'Sign In button', 'language_code': 'DE'}))
        self.assertLessEqual(len(result['suggestions']), 5)

    def test_result_shape(self):
        self._make_similar_tokens()
        result = get_result(self._call({'source_text': 'Sign In to continue', 'language_code': 'DE'}))
        if result['suggestions']:
            s = result['suggestions'][0]
            for key in ('token_key', 'source_text', 'translation_text', 'similarity_score'):
                self.assertIn(key, s)

    def test_read_token_allowed(self):
        self._make_similar_tokens()
        result = get_result(mcp_call(self.client, self.read_access, 'suggest_translation', {
            'source_text': 'Sign In to continue', 'language_code': 'DE',
        }))
        self.assertIn('suggestions', result)


# ── verify_string ─────────────────────────────────────────────────────────────

class VerifyStringTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev3')
        self.project = make_project('VerifyApp', owner=self.user)
        self.access = make_access_token(self.project, self.user)
        self.read_access = make_access_token(
            self.project, self.user,
            permission=ProjectAccessToken.AccessTokenPermissions.read,
        )
        self.client = Client()

    def _call(self, arguments, token=None):
        return mcp_call(self.client, token or self.access, 'verify_string', arguments)

    def _base_args(self):
        return {'source_text': 'Log in', 'translation_text': 'Anmelden', 'language_code': 'DE'}

    def test_appears_in_tools_list(self):
        resp = self.client.post(
            '/api/mcp',
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=self.access.token,
        )
        self.assertIn('verify_string', [t['name'] for t in resp.json()['result']['tools']])

    def test_no_ai_provider_returns_error(self):
        self.assertIn('No AI provider configured', get_error(self._call(self._base_args())))

    def test_missing_required_params_returns_error(self):
        make_ai_provider(self.project)
        self.assertIn('error', self._call({'source_text': 'Log in', 'language_code': 'DE'}).json())

    def test_returns_severity_suggestion_reason(self):
        make_ai_provider(self.project)
        mock_result = [{'token_id': 0, 'plural_form': None, 'severity': 'warning',
                        'suggestion': 'Anmelden', 'reason': 'Better match'}]
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=mock_result):
            result = get_result(self._call(self._base_args()))
        self.assertEqual(result['severity'], 'warning')
        self.assertIn('suggestion', result)
        self.assertIn('reason', result)

    def test_default_checks_exclude_glossary_compliance(self):
        make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]) as mock_v:
            self._call(self._base_args())
        self.assertNotIn('glossary_compliance', mock_v.call_args[0][1])

    def test_custom_checks_used(self):
        make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]) as mock_v:
            self._call({**self._base_args(), 'checks': ['semantic_accuracy']})
        self.assertEqual(mock_v.call_args[0][1], ['semantic_accuracy'])

    def test_all_invalid_checks_falls_back_to_defaults(self):
        make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]) as mock_v:
            self._call({**self._base_args(), 'checks': ['nonexistent']})
        self.assertGreater(len(mock_v.call_args[0][1]), 1)
        self.assertNotIn('glossary_compliance', mock_v.call_args[0][1])

    def test_provider_error_returns_mcp_error(self):
        make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', side_effect=RuntimeError('quota exceeded')):
            error = self._call(self._base_args()).json().get('error', {})
        self.assertEqual(error.get('code'), -32603)

    def test_empty_provider_result_returns_ok(self):
        make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]):
            result = get_result(self._call(self._base_args()))
        self.assertEqual(result['severity'], 'ok')
        self.assertEqual(result['suggestion'], '')
        self.assertIn('No issues found', result['reason'])

    def test_read_token_allowed(self):
        make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]):
            result = get_result(self._call(self._base_args(), token=self.read_access))
        self.assertIn('severity', result)
