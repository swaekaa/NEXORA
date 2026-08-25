# NEXORA — Merchant Agent

## 1. Purpose
The Merchant Agent represents the merchant's commercial interests during autonomous negotiations on NEXORA. It evaluates incoming buyer proposals, references the merchant's active policy constraints, and decides whether to ACCEPT, REJECT, or issue a COUNTER_PROPOSAL.

## 2. Architecture
The Merchant Agent is orchestrated via LangGraph, with LangChain handling the interaction with the underlying LLM. The agent is entirely bounded by a deterministic PolicyEngine.

**Architectural Flow:**
`Buyer Proposal → NegotiationService (DB) → Merchant Agent (LLM) → Deterministic Total Calculation → PolicyEngine Evaluation → Allowed Action → NegotiationService (DB)`

Crucially, there is **NO direct LLM-to-LLM communication**. All communication is mediated through the persisted, immutable `NegotiationMessage` history.

## 3. LangGraph Structure
The graph compiles several nodes to strictly enforce policy:
- **`run_llm_node`**: Invokes the LLM to generate a structured `MerchantAgentAction`.
- **`validate_action_node`**: Deterministically recalculates the total amount (`quantity * unit_price`). The LLM's hallucinated totals are discarded.
- **`policy_check_node`**: Bypasses the LLM entirely and feeds the proposed terms into the Phase 4 `PolicyEngine`.
- **`counter_offer_recovery_node`**: If the PolicyEngine denies a counter-proposal (e.g., unit price below minimum), this node feeds the explicit failure reasons back to the LLM to attempt a revision (up to `MAX_COUNTER_REVISIONS`).

## 4. State & Actions

### MerchantAgentState
The LangGraph runtime state tracks:
- `intent`: The buyer's proposal and merchant policy context.
- `current_action`: The Pydantic-validated action chosen by the LLM.
- `deterministic_total`: The exact calculated total value.
- `policy_decision`: The output of the PolicyEngine (`ALLOW`, `DENY`, `HUMAN_APPROVAL_REQUIRED`).
- `proposal_revisions`: Integer tracking how many times the LLM has attempted an invalid counter-offer.

### Allowed Actions
The LLM is strictly limited to an Enum of actions:
1. `ACCEPT_PROPOSAL`: Merchant agrees to the buyer's terms. (Still routed through PolicyEngine for deterministic verification).
2. `REJECT_PROPOSAL`: Merchant outright rejects the terms.
3. `COUNTER_PROPOSAL`: Merchant suggests new terms.
4. `REQUEST_HUMAN_APPROVAL`: Merchant escalates to a human manager.
5. `STOP`: Terminal state.

## 5. Security & Boundary Enforcement
1. **Deterministic Calculations**: Financial values are exclusively calculated using `Decimal` in Python. The LLM cannot authorize arbitrary totals.
2. **Policy Enforcement**: The `PolicyEngine` determines if a proposal is valid. The LLM cannot override a `DENY`.
3. **Prompt Injection Defense**: Buyer messages are passed as context but the system prompt explicitly marks them as untrusted. The LLM is instructed to ignore buyer demands that violate policy.
4. **Bounded Revisions**: The LLM gets a maximum of 3 attempts (`MAX_COUNTER_REVISIONS`) to generate a valid counter-offer before the negotiation errors out.
5. **Bounded Negotiation Rounds**: The orchestrator enforces `MAX_NEGOTIATION_ROUNDS = 10` to prevent infinite LLM chatter loops.

## 6. Integration with NegotiationService
The `NegotiationService` serves as the persistence boundary. When the Merchant Agent completes a successful run, its output is atomically appended to the `NegotiationMessage` table via `append_negotiation_message`. This ensures an auditable history of all agent reasoning and actions.
