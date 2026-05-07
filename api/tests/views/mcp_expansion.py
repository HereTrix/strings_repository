import json
from unittest.mock import patch

from django.test import TestCase, Client

from api.crypto import encrypt
from api.models.language import Language
from api.models.project import ProjectAccessToken, ProjectAIProvider
from api.tests.helpers import (
    make_access_token, make_glossary_term, make_glossary_translation,
    make_language, make_project, make_token, make_translation, make_user,
)


def _make_ai_provider(project):
    return ProjectAIProvider.objects.create(
        project=project,
        provider_type='openai',
        model_name='gpt-4o-mini',
        endpoint_url='',
        api_key=encrypt('sk-test'),
    )


def mcp_call(client, token, tool_name, arguments):
    return client.post(
        '/api/mcp',
        data=json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }),
        content_type='application/json',
        HTTP_ACCESS_TOKEN=token.token,
    )


def get_result(response):
    return json.loads(response.json()['result']['content'][0]['text'])


def get_error(response):
    return response.json().get('error', {}).get('message', '')


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

    def test_check_glossary_appears_in_tools_list(self):
        resp = self.client.post(
            '/api/mcp',
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=self.access.token,
        )
        tools = resp.json()['result']['tools']
        names = [t['name'] for t in tools]
        self.assertIn('check_glossary', names)

    def test_check_glossary_empty_source_returns_empty(self):
        result = get_result(self._call({'source_text': ''}))
        self.assertEqual(result, {'matches': []})

    def test_check_glossary_no_terms_returns_empty(self):
        result = get_result(self._call(
            {'source_text': 'Click Login to continue'}))
        self.assertEqual(result, {'matches': []})

    def test_check_glossary_match_case_insensitive(self):
        make_glossary_term(self.project, term='Login', case_sensitive=False)
        result = get_result(self._call({'source_text': 'Click login button'}))
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['matches'][0]['term'], 'Login')

    def test_check_glossary_no_match(self):
        make_glossary_term(self.project, term='Submit', case_sensitive=False)
        result = get_result(self._call({'source_text': 'Click login button'}))
        self.assertEqual(result, {'matches': []})

    def test_check_glossary_case_sensitive_no_match(self):
        make_glossary_term(self.project, term='Login', case_sensitive=True)
        result = get_result(self._call({'source_text': 'Click login button'}))
        self.assertEqual(result, {'matches': []})

    def test_check_glossary_case_sensitive_match(self):
        make_glossary_term(self.project, term='Login', case_sensitive=True)
        result = get_result(self._call({'source_text': 'Click Login button'}))
        self.assertEqual(len(result['matches']), 1)

    def test_check_glossary_with_language_code_includes_preferred_translation(self):
        term = make_glossary_term(
            self.project, term='Login', case_sensitive=False)
        make_glossary_translation(
            term, language_code='DE', preferred_translation='Anmelden')
        result = get_result(self._call(
            {'source_text': 'Click Login to continue', 'language_code': 'DE'}))
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['matches'][0]
                         ['preferred_translation'], 'Anmelden')

    def test_check_glossary_without_language_code_returns_null_preferred_translation(self):
        term = make_glossary_term(
            self.project, term='Login', case_sensitive=False)
        make_glossary_translation(
            term, language_code='DE', preferred_translation='Anmelden')
        result = get_result(self._call(
            {'source_text': 'Click Login to continue'}))
        self.assertIsNone(result['matches'][0]['preferred_translation'])

    def test_check_glossary_language_with_no_preferred_translation(self):
        term = make_glossary_term(
            self.project, term='Login', case_sensitive=False)
        make_glossary_translation(
            term, language_code='FR', preferred_translation='Connexion')
        result = get_result(self._call(
            {'source_text': 'Click Login to continue', 'language_code': 'DE'}))
        self.assertIsNone(result['matches'][0]['preferred_translation'])

    def test_check_glossary_multiple_terms_multiple_matches(self):
        make_glossary_term(self.project, term='Login', case_sensitive=False)
        make_glossary_term(self.project, term='Submit', case_sensitive=False)
        make_glossary_term(self.project, term='Register', case_sensitive=False)
        result = get_result(self._call(
            {'source_text': 'Click Login and Submit form'}))
        self.assertEqual(len(result['matches']), 2)

    def test_check_glossary_read_token_allowed(self):
        make_glossary_term(self.project, term='Login', case_sensitive=False)
        result = get_result(self._call(
            {'source_text': 'Click Login'}, token=self.read_access))
        self.assertEqual(len(result['matches']), 1)


# ── suggest_translation ───────────────────────────────────────────────────────

class SuggestTranslationTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev2')
        self.project = make_project('TMApp', owner=self.user)
        self.lang_en = Language.objects.create(
            code='EN', project=self.project, is_default=True)
        self.lang_de = make_language(self.project, 'DE')
        self.access = make_access_token(self.project, self.user)
        self.read_access = make_access_token(
            self.project, self.user,
            permission=ProjectAccessToken.AccessTokenPermissions.read,
        )
        self.client = Client()

    def _call(self, arguments, token=None):
        return mcp_call(self.client, token or self.access, 'suggest_translation', arguments)

    def test_suggest_translation_appears_in_tools_list(self):
        resp = self.client.post(
            '/api/mcp',
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=self.access.token,
        )
        tools = resp.json()['result']['tools']
        names = [t['name'] for t in tools]
        self.assertIn('suggest_translation', names)

    def test_suggest_translation_invalid_language_returns_error(self):
        resp = self._call({'source_text': 'Sign In', 'language_code': 'XX'})
        self.assertIn('not found in project', get_error(resp))

    def test_suggest_translation_empty_source_returns_empty(self):
        result = get_result(self._call(
            {'source_text': '', 'language_code': 'DE'}))
        self.assertEqual(result, {'suggestions': []})

    def test_suggest_translation_no_default_language_returns_empty(self):
        project2 = make_project('NoDefault', owner=self.user)
        lang_de2 = make_language(project2, 'DE')
        access2 = make_access_token(project2, self.user)
        result = get_result(mcp_call(self.client, access2, 'suggest_translation', {
                            'source_text': 'Sign In', 'language_code': 'DE'}))
        self.assertEqual(result, {'suggestions': []})

    def test_suggest_translation_no_candidates_above_threshold(self):
        token = make_token(self.project, 'btn.cancel')
        make_translation(token, self.lang_en, 'XXXXXXXXXXXXXXXXXXXXXXXXXXX')
        make_translation(token, self.lang_de, 'Abbrechen')
        result = get_result(self._call(
            {'source_text': 'Sign In', 'language_code': 'DE'}))
        self.assertEqual(result, {'suggestions': []})

    def _make_similar_tokens(self):
        for i, (src, de) in enumerate([
            ('Sign In to continue', 'Anmelden um fortzufahren'),
            ('Sign In now', 'Jetzt anmelden'),
            ('Sign In please', 'Bitte anmelden'),
        ]):
            t = make_token(self.project, f'btn.signin{i}')
            make_translation(t, self.lang_en, src)
            make_translation(t, self.lang_de, de)

    def test_suggest_translation_returns_similar_strings(self):
        self._make_similar_tokens()
        result = get_result(self._call(
            {'source_text': 'Sign In to continue', 'language_code': 'DE'}))
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggest_translation_sorted_by_similarity_desc(self):
        self._make_similar_tokens()
        result = get_result(self._call(
            {'source_text': 'Sign In to continue', 'language_code': 'DE'}))
        scores = [s['similarity_score'] for s in result['suggestions']]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_suggest_translation_max_5_results(self):
        for i in range(8):
            t = make_token(self.project, f'btn.signin{i}')
            make_translation(t, self.lang_en, f'Sign In button {i}')
            make_translation(t, self.lang_de, f'Anmelden Schaltfläche {i}')
        result = get_result(self._call(
            {'source_text': 'Sign In button', 'language_code': 'DE'}))
        self.assertLessEqual(len(result['suggestions']), 5)

    def test_suggest_translation_result_shape(self):
        self._make_similar_tokens()
        result = get_result(self._call(
            {'source_text': 'Sign In to continue', 'language_code': 'DE'}))
        if result['suggestions']:
            s = result['suggestions'][0]
            self.assertIn('token_key', s)
            self.assertIn('source_text', s)
            self.assertIn('translation_text', s)
            self.assertIn('similarity_score', s)

    def test_suggest_translation_read_token_allowed(self):
        self._make_similar_tokens()
        result = get_result(mcp_call(self.client, self.read_access, 'suggest_translation', {
                            'source_text': 'Sign In to continue', 'language_code': 'DE'}))
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

    def test_verify_string_appears_in_tools_list(self):
        resp = self.client.post(
            '/api/mcp',
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=self.access.token,
        )
        tools = resp.json()['result']['tools']
        names = [t['name'] for t in tools]
        self.assertIn('verify_string', names)

    def test_verify_string_no_ai_provider_returns_error(self):
        resp = self._call(self._base_args())
        self.assertIn('No AI provider configured', get_error(resp))

    def test_verify_string_missing_required_params_returns_error(self):
        _make_ai_provider(self.project)
        resp = self._call({'source_text': 'Log in', 'language_code': 'DE'})
        self.assertIn('error', resp.json())

    def test_verify_string_returns_severity_suggestion_reason(self):
        _make_ai_provider(self.project)
        mock_result = [{'token_id': 0, 'plural_form': None, 'severity': 'warning',
                        'suggestion': 'Anmelden', 'reason': 'Better match'}]
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=mock_result):
            result = get_result(self._call(self._base_args()))
        self.assertIn('severity', result)
        self.assertIn('suggestion', result)
        self.assertIn('reason', result)
        self.assertEqual(result['severity'], 'warning')

    def test_verify_string_default_checks_exclude_glossary_compliance(self):
        _make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]) as mock_verify:
            self._call(self._base_args())
            called_checks = mock_verify.call_args[0][1]
        self.assertNotIn('glossary_compliance', called_checks)

    def test_verify_string_custom_checks_used(self):
        _make_ai_provider(self.project)
        args = {**self._base_args(), 'checks': ['semantic_accuracy']}
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]) as mock_verify:
            self._call(args)
            called_checks = mock_verify.call_args[0][1]
        self.assertEqual(called_checks, ['semantic_accuracy'])

    def test_verify_string_all_invalid_checks_uses_defaults(self):
        _make_ai_provider(self.project)
        args = {**self._base_args(), 'checks': ['nonexistent']}
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]) as mock_verify:
            self._call(args)
            called_checks = mock_verify.call_args[0][1]
        self.assertGreater(len(called_checks), 1)
        self.assertNotIn('glossary_compliance', called_checks)

    def test_verify_string_provider_error_returns_mcp_error(self):
        _make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', side_effect=RuntimeError('quota exceeded')):
            resp = self._call(self._base_args())
        error = resp.json().get('error', {})
        self.assertEqual(error.get('code'), -32603)

    def test_verify_string_empty_provider_result_returns_ok(self):
        _make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]):
            result = get_result(self._call(self._base_args()))
        self.assertEqual(result['severity'], 'ok')
        self.assertEqual(result['suggestion'], '')
        self.assertIn('No issues found', result['reason'])

    def test_verify_string_read_token_allowed(self):
        _make_ai_provider(self.project)
        with patch('api.verification_providers.openai.OpenAIVerificationProvider.verify', return_value=[]):
            result = get_result(self._call(
                self._base_args(), token=self.read_access))
        self.assertIn('severity', result)
