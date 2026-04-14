"""Shared LLM factory (OpenAI, Google Gemini, or local Ollama)."""

from langchain_community.chat_models import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from ats_agent.src.core.exceptions import ATSAgentConfigError
from ats_agent.src.settings import settings
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)


def _provider_mode() -> str:
    raw = (settings.LLM_PROVIDER or "auto").strip().lower()
    if raw in ("auto", "openai", "google", "ollama"):
        return raw
    return "auto"


def get_llm() -> BaseChatModel:
    """Return chat model from ``LLM_PROVIDER`` and env (keys optional for Ollama)."""
    llm_config = settings.get_llm_config()
    mode = _provider_mode()
    temperature = llm_config["temperature"]
    max_tokens = llm_config["max_tokens"]
    model = llm_config["model"]

    def _openai() -> ChatOpenAI:
        if not settings.OPENAI_API_KEY:
            raise ATSAgentConfigError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai (or auto with this key unset and no other backend)."
            )
        logger.info("Using OpenAI LLM (%s)", model)
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _google() -> ChatGoogleGenerativeAI:
        if not settings.GOOGLE_API_KEY:
            raise ATSAgentConfigError(
                "GOOGLE_API_KEY is required when LLM_PROVIDER=google (or auto with OpenAI key unset)."
            )
        logger.info("Using Google Generative AI (%s)", model)
        return ChatGoogleGenerativeAI(
            google_api_key=settings.GOOGLE_API_KEY,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _ollama() -> ChatOllama:
        logger.info(
            "Using Ollama at %s model=%s",
            settings.OLLAMA_BASE_URL,
            settings.OLLAMA_MODEL,
        )
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=temperature,
            num_predict=max_tokens,
        )

    if mode == "openai":
        return _openai()
    if mode == "google":
        return _google()
    if mode == "ollama":
        return _ollama()

    # auto
    if settings.OPENAI_API_KEY:
        return _openai()
    if settings.GOOGLE_API_KEY:
        return _google()
    return _ollama()
