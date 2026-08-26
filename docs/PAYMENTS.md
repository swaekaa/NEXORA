# NEXORA — Payments & Idempotency Architecture

This document outlines the Phase 7 integration of Razorpay for deterministic payment execution in NEXORA.

## 1. Principles
- **No LLM Involvement**: All payment operations happen strictly server-side through deterministic code.
- **Agreement as the Source of Truth**: The `Agreement` model determines the `total_amount` to be charged. The client cannot dictate this amount.
- **Idempotency**: All operations (Payment Initiation and Webhooks) are strictly idempotent.

## 2. Agreement Flow
1. **Negotiation ACCEPTED**: The agents have agreed on terms.
2. **Agreement Creation**: A deterministic snapshot is taken, translating `unit_price * quantity` into `total_amount` using exact `Decimal` math.
3. **FINAL Policy Gate**: The `PolicyEngine` evaluates the terms against the *current* merchant policy. Only `ALLOW` proceeds.

## 3. Payment Initiation
The client posts an `agreement_id` to `/api/v1/payments/initiate`.
1. The server verifies the Agreement is `VALIDATED` or `APPROVED`.
2. A local `Payment` intent is created in the database with status `CREATED`.
3. The server calls the Razorpay API to create an Order.
4. The local `Payment` intent is updated with the `razorpay_order_id`.

### External Race Condition (Orphaned Order)
If Razorpay creates the order but the local database fails to commit the `razorpay_order_id`, the system will self-heal on the next request by fetching the order from Razorpay using the `receipt` field (`agr_{agreement_id}`).

## 4. Webhook Architecture
Incoming webhooks from Razorpay are verified cryptographically using `RAZORPAY_WEBHOOK_SECRET` against the raw byte stream of the request. 

### Idempotency
Webhooks are deduplicated at the database level:
- The `PaymentWebhookEvent` table enforces a `UNIQUE(event_id)` constraint.
- The ingestion endpoint uses an atomic try/catch pattern.
- If a duplicate event arrives, the database rejects the insert, and the endpoint safely returns a `200 OK` to Razorpay.

### Atomicity
The update to the Webhook Status (`PROCESSED`), the Payment Status (`CAPTURED`), and the Agreement Status (`PAYMENT_CAPTURED`) are performed within a single database transaction. If any part fails, the entire transaction rolls back, leaving the webhook in a `RECEIVED` state so Razorpay can retry it.
