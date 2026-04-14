
from api.crypto import decrypt
from api.models.project import TranslationIntegration
from api.translation_providers.base import TranslationProvider
from api.translation_providers.deepl import DeepLProvider
from api.translation_providers.google import GoogleTranslateProvider


def get_provider(integration: TranslationIntegration) -> TranslationProvider:
    key = decrypt(integration.api_key)
    if integration.provider == TranslationIntegration.PROVIDER_DEEPL:
        return DeepLProvider(key)
    return GoogleTranslateProvider(key)
