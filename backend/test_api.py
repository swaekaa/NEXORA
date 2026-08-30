import asyncio
import httpx

async def test_initiate():
    # Fetch an agreement to use
    async with httpx.AsyncClient() as client:
        # We don't have the UUID easily, let's just see if we can spot the issue by looking at the Pydantic models.
        pass
