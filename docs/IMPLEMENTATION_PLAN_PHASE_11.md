# Phase 11: AI Merchant Agent Implementation Plan

**Goal**: Upgrade the Phase 6 Merchant Agent prototype into a production-ready, autonomous agent that safely negotiates with the Buyer Agent using a robust, database-persisted protocol.

## 1. Research & Audit Summary
- **Existing Phase 6 Baseline**: We have a prototype in `backend/app/agents/merchant/` that includes schemas, prompts, nodes, policy checks, and a LangGraph workflow. It currently supports ACCEPT, REJECT, COUNTER, and HUMAN_APPROVAL states.
- **Missing Functionality**:
  - **Database Persistence**: The current agent does not persist its output into the PostgreSQL database. It must be updated to use `NegotiationService` to read/write `NegotiationMessage`s.
  - **Agreement Creation**: Must trigger `AgreementService` when a deal is ACCEPTED.
  - **Runner Architecture**: Needs a standard `runner.py` similar to the Buyer Agent to handle safe invocation, dependency injection, and deterministic limits.
  - **API Integration**: Needs a dedicated FastAPI endpoint (`POST /api/v1/merchants/{merchant_id}/agent/runs`) to invoke the workflow.
  - **Audit Logging**: Must record critical events in the `AuditService`.

## User Review Required
> [!IMPORTANT]
> The Merchant Agent acts as the final gatekeeper for the merchant's financial interests. Its counter-offers and acceptance criteria will be strictly checked against the deterministic `PolicyEngine`.
> 
> As requested, we will architect this as a **resumable workflow**. The agent will load state from the DB, execute its logic, persist its response, and then exit. It will **not** block or poll for buyer responses within a single execution loop.

## Open Questions
- Should the `MerchantIntent` load its own context (like product/policy data) inside the runner before kicking off the graph, or should the agent graph actively retrieve it? *(I plan to have the runner retrieve this and pass it into the graph to keep the LLM completely decoupled from DB queries, as was done in Phase 10).*

## Proposed Changes

### 1. Schemas & Data Models
#### [MODIFY] `backend/app/agents/merchant/schemas.py`
- Modify `MerchantIntent` to carry robust data about the specific negotiation and buyer.
- Update `MerchantAgentState` to track execution safely.

### 2. LangGraph Execution Nodes
#### [MODIFY] `backend/app/agents/merchant/nodes.py` & `policy_node.py`
- Ensure the `run_llm_node` properly leverages the existing `MerchantAgentAction` structured outputs.
- Evolve `validate_action_node` to mathematically calculate totals deterministically, ignoring LLM hallucinations.
- Ensure `policy_check_node` correctly formats the `PolicyEvaluationRequest` using deterministic totals.
- Add new nodes for DB persistence (e.g., `submit_decision_node`) to append messages to `NegotiationService` and trigger `AgreementService` on an `ACCEPT_PROPOSAL`.

### 3. Orchestration Runner
#### [NEW] `backend/app/agents/merchant/runner.py`
- Abstract LangGraph execution out of API boundaries.
- Read negotiation history and map it into LLM context.
- Start a local LangGraph cycle that terminates safely by saving the Merchant's response into the database.

### 4. Merchant Agent API
#### [NEW] `backend/app/api/v1/endpoints/merchants_agent.py`
- Implement `POST /api/v1/merchants/{merchant_id}/agent/runs` endpoint.
- Ensure proper merchant ownership validation.

### 5. Audit Logging
- Intertwine `AuditService` in the DB-saving nodes to log events like `MERCHANT_PROPOSAL_EVALUATED`, `MERCHANT_COUNTER_PROPOSAL`, and `MERCHANT_PROPOSAL_ACCEPTED`.

## Verification Plan

### Automated Tests
- **`backend/tests/unit/test_merchant_agent.py`**: Refactor and expand to ensure policy check nodes behave properly (e.g. testing `DENY` loops, prompt injection).
- **`backend/tests/integration/test_multi_agent_negotiation.py`**: Simulate a full end-to-end multi-agent flow by mocking the Buyer's input in the DB and verifying that the Merchant Agent properly interacts with the `NegotiationService` and `PolicyEngine`.

### End-to-End Regression
Run `pytest` to ensure all existing tests (spanning Phase 1-10) continue passing. Validate that no microservices, generic CRUD abstractions, or floating-point decimals were introduced.
