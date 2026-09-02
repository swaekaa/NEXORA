import asyncio
import json
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc
from app.models.audit_event import AuditEvent
from app.config import settings

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

async def get_logs():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(
            select(AuditEvent)
            .order_by(desc(AuditEvent.created_at))
            .limit(10)
        )
        events = result.scalars().all()
        for e in reversed(events):
            print(f"[{e.created_at}] {e.event_type} | Actor: {e.actor_type} | Metadata: {json.dumps(e.metadata, cls=UUIDEncoder)}")
            
if __name__ == "__main__":
    asyncio.run(get_logs())
