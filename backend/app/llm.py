"""
NEXORA Backend — Centralized LLM Factory
"""

from langchain_core.language_models import BaseChatModel

from app.config import settings

def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Returns the configured Azure OpenAI model (GPT-4.1-mini).
    Uses the centralized AZURE_OPENAI_ configuration.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise RuntimeError("langchain-openai is not installed. Run 'pip install langchain-openai'")
        
    if not settings.AZURE_OPENAI_API_KEY and not settings.is_test:
        raise ValueError("AZURE_OPENAI_API_KEY must be set in the environment to run the agents.")
        
    if not settings.AZURE_OPENAI_ENDPOINT and not settings.is_test:
        raise ValueError("AZURE_OPENAI_ENDPOINT must be set in the environment to run the agents.")

    if not settings.AZURE_OPENAI_DEPLOYMENT_NAME and not settings.is_test:
        raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME must be set in the environment to run the agents.")

    logger.info("LLM_PROVIDER=azure-foundry-serverless")
    logger.info(f"LLM_MODEL={settings.AZURE_OPENAI_DEPLOYMENT_NAME}")

    return ChatOpenAI(
        base_url=settings.AZURE_OPENAI_ENDPOINT or "https://fake-endpoint.openai.azure.com/openai/v1",
        api_key=settings.AZURE_OPENAI_API_KEY or "fake-key-for-tests",
        model=settings.AZURE_OPENAI_DEPLOYMENT_NAME or "gpt-4.1-mini",
        temperature=temperature,
        max_retries=2, # Allow 1 retry for transient 504s/503s
        timeout=30.0   # Enforce a 30s timeout
    )
