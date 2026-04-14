import json
import urllib.error
import urllib.request

from api.translation_providers.base import TranslationProvider


class GoogleTranslateProvider(TranslationProvider):
    BASE_URL = 'https://translation.googleapis.com/language/translate/v2'

    def __init__(self, api_key: str):
        self.api_key = api_key

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        payload: dict = {
            'q': text,
            'target': target_lang,
            'key': self.api_key,
            'format': 'text',
        }
        if source_lang:
            payload['source'] = source_lang

        req = urllib.request.Request(
            self.BASE_URL,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'Google Translate error {e.code}: {e.read().decode()}') from e

        return result['data']['translations'][0]['translatedText']
