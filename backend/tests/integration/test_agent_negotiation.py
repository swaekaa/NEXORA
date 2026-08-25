"""
Integration tests for Agent-to-Agent Negotiation (Phase 6).
Verifies the persistence boundary, state machine, and round limitations.
"""
import uuid
import pytest
import pytest_asyncio
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock

from app.database.connection import get_db
from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.product import Product
from app.models.negotiation import NegotiationState
from app.models.negotiation_message import SenderType, MessageType
from app.schemas.negotiation import NegotiationMessagePayload
from app.services.negotiation_service import (
    create_negotiation_with_proposal,
    append_negotiation_message,
    get_negotiation,
    get_negotiation_messages,
    NegotiationTerminalError
)

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def db_session():
    # Setup real DB session for integration test
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
    
    return buyer_id, merchant_id, product_id

async def test_negotiation_persistence_boundary(db_session: AsyncSession, setup_db_entities):
    mock_buyer_id, mock_merchant_id, mock_product_id = setup_db_entities
    
    # 1. Buyer creates proposal
    payload = NegotiationMessagePayload(
        product_id=mock_product_id,
        quantity=100,
        unit_price=Decimal("9500.00"),
        total_amount=Decimal("950000.00")
    )
    
    negotiation = await create_negotiation_with_proposal(
        session=db_session,
        buyer_id=mock_buyer_id,
        merchant_id=mock_merchant_id,
        product_id=mock_product_id,
        payload=payload
    )
    
    assert negotiation.state == NegotiationState.OFFER.value
    assert negotiation.round_count == 1
    
    messages = await get_negotiation_messages(db_session, negotiation.id)
    assert len(messages) == 1
    assert messages[0].sender_type == SenderType.BUYER_AGENT.value
    
    # 2. Merchant Agent processes and counters
    merchant_payload = NegotiationMessagePayload(
        product_id=mock_product_id,
        quantity=100,
        unit_price=Decimal("10500.00"),
        total_amount=Decimal("1050000.00")
    )
    
    await append_negotiation_message(
        session=db_session,
        negotiation_id=negotiation.id,
        sender_type=SenderType.MERCHANT_AGENT,
        sender_id=str(mock_merchant_id),
        message_type=MessageType.COUNTER_OFFER,
        payload=merchant_payload
    )
    
    await db_session.refresh(negotiation)
    assert negotiation.state == NegotiationState.COUNTER_OFFER.value
    # Round count does NOT increment on merchant reply
    assert negotiation.round_count == 1
    
    # 3. Buyer Agent processes and counters
    buyer_payload = NegotiationMessagePayload(
        product_id=mock_product_id,
        quantity=100,
        unit_price=Decimal("10000.00"),
        total_amount=Decimal("1000000.00")
    )
    
    await append_negotiation_message(
        session=db_session,
        negotiation_id=negotiation.id,
        sender_type=SenderType.BUYER_AGENT,
        sender_id=str(mock_buyer_id),
        message_type=MessageType.COUNTER_OFFER,
        payload=buyer_payload
    )
    
    await db_session.refresh(negotiation)
    # Round count INCREMENTS when buyer makes a new counter-offer
    assert negotiation.round_count == 2
    
    # 4. Merchant Accepts
    await append_negotiation_message(
        session=db_session,
        negotiation_id=negotiation.id,
        sender_type=SenderType.MERCHANT_AGENT,
        sender_id=str(mock_merchant_id),
        message_type=MessageType.ACCEPT,
        payload=buyer_payload # Accepting the same terms
    )
    
    await db_session.refresh(negotiation)
    assert negotiation.state == NegotiationState.ACCEPTED.value
    
    # 5. Verify Terminal Protection
    with pytest.raises(NegotiationTerminalError):
        await append_negotiation_message(
            session=db_session,
            negotiation_id=negotiation.id,
            sender_type=SenderType.BUYER_AGENT,
            sender_id=str(mock_buyer_id),
            message_type=MessageType.COUNTER_OFFER,
            payload=buyer_payload
        )
