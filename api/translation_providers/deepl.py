import json
import urllib.error
import urllib.request

from api.translation_providers.base import TranslationProvider


class DeepLProvider(TranslationProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Free-tier keys end with ':fx'
        if api_key.endswith(':fx'):
            self.base_url = 'https://api-free.deepl.com/v2'
        else:
            self.base_url = 'https://api.deepl.com/v2'

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        payload: dict = {
            'text': [text],
            'target_lang': target_lang.upper(),
        }
        if source_lang:
            payload['source_lang'] = source_lang.upper()

        req = urllib.request.Request(
            f'{self.base_url}/translate',
            data=json.dumps(payload).encode(),
            headers={
                'Authorization': f'DeepL-Auth-Key {self.api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'DeepL error {e.code}: {e.read().decode()}') from e

        return result['translations'][0]['text']
