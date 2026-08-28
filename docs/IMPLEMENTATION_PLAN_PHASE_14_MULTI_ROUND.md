# Multi-Round AI Negotiation Demo

This plan details the changes required to upgrade the single-round acceptance flow into a rich, multi-round negotiation, preserving all deterministic boundaries.

## Architectural Audit & Root Cause Analysis (13-Point Report)

1. **Current Buyer graph**: `backend/app/agents/buyer/graph.py` routes `run_llm` -> `execute_action` -> `validate_proposal` (invokes `BuyerConstraintEngine`) -> `policy_check` (improperly invokes Merchant `PolicyEngine`) -> `submit_proposal`.
2. **Current Merchant graph**: `backend/app/agents/merchant/graph.py` routes `run_llm` -> `validate_action` -> `policy_check` (invokes `PolicyEngine`) -> `submit_decision` or `request_approval`.
3. **Current orchestrator**: `backend/app/services/orchestrator.py` loops up to 20 times, checking `negotiation.state`. If `OFFER`, triggers Merchant. If `COUNTER_OFFER`, triggers Buyer. Breaks on terminal states.
4. **Current round-counting mechanism**: `NegotiationService.append_negotiation_message` increments `round_count` exclusively when the Buyer sends a subsequent `COUNTER_OFFER` (meaning a full back-and-forth exchange constitutes a round).
5. **Current acceptance routing**: The Merchant LLM chooses `ACCEPT_PROPOSAL`, routing to `policy_check` (which validates the accepted price against Merchant policy), then routes to `submit_decision` (which writes to the DB) and AgreementService.
6. **Current PolicyEngine invocation points**: Invoked in both `BuyerAgent` (`policy_node.py`) and `MerchantAgent` (`policy_node.py`).
7. **Current BuyerConstraintEngine invocation points**: Invoked exclusively in `BuyerAgent` (`nodes.py -> validate_proposal_node`).
8. **Current NegotiationService persistence calls**: Used cleanly inside `buyer/nodes.py` (`submit_proposal_node`) and `merchant/nodes.py` (`submit_decision_node`). No raw DB writes exist for messages.
9. **Current frontend polling behavior**: `usePolling` fetches the DB state every 2 seconds. It correctly stops polling when the `stopCondition` is met (`ACCEPTED`, `REJECTED`, `EXPIRED`). It only performs `GET` requests; agent execution is distinct (`POST /agent/runs`).
10. **Exact cause of immediate acceptance**: The Buyer was previously forced to offer exactly the Merchant's minimum price to bypass the improper `PolicyEngine` check inside the Buyer's own graph. Since the offer satisfied all Merchant conditions, the Merchant LLM logically accepted it on Round 1.
11. **Exact files requiring changes**: 
    - `backend/app/agents/buyer/policy_node.py` (Remove `PolicyEngine`)
    - `backend/app/agents/buyer/prompts.py` (Add Demo Strategy)
    - `backend/app/agents/merchant/prompts.py` (Add Demo Strategy)
    - `backend/app/agents/merchant/policy_node.py` or `nodes.py` (Enforce Demo Strategy deterministic bounds)
    - `backend/app/services/orchestrator.py` (Add structured logging)
    - `backend/tests/integration/test_multi_round_negotiation.py` (New tests)
12. **How I will guarantee 3+ genuine rounds without fake messages**: I will introduce a deterministic demo negotiation rule: `DEMO_MIN_ROUNDS = 3`. If the Merchant LLM generates `ACCEPT_PROPOSAL` before `round >= 3`, the Merchant's deterministic layer will intercept the action and send feedback back to the LLM: "Demo Strategy requires a COUNTER_PROPOSAL for the first 3 rounds. Generate a realistic counteroffer instead." The LLM will then generate a real counteroffer, which will be validated and persisted natively.
13. **How I will preserve all existing safety boundaries**: The Merchant's `policy_check_node` will still run `PolicyEngine.evaluate()`. If a generated counteroffer or an eventual acceptance violates the mathematical rules (e.g. `unit_price < minimum_price`), it will be deterministically `DENIED`. Human approval limits will still trigger `HUMAN_APPROVAL_REQUIRED`. No dummy data will be injected into `NegotiationService`.

## Proposed Execution Plan

### 1. Fix Buyer Policy Leakage
- **[MODIFY]** `backend/app/agents/buyer/policy_node.py`: Remove the `PolicyEngine` evaluation. The Buyer should only evaluate `BuyerConstraintEngine`.

### 2. Introduce Deterministic Demo Strategy
- **[MODIFY]** `backend/app/agents/merchant/nodes.py` & `backend/app/agents/buyer/nodes.py`: Intercept early `ACCEPT_PROPOSAL` or `ACCEPT_COUNTER` actions when `round < 3`. Return a deterministic prompt feedback forcing the LLM to counteroffer instead.

### 3. Update Prompts for Negotiation Realism
- **[MODIFY]** `backend/app/agents/buyer/prompts.py`: Instruct the Buyer to start below its maximum budget.
- **[MODIFY]** `backend/app/agents/merchant/prompts.py`: Instruct the Merchant to negotiate gradually.

### 4. Upgrade Orchestrator Logging
- **[MODIFY]** `backend/app/services/orchestrator.py`: Add structured logging for each turn (`NEGOTIATION_TURN_STARTED`, `POLICY_CHECK_COMPLETED`, etc.)

### 5. Integration Testing
- **[NEW]** `backend/tests/integration/test_multi_round_negotiation.py`: Add the 8 required deterministic tests (Counteroffer flow, early acceptance interception, policy override, human approval, max rounds, DB truth).

## Verification Plan
1. `pytest -q` to ensure the baseline passes.
2. Run the new multi-round tests.
3. Launch the UI and manually confirm the multi-round ping-pong timeline.

