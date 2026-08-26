# Phase 9: Human Approval & Immutable Audit Trail

## 1. Phase 9 Repository Audit

- **Existing approval infrastructure**: None. Checked `app/models/` and `app/services/`. No approval models or services exist.
- **Existing audit infrastructure**: Minimal skeleton. Checked `app/audit/` which contains an `__init__.py` with a TODO for Phase 11. No tables or services exist yet.
- **Policy → Approval gap**: `PolicyEngine` successfully returns `HUMAN_APPROVAL_REQUIRED` (e.g., if the transaction exceeds `maximum_autonomous_transaction`), but this currently acts as a hard blocker. There is no mechanism to store the pending request, notify a human, or accept their decision to override and proceed.
- **Payment → Approval gap**: `PaymentService` (`initiate_payment`) expects an agreement to be in a valid state. Currently, if it's `HUMAN_APPROVAL_REQUIRED`, payment initiation fails. We need a way for `initiate_payment` to check if an `ApprovalRequest` exists and is `APPROVED` before proceeding, while ensuring the PolicyEngine re-validates the terms as a final check.
- **Inventory → Approval interaction**: Since inventory reservation currently happens *inside* `initiate_payment` (Reserve-First architecture), inventory is **not** reserved while waiting for human approval. This is the correct behavior: we do not hold inventory indefinitely while waiting for a merchant to click approve. Inventory is only reserved when the human approves and the payment is actually initiated.

## 2. Files that need modification
- `backend/app/models/__init__.py` (Import new models for Alembic)
- `backend/app/services/payment_service.py` (Final policy check taking approval into account before Razorpay)
- `backend/app/api/v1/endpoints/payments.py` (Audit logging for payment events)
- `backend/app/services/inventory_service.py` (Audit logging for inventory events)
- `backend/app/main.py` (Register new routers)
- `backend/docs/ARCHITECTURE.md` (Update flow diagrams)

## 3. Files that need creation
- `backend/app/models/approval_request.py`
- `backend/app/models/audit_event.py`
- `backend/app/services/approval_service.py`
- `backend/app/services/audit_service.py`
- `backend/app/api/v1/endpoints/approvals.py`
- `backend/app/api/v1/endpoints/audit.py`
- `backend/tests/unit/test_approval_service.py`
- `backend/tests/unit/test_audit_service.py`
- `backend/tests/integration/test_approval_flow.py`
- `docs/HUMAN_APPROVAL.md`
- `docs/AUDIT_TRAIL.md`

## 4. Database changes
- New table: `approval_requests`
  - `id` (UUID, PK)
  - `agreement_id` (UUID, FK, Unique)
  - `merchant_id` (UUID, FK)
  - `status` (String: PENDING, APPROVED, REJECTED)
  - `policy_decision` (String)
  - `requested_at`, `resolved_at`, `created_at`, `updated_at` (Timestamps)
  - `resolution_reason` (String, nullable)
- New table: `audit_events`
  - `id` (UUID, PK)
  - `event_type` (String)
  - `actor_type` (String)
  - `actor_id` (UUID, nullable)
  - `agreement_id` (UUID, nullable)
  - `metadata` (JSONB)
  - `created_at` (Timestamp, immutable)

## 5. State machines
- **ApprovalRequest**: `PENDING` → `APPROVED` | `REJECTED`. Terminal states are immutable. Rejection blocks payment forever for that specific agreement workflow.

## 6. Implementation plan
- **Step 1**: Create `ApprovalRequest` and `AuditEvent` ORM models and generate Alembic migrations.
- **Step 2**: Implement `AuditService` (append-only `record_event`, and read endpoints).
- **Step 3**: Implement `ApprovalService` (`create`, `approve`, `reject`). Enforce SQL-level merchant ownership.
- **Step 4**: Inject `AuditService` into the existing `PaymentService` and `InventoryService` to log events seamlessly within their DB transactions.
- **Step 5**: Update `PaymentService.initiate_payment` to fetch the `ApprovalRequest` if the agreement requires human approval, re-run `PolicyEngine`, and verify that the combination allows payment.
- **Step 6**: Add FastAPI routers for Approvals (to simulate merchant UI actions) and Audit.
- **Step 7**: Write comprehensive unit and integration tests (including the critical failure test where a policy changes after human approval).
- **Step 8**: Update documentation and create buildathon demo script.

## 7. Risks
- **Concurrency & Idempotency**: Double-clicking "Approve" must not initiate two concurrent downstream actions. Will enforce idempotent API design and rely on database uniqueness (`agreement_id` constraints).
- **Policy Mismatch**: If an agreement is approved, but the merchant immediately changes their minimum price policy before the buyer pays, the final deterministic `PolicyEngine` check must catch this and hard-DENY the payment, overriding the human approval. This proves human approval is not a bypass.
