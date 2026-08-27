import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import select
from app.database.connection import get_db
from app.models.negotiation_message import NegotiationMessage

async def main():
    async for session in get_db():
        result = await session.execute(
            select(NegotiationMessage)
            .where(NegotiationMessage.payload.is_not(None))
            .limit(1)
        )
        msg = result.scalar_one_or_none()
        print(f"Found message: {msg}")
        break

if __name__ == "__main__":
    asyncio.run(main())
