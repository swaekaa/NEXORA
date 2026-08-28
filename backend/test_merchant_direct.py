import asyncio
import uuid
import logging
import time
from app.database.connection import AsyncSessionLocal
from app.agents.merchant.runner import run_merchant_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_merchant")

async def test_direct_merchant():
    negotiation_id = uuid.UUID("f629a4c9-ab64-4e9e-a889-befbcc4d2c7b") # from the screenshot!
    logger.info(f"Starting direct Merchant test for {negotiation_id}")
    
    async with AsyncSessionLocal() as session:
        try:
            start = time.time()
            result = await run_merchant_agent(session, negotiation_id)
            duration = time.time() - start
            logger.info(f"Direct test completed in {duration:.2f}s. Result: {result}")
        except Exception as e:
            logger.error(f"Direct test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_direct_merchant())
