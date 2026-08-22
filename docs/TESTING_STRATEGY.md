# NEXORA — Testing Strategy

**Version:** 1.0  
**Date:** August 22, 2026

---

## Testing Philosophy

1. **Policy engine is unit-testable without any mocking** — pure functions, no dependencies
2. **Agent tools are testable via schema validation** — no LLM needed
3. **Payment flow is integration-testable with Razorpay Test Mode**
4. **All 7 failure cases have explicit tests**
5. **Financial calculations have boundary tests at every paise boundary**

---

## Test Structure

```
backend/tests/
├── unit/
│   ├── test_policy_engine.py           ← 40+ test cases (no mocking)
│   ├── test_agreement_integrity.py     ← total calculation tests
│   ├── test_negotiation_states.py      ← state machine tests
│   ├── test_buyer_tool_schemas.py      ← Pydantic validation tests
│   ├── test_merchant_tool_schemas.py   ← Pydantic validation tests
│   ├── test_webhook_signature.py       ← HMAC verification tests
│   └── test_amount_conversion.py       ← paise conversion tests
├── integration/
│   ├── test_negotiation_flow.py        ← full negotiation happy path
│   ├── test_agreement_flow.py          ← agreement creation + validation
│   ├── test_payment_flow.py            ← Razorpay Test Mode (requires keys)
│   ├── test_webhook_processor.py       ← webhook handling
│   └── test_failure_scenarios.py       ← all 7 failure cases
└── fixtures/
    ├── demo_merchant.json
    ├── demo_buyer.json
    ├── demo_product.json
    ├── demo_policy.json
    └── sample_webhooks/
        ├── payment_captured.json
        ├── payment_failed.json
        └── invalid_signature.json
```

---

## Unit Tests: Policy Engine

Target: **40+ test cases**, zero mocking.

```python
# test_policy_engine.py
class TestMinPriceRule:
    def test_exactly_at_minimum_passes(self):
        result = engine.check_min_price(unit_price=D("10500.00"), min_price=D("10500.00"))
        assert result.passed
    
    def test_one_paise_below_minimum_fails(self):
        result = engine.check_min_price(unit_price=D("10499.99"), min_price=D("10500.00"))
        assert not result.passed
        assert "10499.99" in result.reason
        assert "10500.00" in result.reason

class TestBulkDiscountRule:
    @pytest.mark.parametrize("qty,expected_pct", [
        (1, D("0.00")),
        (49, D("0.00")),
        (50, D("5.00")),
        (99, D("5.00")),
        (100, D("8.00")),
        (1000, D("8.00")),
    ])
    def test_bulk_discount_tiers(self, qty, expected_pct):
        pct = engine.get_bulk_discount(qty, demo_policy.bulk_discounts)
        assert pct == expected_pct

class TestTotalIntegrity:
    def test_correct_total_passes(self):
        result = engine.check_total_integrity(
            unit_price=D("10819.20"), quantity=100, total=D("1081920.00")
        )
        assert result.passed
    
    def test_one_paise_mismatch_fails(self):
        result = engine.check_total_integrity(
            unit_price=D("10819.20"), quantity=100, total=D("1081920.01")
        )
        assert not result.passed

class TestAutonomousLimit:
    def test_exactly_at_limit_passes(self):
        result = engine.check_autonomous_limit(D("1000000.00"), D("1000000.00"))
        assert result.decision == PolicyDecision.PASS
    
    def test_one_paise_above_requires_approval(self):
        result = engine.check_autonomous_limit(D("1000000.01"), D("1000000.00"))
        assert result.decision == PolicyDecision.REQUIRES_HUMAN_APPROVAL
```

---

## Unit Tests: Webhook Signature

```python
class TestWebhookSignature:
    def test_valid_signature_passes(self):
        secret = "test_secret"
        body = b'{"event": "payment.captured"}'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert verify_webhook_signature(body, sig, secret)
    
    def test_invalid_signature_fails(self):
        assert not verify_webhook_signature(b"body", "wrong_sig", "secret")
    
    def test_empty_signature_fails(self):
        assert not verify_webhook_signature(b"body", "", "secret")
    
    def test_tampered_body_fails(self):
        secret = "test_secret"
        original = b'{"amount": 100}'
        tampered = b'{"amount": 99999}'
        sig = hmac.new(secret.encode(), original, hashlib.sha256).hexdigest()
        assert not verify_webhook_signature(tampered, sig, secret)
```

---

## Integration Tests: Failure Scenarios

```python
class TestFailureScenarios:
    async def test_f1_payment_amount_mismatch(self, client, seeded_db):
        # Create valid negotiation and agreement
        agreement = await create_demo_agreement(seeded_db)
        
        # Simulate webhook with tampered amount
        tampered_payload = build_payment_captured_payload(
            order_id=agreement.razorpay_order_id,
            amount_paise=int(agreement.total_amount * 100) + 100  # +1 rupee
        )
        sig = sign_payload(tampered_payload, WEBHOOK_SECRET)
        response = await client.post(
            "/api/v1/webhooks/razorpay",
            content=tampered_payload,
            headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_001"}
        )
        assert response.status_code == 200  # Accepted but blocked internally
        
        # Agreement NOT marked as paid
        refreshed = await get_agreement(seeded_db, agreement.id)
        assert refreshed.status == "PAYMENT_INITIATED"  # unchanged
        
        # Audit event recorded
        events = await get_audit_events(seeded_db, agreement_id=agreement.id)
        assert any(e.action == "PAYMENT_AMOUNT_MISMATCH" for e in events)
    
    async def test_f4_duplicate_webhook_skipped(self, client, seeded_db):
        payload = build_payment_captured_payload(order_id="order_test", amount_paise=100000)
        sig = sign_payload(payload, WEBHOOK_SECRET)
        headers = {"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_dupe_001"}
        
        # First call
        r1 = await client.post("/api/v1/webhooks/razorpay", content=payload, headers=headers)
        assert r1.status_code == 200
        
        # Duplicate call (same event_id)
        r2 = await client.post("/api/v1/webhooks/razorpay", content=payload, headers=headers)
        assert r2.status_code == 200
        assert r2.json()["status"] == "already_processed"
    
    async def test_f6_invalid_signature_rejected(self, client):
        payload = b'{"event": "payment.captured", "payload": {}}'
        response = await client.post(
            "/api/v1/webhooks/razorpay",
            content=payload,
            headers={"X-Razorpay-Signature": "invalid_sig", "X-Razorpay-Event-Id": "evt_bad"}
        )
        assert response.status_code == 400
```

---

## Running Tests

```bash
# Unit tests only (fast, no Razorpay keys needed)
cd backend
pytest tests/unit/ -v

# All tests (requires .env with RAZORPAY test keys)
pytest tests/ -v

# Specific failure scenario tests
pytest tests/integration/test_failure_scenarios.py -v

# Coverage report
pytest --cov=app --cov-report=html tests/
```

---

## CI Targets

| Category | Minimum |
|----------|---------|
| Policy Engine unit tests | 40 |
| Webhook unit tests | 10 |
| Integration tests (happy path) | 5 |
| Integration tests (failure cases) | 7 |
| Overall coverage | > 70% |
