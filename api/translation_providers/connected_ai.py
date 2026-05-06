import json
import urllib.error
import urllib.request

from api.translation_providers.base import TranslationProvider
from api.url_validation import validate_url_for_outbound

OPENAI_DEFAULT_ENDPOINT = 'https://api.openai.com/v1/chat/completions'
ANTHROPIC_DEFAULT_ENDPOINT = 'https://api.anthropic.com/v1/messages'
ANTHROPIC_VERSION = '2023-06-01'


class ConnectedAIProvider(TranslationProvider):
    def __init__(self, provider_type: str, api_key: str, endpoint_url: str, model_name: str, translation_instructions: str = ''):
        self.provider_type = provider_type
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.translation_instructions = translation_instructions

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        if self.provider_type == 'anthropic':
            return self._translate_anthropic(text, target_lang)
        return self._translate_openai(text, target_lang)

    def _translate_openai(self, text: str, target_lang: str) -> str:
        endpoint = self.endpoint_url or OPENAI_DEFAULT_ENDPOINT
        try:
            validate_url_for_outbound(endpoint)
        except ValueError as e:
            raise RuntimeError(f'Invalid endpoint URL: {e}') from e

        try:
            directive = self.translation_instructions.format(target_lang=target_lang) if self.translation_instructions else f'Translate to {target_lang}.'
        except KeyError:
            directive = self.translation_instructions
        system_content = f'{directive}\nReturn only the translation, no explanations.'
        payload = {
            'model': self.model_name,
            'messages': [
                {'role': 'system', 'content': system_content},
                {'role': 'user', 'content': text},
            ],
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'AI provider error {e.code}: {e.read().decode("utf-8", errors="replace")}') from e

        return raw.get('choices', [{}])[0].get('message', {}).get('content', '').strip()

    def _translate_anthropic(self, text: str, target_lang: str) -> str:
        endpoint = self.endpoint_url or ANTHROPIC_DEFAULT_ENDPOINT
        try:
            validate_url_for_outbound(endpoint)
        except ValueError as e:
            raise RuntimeError(f'Invalid endpoint URL: {e}') from e

        try:
            directive = self.translation_instructions.format(target_lang=target_lang) if self.translation_instructions else f'Translate to {target_lang}.'
        except KeyError:
            directive = self.translation_instructions
        system_content = f'{directive}\nReturn only the translation, no explanations.'
        payload = {
            'model': self.model_name,
            'max_tokens': 1024,
            'system': system_content,
            'messages': [{'role': 'user', 'content': text}],
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode(),
            headers={
                'x-api-key': self.api_key,
                'anthropic-version': ANTHROPIC_VERSION,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'AI provider error {e.code}: {e.read().decode("utf-8", errors="replace")}') from e

        return raw.get('content', [{}])[0].get('text', '').strip()
