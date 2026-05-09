# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from api.crypto import encrypt
from api.models.project import ProjectAIProvider
from api.verification_providers import get_verification_provider
from api.verification_providers.anthropic import AnthropicVerificationProvider
from api.verification_providers.openai import (
    OpenAIVerificationProvider,
    _build_system_prompt,
    _build_user_message,
    _normalize,
    _parse_glossary_response,
    _parse_response,
)

# Sample item for verify() calls.
_ITEM = {
    'token_id': 1,
    'token_key': 'greeting',
    'language': 'DE',
    'plural_form': None,
    'source': 'Hello',
    'current': 'Hallo',
    'placeholders': [],
}

_CANDIDATES = [
    {'token_key': 'greet', 'source_text': 'Hello', 'translation_text': 'Hallo', 'similarity_score': 0.9},
    {'token_key': 'bye',   'source_text': 'Goodbye', 'translation_text': 'Auf Wiedersehen', 'similarity_score': 0.3},
]


def _mock_ctx(raw_data: dict):
    """Context-manager-compatible mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = json.dumps(raw_data).encode()
    return mock_resp


def _openai_raw(content: str) -> dict:
    return {'choices': [{'message': {'content': content}}]}


def _anthropic_raw(content: str) -> dict:
    return {'content': [{'text': content}]}


def _urlparse_mock():
    """Return a urlparse mock that reports scheme='https'."""
    m = MagicMock()
    m.return_value.scheme = 'https'
    return m


# ---------------------------------------------------------------------------
# Pure function unit tests
# ---------------------------------------------------------------------------

class BuildSystemPromptTests(SimpleTestCase):

    def test_default_role_when_no_instruction(self):
        result = _build_system_prompt(['spelling_grammar'], '', '')
        self.assertIn('translation quality reviewer', result)

    def test_custom_instruction_replaces_default_role(self):
        result = _build_system_prompt(['c'], '', 'You are a strict reviewer.')
        self.assertIn('You are a strict reviewer.', result)
        self.assertNotIn('translation quality reviewer', result)

    def test_checks_listed_in_prompt(self):
        result = _build_system_prompt(['spelling_grammar', 'semantic_accuracy'], '', '')
        self.assertIn('spelling_grammar', result)
        self.assertIn('semantic_accuracy', result)

    def test_project_description_included(self):
        result = _build_system_prompt(['c'], 'An e-commerce app', '')
        self.assertIn('Project context:', result)
        self.assertIn('An e-commerce app', result)

    def test_empty_description_omits_context_line(self):
        result = _build_system_prompt(['c'], '', '')
        self.assertNotIn('Project context:', result)

    def test_glossary_section_present_with_terms(self):
        terms = [{'term': 'Submit', 'preferred_translation': 'Absenden', 'case_sensitive': False}]
        result = _build_system_prompt(['c'], '', '', terms)
        self.assertIn('GLOSSARY TERMS', result)
        self.assertIn('Submit', result)
        self.assertIn('Absenden', result)

    def test_term_without_preferred_translation_shows_placeholder(self):
        terms = [{'term': 'Submit', 'preferred_translation': '', 'case_sensitive': False}]
        result = _build_system_prompt(['c'], '', '', terms)
        self.assertIn('no preferred translation', result)

    def test_case_sensitive_term_annotated(self):
        terms = [{'term': 'AppName', 'preferred_translation': 'AppName', 'case_sensitive': True}]
        result = _build_system_prompt(['c'], '', '', terms)
        self.assertIn('(case-sensitive)', result)

    def test_no_glossary_omits_section(self):
        result = _build_system_prompt(['c'], '', '')
        self.assertNotIn('GLOSSARY TERMS', result)


class ParseResponseTests(SimpleTestCase):

    def test_list_returned_as_is(self):
        data = [{'token_id': 1, 'severity': 'ok', 'suggestion': '', 'reason': ''}]
        self.assertEqual(_parse_response(json.dumps(data)), data)

    def test_dict_with_list_value_normalizes_to_empty(self):
        # _normalize strips non-dict values, so a dict whose values are lists
        # (not dicts) produces an empty list after normalization.
        inner = [{'token_id': 1, 'severity': 'ok'}]
        result = _parse_response(json.dumps({'results': inner}))
        self.assertEqual(result, [])

    def test_dict_keyed_by_digit_normalizes_token_id_to_int(self):
        data = {'1': {'severity': 'ok', 'suggestion': '', 'reason': ''}}
        result = _parse_response(json.dumps(data))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['token_id'], 1)

    def test_dict_keyed_by_non_digit_keeps_string_token_id(self):
        data = {'abc': {'severity': 'ok'}}
        result = _parse_response(json.dumps(data))
        self.assertEqual(result[0]['token_id'], 'abc')

    def test_unexpected_shape_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            _parse_response(json.dumps('just a string'))

    def test_invalid_json_raises(self):
        with self.assertRaises((json.JSONDecodeError, ValueError)):
            _parse_response('not json')


class ParseGlossaryResponseTests(SimpleTestCase):

    def test_list_returned_as_is(self):
        data = [{'term': 'Submit'}]
        self.assertEqual(_parse_glossary_response(json.dumps(data)), data)

    def test_dict_with_terms_key(self):
        inner = [{'term': 'Submit'}]
        self.assertEqual(_parse_glossary_response(json.dumps({'terms': inner})), inner)

    def test_dict_with_glossary_key(self):
        inner = [{'term': 'Cancel'}]
        self.assertEqual(_parse_glossary_response(json.dumps({'glossary': inner})), inner)

    def test_dict_with_results_key(self):
        inner = [{'term': 'OK'}]
        self.assertEqual(_parse_glossary_response(json.dumps({'results': inner})), inner)

    def test_dict_with_items_key(self):
        inner = [{'term': 'Save'}]
        self.assertEqual(_parse_glossary_response(json.dumps({'items': inner})), inner)

    def test_unknown_shape_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            _parse_glossary_response(json.dumps({'unexpected': 'scalar'}))


class NormalizeTests(SimpleTestCase):

    def test_dict_digit_keys_become_int_token_ids(self):
        result = _normalize({'1': {'severity': 'ok'}, '3': {'severity': 'error'}})
        ids = {item['token_id'] for item in result}
        self.assertEqual(ids, {1, 3})

    def test_non_digit_key_kept_as_string_token_id(self):
        result = _normalize({'abc': {'severity': 'ok'}})
        self.assertEqual(result[0]['token_id'], 'abc')

    def test_non_dict_values_skipped(self):
        result = _normalize({'1': 'not a dict', '2': {'severity': 'ok'}})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['token_id'], 2)

    def test_list_input_returned_unchanged(self):
        data = [{'token_id': 1}]
        self.assertEqual(_normalize(data), data)


class BuildUserMessageTests(SimpleTestCase):

    def test_serializes_items_to_json_array(self):
        result = json.loads(_build_user_message([_ITEM]))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['token_id'], 1)
        self.assertEqual(result[0]['token_key'], 'greeting')

    def test_placeholders_keyed_as_required_placeholders(self):
        item = {**_ITEM, 'placeholders': ['%s', '{name}']}
        result = json.loads(_build_user_message([item]))
        self.assertEqual(result[0]['required_placeholders'], ['%s', '{name}'])


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIVerifyTests(SimpleTestCase):

    def _provider(self, instructions=''):
        return OpenAIVerificationProvider(
            api_key='sk-test',
            endpoint_url='https://api.openai.com/v1/chat/completions',
            model_name='gpt-4o',
            verification_instructions=instructions,
        )

    def test_returns_parsed_results(self):
        results = [{'token_id': 1, 'plural_form': None, 'severity': 'ok', 'suggestion': '', 'reason': ''}]
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', return_value=_mock_ctx(_openai_raw(json.dumps(results)))):
            result = self._provider().verify([_ITEM], ['spelling_grammar'], '')
        self.assertEqual(result, results)

    def test_raises_on_http_error(self):
        err = urllib.error.HTTPError('url', 429, 'Rate limited', {}, io.BytesIO(b'too many'))
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RuntimeError) as ctx:
                self._provider().verify([_ITEM], ['spelling_grammar'], '')
        self.assertIn('429', str(ctx.exception))

    def test_raises_on_invalid_url(self):
        with patch('api.verification_providers.openai.validate_url_for_outbound',
                   side_effect=ValueError('private IP')):
            with self.assertRaises(RuntimeError) as ctx:
                self._provider().verify([_ITEM], ['spelling_grammar'], '')
        self.assertIn('Invalid endpoint URL', str(ctx.exception))

    def test_sends_bearer_authorization_header(self):
        results = [{'token_id': 1, 'plural_form': None, 'severity': 'ok', 'suggestion': '', 'reason': ''}]
        mock_resp = _mock_ctx(_openai_raw(json.dumps(results)))
        captured = {}

        def capture(req, timeout=None):
            captured['auth'] = req.get_header('Authorization')
            return mock_resp

        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=capture):
            self._provider().verify([_ITEM], ['spelling_grammar'], '')
        self.assertEqual(captured['auth'], 'Bearer sk-test')

    def test_uses_default_endpoint_when_empty_string(self):
        provider = OpenAIVerificationProvider(api_key='k', endpoint_url='', model_name='m')
        self.assertEqual(provider.endpoint_url, 'https://api.openai.com/v1/chat/completions')


class OpenAIExtractGlossaryTests(SimpleTestCase):

    def _provider(self, instructions=''):
        return OpenAIVerificationProvider(
            api_key='sk-test',
            endpoint_url='https://api.openai.com/v1/chat/completions',
            model_name='gpt-4o',
            glossary_extraction_instructions=instructions,
        )

    def test_returns_glossary_list(self):
        terms = [{'term': 'Submit', 'definition': 'To send', 'translations': []}]
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', return_value=_mock_ctx(_openai_raw(json.dumps(terms)))):
            result = self._provider().extract_glossary(['Submit form', 'Cancel'], '')
        self.assertEqual(result, terms)

    def test_raises_on_http_error(self):
        err = urllib.error.HTTPError('url', 500, 'Server Error', {}, io.BytesIO(b'err'))
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RuntimeError):
                self._provider().extract_glossary(['Submit'], '')

    def test_raises_on_invalid_url(self):
        with patch('api.verification_providers.openai.validate_url_for_outbound',
                   side_effect=ValueError('blocked')):
            with self.assertRaises(RuntimeError):
                self._provider().extract_glossary(['Submit'], '')

    def test_custom_extraction_instructions_in_system_prompt(self):
        provider = self._provider(instructions='You are a medical translator.')
        terms = [{'term': 'Dosage', 'definition': '', 'translations': []}]
        captured = {}

        def capture(req, timeout=None):
            body = json.loads(req.data)
            captured['system'] = body['messages'][0]['content']
            return _mock_ctx(_openai_raw(json.dumps(terms)))

        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=capture):
            provider.extract_glossary(['dosage', 'mg'], '')
        self.assertIn('You are a medical translator.', captured.get('system', ''))


class OpenAIRankBySimilarityTests(SimpleTestCase):

    def _provider(self):
        return OpenAIVerificationProvider(
            api_key='sk-test',
            endpoint_url='https://api.openai.com/v1/chat/completions',
            model_name='gpt-4o',
        )

    def test_empty_candidates_returns_immediately_without_http(self):
        with patch('urllib.request.urlopen') as mock_urlopen:
            result = self._provider().rank_by_similarity('Hello', [])
        self.assertEqual(result, [])
        mock_urlopen.assert_not_called()

    def test_invalid_url_returns_candidates_unchanged(self):
        with patch('api.verification_providers.openai.validate_url_for_outbound',
                   side_effect=ValueError('blocked')):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result, _CANDIDATES)

    def test_http_error_returns_candidates_unchanged(self):
        err = urllib.error.HTTPError('url', 500, 'Error', {}, io.BytesIO(b'err'))
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=err):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result, _CANDIDATES)

    def test_reorders_candidates_by_returned_key_order(self):
        response_keys = ['bye', 'greet']
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_openai_raw(json.dumps(response_keys)))):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result[0]['token_key'], 'bye')
        self.assertEqual(result[1]['token_key'], 'greet')

    def test_response_wrapped_in_dict_unwrapped(self):
        wrapped = {'order': ['bye', 'greet']}
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_openai_raw(json.dumps(wrapped)))):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result[0]['token_key'], 'bye')

    def test_keys_missing_from_response_appended_at_end(self):
        # Response only mentions 'greet'; 'bye' must be appended
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_openai_raw(json.dumps(['greet'])))):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result[0]['token_key'], 'greet')
        self.assertEqual(result[1]['token_key'], 'bye')

    def test_invalid_json_content_returns_candidates_unchanged(self):
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_openai_raw('not valid json {{'))):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result, _CANDIDATES)

    def test_non_list_json_without_nested_list_returns_unchanged(self):
        with patch('api.verification_providers.openai.validate_url_for_outbound'), \
             patch('api.verification_providers.openai.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_openai_raw(json.dumps({'scalar': 'value'})))):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result, _CANDIDATES)


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

class AnthropicVerifyTests(SimpleTestCase):

    def _provider(self):
        return AnthropicVerificationProvider(
            api_key='ant-key',
            endpoint_url='https://api.anthropic.com/v1/messages',
            model_name='claude-3-5-haiku-20241022',
        )

    def test_returns_parsed_results(self):
        results = [{'token_id': 1, 'plural_form': None, 'severity': 'ok', 'suggestion': '', 'reason': ''}]
        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_anthropic_raw(json.dumps(results)))):
            result = self._provider().verify([_ITEM], ['spelling_grammar'], '')
        self.assertEqual(result, results)

    def test_sends_x_api_key_header(self):
        results = [{'token_id': 1, 'plural_form': None, 'severity': 'ok', 'suggestion': '', 'reason': ''}]
        captured = {}

        def capture(req, timeout=None):
            captured['key'] = req.get_header('X-api-key')
            captured['version'] = req.get_header('Anthropic-version')
            return _mock_ctx(_anthropic_raw(json.dumps(results)))

        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=capture):
            self._provider().verify([_ITEM], ['spelling_grammar'], '')
        self.assertEqual(captured['key'], 'ant-key')
        self.assertIsNotNone(captured['version'])

    def test_payload_includes_max_tokens_and_system(self):
        results = [{'token_id': 1, 'plural_form': None, 'severity': 'ok', 'suggestion': '', 'reason': ''}]
        captured = {}

        def capture(req, timeout=None):
            captured['body'] = json.loads(req.data)
            return _mock_ctx(_anthropic_raw(json.dumps(results)))

        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=capture):
            self._provider().verify([_ITEM], ['spelling_grammar'], '')
        self.assertIn('max_tokens', captured['body'])
        self.assertIn('system', captured['body'])

    def test_raises_on_http_error(self):
        err = urllib.error.HTTPError('url', 401, 'Unauthorized', {}, io.BytesIO(b'unauth'))
        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RuntimeError) as ctx:
                self._provider().verify([_ITEM], ['spelling_grammar'], '')
        self.assertIn('401', str(ctx.exception))

    def test_raises_on_invalid_url(self):
        with patch('api.verification_providers.anthropic.validate_url_for_outbound',
                   side_effect=ValueError('blocked')):
            with self.assertRaises(RuntimeError):
                self._provider().verify([_ITEM], ['spelling_grammar'], '')

    def test_uses_default_endpoint_when_empty_string(self):
        provider = AnthropicVerificationProvider(api_key='k', endpoint_url='', model_name='m')
        self.assertEqual(provider.endpoint_url, 'https://api.anthropic.com/v1/messages')


class AnthropicExtractGlossaryTests(SimpleTestCase):

    def _provider(self):
        return AnthropicVerificationProvider(
            api_key='ant-key',
            endpoint_url='https://api.anthropic.com/v1/messages',
            model_name='claude-3-5-haiku-20241022',
        )

    def test_returns_glossary_list(self):
        terms = [{'term': 'Submit', 'definition': 'To send', 'translations': []}]
        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_anthropic_raw(json.dumps(terms)))):
            result = self._provider().extract_glossary(['Submit form'], '')
        self.assertEqual(result, terms)

    def test_raises_on_http_error(self):
        err = urllib.error.HTTPError('url', 500, 'Error', {}, io.BytesIO(b'err'))
        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RuntimeError):
                self._provider().extract_glossary(['Submit'], '')

    def test_raises_on_invalid_url(self):
        with patch('api.verification_providers.anthropic.validate_url_for_outbound',
                   side_effect=ValueError('blocked')):
            with self.assertRaises(RuntimeError):
                self._provider().extract_glossary(['Submit'], '')


class AnthropicRankBySimilarityTests(SimpleTestCase):

    def _provider(self):
        return AnthropicVerificationProvider(
            api_key='ant-key',
            endpoint_url='https://api.anthropic.com/v1/messages',
            model_name='claude-3',
        )

    def test_empty_candidates_returns_immediately_without_http(self):
        with patch('urllib.request.urlopen') as mock_urlopen:
            result = self._provider().rank_by_similarity('Hello', [])
        self.assertEqual(result, [])
        mock_urlopen.assert_not_called()

    def test_invalid_url_returns_candidates_unchanged(self):
        with patch('api.verification_providers.anthropic.validate_url_for_outbound',
                   side_effect=ValueError('blocked')):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result, _CANDIDATES)

    def test_http_error_returns_candidates_unchanged(self):
        err = urllib.error.HTTPError('url', 500, 'Error', {}, io.BytesIO(b'err'))
        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen', side_effect=err):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result, _CANDIDATES)

    def test_reorders_candidates_by_returned_key_order(self):
        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_anthropic_raw(json.dumps(['bye', 'greet'])))):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result[0]['token_key'], 'bye')
        self.assertEqual(result[1]['token_key'], 'greet')

    def test_keys_missing_from_response_appended_at_end(self):
        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_anthropic_raw(json.dumps(['greet'])))):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result[0]['token_key'], 'greet')
        self.assertEqual(result[1]['token_key'], 'bye')

    def test_invalid_json_content_returns_candidates_unchanged(self):
        with patch('api.verification_providers.anthropic.validate_url_for_outbound'), \
             patch('api.verification_providers.anthropic.urlparse', _urlparse_mock()), \
             patch('urllib.request.urlopen',
                   return_value=_mock_ctx(_anthropic_raw('not json {{'))):
            result = self._provider().rank_by_similarity('Hello', _CANDIDATES)
        self.assertEqual(result, _CANDIDATES)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

class GetVerificationProviderTests(TestCase):

    def setUp(self):
        from api.tests.helpers import make_project, make_user
        self.project = make_project(owner=make_user('vp_user'))

    def _make_ai_provider(self, provider_type):
        return ProjectAIProvider.objects.create(
            project=self.project,
            provider_type=provider_type,
            model_name='test-model',
            endpoint_url='',
            api_key=encrypt('sk-real'),
        )

    def test_openai_type_returns_openai_provider(self):
        ai_provider = self._make_ai_provider(ProjectAIProvider.ProviderType.openai)
        self.assertIsInstance(get_verification_provider(ai_provider), OpenAIVerificationProvider)

    def test_anthropic_type_returns_anthropic_provider(self):
        ai_provider = self._make_ai_provider(ProjectAIProvider.ProviderType.anthropic)
        self.assertIsInstance(get_verification_provider(ai_provider), AnthropicVerificationProvider)

    def test_api_key_decrypted(self):
        ai_provider = self._make_ai_provider(ProjectAIProvider.ProviderType.openai)
        provider = get_verification_provider(ai_provider)
        self.assertEqual(provider.api_key, 'sk-real')
