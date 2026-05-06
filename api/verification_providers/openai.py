import json
import urllib.error
import urllib.request

from api.url_validation import validate_url_for_outbound
from api.verification_providers.base import VerificationProvider

DEFAULT_ENDPOINT = 'https://api.openai.com/v1/chat/completions'


def _build_system_prompt(checks: list[str], project_description: str, custom_instruction: str = '') -> str:
    checks_str = ', '.join(checks)
    role = custom_instruction if custom_instruction else 'You are a translation quality reviewer.'
    desc_part = f'\nProject context: {project_description}' if project_description else ''
    return (
        f'{role}{desc_part}\n'
        f'Checks to perform: {checks_str}\n'
        'You will receive a JSON array of items to review. '
        'Return ONLY a valid JSON array. '
        'No explanations. No extra text. '
        'If you cannot, return an empty array []. '
        'Do not return a single object. '
        'Each item MUST contain token_id field. '
        'Do not group items. '
        'Do not use object keys as IDs. '
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


def _normalize(parsed):
    if isinstance(parsed, dict):
        items = []
        for k, v in parsed.items():
            if isinstance(v, dict):
                v["token_id"] = int(k) if k.isdigit() else k
                items.append(v)
        return items

    return parsed


def _parse_response(content: str) -> list[dict]:
    parsed = json.loads(content)
    parsed = _normalize(parsed)
    if isinstance(parsed, list):
        return parsed

    if isinstance(parsed, dict):
        for value in parsed.values():
            if isinstance(value, list) and all(isinstance(i, dict) for i in value):
                return value

    raise RuntimeError(f'Unexpected AI response: {parsed}')


class OpenAIVerificationProvider(VerificationProvider):
    def __init__(self, api_key: str, endpoint_url: str, model_name: str, timeout: int = 120, verification_instructions: str = ''):
        self.api_key = api_key
        self.endpoint_url = endpoint_url or DEFAULT_ENDPOINT
        self.model_name = model_name
        self.timeout = timeout
        self.verification_instructions = verification_instructions

    def verify(self, items: list[dict], checks: list[str], project_description: str) -> list[dict]:
        try:
            validate_url_for_outbound(self.endpoint_url)
        except ValueError as e:
            raise RuntimeError(f'Invalid endpoint URL: {e}') from e

        system_prompt = _build_system_prompt(checks, project_description, self.verification_instructions)
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
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f'AI provider error {e.code}: {e.read().decode("utf-8", errors="replace")}') from e

        content = raw.get('choices', [{}])[0].get(
            'message', {}).get('content', '')
        return _parse_response(content)
