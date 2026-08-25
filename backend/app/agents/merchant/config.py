"""
NEXORA — Merchant Agent Configuration

Provides a thin ChatModel abstraction so production can use langchain-openai
while tests can inject a deterministic fake model.
"""

from langchain_core.language_models import BaseChatModel

from app.config import settings


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Returns the configured LLM for the Merchant Agent.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise RuntimeError("langchain-openai is not installed. Run 'pip install langchain-openai'")
        
    if not settings.LLM_API_KEY and not settings.is_test:
        raise ValueError("LLM_API_KEY must be set in the environment to run the Merchant Agent.")

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,
        api_key=settings.LLM_API_KEY or "fake-key-for-tests"
    )
