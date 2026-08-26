# Phase 8 — Inventory Reservation & Fulfillment: Implementation Plan

## 1. Architectural Strategy: The "Reserve-First" Flow
Following the core principle **"LLMs PROPOSE. DETERMINISTIC SYSTEMS DECIDE."**, agents will have ZERO authority over inventory. All inventory operations will be handled by a deterministic `InventoryService`.

Based on the repository audit and the requirement to prevent overselling, we will adopt the **Reserve-First (Approach B)** architecture:
1. `Agreement` is reached and `VALIDATED`.
2. Client calls `/api/v1/payments/initiate`.
3. `InventoryService` atomically deducts `Agreement.quantity` from `Product.inventory` and creates an `InventoryReservation(status=RESERVED)`.
4. `PaymentService` creates the Razorpay order and `Payment` intent.
5. Client completes Razorpay checkout.
6. Webhook `payment.captured` triggers `InventoryService` to update the reservation to `COMMITTED`.
7. A later fulfillment action transitions it to `FULFILLED`.
8. Webhook `payment.failed` (or expiration) triggers `InventoryService` to release the reservation, returning stock to `Product.inventory`.

**Why this approach?** This guarantees that a buyer can never successfully pay for an item that is out of stock. It provides the strongest financial guarantee.

## 2. Database Models
We will retain `Product.inventory` as the canonical source of truth for **Available Inventory**. We will introduce a new `InventoryReservation` table to track the lifecycle of reserved quantities.

### New Table: `inventory_reservations`
- `id`: UUID (Primary Key)
- `agreement_id`: UUID (Foreign Key to `agreements`, UNIQUE - 1 reservation per agreement)
- `product_id`: UUID (Foreign Key to `products`)
- `quantity`: Integer (CHECK > 0)
- `status`: String (RESERVED, COMMITTED, FULFILLED, CANCELLED, RELEASED, EXPIRED)
- `expires_at`: Timestamp (Null if committed/released)
- `created_at`, `updated_at`: Timestamps

### Reservation State Transitions
- `RESERVED` -> `COMMITTED`
- `RESERVED` -> `RELEASED` (if Razorpay order fails or payment fails)
- `RESERVED` -> `EXPIRED` (if TTL reached)
- `COMMITTED` -> `FULFILLED`

Terminal states are protected. `COMMITTED` cannot go back to `RELEASED`.

## 3. Concurrency Control
To prevent overselling when concurrent requests arrive (e.g., 10 available, A requests 7, B requests 6), we will rely on PostgreSQL's atomic updates rather than Python-level checks:

```sql
UPDATE products 
SET inventory = inventory - :quantity 
WHERE id = :product_id AND inventory >= :quantity
```
If `rowcount == 0`, we raise `InsufficientInventoryError`. This completely eliminates race conditions without requiring expensive table/row locks (`SELECT FOR UPDATE`) that could block reads.

## 4. Components to Implement/Modify

### A. `InventoryService` (`backend/app/services/inventory_service.py`)
- `reserve_inventory(session, agreement)`: Atomic deduction and reservation creation.
- `commit_reservation(session, agreement_id)`: Transitions `RESERVED` -> `COMMITTED`.
- `release_reservation(session, agreement_id)`: Transitions `RESERVED` -> `RELEASED` and refunds `Product.inventory`.
- `fulfill_reservation(session, agreement_id)`: Transitions `COMMITTED` -> `FULFILLED`.

### B. `PaymentService` Integration (`backend/app/services/payment_service.py`)
- Update `initiate_payment` to call `reserve_inventory` before calling Razorpay.
- Update `_handle_payment_captured` to call `commit_reservation`.
- Update `_handle_payment_failed` to call `release_reservation`.

### C. API Endpoints
- **POST** `/api/v1/inventory/release-expired`: A maintenance endpoint to release reservations where `expires_at < now()`.
- **POST** `/api/v1/agreements/{id}/fulfill`: Endpoint for the merchant to mark a committed reservation as fulfilled.

## 5. Failure & Recovery Matrix

| Scenario | Detection | Response | Final State |
| :--- | :--- | :--- | :--- |
| **Concurrent Oversell** | Atomic `UPDATE` returns 0 rows | Return 400 Insufficient Inventory | No reservation created |
| **Payment Fails** | Webhook `payment.failed` | Release inventory | `RELEASED` |
| **Razorpay Initiation Fails** | Razorpay SDK throws exception | Release inventory immediately | `RELEASED` |
| **Buyer Abandons Checkout** | Reservation passes `expires_at` | Maintenance endpoint releases inventory | `EXPIRED` |
| **Duplicate Webhook** | Handled by Phase 7 Idempotency | DB unique constraint catches it | `COMMITTED` (No duplicate deduction) |

## Configuration
- `INVENTORY_RESERVATION_TTL_MINUTES`: Default 15 minutes, configurable in environment.

## 6. Execution Tasks
- [ ] Update `Product` model with any missing constraints and create `InventoryReservation` model.
- [ ] Generate Alembic migration.
- [ ] Implement `InventoryService` (reserve, commit, release, release_expired, fulfill).
- [ ] Update `PaymentService` to call `reserve_inventory` and `commit_reservation`.
- [ ] Create API endpoints (`/api/v1/inventory/release-expired`, `/api/v1/agreements/{id}/fulfill`).
- [ ] Write Unit and Concurrency tests (`tests/integration/test_inventory_service.py`).
- [ ] Update documentation (`docs/INVENTORY.md` and others).
