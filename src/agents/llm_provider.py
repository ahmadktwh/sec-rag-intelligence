"""
LiteLLM Provider — Universal AI Bridge
Supports ANY model: gemini, gpt-4, claude, mistral, ollama, etc.
User provides their own API key at runtime via environment or API header.
"""
import os
import logging
import litellm
from litellm import completion, acompletion
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Silence LiteLLM's verbose logging
litellm.suppress_debug_info = True


class LLMProvider:
    """
    Universal LLM wrapper using LiteLLM.
    Users can inject any model and API key — zero cost to the project owner.

    Supported providers (examples):
      - Google:    model="gemini/gemini-2.5-pro"     key=GOOGLE_API_KEY
      - OpenAI:    model="gpt-4o"                    key=OPENAI_API_KEY
      - Anthropic: model="claude-3-5-sonnet-20241022" key=ANTHROPIC_API_KEY
      - Mistral:   model="mistral/mistral-large"     key=MISTRAL_API_KEY
      - Ollama:    model="ollama/llama3"              key=not needed (local)
    """

    def __init__(self, model: str = None, api_key: str = None):
        # Priority: runtime arg > env var > default
        self.model = model or os.getenv("LLM_MODEL", "gemini/gemini-2.5-pro")
        self.api_key = api_key or self._resolve_api_key()
        logger.info(f"LLMProvider initialized with model: {self.model}")

    def _resolve_api_key(self) -> str:
        """Auto-detect API key from environment based on model prefix."""
        model = self.model.lower()
        if model.startswith("gemini/") or model.startswith("google/"):
            return os.getenv("GOOGLE_API_KEY", "")
        elif model.startswith("gpt") or model.startswith("openai/"):
            return os.getenv("OPENAI_API_KEY", "")
        elif model.startswith("claude") or model.startswith("anthropic/"):
            return os.getenv("ANTHROPIC_API_KEY", "")
        elif model.startswith("mistral/"):
            return os.getenv("MISTRAL_API_KEY", "")
        elif model.startswith("ollama/"):
            return "ollama"  # Local, no key needed
        return os.getenv("GOOGLE_API_KEY", "")

    async def ainvoke(self, messages: list, temperature: float = 0.1) -> str:
        """Async invocation — used by LangGraph agent nodes."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            # Inject API key based on provider
            if self.model.startswith("gemini/") or self.model.startswith("google/"):
                kwargs["api_key"] = self.api_key
            elif "gpt" in self.model or self.model.startswith("openai/"):
                kwargs["api_key"] = self.api_key
            elif "claude" in self.model or self.model.startswith("anthropic/"):
                kwargs["api_key"] = self.api_key
            elif self.model.startswith("mistral/"):
                kwargs["api_key"] = self.api_key

            response = await acompletion(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLMProvider error [{self.model}]: {e}")
            raise e

    def invoke(self, messages: list, temperature: float = 0.1) -> str:
        """Sync invocation fallback."""
        try:
            kwargs = {"model": self.model, "messages": messages, "temperature": temperature}
            if not self.model.startswith("ollama/"):
                kwargs["api_key"] = self.api_key
            response = completion(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLMProvider sync error [{self.model}]: {e}")
            raise e
