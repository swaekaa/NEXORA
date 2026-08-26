import uuid
import pytest
from sqlalchemy import insert
from decimal import Decimal

from app.models.merchant import Merchant
from app.models.buyer import Buyer
from app.models.product import Product
from app.models.negotiation import Negotiation
from app.models.agreement import Agreement, AgreementStatus
from app.models.approval_request import ApprovalStatus, ApprovalRequest
from app.services import approval_service
from app.exceptions import InvalidStateTransitionError
from app.database.connection import get_db

@pytest.fixture
async def db_session():
    async for session in get_db():
        yield session
        await session.rollback()


@pytest.fixture
async def setup_agreement(db_session):
    merchant_id = uuid.uuid4()
    buyer_id = uuid.uuid4()
    product_id = uuid.uuid4()
    negotiation_id = uuid.uuid4()
    agreement_id = uuid.uuid4()

    await db_session.execute(insert(Merchant).values(id=merchant_id, name="Test Merchant", email=f"m_{merchant_id}@test.com", status="active"))
    await db_session.execute(insert(Buyer).values(id=buyer_id, name="Test Buyer", email=f"b_{buyer_id}@test.com", status="active"))
    await db_session.execute(insert(Product).values(id=product_id, merchant_id=merchant_id, sku="SKU-123", name="Product", description="D", price=Decimal("100"), inventory=10, status="active"))
    await db_session.execute(insert(Negotiation).values(id=negotiation_id, merchant_id=merchant_id, buyer_id=buyer_id, product_id=product_id, state="accepted", round_count=1))
    
    await db_session.execute(insert(Agreement).values(
        id=agreement_id,
        negotiation_id=negotiation_id,
        merchant_id=merchant_id,
        buyer_id=buyer_id,
        product_id=product_id,
        product_name="Product",
        quantity=1,
        unit_price=Decimal("100"),
        total_amount=Decimal("100"),
        currency="INR",
        payment_terms="upfront",
        delivery_days=1,
        warranty_months=1,
        status=AgreementStatus.PENDING_APPROVAL.value
    ))
    
    await db_session.commit()
    
    return agreement_id, merchant_id


@pytest.mark.asyncio
async def test_create_and_approve(db_session, setup_agreement):
    agreement_id, merchant_id = setup_agreement
    
    from app.services.agreement_service import get_agreement
    agreement = await get_agreement(db_session, agreement_id)
    
    approval = await approval_service.create_approval_request(
        db_session, agreement, "HUMAN_APPROVAL_REQUIRED", "Testing"
    )
    await db_session.commit()
    
    assert approval.status == ApprovalStatus.PENDING
    
    # Approve
    actor_id = uuid.uuid4()
    approved = await approval_service.approve(db_session, approval.id, merchant_id, actor_id)
    assert approved.status == ApprovalStatus.APPROVED
    
    # Try reject -> error
    with pytest.raises(InvalidStateTransitionError):
        await approval_service.reject(db_session, approval.id, merchant_id, actor_id, "No")


@pytest.mark.asyncio
async def test_create_and_reject(db_session, setup_agreement):
    agreement_id, merchant_id = setup_agreement
    
    from app.services.agreement_service import get_agreement
    agreement = await get_agreement(db_session, agreement_id)
    
    approval = await approval_service.create_approval_request(
        db_session, agreement, "HUMAN_APPROVAL_REQUIRED", "Testing"
    )
    await db_session.commit()
    
    assert approval.status == ApprovalStatus.PENDING
    
    # Reject
    actor_id = uuid.uuid4()
    rejected = await approval_service.reject(db_session, approval.id, merchant_id, actor_id, "Budget exceeded")
    assert rejected.status == ApprovalStatus.REJECTED
    assert rejected.resolution_reason == "Budget exceeded"
