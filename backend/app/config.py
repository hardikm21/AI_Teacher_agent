"""
config.py — single place to configure the LLM provider.

Set LLM_PROVIDER in your .env file:
  LLM_PROVIDER=groq        → Groq cloud (free tier, recommended)
  LLM_PROVIDER=ollama      → Ollama local (completely free, needs Ollama installed)
  LLM_PROVIDER=huggingface → HuggingFace Inference (requires paid credits)
  LLM_PROVIDER=openai      → OpenAI (requires paid credits)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Provider selection ────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

# ── Groq ──────────────────────────────────────────────────────────────────────
# Free tier: https://console.groq.com → create account → API Keys
# Recommended model: llama-3.1-8b-instant (fast, free)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ── Ollama (local) ────────────────────────────────────────────────────────────
# Install: https://ollama.com → `ollama pull llama3.1`
# Runs on your machine, completely free, no API key needed
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.1")

# ── HuggingFace ───────────────────────────────────────────────────────────────
HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_MODEL   = os.getenv("LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── GitHub ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# ── Sarvam AI (multilingual voice) ────────────���───────────────────────────────
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")