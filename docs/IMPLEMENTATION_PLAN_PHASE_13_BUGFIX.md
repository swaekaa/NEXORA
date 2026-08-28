# Gemini Integration Bugfix & Refactoring Plan

## 1. Goal Description
The current Buyer/Merchant Agent LLM integration fails with a 404 because the hardcoded model (`gemini-1.5-flash-latest`) is deprecated or unavailable on the user's API key. Additionally, model configuration is duplicated, and API failures falsely return HTTP 200. This plan will centralize the LLM configuration, upgrade to the preferred model (`gemini-3.7-flash`), and fix the error propagation without breaking existing deterministic boundaries or unit test mocks.

## 2. Proposed Changes

### Configuration & Centralization
- **Create `backend/app/llm.py`**: A centralized factory for `ChatGoogleGenerativeAI` that both Buyer and Merchant agents will use.
- **Update `backend/app/config.py`**: Add `GEMINI_API_KEY` and `GEMINI_MODEL` (defaulting to `gemini-3.7-flash`) to the environment settings. Fallback to `LLM_API_KEY` for backward compatibility.
- **Update `backend/.env.example`**: Document `GEMINI_API_KEY` and `GEMINI_MODEL`.

### Refactoring Agents
#### [DELETE] `backend/app/agents/buyer/config.py`
#### [DELETE] `backend/app/agents/merchant/config.py`
#### [MODIFY] `backend/app/agents/buyer/nodes.py`
- Change `from app.agents.buyer.config import get_llm` to `from app.llm import get_llm`.
#### [MODIFY] `backend/app/agents/merchant/nodes.py`
- Change `from app.agents.merchant.config import get_llm` to `from app.llm import get_llm`.

> [!TIP]
> This specific import change ensures that existing test mocks (e.g., `@patch("app.agents.buyer.nodes.get_llm")`) remain perfectly intact because they mock the function where it is consumed.

### API Error Handling
#### [MODIFY] `backend/app/api/v1/endpoints/buyers_agent.py`
- Inspect `final_state["status"]`. If it is `"failed"`, raise an `HTTPException(status_code=502, detail=...)` or return a structured application-level error so that the HTTP status accurately reflects the internal agent crash.
#### [MODIFY] `backend/app/api/v1/endpoints/merchants_agent.py`
- Apply the same error propagation fix.

### Documentation
#### [NEW] `docs/LLM_CONFIGURATION.md`
- Document the new centralized configuration, test mocking strategy, and how to change models.

## 3. Verification Plan
- Run `pytest` to ensure all existing unit and integration tests pass (verifying that test mocks are unbroken).
- Start `uvicorn app.main:app` and manually trigger a negotiation via the UI to verify `gemini-3.7-flash` successfully negotiates an agreement.
