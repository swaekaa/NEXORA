# Phase 5 — Buyer Agent

The NEXORA Buyer Agent is an autonomous, goal-oriented system powered by **LangGraph** (for state machine orchestration) and **LangChain** (for LLM interactions and tools).

## 1. Purpose
The Buyer Agent accepts a `BuyerIntent` (representing the human buyer's requirements and budget), searches the merchant catalog, selects the best product, and negotiates a commercial agreement. 

## 2. Core Architectural Principle
**"LLMs PROPOSE. DETERMINISTIC SYSTEMS DECIDE."**

The Buyer Agent runs untrusted LLM logic inside a heavily guarded boundary. The LLM can generate a `BuyerAgentAction` (proposing a quantity, unit price, and discount), but it **cannot**:
1. Calculate the final financial total.
2. Override the Policy Engine.
3. Call Razorpay or execute payments.
4. Modify merchant policies or catalogs.

## 3. LangGraph Architecture

The orchestration runs entirely through a LangGraph `StateGraph`.

```
START
  ↓
[run_llm] ────── (LLM Structured Output) ──────┐
  ↑                                            ↓
  │                                     [execute_action]
  │                                            │
  │                  (if PROPOSE_AGREEMENT) ───┤
  │                                            ↓
  │                                   [validate_proposal] 
  │                                     (Deterministic Math)
  │                                            ↓
  │                                      [policy_check]
  │                                   (PolicyEngine.evaluate)
  │                                            │
  ├────── [DENY] ──── [proposal_recovery] ─────┤
  │                                            │
  │                                            ├─ [ALLOW] ──→ [create_negotiation] ──→ END
  │                                            │
  └────────────────────────────────────────────├─ [HUMAN_APPROVAL_REQUIRED] ──→ [await_human_approval] ──→ END
```

## 4. State Schema
The state (`BuyerAgentState`) passed between nodes tracks:
- **Intent**: The buyer's budget, requirements, and constraints.
- **Candidate Products**: Catalog list injected before graph runs.
- **Current Action**: The LLM's selected action and parameters.
- **Deterministic Total**: The validated financial total computed by Python.
- **Policy Feedback**: `ALLOW`, `DENY`, or `HUMAN_APPROVAL_REQUIRED`, along with specific rule violations.

## 5. Security & Prompt Injection Defense
- **Catalog as Untrusted Data**: Product names and descriptions are loaded directly into state, never appended naively into the `SystemPrompt`. The system explicitly instructs the LLM to ignore any "instructions" found within product descriptions.
- **Bounded Revises**: If the Policy Engine rejects a proposal, the LLM is given exactly 3 chances to revise it based on structured feedback before the agent terminates with a `FAILED` state.
- **No DB Sessions**: The LLM node does not have an active database session. Candidate products are injected as dictionaries.

## 6. Testing Strategy
- Unit tests run completely offline using `MagicMock` to stub `ChatOpenAI`.
- Tests verify that deterministic math constraints correctly overwrite malicious LLM outputs.
- Tests verify the DENY recovery loop bounds.

## 7. Future Integration
In Phase 6, the Buyer Agent will interact dynamically with a Merchant Agent. The `create_negotiation` node will hand off control to a Negotiation Engine state machine.
