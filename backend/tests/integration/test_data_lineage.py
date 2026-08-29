"""
Integration tests for Data Lineage.
Proves that user constraints survive the entire pipeline and no hardcoded demo values leak into LIVE mode.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.buyer.schemas import BuyerIntent
from app.agents.buyer.runner import run_buyer_agent
from app.agents.merchant.runner import run_merchant_agent
from app.agents.buyer.schemas import BuyerAgentAction, ActionType
from app.agents.merchant.schemas import MerchantAgentAction, MerchantActionType
from app.database.connection import get_db

@pytest.fixture
async def db_session():
    async for session in get_db():
        yield session
        await session.rollback()

@pytest.fixture
async def setup_db_entities(db_session: AsyncSession):
    from app.models.buyer import Buyer
    from app.models.merchant import Merchant
    from app.models.product import Product
    from app.models.policy import Policy
    
    buyer_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    
    buyer = Buyer(id=buyer_id, name="Test Buyer", email=f"buyer_{buyer_id}@test.com")
    merchant = Merchant(id=merchant_id, name="Test Merchant", email=f"merchant_{merchant_id}@test.com")
    db_session.add_all([buyer, merchant])
    await db_session.flush()
    
    product = Product(
        id=product_id, merchant_id=merchant_id, sku=f"sku_{product_id}", name="Test Product",
        description="A product for testing.", price=Decimal("15000.00"), inventory=1000
    )
    db_session.add(product)
    
    policy = Policy(
        id=uuid.uuid4(), merchant_id=merchant_id, name="Test Policy", minimum_price=Decimal("8000.00"),
        maximum_discount_percent=Decimal("50.0"), maximum_autonomous_transaction=Decimal("2000000.00"),
        human_approval_required=False, is_active=True
    )
    db_session.add(policy)
    await db_session.flush()
    return {"buyer": buyer, "merchant": merchant, "product": product}

@pytest.mark.asyncio
@patch("app.agents.buyer.nodes.get_llm")
@patch("app.agents.merchant.nodes.get_llm")
async def test_user_constraints_survive_pipeline(
    mock_merchant_llm_getter, mock_buyer_llm_getter,
    db_session: AsyncSession, setup_db_entities: dict
):
    buyer_id = setup_db_entities["buyer"].id
    merchant_id = setup_db_entities["merchant"].id
    product = setup_db_entities["product"]
    
    intent = BuyerIntent(
        buyer_id=buyer_id, merchant_id=merchant_id,
        product_query="Buy 10 monitors",
        maximum_budget=Decimal("100000.00"), quantity=10, preferred_currency="INR"
    )
    
    mock_buyer_llm = MagicMock()
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=str(product.id), proposed_unit_price="9500.00", reason="Proposing"
    ))
    mock_buyer_llm_getter.return_value.with_structured_output.return_value = mock_buyer_llm
    
    buyer_state = await run_buyer_agent(db_session, intent)
    negotiation_id = buyer_state["negotiation_id"]
    
    from app.services.negotiation_service import get_negotiation
    db_session.expire_all()
    neg = await get_negotiation(db_session, negotiation_id)
    
    # Assert values
    assert neg.quantity == 10
    assert neg.budget == Decimal("100000.00")
    
    # Merchant counters
    mock_merchant_llm = MagicMock()
    mock_merchant_llm.ainvoke = AsyncMock(return_value=MerchantAgentAction(
        action=MerchantActionType.COUNTER_PROPOSAL,
        proposed_unit_price="9800.00", proposed_quantity=10, reason="Countering"
    ))
    mock_merchant_llm_getter.return_value.with_structured_output.return_value = mock_merchant_llm
    
    await run_merchant_agent(db_session, negotiation_id)
    
    # Check messages
    from app.services.negotiation_service import get_negotiation_messages
    messages = await get_negotiation_messages(db_session, negotiation_id)
    
    assert messages[0].structured_data["quantity"] == 10
    assert messages[0].structured_data["unit_price"] == "9500.00"
    
    assert messages[1].structured_data["quantity"] == 10
    assert messages[1].structured_data["unit_price"] == "9800.00"
    
    # Assert Demo values didn't leak
    for msg in messages:
        if "quantity" in msg.structured_data:
            assert msg.structured_data["quantity"] != 100
        if "unit_price" in msg.structured_data:
            assert msg.structured_data["unit_price"] not in ["820.00", "850.00", "8750.00"]

@pytest.mark.asyncio
@patch("app.agents.buyer.nodes.get_llm")
async def test_different_constraints_produce_different_negotiations(
    mock_buyer_llm_getter,
    db_session: AsyncSession, setup_db_entities: dict
):
    buyer_id = setup_db_entities["buyer"].id
    merchant_id = setup_db_entities["merchant"].id
    product = setup_db_entities["product"]
    
    # Input A
    intent_a = BuyerIntent(
        buyer_id=buyer_id, merchant_id=merchant_id,
        product_query="Buy", maximum_budget=Decimal("100000.00"), quantity=10, preferred_currency="INR"
    )
    
    mock_buyer_llm = MagicMock()
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=str(product.id), proposed_unit_price="9000.00", reason="Proposing"
    ))
    mock_buyer_llm_getter.return_value.with_structured_output.return_value = mock_buyer_llm
    
    state_a = await run_buyer_agent(db_session, intent_a)
    
    # Input B
    intent_b = BuyerIntent(
        buyer_id=buyer_id, merchant_id=merchant_id,
        product_query="Buy", maximum_budget=Decimal("77000.00"), quantity=7, preferred_currency="INR"
    )
    
    state_b = await run_buyer_agent(db_session, intent_b)
    
    from app.services.negotiation_service import get_negotiation
    db_session.expire_all()
    neg_a = await get_negotiation(db_session, state_a["negotiation_id"])
    neg_b = await get_negotiation(db_session, state_b["negotiation_id"])
    
    assert neg_a.quantity == 10
    assert neg_a.budget == Decimal("100000.00")
    
    assert neg_b.quantity == 7
    assert neg_b.budget == Decimal("77000.00")
    
    assert neg_a.quantity != neg_b.quantity
    assert neg_a.budget != neg_b.budget

@pytest.mark.asyncio
@patch("app.agents.buyer.nodes.get_llm")
async def test_live_mode_never_uses_demo_values(
    mock_buyer_llm_getter,
    db_session: AsyncSession, setup_db_entities: dict
):
    buyer_id = setup_db_entities["buyer"].id
    merchant_id = setup_db_entities["merchant"].id
    product = setup_db_entities["product"]
    
    intent = BuyerIntent(
        buyer_id=buyer_id, merchant_id=merchant_id,
        product_query="Buy 3", maximum_budget=Decimal("45000.00"), quantity=3, preferred_currency="INR"
    )
    
    mock_buyer_llm = MagicMock()
    mock_buyer_llm.ainvoke = AsyncMock(return_value=BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        product_id=str(product.id), proposed_unit_price="12000.00", reason="Proposing"
    ))
    mock_buyer_llm_getter.return_value.with_structured_output.return_value = mock_buyer_llm
    
    state = await run_buyer_agent(db_session, intent)
    
    from app.services.negotiation_service import get_negotiation, get_negotiation_messages
    db_session.expire_all()
    neg = await get_negotiation(db_session, state["negotiation_id"])
    messages = await get_negotiation_messages(db_session, state["negotiation_id"])
    
    assert neg.quantity == 3
    assert neg.quantity != 100
    
    assert messages[0].structured_data["quantity"] == 3
    assert messages[0].structured_data["quantity"] != 100
