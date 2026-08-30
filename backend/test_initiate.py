import asyncio
import uuid
from app.database.connection import AsyncSessionLocal
from app.models.agreement import Agreement
from sqlalchemy import select
from app.services.payment_service import initiate_payment, PaymentServiceError
from app.payments.razorpay_client import get_razorpay_client

async def test():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Agreement).where(Agreement.status.in_(["approved", "payment_initiated", "pending_payment"])).order_by(Agreement.created_at.desc())
        )
        agreements = result.scalars().all()
        
        client = get_razorpay_client()
        success = False
        for agreement in agreements:
            try:
                payment = await initiate_payment(session, agreement.id, client)
                print(f"SUCCESS on Agreement {agreement.id}!")
                print(f"Payment ID: {payment.id}")
                print(f"Order ID: {payment.razorpay_order_id}")
                print(f"Amount Paise: {payment.amount_paise}")
                
                order = client.fetch_order(payment.razorpay_order_id)
                print("Order fetched from Razorpay:", order)
                success = True
                break
            except Exception as e:
                pass
                
        if not success:
            print("All agreements failed to initiate payment.")

if __name__ == "__main__":
    asyncio.run(test())
