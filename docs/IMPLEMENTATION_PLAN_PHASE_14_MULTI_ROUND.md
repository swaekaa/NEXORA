# Multi-Round AI Negotiation Demo

This plan details the changes required to upgrade the single-round acceptance flow into a rich, multi-round negotiation, preserving all deterministic boundaries.

## Architectural Audit & Root Cause Analysis

1. **Why the current Merchant accepts immediately:** The Buyer's initial offer was artificially constrained to always be at or above the Merchant's minimum price. When the Merchant LLM receives an offer that already meets all criteria, its prompt tells it to ACCEPT.
2. **Why the current Buyer accepts/reaches the final proposal quickly:** The Buyer Agent's `policy_node.py` was improperly invoking the global `PolicyEngine` (which applies Merchant rules, such as `minimum_unit_price`) to validate the Buyer's *own* outbound proposal. When the Buyer tried to offer a low-ball price (e.g., 9,000), it was deterministically blocked by the Merchant's rules before the Merchant even saw it. The Buyer LLM hit `MAX_PROPOSAL_REVISIONS_EXCEEDED` and crashed.
3. **Where orchestration currently terminates:** The orchestrator loop currently terminates correctly when the state reaches `ACCEPTED`, `REJECTED`, or `EXPIRED`. It correctly toggles between `OFFER` and `COUNTER_OFFER`.
4. **Existing components for reuse:** We will reuse `NegotiationService` for message persistence, `PolicyEngine` (within the Merchant's graph), `BuyerConstraintEngine` (within the Buyer's graph), and the existing LangGraph loops.
5. **Deterministic safety boundaries:** 
   - The **Buyer** will only be constrained by the `BuyerConstraintEngine` (budget limit).
   - The **Merchant LLM** will be allowed to evaluate the Buyer's low-ball offer. If the Merchant LLM mistakenly tries to ACCEPT a price below the floor, the Merchant's own `policy_node.py` (which correctly uses `PolicyEngine`) will deterministically DENY the LLM's action and force it to revise.
   - Human approval limits remain perfectly intact within the Merchant's policy node.

## Proposed Changes

### 1. Decouple Merchant Policy from Buyer Graph
- **[MODIFY]** `backend/app/agents/buyer/policy_node.py`
  - Remove the `PolicyEngine` evaluation. The Buyer should only evaluate `BuyerConstraintEngine` (which is already done in `validate_proposal_node`).
  - The `policy_check_node` will simply check if `policy_decision` was already set to `DENY` by the `BuyerConstraintEngine` and route accordingly.

### 2. Negotiation Strategy Prompts
- **[MODIFY]** `backend/app/agents/buyer/prompts.py`
  - Add explicit "Demo Mode" instruction: *Start bidding at least 20% below your maximum budget to leave room for negotiation. Counter-offer gradually.*
- **[MODIFY]** `backend/app/agents/merchant/prompts.py`
  - Add explicit "Demo Mode" instruction: *Even if the buyer's proposal is above your minimum price, always try to COUNTER_PROPOSAL with a higher price on Round 1 and Round 2 to maximize profit. Accept only when they reach a commercially sound peak.*

### 3. Orchestrator Logging
- **[MODIFY]** `backend/app/services/orchestrator.py`
  - Add explicit structured logs for `NEGOTIATION_TURN_STARTED`, `BUYER_AGENT_TRIGGERED`, `MERCHANT_AGENT_TRIGGERED`, and `NEGOTIATION_TERMINAL`.

### 4. Buyer UI Setup
- **[MODIFY]** `frontend/src/pages/BuyerPage.tsx`
  - Reset the `maximum_budget` to a realistic ceiling (e.g. `1200000.00`) and the default query placeholder to encourage the LLM to negotiate.

### 5. Integration Tests
- **[NEW]** `backend/tests/integration/test_multi_round_negotiation.py`
  - Test 1: Counteroffer flow (alternating messages, round count > 1)
  - Test 2: Merchant deterministic recovery if it accidentally accepts a lowball offer
  - Test 3: Final acceptance to Agreement

## Verification Plan
1. Run `pytest -q` to ensure baseline (246+ tests) passes.
2. Run the new `test_multi_round_negotiation.py`.
3. Launch the full application, initiate a negotiation from the Buyer Console, and visually confirm the multi-round ping-pong in the frontend timeline.

## User Review Required
Does this plan perfectly capture the "LLMs propose, Deterministic systems decide" architecture you envisioned for the demo?
