# LLM Configuration

NEXORA relies on Google's Gemini models for its Agentic interactions (both Buyer and Merchant agents).

## Centralized Configuration

All LLM integrations have been centralized in `backend/app/llm.py`. This ensures that both the Buyer and Merchant agents use the identical foundational configuration and eliminates duplicated configuration code.

## Environment Variables

To configure the LLM, the following environment variables should be set in your `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash
```

*(Note: `LLM_API_KEY` is still supported as a fallback for backward compatibility with older deployments.)*

## Selected Model

We have selected **`gemini-3.7-flash`** (or the latest stable available flash model if `3.7` is unavailable on your key) as the preferred model. 
This model was selected because:
1. It supports `generateContent`.
2. It reliably supports LangChain's Pydantic-based structured output function-calling (unlike some older non-pro/flash aliases that can drop schemas).
3. It has low latency, making it ideal for autonomous multi-agent negotiations.

## Testing & Mocking

**Rule: Do NOT call the real Gemini API from unit tests.**

The centralized `get_llm()` factory in `backend/app/llm.py` is designed to be easily mocked. Because it is imported locally into the specific Agent `nodes.py` files, existing test suites can continue to patch the local symbol:

```python
@patch("app.agents.buyer.nodes.get_llm")
```

This ensures that our 246+ offline tests remain fast, deterministic, and free of network dependencies.

## Error Handling & Failure Behavior

If the LLM fails to generate a response (e.g., if an invalid model is configured and a permanent 404 is thrown, or if the structured output fails completely), the backend API will intercept the failure and return an explicit HTTP `502 Bad Gateway`. It will **not** falsely return an HTTP `200 OK`. 

### Retry Behavior
We have configured `max_retries=1` for the `ChatGoogleGenerativeAI` instance to ensure that permanent 404 configuration errors (e.g. invalid model string) fail-fast rather than repeatedly blocking the agent execution for 60 seconds.
