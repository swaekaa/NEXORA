import uuid
import pytest
from app.services.audit_service import record_event, get_merchant_audit, get_agreement_audit, AuditEventType
from app.database.connection import get_db

@pytest.fixture
async def db_session():
    async for session in get_db():
        yield session
        await session.rollback()

@pytest.mark.asyncio
async def test_record_event(db_session):
    actor_id = uuid.uuid4()
    agreement_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    
    event = await record_event(
        session=db_session,
        event_type=AuditEventType.POLICY_CHECK,
        actor_type="SYSTEM",
        actor_id=actor_id,
        agreement_id=agreement_id,
        merchant_id=merchant_id,
        metadata={"decision": "ALLOW"}
    )
    
    await db_session.commit()
    
    assert event.id is not None
    assert event.event_type == AuditEventType.POLICY_CHECK
    assert event.metadata_ == {"decision": "ALLOW"}
    
    # Verify append-only by fetching
    events = await get_merchant_audit(db_session, merchant_id)
    assert len(events) == 1
    assert events[0].id == event.id
    
    events_agr = await get_agreement_audit(db_session, agreement_id, merchant_id)
    assert len(events_agr) == 1
    assert events_agr[0].id == event.id
