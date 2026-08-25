# Phase 6 — Merchant Agent Implementation Plan

This document outlines the architecture and execution strategy for building the NEXORA Merchant Agent.

## 1. Objective
Build the autonomous Merchant Agent using LangGraph (orchestration) and LangChain (LLM interaction). The agent will evaluate buyer proposals, generate counter-offers, accept, or reject them, while being strictly bounded by the deterministic Phase 4 Policy Engine.

**CRITICAL RULE ENFORCED:** The LLM will NEVER independently authorize a financially invalid transaction. Deterministic systems evaluate policy.

## 2. Dependencies
No new dependencies are required. We will reuse the Phase 5 agent stack (LangGraph, LangChain, OpenAI).

## 3. Proposed Architecture (`backend/app/agents/merchant/`)

### Files to Create:
- `__init__.py`: Module exports.
- `schemas.py`: 
  - `MerchantAgentState` (TypedDict for LangGraph)
  - `ActionType` enum (`REVIEW_PROPOSAL`, `ACCEPT_PROPOSAL`, `REJECT_PROPOSAL`, `COUNTER_PROPOSAL`, `REQUEST_HUMAN_APPROVAL`, `STOP`)
  - `MerchantAgentAction` (Pydantic structured output)
- `config.py`: Reusing the dependency injection approach from Buyer Agent (`get_llm()`).
- `prompts.py`: strict `SYSTEM_INSTRUCTION` that treats buyer messages as untrusted and outlines merchant goals.
- `nodes.py`:
  - `run_llm_node`
  - `execute_action_node`
  - `validate_counter_offer_node` (Deterministic math calculation using Decimal)
- `policy_node.py`:
  - `policy_check_node` (invokes `PolicyEngine`)
  - `route_policy_decision`
  - `counter_offer_recovery_node`
- `graph.py`: The compiled StateGraph orchestrating the flow.

## 4. Negotiation Service Updates (`backend/app/services/negotiation_service.py`)

- **Fix `create_negotiation_with_proposal`**: Currently it incorrectly passes fields like `proposed_unit_price` directly to `NegotiationMessage` instead of packing them into the `payload` JSONB column.
- **Add `append_negotiation_message`**: Securely adds an event to the `NegotiationMessage` table and updates `Negotiation.round_count`.
- **Add `update_negotiation_state`**: Transitions the `Negotiation` to `ACCEPTED`, `REJECTED`, or `EXPIRED`.

## 5. Security & Determinism Boundaries
- **Immutable Proposals**: Any change in price/quantity generates a NEW message. We never mutate history.
- **Untrusted Input**: Buyer proposals are passed as context to the LLM but explicitly marked as untrusted to prevent prompt injections.
- **Max Rounds**: Enforce `MAX_NEGOTIATION_ROUNDS = 10` on the orchestration layer.
- **Max Revisions**: The Merchant LLM gets a maximum of 3 revisions if its counter-offer violates policy (e.g. going below minimum price).

## 6. Testing Strategy

### Unit Tests (`backend/tests/unit/test_merchant_agent.py`)
Use `MagicMock` (no real LLM) to verify:
- Valid counter-offers pass PolicyEngine.
- Invalid counter-offers trigger DENY and recovery loops.
- Reaching revision limits results in failure.
- Accept/Reject actions transition state correctly.

### Integration Tests (`backend/tests/integration/test_agent_negotiation.py`)
Test the end-to-end multi-agent persistent protocol:
1. Buyer Agent generates proposal.
2. Saved to `NegotiationMessage`.
3. Merchant Agent evaluates and counters.
4. Saved to `NegotiationMessage`.
5. Validations, constraints, and PolicyEngine execution are verified.
