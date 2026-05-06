import json
import urllib.error
import urllib.request

from api.url_validation import validate_url_for_outbound
from api.verification_providers.base import VerificationProvider
from api.verification_providers.openai import _build_system_prompt, _build_user_message, _parse_response, _parse_glossary_response

DEFAULT_ENDPOINT = 'https://api.anthropic.com/v1/messages'
ANTHROPIC_VERSION = '2023-06-01'


class AnthropicVerificationProvider(VerificationProvider):
    def __init__(self, api_key: str, endpoint_url: str, model_name: str, timeout: int = 120, verification_instructions: str = '', glossary_extraction_instructions: str = '', translation_memory_instructions: str = ''):
        self.api_key = api_key
        self.endpoint_url = endpoint_url or DEFAULT_ENDPOINT
        self.model_name = model_name
        self.timeout = timeout
        self.verification_instructions = verification_instructions
        self.glossary_extraction_instructions = glossary_extraction_instructions
        self.translation_memory_instructions = translation_memory_instructions

    def verify(self, items: list[dict], checks: list[str], project_description: str, glossary_terms=()) -> list[dict]:
        try:
            validate_url_for_outbound(self.endpoint_url)
        except ValueError as e:
            raise RuntimeError(f'Invalid endpoint URL: {e}') from e

        system_prompt = _build_system_prompt(checks, project_description, self.verification_instructions, glossary_terms)
        user_message = _build_user_message(items)

        payload = {
            'model': self.model_name,
            'max_tokens': 4096,
            'system': system_prompt,
            'messages': [
                {'role': 'user', 'content': user_message},
            ],
        }

        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode(),
            headers={
                'x-api-key': self.api_key,
                'anthropic-version': ANTHROPIC_VERSION,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'AI provider error {e.code}: {e.read().decode("utf-8", errors="replace")}') from e

        content = raw.get('content', [{}])[0].get('text', '')
        return _parse_response(content)

    def extract_glossary(self, strings: list[str], project_description: str) -> list[dict]:
        try:
            validate_url_for_outbound(self.endpoint_url)
        except ValueError as e:
            raise RuntimeError(f'Invalid endpoint URL: {e}') from e

        role = self.glossary_extraction_instructions if self.glossary_extraction_instructions else 'You are a localization expert.'
        desc_part = f'\nProject context: {project_description}' if project_description else ''
        system_prompt = (
            f'{role}{desc_part}\n'
            'Analyze the provided list of source strings and identify terms that should be in a translation glossary: '
            'product names, technical terms, UI labels, or phrases requiring consistent translation.\n'
            'Respond with ONLY a JSON array — no markdown, no prose. '
            'Each object must have keys: '
            '"term" (str, the source-language term), '
            '"definition" (str, a brief explanation, may be empty string), '
            '"translations" (array of {language_code: str, preferred_translation: str} — may be empty array).\n'
            'Return between 5 and 30 terms. Do not include trivial common words.'
        )
        payload = {
            'model': self.model_name,
            'max_tokens': 4096,
            'system': system_prompt,
            'messages': [
                {'role': 'user', 'content': json.dumps(strings, ensure_ascii=False)},
            ],
        }
        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode(),
            headers={
                'x-api-key': self.api_key,
                'anthropic-version': ANTHROPIC_VERSION,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                raw = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'AI provider error {e.code}: {e.read().decode("utf-8", errors="replace")}') from e
        content = raw.get('content', [{}])[0].get('text', '')
        return _parse_glossary_response(content)

    def rank_by_similarity(self, source: str, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return candidates
        try:
            validate_url_for_outbound(self.endpoint_url)
        except ValueError:
            return candidates

        role = self.translation_memory_instructions if self.translation_memory_instructions else 'You are a translation expert.'
        system_prompt = (
            f'{role} Given a source string and a list of candidate token keys, '
            'rank the candidates by how semantically similar their source meaning is to the given source string. '
            'Respond with ONLY a JSON array of token_key strings, most similar first. '
            'Include every key exactly once. No prose, no markdown.'
        )
        user_message = json.dumps({
            'source': source[:500],
            'candidates': [
                {'token_key': c['token_key'], 'source_text': c['source_text'][:500]}
                for c in candidates
            ]
        }, ensure_ascii=False)

        payload = {
            'model': self.model_name,
            'max_tokens': 1024,
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': user_message}],
        }
        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode(),
            headers={
                'x-api-key': self.api_key,
                'anthropic-version': ANTHROPIC_VERSION,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                raw = json.loads(response.read())
        except Exception:
            return candidates

        try:
            content = raw.get('content', [{}])[0].get('text', '')
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                for val in parsed.values():
                    if isinstance(val, list):
                        parsed = val
                        break
            if not isinstance(parsed, list):
                return candidates
            ordered_keys = [str(k) for k in parsed]
        except Exception:
            return candidates

        key_to_candidate = {c['token_key']: c for c in candidates}
        result = [key_to_candidate[k] for k in ordered_keys if k in key_to_candidate]
        seen = set(ordered_keys)
        result += [c for c in candidates if c['token_key'] not in seen]
        return result
