# NEXORA — 5-Minute Demo Scenario

**Version:** 1.0  
**Date:** August 22, 2026  
**Audience:** Razorpay AI Buildathon 2026 Evaluators

---

## Demo Setup

**Pre-conditions:**
- `docker-compose up` running
- Demo data seeded: Dell monitor merchant, Horizon Corp buyer
- Razorpay Test Mode keys configured
- Two browser tabs open:
  - Tab 1: Buyer Interface (localhost:3000/buyer)
  - Tab 2: Merchant Dashboard (localhost:3000/merchant)
- Screen recording running

**Reset:** `python scripts/demo_reset.py` before each demo run.

---

## Demo Script (5 Minutes)

---

### [0:00 – 0:30] The Problem Statement

**[SCREEN: Slide or intro page]**

**Narration:**
> "AI agents will soon purchase products, negotiate contracts, and execute payments autonomously. But today's payment infrastructure assumes a human at every step. NEXORA is the missing layer: a negotiation and authorization infrastructure that lets AI buyers and AI sellers transact with each other, safely."

**Key point to land:**
> "The innovation is not AI negotiation — it's the **agreement layer** between negotiation and payment."

---

### [0:30 – 1:30] Happy Path: AI-to-AI Deal Gets Done

**[SCREEN: Buyer Interface — Tab 1]**

**Narrator types in Buyer Chat:**
> "Buy 100 Dell monitors for our new office, budget ₹11 lakh, delivery within 7 days, at least 12 months warranty, pay upfront for discount."

**[Watch as agents negotiate — show live negotiation feed]**

Points to narrate:
- "The buyer agent extracts constraints — budget, quantity, delivery, warranty"
- "It discovers the Dell monitor from the merchant catalog"  
- "It submits a structured buy request — via a typed tool call, not free text"
- "The merchant agent evaluates it against its policy — base ₹12,000, 8% bulk discount for 100 units, 2% upfront discount"
- "Both agents exchange one round of negotiation"
- "Merchant offers ₹10,819/unit — within buyer budget"
- "Buyer accepts"

**[SCREEN: Agreement Card appears]**

Points to narrate:
- "Agreement created: ₹10,81,920 total. Quantity 100. Delivery 5 days. Warranty 24 months."
- "Now the policy engine validates this. No LLM involved here."
- "All 7 checks pass. Agreement is VALIDATED."

**[SCREEN: Razorpay Checkout appears]**

- "Payment authorization — Razorpay Order created for exactly ₹10,81,920."
- "Test card 4111 1111 1111 1111"
- **Complete the payment**

**[SCREEN: Merchant Dashboard — Tab 2 — Agreement shows PAYMENT_CAPTURED]**

- "Webhook received, signature verified, amount verified — agreement marked PAID."
- "Full audit trail below."

---

### [1:30 – 2:15] Failure 1: Price Below Merchant Minimum

**[SCREEN: Buyer Interface]**

**Narrator types:**
> "Buy 5 monitors at ₹9,000 each."

**[Watch agent response]**

Narrate:
- "Buyer agent submits ₹9,000. Merchant minimum is ₹10,500."
- "Policy engine catches it: MERCHANT_MIN_PRICE FAIL."
- "Agreement status: VALIDATION_FAILED. Payment blocked."
- **[Show audit log event: POLICY_BLOCKED]**
- "The LLM never touched the financial calculation. The deterministic engine blocked it."

---

### [2:15 – 3:00] Failure 2: Human Approval Required

**[SCREEN: Buyer Interface]**

**Narrator types:**
> "Buy 150 monitors at base price, no discounts expected."

Narrate:
- "150 × ₹12,000 = ₹18,00,000. Merchant autonomous limit: ₹10,00,000."
- "Policy engine: REQUIRES_HUMAN_APPROVAL."

**[SCREEN: Merchant Dashboard — approval card appears]**

- "The merchant sees a pending approval: ₹18L transaction."
- "Merchant clicks APPROVE."
- "Payment authorization proceeds."
- **[Show agreement moving to PAYMENT_INITIATED]**

---

### [3:00 – 3:45] Failure 3 & 4: Webhook Attacks

**[SCREEN: Terminal / Audit Log]**

Run: `python scripts/simulate_failures.py invalid_signature`

Narrate:
- "A forged webhook arrives — wrong signature."
- "NEXORA verifies HMAC-SHA256 on raw body before parsing."
- "Result: 400 rejected. Audit event logged."

Run: `python scripts/simulate_failures.py duplicate_event evt_001`

Narrate:
- "Same webhook event arrives twice — Razorpay retries happen in production."
- "NEXORA checks X-Razorpay-Event-Id — already seen."
- "Result: silently skipped. No double-processing. 200 returned."

---

### [3:45 – 4:30] The Architecture Moment

**[SCREEN: Architecture diagram]**

Narrate:
- "Here is the key principle: LLMs propose, deterministic systems decide."
- [Trace the path] "Buyer agent → negotiation → agreement → **policy engine** → payment auth → Razorpay → webhook verification → settlement"
- "At no point does the LLM call Razorpay."
- "At no point does the LLM calculate prices."
- "Every financial decision is auditable, deterministic, and blockable."

---

### [4:30 – 5:00] The Bigger Picture

**Narration:**
> "In the next few years, AI agents will represent buyers and sellers in commercial transactions worth billions. They'll need exactly this layer: a protocol to negotiate, an agreement schema to formalize terms, a policy engine to enforce boundaries, and an audit trail to explain every decision. NEXORA is that layer. Built on Razorpay's payment infrastructure. That's the agreement layer for AI commerce."

**[End on NEXORA logo / tagline: "The agreement layer for AI commerce."]**

---

## Pre-Demo Checklist

```
[ ] docker-compose up (all 3 services green)
[ ] Demo data seeded (python scripts/demo_setup.py)
[ ] Razorpay Test Mode keys configured in .env
[ ] ngrok running (or webhook simulation script ready)
[ ] Razorpay Dashboard open (to show webhook logs)
[ ] Buyer tab open at localhost:3000/buyer
[ ] Merchant tab open at localhost:3000/merchant
[ ] Screen recording started
[ ] Scripts ready: simulate_failures.py
[ ] Test card ready: 4111 1111 1111 1111 / CVV: any / Expiry: any future
```

---

## Recovery Plans

| Problem | Recovery |
|---------|----------|
| LLM slow / timeout | Pre-cached demo mode: `DEMO_MODE=cached` uses pre-recorded agent responses |
| Razorpay webhook not arriving | Run `python scripts/simulate_webhook.py payment.captured <order_id>` |
| Docker crash | Pre-recorded screen capture backup |
| ngrok disconnects | Use local webhook simulator |
