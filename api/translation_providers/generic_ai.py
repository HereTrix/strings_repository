import json
import urllib.error
import urllib.request

from api.translation_providers.base import TranslationProvider
from api.url_validation import validate_url_for_outbound


class GenericAIProvider(TranslationProvider):
    def __init__(
        self,
        api_key: str,
        endpoint_url: str,
        payload_template: str,
        response_path: str,
        auth_header: str = 'Authorization',
    ):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.payload_template = payload_template
        self.response_path = response_path or 'choices.0.message.content'
        self.auth_header = auth_header or 'Authorization'

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        try:
            validate_url_for_outbound(self.endpoint_url)
        except ValueError as e:
            raise RuntimeError(f'Invalid endpoint URL: {e}') from e

        rendered = (
            self.payload_template
            .replace('{{text}}', text)
            .replace('{{target_lang}}', target_lang)
            .replace('{{source_lang}}', source_lang or '')
        )
        payload = json.loads(rendered)

        auth_value = (
            f'Bearer {self.api_key}'
            if self.auth_header.lower() == 'authorization'
            else self.api_key
        )
        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode(),
            headers={
                self.auth_header: auth_value,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'AI provider error {e.code}: {e.read().decode()}') from e

        return self._extract(result, self.response_path)

    def _extract(self, data: dict, path: str) -> str:
        parts = path.split('.')
        current = data
        for part in parts:
            try:
                current = current[int(part)] if isinstance(current, list) else current[part]
            except (KeyError, IndexError, TypeError, ValueError) as e:
                raise RuntimeError(f'Cannot extract response_path "{path}": failed at "{part}"') from e
        if not isinstance(current, str):
            raise RuntimeError(f'response_path "{path}" resolved to {type(current).__name__}, expected str')
        return current
