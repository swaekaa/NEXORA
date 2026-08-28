"""
NEXORA Backend — Centralized LLM Factory
"""

from langchain_core.language_models import BaseChatModel

from app.config import settings

def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Returns the configured Gemini model.
    Uses the centralized GEMINI_MODEL configuration.
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise RuntimeError("langchain-google-genai is not installed. Run 'pip install langchain-google-genai'")
        
    api_key = settings.GEMINI_API_KEY or settings.LLM_API_KEY
    if not api_key and not settings.is_test:
        raise ValueError("GEMINI_API_KEY must be set in the environment to run the agents.")

    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        temperature=temperature,
        api_key=api_key or "fake-key-for-tests",
        max_retries=2, # Allow 1 retry for transient 504s/503s, but limit to prevent 60s 404 loops
        timeout=30.0   # Enforce a 30s timeout so 504s fail faster if Google hangs
    )
