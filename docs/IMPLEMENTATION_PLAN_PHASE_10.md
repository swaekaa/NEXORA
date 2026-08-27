# Phase 10: AI Buyer Agent Implementation Plan

**Goal**: Transform the Phase 5 Buyer Agent prototype into a complete, autonomous procurement agent that can negotiate multi-round deals with the Merchant Agent, bounded by strict deterministic financial constraints ("LLMs PROPOSE. DETERMINISTIC SYSTEMS DECIDE").

## 1. Research & Audit Summary
- **Existing Phase 5 Baseline**: Found in `backend/app/agents/buyer/`. It includes `schemas.py`, `prompts.py`, `nodes.py`, `policy_node.py`, `graph.py`, and `tools.py`. It currently implements a basic "one-shot" proposal flow with deterministic calculation of totals.
- **Missing Functionality**:
  - `BuyerConstraintEngine` to deterministically block budget violations.
  - Multi-round negotiation loops integrating with `NegotiationService`.
  - Dynamic product search using `ProductService`.
  - `runner.py` to instantiate and execute the agent reliably without polluting API endpoints.
  - Audit logging for agent actions.
- **Note on Baseline Tests**: The `pytest` test runner was temporarily blocked by a local filesystem permissions error in the environment, but based on Phase 9's final report, the baseline is exactly 246 passing tests.

## User Review Required
> [!IMPORTANT]
> The AI Agent will run autonomously and negotiate financial terms. We are implementing a strict `BuyerConstraintEngine` to ensure the agent never exceeds its maximum budget, and integrating the existing `PolicyEngine` to ensure it never violates merchant policies. 
> 
> We will also implement a strict limit on the number of negotiation rounds and the number of graph steps to prevent infinite looping and excessive LLM API costs.

## Proposed Changes

We will strictly follow the 14-step workflow, implementing this incrementally.

### 1. Schemas & Core Data Models
Update the schemas in `backend/app/agents/buyer/schemas.py`.
- **Modify** `BuyerIntent` to enforce stricter validation on limits.
- **Modify** `BuyerAgentState` to track multi-round negotiations, merchant counteroffers, and negotiation IDs.
- **Modify** `BuyerAgentAction` to support `COUNTER_PROPOSAL` and `ACCEPT_COUNTER`.

### 2. Buyer Constraint Engine
#### [NEW] `backend/app/agents/buyer/constraints.py`
- Implement `BuyerConstraintEngine` to independently evaluate proposals and merchant counteroffers against the buyer's budget and requirements. 
- Must use `Decimal` for all calculations and reject proposals where `unit_price * quantity > maximum_budget`.

### 3. Agent Tools
#### [MODIFY] `backend/app/agents/buyer/tools.py`
- Update `search_products` to safely query the database via `ProductService` instead of relying on a pre-injected list.
- Return bounded DTOs to the LLM (omitting database internals).

### 4. LangGraph Evolution
#### [MODIFY] `backend/app/agents/buyer/graph.py` & `nodes.py`
- Evolve the state machine to handle the full negotiation lifecycle:
  - `START` -> `parse_intent` -> `discover_products` -> `select_product` -> `create_negotiation` -> `wait_for_merchant` -> `evaluate_response` -> `[ACCEPT, COUNTER, REJECT]`
- Implement strict deterministic boundaries in the nodes. The LLM's proposed totals are dropped in favor of recalculated `unit_price * qty`.

### 5. Negotiation Integration & Handoff
#### [MODIFY] `backend/app/agents/buyer/nodes.py`
- Connect nodes directly to `NegotiationService` to read and append messages.
- Upon `ACCEPTED` state, trigger `AgreementService` to generate the immutable commercial agreement.
- Do NOT allow the LLM to write to the database directly.

### 6. Audit Logging
- Integrate `AuditService` in critical graph nodes to record immutable lifecycle events (e.g., `BUYER_INTENT_PARSED`, `PROPOSAL_GENERATED`, `NEGOTIATION_ACCEPTED`).

### 7. Orchestration & API
#### [NEW] `backend/app/agents/buyer/runner.py`
- Create a reusable orchestrator that abstracts the LangGraph execution away from API routes.
#### [NEW] `backend/app/api/v1/endpoints/buyers_agent.py`
- Create `POST /api/v1/buyers/{buyer_id}/agent/runs` to kick off the agent asynchronously.

## Verification Plan

### Automated Tests
We will add extensive unit and integration tests to guarantee financial safety.
- **`backend/tests/unit/test_buyer_constraints.py`**: Assert `BuyerConstraintEngine` denies budget violations.
- **`backend/tests/unit/test_buyer_agent.py`**: Assert structured output parsing, deterministic recalculation of hallucinated totals, and prompt injection defense.
- **`backend/tests/integration/test_buyer_agent_flow.py`**: Full mock end-to-end negotiation loop without external API calls. Ensure DB state is correctly mutated through services.

### End-to-End Regression
Run `pytest` to ensure all 246 existing tests continue to pass alongside the new Phase 10 suite.
