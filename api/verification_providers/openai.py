import json
import urllib.error
import urllib.request

from api.url_validation import validate_url_for_outbound
from api.verification_providers.base import VerificationProvider

DEFAULT_ENDPOINT = 'https://api.openai.com/v1/chat/completions'


def _build_system_prompt(checks: list[str], project_description: str) -> str:
    checks_str = ', '.join(checks)
    desc_part = f'\nProject context: {project_description}' if project_description else ''
    return (
        f'You are a translation quality reviewer.{desc_part}\n'
        f'Checks to perform: {checks_str}\n'
        'You will receive a JSON array of items to review. '
        'Respond with ONLY a JSON array — no markdown, no prose, no code fences. '
        'One object per input item with keys: '
        '"token_id" (int), "plural_form" (string or null), '
        '"severity" ("ok", "warning", or "error"), '
        '"suggestion" (corrected text, empty string if ok), '
        '"reason" (brief explanation).\n'
        'For items with severity "ok", set suggestion to "" and explain briefly why it is correct.'
    )


def _build_user_message(items: list[dict]) -> str:
    return json.dumps([
        {
            'token_id': item['token_id'],
            'token_key': item['token_key'],
            'language': item['language'],
            'plural_form': item['plural_form'],
            'source': item['source'],
            'current': item['current'],
            'required_placeholders': item['placeholders'],
        }
        for item in items
    ], ensure_ascii=False)


def _parse_response(content: str) -> list[dict]:
    parsed = json.loads(content)
    if isinstance(parsed, dict):
        for key in ('results', 'items', 'data'):
            if isinstance(parsed.get(key), list):
                return parsed[key]
    if isinstance(parsed, list):
        return parsed
    raise RuntimeError(f'Unexpected AI response shape: {type(parsed)}')


class OpenAIVerificationProvider(VerificationProvider):
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
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message},
            ],
            'response_format': {'type': 'json_object'},
        }

        req = urllib.request.Request(
            self.endpoint_url,
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

        content = raw.get('choices', [{}])[0].get('message', {}).get('content', '')
        return _parse_response(content)
