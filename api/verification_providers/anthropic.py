import json
import urllib.error
import urllib.request

from api.url_validation import validate_url_for_outbound
from api.verification_providers.base import VerificationProvider
from api.verification_providers.openai import _build_system_prompt, _build_user_message, _parse_response

DEFAULT_ENDPOINT = 'https://api.anthropic.com/v1/messages'
ANTHROPIC_VERSION = '2023-06-01'


class AnthropicVerificationProvider(VerificationProvider):
    def __init__(self, api_key: str, endpoint_url: str, model_name: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url or DEFAULT_ENDPOINT
        self.model_name = model_name

    def verify(self, items: list[dict], checks: list[str], project_description: str) -> list[dict]:
        try:
            validate_url_for_outbound(self.endpoint_url)
        except ValueError as e:
            raise RuntimeError(f'Invalid endpoint URL: {e}') from e

        system_prompt = _build_system_prompt(checks, project_description)
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
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'AI provider error {e.code}: {e.read().decode("utf-8", errors="replace")}') from e

        content = raw.get('content', [{}])[0].get('text', '')
        return _parse_response(content)
