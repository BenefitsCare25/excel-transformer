"""
Multi-provider AI abstraction layer. Supports Anthropic, OpenAI, and Google Gemini.
Keys are passed per-request and never stored.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """Send a completion request and return the text response."""
        ...

    def test_connection(self) -> bool:
        """Test the API key works by sending a minimal request."""
        try:
            result = self.complete("You are a test assistant.", "Say 'ok'", max_tokens=5)
            return bool(result)
        except Exception as e:
            logger.warning(f"AI provider test failed: {e}")
            return False


class AnthropicProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = 'claude-haiku-4-5-20251001'):
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{'role': 'user', 'content': user}]
        )
        return message.content[0].text


class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = 'gpt-4o-mini'):
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ]
        )
        return response.choices[0].message.content


class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = 'gemini-2.0-flash'):
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
            contents=user,
        )
        return response.text


class AIProviderFactory:
    SUPPORTED_PROVIDERS = {
        'anthropic': {
            'class': AnthropicProvider,
            'models': ['claude-haiku-4-5-20251001', 'claude-sonnet-4-6'],
            'default_model': 'claude-haiku-4-5-20251001',
        },
        'openai': {
            'class': OpenAIProvider,
            'models': ['gpt-4o-mini', 'gpt-4o'],
            'default_model': 'gpt-4o-mini',
        },
        'gemini': {
            'class': GeminiProvider,
            'models': ['gemini-2.0-flash', 'gemini-2.5-pro-preview-03-25'],
            'default_model': 'gemini-2.0-flash',
        },
    }

    @staticmethod
    def get_provider(provider: str, api_key: str, model: Optional[str] = None) -> BaseAIProvider:
        provider = provider.lower()
        if provider not in AIProviderFactory.SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider '{provider}'. Supported: {list(AIProviderFactory.SUPPORTED_PROVIDERS)}")

        cfg = AIProviderFactory.SUPPORTED_PROVIDERS[provider]
        resolved_model = model or cfg['default_model']
        return cfg['class'](api_key=api_key, model=resolved_model)

    @staticmethod
    def list_providers() -> dict:
        return {
            name: {'models': cfg['models'], 'default_model': cfg['default_model']}
            for name, cfg in AIProviderFactory.SUPPORTED_PROVIDERS.items()
        }
