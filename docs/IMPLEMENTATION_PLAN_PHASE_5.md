# Phase 5 — Buyer Agent Implementation Plan

This document outlines the architecture and execution strategy for building the NEXORA Buyer Agent.

## 1. Objective
Build the autonomous Buyer Agent using LangGraph (orchestration) and LangChain (LLM interaction). The agent will interpret buyer intent, discover products, generate proposals, and validate them deterministically using the Phase 4 Policy Engine.

**CRITICAL RULE ENFORCED:** The LLM will NEVER calculate authoritative financial totals, execute payments, or override policy. 

## 2. Dependencies to Add
We will append the following to `backend/requirements.txt`:
```text
# ── AI Agents (Phase 5+) ──────────────────────────────────────────────────────
langgraph==0.1.19
langchain==0.2.11
langchain-openai==0.1.19
langchain-core==0.2.23
```

## 3. Proposed Architecture (`backend/app/agents/buyer/`)

### Files to Create:
- `__init__.py`: Module exports.
- `schemas.py`: `BuyerIntent`, `BuyerAgentState` (TypedDict for LangGraph), `BuyerAgentAction` (Pydantic model for structured output).
- `prompts.py`: Safe, isolated system prompts that treat product/merchant info as untrusted data.
- `tools.py`: Bounded tools wrapping the existing `ProductService` and `PolicyService`.
  - `search_products(query)`
  - `get_product(product_id)`
  - `create_negotiation(product_id, quantity, unit_price)`
- `nodes.py`: The LangGraph execution nodes.
- `graph.py`: The LangGraph state machine builder.
- `config.py`: LLM configurations (OpenAI integration based on `LLM_API_KEY`).

## 4. LangGraph Flow

```
START
  ↓
parse_intent
  ↓
discover_products
  ↓
evaluate_products
  ↓
select_product
  ↓
generate_proposal
  ↓
validate_proposal (calculates deterministic total)
  ↓
policy_check (calls PolicyEngine.evaluate)
  ↓
route_policy_decision
  │
  ├─ [ALLOW] ──→ create_negotiation ──→ COMPLETE (END)
  │
  ├─ [HUMAN_APPROVAL_REQUIRED] ──→ await_human_approval ──→ INTERRUPT (END)
  │
  └─ [DENY] ──→ proposal_recovery
                 │
                 ├─ [revise] ──→ validate_proposal (loop max 3 times)
                 │
                 └─ [stop] ──→ FAILED (END)
```

## 5. Security & Isolation
- **No DB Sessions in LLM:** The LLM will only receive Pydantic data from tools, never raw SQLAlchemy models.
- **Decimal Everywhere:** Output parsing will strictly convert monetary outputs into Python `Decimal` objects.
- **Deterministic Override:** If the LLM proposes `total_amount = 100`, but `unit_price * qty = 500`, the system will overwrite the LLM's total with `500` before sending it to the Policy Engine.

## 6. Testing Strategy (`backend/tests/unit/test_buyer_agent.py`)
- We will use `langchain_core.language_models.FakeListChatModel` to mock LLM responses deterministically.
- We will test the happy path (ALLOW), the DENY-recovery loop, the hard STOP limits, and prompt injection defense.

## User Feedback Required
> [!IMPORTANT]
> Because of a local environment issue with the `brain` artifact folder, I have placed this plan in `docs/IMPLEMENTATION_PLAN_PHASE_5.md`. 
> 
> Please review the LangGraph flow and architecture above. Do you approve of this approach and the `langchain-openai` dependency choice? If approved, I will begin execution.
