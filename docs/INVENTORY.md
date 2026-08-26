# NEXORA Inventory Architecture

This document outlines the inventory reservation and fulfillment system implemented in Phase 8.

## The Principle
**"LLMs PROPOSE. DETERMINISTIC SYSTEMS DECIDE."**
Inventory is not an AI decision. Agents have ZERO authority over inventory. Only the deterministic Application Layer (via the `InventoryService`) modifies stock levels.

## The "Reserve-First" Flow
To guarantee that a buyer never successfully pays for an out-of-stock item, we use a Reserve-First architecture:
1. `Agreement` is negotiated and `VALIDATED`.
2. Buyer initiates payment.
3. **`InventoryService`** deducts stock and creates a `RESERVED` record.
4. `PaymentService` creates the Razorpay order and returns intent to the client.
5. Buyer completes checkout.
6. Webhook receives `payment.captured`.
7. **`InventoryService`** updates the reservation to `COMMITTED`.
8. Merchant ships goods, transitioning reservation to `FULFILLED`.

## Concurrency Control
We prevent overselling and negative inventory using PostgreSQL's atomic operations:
```sql
UPDATE products 
SET inventory = inventory - :quantity 
WHERE id = :product_id AND inventory >= :quantity
```
If two buyers attempt to purchase the last unit at the same millisecond, the database serializes the `UPDATE`. Exactly one request will find `inventory >= quantity` to be true. The other request's `rowcount` will be `0`, allowing us to gracefully raise an `InsufficientInventoryError`.

## Expiration & Recovery
- **TTL**: Reservations default to 15 minutes (`INVENTORY_RESERVATION_TTL_MINUTES`).
- **Client Abandonment**: If the checkout is abandoned, the reservation passes its `expires_at` timestamp. A maintenance cron/endpoint (`/api/v1/inventory/release-expired`) reaps these and refunds the inventory.
- **Payment Failure**: If Razorpay fails immediately or sends a `payment.failed` webhook, the reservation is instantly transitioned to `RELEASED` and inventory is refunded.
- **Crash Recovery**: If the server crashes *after* reserving inventory but *before* Razorpay is called, the reservation remains `RESERVED` and naturally expires via TTL, ensuring safety.

## Failure Scenarios Matrix

| Scenario | Detection | Response | Final State |
| :--- | :--- | :--- | :--- |
| **Concurrent Oversell** | Atomic `UPDATE` returns 0 rows | Return 400 Insufficient Inventory | No reservation created |
| **Payment Fails** | Webhook `payment.failed` | Release inventory | `RELEASED` |
| **Razorpay Initiation Fails** | Razorpay SDK throws exception | Release inventory immediately | `RELEASED` |
| **Buyer Abandons Checkout** | Reservation passes `expires_at` | Maintenance endpoint releases inventory | `EXPIRED` |
| **Duplicate Webhook** | Handled by Phase 7 Idempotency | DB unique constraint catches it | `COMMITTED` (No duplicate deduction) |

## API Endpoints
- `POST /api/v1/inventory/release-expired`: Maintenance endpoint to reap expired reservations.
- `POST /api/v1/inventory/agreements/{agreement_id}/fulfill`: Marks a `COMMITTED` reservation as `FULFILLED`.
