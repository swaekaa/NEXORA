# NEXORA — Product Requirements Document (PRD)

**Version:** 1.0  
**Date:** August 22, 2026  
**Author:** NEXORA Architecture Team  
**Status:** Final — Architecture Phase

---

## 1. Executive Summary

NEXORA is the **agreement layer for AI commerce**. It provides the missing infrastructure that allows autonomous AI buyer agents and autonomous AI merchant agents to discover, negotiate, agree on, and pay for commercial transactions — within strict, deterministic economic policies — and with complete auditability.

NEXORA is being built as a production-quality prototype for the **Razorpay AI Buildathon 2026**, Track: AI Growth & Agentic Commerce. Submission deadline: September 5, 2026.

---

## 2. Problem Statement

### 2.1 Traditional Commerce Model

```
Human Buyer → Search → Compare → Contact → Negotiate → Agree → Checkout → Pay
```

Every step assumes a human in the loop. The infrastructure (search engines, comparison sites, checkout pages, payment forms) is designed for human interaction.

### 2.2 Emerging Agentic Commerce Model

```
AI Buyer Agent ↔ AI Merchant Agent ↔ Payment Infrastructure
```

As AI agents become capable of autonomous procurement, B2B commerce, SaaS purchasing, and bulk ordering, the existing payment infrastructure is fundamentally inadequate:

- Checkout pages are designed for humans (CAPTCHAs, form filling, 2FA)
- There is no standard protocol for AI-to-AI commercial negotiation
- There is no standard structure for a machine-readable commercial agreement
- There is no infrastructure to prevent an LLM from authorizing financially invalid actions
- There is no audit trail designed for AI agent decisions

### 2.3 The Specific Gap NEXORA Fills

| Gap | NEXORA Solution |
|-----|-----------------|
| No standard AI negotiation protocol | NEXORA Agent Protocol with structured states |
| No machine-readable commercial agreement format | NEXORA Agreement Schema (JSON-canonical) |
| LLMs can hallucinate financial terms | Deterministic Policy Engine validates all financial logic |
| No authorization layer for AI transactions | Payment Authorization Gate — policy must PASS before Razorpay |
| No audit trail for agent decisions | Structured Audit Trail — every decision recorded |
| No human escalation system | Human Approval System — configurable approval thresholds |

---

## 3. Target Users

### 3.1 Primary Demo Users (Buildathon Context)

| User | Role |
|------|------|
| Merchant (Demo) | Configures economic policy, owns a product catalog, reviews approvals |
| Buyer (Demo) | Gives natural-language procurement goal to AI buyer agent |
| Razorpay Engineer (Evaluator) | Evaluates quality of Razorpay integration and AI architecture |

### 3.2 Eventual Production Users

| User | Role |
|------|------|
| Enterprise Merchant | Configures autonomous agent policies for their business |
| Enterprise Buyer | Delegates procurement to AI agent with budget constraints |
| Platform Operator | Runs NEXORA infrastructure, monitors system health |

---

## 4. Core User Stories

### 4.1 Buyer Stories

- **B1:** As a buyer, I can describe my procurement need in natural language ("Buy 100 monitors under ₹11L, delivery within 7 days") and my AI agent negotiates on my behalf.
- **B2:** As a buyer, I can define maximum budget, quantity, delivery deadline, and warranty requirements as constraints my agent cannot exceed.
- **B3:** As a buyer, I can see a real-time log of what my agent is doing and why.
- **B4:** As a buyer, I can see the final commercial agreement before payment is authorized.
- **B5:** As a buyer, I am notified when my agent successfully purchases and when it cannot.

### 4.2 Merchant Stories

- **M1:** As a merchant, I can configure my product catalog with base prices, minimum prices, and bulk discount tiers.
- **M2:** As a merchant, I can define an autonomous transaction limit above which human approval is required.
- **M3:** As a merchant, I can see pending human approval requests and approve or reject them from my dashboard.
- **M4:** As a merchant, I can see all completed negotiations, agreements, and payments.
- **M5:** As a merchant, I can see blocked transactions and the reason they were blocked.

### 4.3 System Stories

- **S1:** The system must never allow an LLM to directly execute a financial action.
- **S2:** The system must validate every proposed agreement against merchant and buyer policies before authorizing payment.
- **S3:** The system must record every agent decision in an immutable audit trail.
- **S4:** The system must handle Razorpay webhook events idempotently.
- **S5:** The system must gracefully handle payment failures without corrupting agreement state.

---

## 5. Product Scope

### 5.1 MVP Scope (Target: September 5, 2026)

**In Scope:**
- Single merchant, single buyer demo scenario
- AI Merchant Agent (LLM-powered, policy-bounded)
- AI Buyer Agent (LLM-powered, goal-driven)
- Negotiation Engine (structured state machine: DISCOVER → AGREEMENT)
- Commercial Agreement Engine (JSON canonical schema)
- Deterministic Policy Engine (all financial validation)
- Razorpay Orders API integration (Test Mode)
- Razorpay Payment verification (signature validation)
- Razorpay Webhook processing (idempotent, signature-verified)
- Human Approval System (basic: approve/reject UI)
- Audit Trail (every decision logged)
- Merchant Dashboard (negotiations, agreements, approvals, audit)
- Buyer Interface (conversational, natural language input)
- 7 documented failure scenarios with graceful handling
- Docker Compose for local demo

**Out of Scope (MVP):**
- Multi-tenant merchant management
- Real money payments (Test Mode only)
- Mobile app
- Production-grade authentication (JWT stub only)
- Advanced ML fraud detection
- Real-time websockets for multi-party negotiations (polling acceptable)
- Payment refunds in MVP (architecture supports it)

### 5.2 Future Scope (Post-Buildathon)

- Multi-merchant, multi-buyer platform
- UPI Circle / UPI Reserve Pay for autonomous payments (requires regulatory approval)
- Razorpay Agent Studio integration
- MCP server exposure (allow external AI assistants to use NEXORA tools)
- Smart contract-style agreement finality
- Cross-agent reputation scoring
- Real-time negotiation websockets
- Mobile SDK for buyer agents
- Multi-round, multi-product basket negotiation

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Correctness** | All financial calculations use `Decimal`, never `float` |
| **Idempotency** | All external events (webhooks) processed exactly once |
| **Auditability** | Every financial decision logged with agent_id, timestamp, reason |
| **Security** | No secrets in code; HMAC-SHA256 webhook verification; no trust of frontend payment state |
| **Testability** | Policy engine 100% unit-testable without LLM; agreement validation 100% deterministic |
| **Demonstrability** | System must be runnable with `docker-compose up` for demo |
| **Failure Handling** | At least 7 failure modes explicitly handled and demonstrable |

---

## 7. Success Criteria (Buildathon)

| Criterion | How NEXORA Demonstrates It |
|-----------|---------------------------|
| Problem Taste | Clear articulation of "agentic commerce needs an agreement layer" |
| Build Quality | Clean monorepo, tested policy engine, working Razorpay integration |
| AI Judgment | Explicit LLM/deterministic boundary; tools pattern; schema validation |
| Failure Recovery | 7 deliberately demonstrated failure modes with graceful recovery |
| Razorpay Integration | Orders API + webhook verification + Test Mode end-to-end |
