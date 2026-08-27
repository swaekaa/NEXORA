import uuid
from decimal import Decimal
import pytest

from app.agents.buyer.constraints import BuyerConstraintEngine
from app.agents.buyer.schemas import BuyerIntent

def test_buyer_constraint_engine_passes_valid_proposal():
    engine = BuyerConstraintEngine()
    intent = BuyerIntent(
        buyer_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        product_query="Laptop",
        quantity=5,
        maximum_budget=Decimal("5000.00"),
        preferred_currency="INR"
    )
    
    # 5 * 1000 = 5000 (exactly at budget)
    result = engine.evaluate_proposal(intent, Decimal("1000.00"), Decimal("5"))
    assert result.passed is True
    assert len(result.reasons) == 0


def test_buyer_constraint_engine_fails_quantity_mismatch():
    engine = BuyerConstraintEngine()
    intent = BuyerIntent(
        buyer_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        product_query="Laptop",
        quantity=5,
        maximum_budget=Decimal("5000.00"),
        preferred_currency="INR"
    )
    
    result = engine.evaluate_proposal(intent, Decimal("1000.00"), Decimal("4"))
    assert result.passed is False
    assert "Quantity mismatch" in result.reasons[0]


def test_buyer_constraint_engine_fails_budget_exceeded():
    engine = BuyerConstraintEngine()
    intent = BuyerIntent(
        buyer_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        product_query="Laptop",
        quantity=5,
        maximum_budget=Decimal("5000.00"),
        preferred_currency="INR"
    )
    
    # 5 * 1000.01 = 5000.05 > 5000.00
    result = engine.evaluate_proposal(intent, Decimal("1000.01"), Decimal("5"))
    assert result.passed is False
    assert "Budget exceeded" in result.reasons[0]
