from api.crypto import decrypt
from api.models.project import ProjectAIProvider
from api.verification_providers.base import VerificationProvider
from api.verification_providers.openai import OpenAIVerificationProvider
from api.verification_providers.anthropic import AnthropicVerificationProvider


def get_verification_provider(ai_provider: ProjectAIProvider) -> VerificationProvider:
    key = decrypt(ai_provider.api_key)
    if ai_provider.provider_type == ProjectAIProvider.ProviderType.anthropic:
        return AnthropicVerificationProvider(key, ai_provider.endpoint_url, ai_provider.model_name)
    return OpenAIVerificationProvider(key, ai_provider.endpoint_url, ai_provider.model_name)
