"""
LLM Client Factory — provider-agnostic interface supporting:
  - Anthropic Claude (cloud)
  - OpenAI (cloud)
  - Ollama (local, mandatory for demo)

Switch providers by changing LLM_PROVIDER in .env — zero code changes.
"""
import time
import httpx
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from app.core.config import Settings, LLMProvider, settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class BaseLLMClient(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Non-streaming chat completion."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[LLMMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion — yields text deltas."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude via official SDK."""

    def __init__(self, cfg: Settings):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=cfg.ANTHROPIC_API_KEY)
            self._model = cfg.ANTHROPIC_MODEL
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _build_messages(self, messages: list[LLMMessage]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

    async def chat(self, messages, system_prompt=None, max_tokens=4096, temperature=0.7) -> str:
        import anthropic
        start = time.time()
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "You are a helpful assistant.",
                messages=self._build_messages(messages),
            )
            latency = round((time.time() - start) * 1000)
            logger.info("llm_response", provider="anthropic", model=self._model,
                        tokens=response.usage.output_tokens, latency_ms=latency)
            return response.content[0].text
        except anthropic.APIConnectionError as e:
            logger.error("anthropic_connection_error", error=str(e))
            raise RuntimeError(f"Anthropic API unreachable: {e}") from e
        except anthropic.AuthenticationError:
            raise RuntimeError("Invalid Anthropic API key. Check ANTHROPIC_API_KEY in .env")

    async def stream_chat(self, messages, system_prompt=None, max_tokens=4096, temperature=0.7):
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "You are a helpful assistant.",
            messages=self._build_messages(messages),
        ) as stream:
            async for text in stream.text_stream:
                yield text


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT via official SDK."""

    def __init__(self, cfg: Settings):
        try:
            import openai
            self._client = openai.AsyncOpenAI(api_key=cfg.OPENAI_API_KEY)
            self._model = cfg.OPENAI_MODEL
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "openai"

    async def chat(self, messages, system_prompt=None, max_tokens=4096, temperature=0.7) -> str:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs += [{"role": m.role, "content": m.content} for m in messages]
        start = time.time()
        response = await self._client.chat.completions.create(
            model=self._model, messages=msgs, max_tokens=max_tokens, temperature=temperature
        )
        latency = round((time.time() - start) * 1000)
        logger.info("llm_response", provider="openai", model=self._model,
                    tokens=response.usage.completion_tokens, latency_ms=latency)
        return response.choices[0].message.content

    async def stream_chat(self, messages, system_prompt=None, max_tokens=4096, temperature=0.7):
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs += [{"role": m.role, "content": m.content} for m in messages]
        stream = await self._client.chat.completions.create(
            model=self._model, messages=msgs, max_tokens=max_tokens,
            temperature=temperature, stream=True
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class OllamaClient(BaseLLMClient):
    """Local Ollama via REST API — no external dependencies required."""

    def __init__(self, cfg: Settings):
        self._base_url = cfg.OLLAMA_BASE_URL.rstrip("/")
        self._model = cfg.OLLAMA_MODEL
        self._timeout = cfg.OLLAMA_TIMEOUT

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def _is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def chat(self, messages, system_prompt=None, max_tokens=4096, temperature=0.7) -> str:
        if not await self._is_available():
            raise RuntimeError(
                f"Ollama is not running at {self._base_url}. "
                "Start it with: ollama serve && ollama pull " + self._model
            )
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs += [{"role": m.role, "content": m.content} for m in messages]

        start = time.time()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={"model": self._model, "messages": msgs, "stream": False,
                      "options": {"temperature": temperature, "num_predict": max_tokens}},
            )
            response.raise_for_status()
            data = response.json()
            latency = round((time.time() - start) * 1000)
            logger.info("llm_response", provider="ollama", model=self._model, latency_ms=latency)
            return data["message"]["content"]

    async def stream_chat(self, messages, system_prompt=None, max_tokens=4096, temperature=0.7):
        if not await self._is_available():
            raise RuntimeError(f"Ollama not available at {self._base_url}")
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs += [{"role": m.role, "content": m.content} for m in messages]

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json={"model": self._model, "messages": msgs, "stream": True,
                      "options": {"temperature": temperature, "num_predict": max_tokens}},
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        chunk = json.loads(line)
                        if not chunk.get("done"):
                            yield chunk.get("message", {}).get("content", "")


def get_llm_client(cfg: Settings = settings) -> BaseLLMClient:
    """
    Factory: return the correct LLM client based on LLM_PROVIDER env var.
    No application code needs to change when switching providers.
    """
    provider = cfg.LLM_PROVIDER

    if provider == LLMProvider.ANTHROPIC:
        if not cfg.ANTHROPIC_API_KEY:
            logger.warning("anthropic_key_missing", fallback="ollama")
            return OllamaClient(cfg)
        return AnthropicClient(cfg)

    elif provider == LLMProvider.OPENAI:
        if not cfg.OPENAI_API_KEY:
            logger.warning("openai_key_missing", fallback="ollama")
            return OllamaClient(cfg)
        return OpenAIClient(cfg)

    elif provider == LLMProvider.OLLAMA:
        return OllamaClient(cfg)

    raise ValueError(f"Unknown LLM provider: {provider}")


# Singleton — shared across requests
_llm_client: Optional[BaseLLMClient] = None


def get_cached_llm_client() -> BaseLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = get_llm_client()
        logger.info("llm_client_initialized",
                    provider=_llm_client.provider_name,
                    model=_llm_client.model_name)
    return _llm_client
