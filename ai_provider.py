"""
AI provider abstraction.

A single `AIProvider` interface with five implementations:
  - ManualProvider     : no AI - returns a placeholder so the user edits text by hand
  - OpenAIProvider     : OpenAI direct (api.openai.com)
  - AzureOpenAIProvider: Azure OpenAI Service (corporate)
  - AnthropicProvider  : Claude
  - OllamaProvider     : local Ollama

All providers expose the same `complete(prompt, system=None, temperature=0.0, max_tokens=4000)` method
returning a string. Callers (the normalizer) don't know which provider is active.

Provider selection happens via `get_provider(settings_dict)` which reads the
"ai" block from settings.yaml.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AIError(Exception):
    pass


class AIProvider:
    """Base class. Subclasses implement `complete`."""

    name: str = "base"
    model: str = ""

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4000,
        retry: int = 2,
    ) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        """Quick check whether this provider is usable (deps + config)."""
        return False


# --------------------------------------------------------------------------- Manual
class ManualProvider(AIProvider):
    """No AI - returns a marker that the UI can detect and prompt for manual edit."""
    name = "manual"
    model = "manual"

    def complete(self, prompt, system=None, temperature=0.0, max_tokens=4000, retry=2) -> str:
        # Return a JSON marker the caller can detect
        return json.dumps({
            "_manual_mode": True,
            "message": "AI provider is set to 'manual'. Edit the extracted text by hand in the Review tab.",
        })

    def is_available(self) -> bool:
        return True


# --------------------------------------------------------------------------- OpenAI direct
class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None):
        if not api_key:
            raise AIError("OpenAI API key is missing. Add it in Settings.")
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise AIError("openai package not installed. Run: pip install openai") from e
        # base_url lets us point at any OpenAI-compatible server
        # (LM Studio, llama.cpp, vLLM, Ollama's /v1 endpoint, etc.)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def complete(self, prompt, system=None, temperature=0.0, max_tokens=4000, retry=2) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        last_err: Optional[Exception] = None
        for attempt in range(retry + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                last_err = e
                logger.warning(f"OpenAI call failed (attempt {attempt+1}/{retry+1}): {e}")
                time.sleep(2 ** attempt)
        raise AIError(f"OpenAI call failed after {retry+1} attempts: {last_err}")

    def is_available(self) -> bool:
        return True


# --------------------------------------------------------------------------- Local OpenAI-compatible server
# Works with: LM Studio, llama.cpp server, vLLM, Ollama's /v1 endpoint,
# LocalAI, text-generation-webui with OpenAI extension, etc.
# Use this to run GLM-4.6 (or any open-weight GLM) locally via any of the
# desktop agents above.
class LocalServerProvider(AIProvider):
    name = "local_server"

    def __init__(self, base_url: str, model: str = "glm-4.6", api_key: str = "local"):
        if not base_url:
            raise AIError("Local server: base_url is required (e.g. http://localhost:1234/v1)")
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise AIError("openai package not installed. Run: pip install openai") from e
        # Local servers typically don't check the key, but the SDK requires one
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url
        self.model = model

    def complete(self, prompt, system=None, temperature=0.0, max_tokens=4000, retry=2) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        last_err: Optional[Exception] = None
        for attempt in range(retry + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                last_err = e
                logger.warning(f"Local server call failed (attempt {attempt+1}/{retry+1}): {e}")
                time.sleep(2 ** attempt)
        raise AIError(f"Local server call failed after {retry+1} attempts: {last_err}")

    def is_available(self) -> bool:
        try:
            # Try a tiny request to verify the server is up
            self.client.models.list()
            return True
        except Exception:
            return False


# --------------------------------------------------------------------------- Azure OpenAI
class AzureOpenAIProvider(AIProvider):
    name = "azure_openai"

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        api_version: str = "2024-06-01",
        deployment_name: str = "gpt-4o-mini",
        model: str = "gpt-4o-mini",
    ):
        if not api_key or not endpoint:
            raise AIError("Azure OpenAI: api_key and endpoint are required.")
        try:
            from openai import AzureOpenAI  # type: ignore
        except ImportError as e:
            raise AIError("openai package not installed. Run: pip install openai") from e
        self.client = AzureOpenAI(
            api_key=api_key, azure_endpoint=endpoint, api_version=api_version,
        )
        self.deployment_name = deployment_name
        self.model = model

    def complete(self, prompt, system=None, temperature=0.0, max_tokens=4000, retry=2) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        last_err: Optional[Exception] = None
        for attempt in range(retry + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.deployment_name,  # Azure uses deployment name here
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                last_err = e
                logger.warning(f"Azure OpenAI call failed (attempt {attempt+1}/{retry+1}): {e}")
                time.sleep(2 ** attempt)
        raise AIError(f"Azure OpenAI call failed after {retry+1} attempts: {last_err}")

    def is_available(self) -> bool:
        return True


# --------------------------------------------------------------------------- Anthropic
class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        if not api_key:
            raise AIError("Anthropic API key is missing.")
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise AIError("anthropic package not installed. Run: pip install anthropic") from e
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, prompt, system=None, temperature=0.0, max_tokens=4000, retry=2) -> str:
        last_err: Optional[Exception] = None
        for attempt in range(retry + 1):
            try:
                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if system:
                    kwargs["system"] = system
                resp = self.client.messages.create(**kwargs)
                # Anthropic returns a list of content blocks
                parts = []
                for block in resp.content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
                return "".join(parts)
            except Exception as e:
                last_err = e
                logger.warning(f"Anthropic call failed (attempt {attempt+1}/{retry+1}): {e}")
                time.sleep(2 ** attempt)
        raise AIError(f"Anthropic call failed after {retry+1} attempts: {last_err}")

    def is_available(self) -> bool:
        return True


# --------------------------------------------------------------------------- Ollama
class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        try:
            import ollama  # type: ignore
        except ImportError as e:
            raise AIError("ollama package not installed. Run: pip install ollama") from e
        self.client = ollama.Client(host=host)
        self.host = host
        self.model = model

    def complete(self, prompt, system=None, temperature=0.0, max_tokens=4000, retry=2) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        last_err: Optional[Exception] = None
        for attempt in range(retry + 1):
            try:
                resp = self.client.chat(
                    model=self.model,
                    messages=msgs,
                    options={"temperature": temperature, "num_predict": max_tokens},
                )
                return resp["message"]["content"] or ""
            except Exception as e:
                last_err = e
                logger.warning(f"Ollama call failed (attempt {attempt+1}/{retry+1}): {e}")
                time.sleep(2 ** attempt)
        raise AIError(f"Ollama call failed after {retry+1} attempts: {last_err}")

    def is_available(self) -> bool:
        try:
            self.client.list()
            return True
        except Exception:
            return False


# --------------------------------------------------------------------------- Factory
def get_provider(settings: dict[str, Any]) -> AIProvider:
    """
    Build an AIProvider from the "ai" block of settings.yaml.

    Returns ManualProvider if provider is 'manual' or any error occurs - this
    makes the app robust: a misconfigured API key never blocks the pipeline.
    """
    ai = settings.get("ai", {}) or {}
    provider_name = ai.get("provider", "manual")

    try:
        if provider_name == "manual":
            return ManualProvider()

        elif provider_name == "openai":
            cfg = ai.get("openai", {}) or {}
            return OpenAIProvider(
                api_key=cfg.get("api_key", ""),
                model=cfg.get("model", "gpt-4o-mini"),
            )

        elif provider_name == "azure_openai":
            cfg = ai.get("azure_openai", {}) or {}
            return AzureOpenAIProvider(
                api_key=cfg.get("api_key", ""),
                endpoint=cfg.get("endpoint", ""),
                api_version=cfg.get("api_version", "2024-06-01"),
                deployment_name=cfg.get("deployment_name", "gpt-4o-mini"),
                model=cfg.get("model", "gpt-4o-mini"),
            )

        elif provider_name == "anthropic":
            cfg = ai.get("anthropic", {}) or {}
            return AnthropicProvider(
                api_key=cfg.get("api_key", ""),
                model=cfg.get("model", "claude-3-5-sonnet-20241022"),
            )

        elif provider_name == "ollama":
            cfg = ai.get("ollama", {}) or {}
            return OllamaProvider(
                host=cfg.get("host", "http://localhost:11434"),
                model=cfg.get("model", "llama3.1:8b"),
            )

        elif provider_name == "local_server":
            cfg = ai.get("local_server", {}) or {}
            return LocalServerProvider(
                base_url=cfg.get("base_url", "http://localhost:1234/v1"),
                model=cfg.get("model", "glm-4.6"),
                api_key=cfg.get("api_key", "local"),
            )

        else:
            logger.warning(f"Unknown AI provider '{provider_name}', falling back to manual")
            return ManualProvider()

    except AIError as e:
        logger.warning(f"AI provider init failed: {e}. Falling back to manual.")
        return ManualProvider()
    except Exception as e:
        logger.warning(f"Unexpected AI provider init error: {e}. Falling back to manual.")
        return ManualProvider()
