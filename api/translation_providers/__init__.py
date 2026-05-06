
from api.crypto import decrypt
from api.models.project import ProjectAIProvider, TranslationIntegration
from api.translation_providers.base import TranslationProvider
from api.translation_providers.connected_ai import ConnectedAIProvider
from api.translation_providers.deepl import DeepLProvider
from api.translation_providers.google import GoogleTranslateProvider


def get_provider(integration: TranslationIntegration, ai_provider: ProjectAIProvider | None = None) -> TranslationProvider:
    if integration.provider == TranslationIntegration.PROVIDER_AI:
        if ai_provider is None:
            raise RuntimeError('No AI provider configured for this project')
        key = decrypt(ai_provider.api_key)
        return ConnectedAIProvider(ai_provider.provider_type, key, ai_provider.endpoint_url, ai_provider.model_name, ai_provider.translation_instructions)
    key = decrypt(integration.api_key)
    if integration.provider == TranslationIntegration.PROVIDER_DEEPL:
        return DeepLProvider(key)
    return GoogleTranslateProvider(key)
