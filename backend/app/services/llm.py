"""
services/llm.py
───────────────
Single factory function that returns a LangChain chat model based on the
LLM_PROVIDER env variable.  Every agent node calls get_llm() instead of
constructing the model directly — so you can switch providers in .env
without touching any node file.

Usage in a node:
    from app.services.llm import get_llm
    self.llm = get_llm()
"""

import os
import logging
from app.config import (
    LLM_PROVIDER,
    GROQ_API_KEY, GROQ_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    HF_API_KEY, HF_MODEL,
    OPENAI_API_KEY, OPENAI_MODEL,
)

logger = logging.getLogger(__name__)


def get_llm(max_tokens: int = 2048):
    """
    Return a LangChain chat model for the configured provider.

    Args:
        max_tokens: Maximum tokens to generate (default 2048).

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider is unknown or required keys are missing.
    """
    provider = LLM_PROVIDER.strip().lower()
    logger.info(f"LLM provider: {provider}")

    # ── Groq ──────────────────────────────────────────────────────────────────
    if provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com"
            )
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("Run: pip install langchain-groq")

        logger.info(f"Using Groq model: {GROQ_MODEL}")
        return ChatGroq(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
            max_tokens=max_tokens,
            temperature=0.3,
        )

    # ── Ollama (local) ────────────────────────────────────────────────────────
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError("Run: pip install langchain-ollama")

        logger.info(f"Using Ollama model: {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
        return ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            num_predict=max_tokens,
            temperature=0.3,
        )

    # ── HuggingFace ───────────────────────────────────────────────────────────
    if provider == "huggingface":
        if not HF_API_KEY:
            raise ValueError("HF_API_KEY is not set.")
        try:
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        except ImportError:
            raise ImportError("Run: pip install langchain-huggingface")

        logger.info(f"Using HuggingFace model: {HF_MODEL}")
        return ChatHuggingFace(
            llm=HuggingFaceEndpoint(
                repo_id=HF_MODEL,
                huggingfacehub_api_token=HF_API_KEY,
                task="text-generation",
                max_new_tokens=max_tokens,
            )
        )

    # ── OpenAI ────────────────────────────────────────────────────────────────
    if provider == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set.")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Run: pip install langchain-openai")

        logger.info(f"Using OpenAI model: {OPENAI_MODEL}")
        return ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            max_tokens=max_tokens,
            temperature=0.3,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER: '{provider}'. "
        "Choose from: groq, ollama, huggingface, openai"
    )