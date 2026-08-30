import asyncio
from sqlalchemy import delete
from app.database.connection import AsyncSessionLocal
from app.models.payment import Payment

async def cleanup():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(Payment).where(Payment.status == "created")
        )
        await session.commit()
        print(f"✅ Cleared {result.rowcount} stuck Payment records.")
        print("You can now click 'PAY NOW' on any existing approved Deals in your dashboard.")
        print("A fresh Razorpay order will be generated successfully!")

if __name__ == "__main__":
    asyncio.run(cleanup())
