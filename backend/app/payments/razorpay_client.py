"""
NEXORA — Razorpay Client Abstraction

Thin wrapper around the Razorpay Python SDK.
Contains zero business rules.
"""
import hmac
import hashlib
from typing import Any, Protocol

import razorpay

from app.config import settings


class RazorpayClientProtocol(Protocol):
    def create_order(self, amount_paise: int, currency: str, receipt: str, notes: dict) -> dict:
        ...
        
    def fetch_order(self, order_id: str) -> dict:
        ...
        
    def fetch_orders_by_receipt(self, receipt: str) -> list[dict]:
        ...
        
    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        ...


class RazorpayClient:
    def __init__(self):
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise ValueError("Razorpay credentials not configured")
            
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        
    def create_order(self, amount_paise: int, currency: str, receipt: str, notes: dict) -> dict:
        return self.client.order.create({
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "notes": notes
        })
        
    def fetch_order(self, order_id: str) -> dict:
        return self.client.order.fetch(order_id)
        
    def fetch_orders_by_receipt(self, receipt: str) -> list[dict]:
        # fetch_all returns a dict with 'count' and 'items'
        response = self.client.order.fetch_all({"receipt": receipt})
        return response.get("items", [])
        
    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        if not self.webhook_secret:
            raise ValueError("Webhook secret not configured")
            
        expected_signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)


class FakeRazorpayClient:
    """Deterministic mock client for isolated testing."""
    def __init__(self):
        self.orders = {}
        # Allows tests to force a failure
        self.should_fail_create = False
        
    def create_order(self, amount_paise: int, currency: str, receipt: str, notes: dict) -> dict:
        if self.should_fail_create:
            raise Exception("Fake network error")
            
        order_id = f"order_fake_{receipt}"
        order = {
            "id": order_id,
            "entity": "order",
            "amount": amount_paise,
            "amount_paid": 0,
            "amount_due": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
            "attempts": 0,
            "notes": notes,
            "created_at": 1700000000
        }
        self.orders[order_id] = order
        return order
        
    def fetch_order(self, order_id: str) -> dict:
        if order_id not in self.orders:
            raise Exception("Invalid order id")
        return self.orders[order_id]
        
    def fetch_orders_by_receipt(self, receipt: str) -> list[dict]:
        return [o for o in self.orders.values() if o.get("receipt") == receipt]
        
    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        # Mock logic: Accept if signature == "valid_signature", else reject
        return signature == "valid_signature"


# Dependency Injection Getter
def get_razorpay_client() -> RazorpayClientProtocol:
    # In a real framework, you might use DI containers or FastAPI Depends,
    # but for simple access:
    return RazorpayClient()
