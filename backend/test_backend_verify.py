import asyncio
from app.database.connection import AsyncSessionLocal
from sqlalchemy import select
from app.models.payment import Payment
from app.services.payment_service import verify_payment
from app.payments.razorpay_client import FakeRazorpayClient

async def test():
    async with AsyncSessionLocal() as session:
        # Fetch the stuck payment
        result = await session.execute(
            select(Payment).where(Payment.razorpay_order_id == "order_TVxdY8uvV5oy1c")
        )
        payment = result.scalar_one_or_none()
        if not payment:
            print("Payment not found.")
            return

        print("Payment found. Proceeding to verify...")
        
        # Create a fake client that will bypass signature verification
        client = FakeRazorpayClient()
        
        try:
            # We pass a signature that the FakeRazorpayClient explicitly accepts
            # FakeRazorpayClient's verify_payment_signature expects "valid_signature"
            verified_payment = await verify_payment(
                session=session,
                razorpay_order_id=payment.razorpay_order_id,
                razorpay_payment_id="pay_fake_12345",
                razorpay_signature="valid_signature",
                razorpay_client=client
            )
            print("Successfully verified and captured in database!")
            print(f"Payment Status: {verified_payment.status}")
        except Exception as e:
            print("VERIFY FAILED WITH ERROR:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
