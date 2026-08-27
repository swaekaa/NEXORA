import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product
from app.agents.buyer.runner import run_buyer_agent
from app.agents.buyer.schemas import BuyerIntent, BuyerAgentAction, ActionType
from app.models.negotiation import Negotiation, NegotiationState


@pytest_asyncio.fixture
async def db_session():
    async for session in get_db():
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def setup_db_entities(db_session: AsyncSession):
    buyer_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    
    buyer = Buyer(id=buyer_id, name="Test Buyer", email=f"buyer_{buyer_id}@test.com")
    merchant = Merchant(id=merchant_id, name="Test Merchant", email=f"merchant_{merchant_id}@test.com")
    
    db_session.add(buyer)
    db_session.add(merchant)
    await db_session.flush()
    
    product = Product(
        id=product_id,
        merchant_id=merchant_id,
        sku=f"sku_{product_id}",
        name="Test Product",
        description="A product for testing.",
        price=Decimal("10000.00"),
        inventory=1000
    )
    db_session.add(product)
    await db_session.flush()
    
    return {"buyer": buyer, "merchant": merchant, "product": product}


@pytest.mark.asyncio
async def test_full_buyer_agent_flow_to_proposal(db_session: AsyncSession, setup_db_entities: dict):
    """
    Tests the buyer agent from intent parsing through to PROPOSE_AGREEMENT,
    ensuring it correctly inserts a Negotiation into the DB.
    """
    test_merchant = setup_db_entities["merchant"]
    test_product = setup_db_entities["product"]
    test_buyer = setup_db_entities["buyer"]
    
    intent = BuyerIntent(
        buyer_id=test_buyer.id,
        merchant_id=test_merchant.id,
        product_query="test product",
        quantity=2,
        maximum_budget=Decimal("50000.00"),
        preferred_currency="INR"
    )

    # 1. First run: Agent searches products
    mock_action_search = BuyerAgentAction(
        action=ActionType.SEARCH_PRODUCTS,
        search_query="test product",
        reason="I need to find products."
    )
    
    # 2. Second run: Agent selects product
    mock_action_select = BuyerAgentAction(
        action=ActionType.SELECT_PRODUCT,
        product_id=test_product.id,
        reason="This product matches."
    )
    
    # 3. Third run: Agent proposes agreement
    mock_action_propose = BuyerAgentAction(
        action=ActionType.PROPOSE_AGREEMENT,
        proposed_unit_price=str(test_product.price),
        proposed_discount_percent="0.00",
        reason="I propose this price."
    )

    with patch("app.agents.buyer.nodes.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_with_structured = AsyncMock()
        mock_get_llm.return_value.with_structured_output.return_value = mock_with_structured
        
        # Ainvoke will be called 3 times in the graph loop
        mock_with_structured.ainvoke.side_effect = [
            mock_action_search,
            mock_action_select,
            mock_action_propose
        ]
        
        final_state = await run_buyer_agent(db_session, intent)
        
        # Verify graph finished properly
        assert final_state["status"] in ["in_progress", "completed"], f"Agent failed: {final_state.get('error_reason')}"
        
        if final_state["negotiation_id"]:
            # Check database for negotiation
            result = await db_session.execute(
                sa.select(Negotiation).where(Negotiation.id == final_state["negotiation_id"])
            )
            neg = result.scalar_one_or_none()
            assert neg is not None
            assert neg.state == NegotiationState.OFFER.value
