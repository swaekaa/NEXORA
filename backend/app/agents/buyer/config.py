"""
NEXORA — Buyer Agent Configuration

Provides a thin ChatModel abstraction so production can use langchain-openai
while tests can inject a deterministic fake model.
"""

from langchain_core.language_models import BaseChatModel

from app.config import settings


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Returns the configured LLM for the Buyer Agent.
    In testing or if LLM_API_KEY is not set, we can return a fake.
    """
    # For Phase 5 development, if API key is not present or we're in test mode,
    # we might want to return a Fake model, but since we inject fake models
    # dynamically in our pytest fixtures, here we just return the real one by default
    # and fail fast if the key is missing (unless we are explicitly testing).
    
    # We will use ChatOpenAI as requested by the plan.
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise RuntimeError("langchain-openai is not installed. Run 'pip install langchain-openai'")
        
    if not settings.LLM_API_KEY and not settings.is_test:
        raise ValueError("LLM_API_KEY must be set in the environment to run the Buyer Agent.")

    # Even in test mode, if get_llm is called, it might instantiate ChatOpenAI.
    # The tests will override the LLM directly in the graph or patch this function.
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,
        api_key=settings.LLM_API_KEY or "fake-key-for-tests"
    )
