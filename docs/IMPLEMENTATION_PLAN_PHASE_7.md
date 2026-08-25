# Implementation Plan Phase 7 — Agreement & Razorpay Payment Execution

## 1. Objective
Phase 7 bridges the gap between agentic negotiation (Phase 5 & 6) and deterministic payment execution. The goal is to build an unbreachable boundary where LLMs are no longer involved, transforming accepted negotiations into immutable financial Agreements, verifying policy compliance one final time, and executing real payments via Razorpay (Test Mode).

## 2. Repository Audit Findings
- **Agreement Model**: Enforces immutability for commercial terms. It tracks status via `PENDING_VALIDATION`, `VALIDATED`, `PENDING_APPROVAL`, `APPROVED`, `PAYMENT_INITIATED`, `PAYMENT_CAPTURED`, `PAYMENT_FAILED`, `VALIDATION_FAILED`, `CANCELLED`, `EXPIRED`.
- **Payment Model**: Maps 1:1 with `Agreement`. Tracks status via `CREATED`, `AUTHORIZED`, `CAPTURED`, `FAILED`, `REFUNDED`, `CANCELLED`.
- **Database Gaps**: A `PaymentWebhookEvent` table is required to track incoming webhooks, deduplicate them safely at the database level, and manage their processing lifecycle.

## 3. Architecture: The Payment Authorization Boundary
The architecture strictly enforces: **LLMs PROPOSE. DETERMINISTIC SYSTEMS DECIDE.**
No LLM (neither Buyer nor Merchant) is authorized to trigger payment execution or alter the Agreement.

**Flow:**
1. **Negotiation (ACCEPTED)**
2. **Agreement Creation**: Deterministic parsing of the final negotiation message.
3. **FINAL Policy Gate**: `PolicyEngine` evaluates the exact Agreement against the *current* merchant policy.
4. **Payment Initiation**: `PaymentService` creates the local Payment and external Razorpay Order.
5. **Razorpay Checkout**: Client completes payment.
6. **Verified Webhook**: Cryptographically verified webhook updates the Payment and Agreement state atomically.

## 4. Agreement Lifecycle & State Machine
The state machine strictly enforces the following valid transitions:
- `PENDING_VALIDATION` → `VALIDATED` (PolicyEngine ALLOW)
- `PENDING_VALIDATION` → `VALIDATION_FAILED` (PolicyEngine DENY)
- `PENDING_VALIDATION` → `PENDING_APPROVAL` (PolicyEngine HUMAN_APPROVAL_REQUIRED)
- `PENDING_APPROVAL` → `APPROVED` / `CANCELLED` / `EXPIRED` (Human action / timeout)
- `VALIDATED` or `APPROVED` → `PAYMENT_INITIATED` (PaymentService initiation)
- `PAYMENT_INITIATED` → `PAYMENT_CAPTURED` / `PAYMENT_FAILED` (Webhook confirmation)

**Crucial Note**: `PENDING_APPROVAL` is a hard financial boundary. No LLM or API can bypass this to reach `VALIDATED`. No payment can be initiated while in `PENDING_APPROVAL`.

## 5. Agreement Creation (Deterministic)
Creation originates exclusively from an `ACCEPTED` negotiation. The client provides only `negotiation_id`. The server:
1. Validates the negotiation is `ACCEPTED`.
2. Extracts the canonical final payload.
3. Deterministically computes `total_amount = unit_price × quantity` using Python `Decimal`.
4. Persists the `Agreement` in `PENDING_VALIDATION` state.

## 6. Final Policy Validation
Policy validation is run *again* immediately before payment, as merchant policy might have changed since the negotiation.
- If `ALLOW` → State becomes `VALIDATED` (or proceeds if already `APPROVED`).
- If `DENY` → State becomes `VALIDATION_FAILED` (payment blocked).
- If `HUMAN_APPROVAL_REQUIRED` → State becomes `PENDING_APPROVAL` (payment blocked).

## 7. Decimal → Paise Conversion
All financial authority derives from `Agreement.total_amount`. A centralized utility will handle conversion:
- Requires `Decimal` only, `INR` only.
- Validates against zero or negative amounts.
- Rejects any value with fractional paise (e.g., `10.505` INR).
- Returns exact integer `amount_paise`.

## 8. Payment State Machine
Valid transitions for `Payment`:
- `CREATED` → `AUTHORIZED` (Payment processed, waiting for capture)
- `CREATED` → `FAILED`
- `CREATED` → `CANCELLED`
- `AUTHORIZED` → `CAPTURED` (Terminal)
- `AUTHORIZED` → `FAILED` (Terminal)
- `CAPTURED` → `REFUNDED` (Terminal)

## 9. Razorpay Order Idempotency & External Failure Windows
`UNIQUE(agreement_id)` on the Payment table only protects the local DB. It does not protect against external races.
To protect against the "Razorpay creates order, DB fails to commit" race window:
1. Create a `Payment` record in the DB with status `CREATED` *before* calling Razorpay.
2. The `Payment` record acts as our local intent/lock (enforced by `UNIQUE(agreement_id)`).
3. If Razorpay succeeds, we update the `Payment` with `razorpay_order_id` and commit.
4. **Race Condition**: If the DB commit in step 3 fails, the Razorpay order is orphaned. 
   - **Detection/Recovery**: If a client attempts to initiate payment again, the DB already has a `CREATED` payment intent without an order ID. We can use Razorpay's `receipt` field (`agr_{uuid}`) to fetch the orphaned order from Razorpay (if it exists) and heal the local DB, or create a new one if it doesn't.

## 10. Webhook Idempotency & Atomicity
Duplicate webhooks must be safely ignored.
1. The `PaymentWebhookEvent` table will track: `event_id` (UNIQUE), `event_type`, `payload_hash`, `received_at`, `processed_at`, `status` (`RECEIVED`, `PROCESSING`, `PROCESSED`, `FAILED`).
2. Webhook ingestion uses `INSERT ... ON CONFLICT DO NOTHING` (or PostgreSQL native equivalent) to ensure duplicate `event_id`s safely return 200 OK without triggering business logic twice.
3. **Atomicity**: The webhook event status update (`PROCESSED`), the `Payment` state update, and the `Agreement` state update will all be wrapped in **one single PostgreSQL transaction**. If the business logic fails, the transaction rolls back, leaving the webhook event in `RECEIVED` state, allowing Razorpay's exponential backoff to retry safely.

## 11. Razorpay Client Boundary & Fake Client
- `RazorpayClient`: A thin wrapper around the Razorpay Python SDK. It communicates with Razorpay but holds ZERO business rules.
- `FakeRazorpayClient`: A fully deterministic mock injected during tests. It implements `create_order`, `verify_webhook_signature`, `fetch_order`, ensuring the 200+ test suite runs instantly without network I/O.

## 12. Webhook Signature Verification
Signature verification (`RAZORPAY_WEBHOOK_SECRET`) MUST execute against the raw incoming byte stream (`request.body()`). JSON parsing only occurs after cryptographic verification succeeds. Invalid signatures instantly return 400 Bad Request with no DB changes.

## 13. API Endpoints
- `POST /api/v1/agreements`: Accepts `{ "negotiation_id": "uuid" }`. Deterministic creation. No client-provided amounts.
- `POST /api/v1/agreements/{id}/validate`: Idempotent endpoint to trigger the PolicyEngine against the Agreement.
- `POST /api/v1/payments/initiate`: Requires `VALIDATED` or `APPROVED` Agreement. Checks idempotency. Initiates Razorpay Order.
- `POST /api/v1/webhooks/razorpay`: Ingestion endpoint.

## 14. External Failure Windows Documented
- **A. Razorpay timeout before response**: Payment remains `CREATED`. Client can safely retry.
- **B. Razorpay creates order but response is lost**: Next attempt finds `CREATED` payment, fetches by receipt, heals state.
- **C. Razorpay creates order but DB commit fails**: Same as B.
- **D. DB commit succeeds but response to client is lost**: Client retries; system returns existing `razorpay_order_id` (idempotent success).
- **E. Duplicate payment initiation**: Blocked by DB transaction locks and `UNIQUE(agreement_id)`.
- **F. Duplicate webhook**: Bounces off `UNIQUE(event_id)`. Returns 200 OK.
- **G. Webhook processing failure**: DB rolls back. Webhook stays `RECEIVED`. Razorpay retries automatically.

## 15. Security Controls
- [x] No LLM can initiate payment or create Razorpay orders.
- [x] No client can choose payment amount, currency, or modify Agreement terms.
- [x] Webhook signature required (against raw bytes).
- [x] Webhook event processing is idempotent and atomic.
- [x] Unknown Razorpay payments or Agreements rejected.
- [x] Terminal Agreements/Payments protected.
- [x] Human approval cannot be bypassed.
- [x] No secrets logged or exposed.

## 16. Inventory
Deferred to Phase 8. Phase 7 will not reserve or decrement inventory, avoiding complex distributed rollback scenarios during payment edge-cases.

## 17. Testing Strategy
Includes unit and integration tests (via `FakeRazorpayClient`) covering:
- Deterministic calculation and Decimal boundary values.
- Two simultaneous payment initiation requests.
- Two simultaneous duplicate webhook deliveries.
- Razorpay success + DB failure recovery.
- Stale policy after negotiation (DENY at final check).
- Tampered webhook signature.

## 18. Buildathon Demo Strategy
A 5-minute interactive test-mode flow:
1. Autonomous negotiation reaches `ACCEPTED`.
2. Agreement is deterministically created.
3. Final PolicyEngine check allows the Agreement (`VALIDATED`).
4. Payment initiated → Razorpay TEST Order created.
5. Standard Razorpay checkout / Webhook ingestion.
6. Payment marked `CAPTURED`.
**Failure Demo**: Fire a curl request mimicking a webhook with a tampered signature. Show the system rejecting it instantly with no DB changes.

## 19. Implementation Order
1. AgreementService
2. Agreement validation tests
3. PaymentWebhookEvent model
4. Alembic migration
5. Decimal → paise utility
6. RazorpayClient interface
7. FakeRazorpayClient
8. PaymentService
9. Payment state machine
10. Webhook processing service
11. Agreement APIs if required
12. Payment API
13. Webhook API
14. Unit tests
15. Integration tests
16. Security tests
17. Full regression suite
18. Documentation (`docs/PAYMENTS.md` and updates to existing docs)
19. Demo

## 20. Stop Condition
Implement ONLY Phase 7. Do not implement inventory, fulfillment, refunds, or Phase 8. Preserve the boundary: LLMs Propose -> Deterministic Systems Decide -> Payments Execute safely.
