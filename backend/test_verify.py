import asyncio
from app.database.connection import AsyncSessionLocal
from sqlalchemy import select
from app.models.payment import Payment
from app.models.agreement import Agreement
from app.services.inventory_service import commit_reservation

async def test():
    async with AsyncSessionLocal() as session:
        # Find the payment that was created and paid in Razorpay but stuck
        result = await session.execute(
            select(Payment).where(Payment.razorpay_order_id == "order_TVxdY8uvV5oy1c")
        )
        payment = result.scalar_one_or_none()
        if not payment:
            print("Payment not found")
            return
            
        print("Found payment!")
        # Let's try to simulate the commit reservation step
        try:
            await commit_reservation(session, payment.agreement_id)
            print("Commit reservation succeeded!")
        except Exception as e:
            print(f"Commit reservation FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test())
