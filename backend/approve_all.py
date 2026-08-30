import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select
from app.database.connection import AsyncSessionLocal
from app.models.agreement import Agreement, AgreementStatus
from app.models.payment import Payment, PaymentStatus
from app.services.inventory_service import commit_reservation
from app.services.audit_service import record_event, AuditEventType
from app.payments.utils import convert_decimal_to_paise

async def process_all():
    async with AsyncSessionLocal() as session:
        # Fetch all agreements that are ready for payment or stuck
        result = await session.execute(
            select(Agreement).where(
                Agreement.status.in_([
                    AgreementStatus.VALIDATED.value, 
                    AgreementStatus.APPROVED.value, 
                    AgreementStatus.PAYMENT_INITIATED.value,
                    "pending_payment"
                ])
            )
        )
        agreements = result.scalars().all()
        
        if not agreements:
            print("No pending agreements found to capture.")
            return

        print(f"Found {len(agreements)} agreements to manually mark as CAPTURED.")
        
        count = 0
        for agreement in agreements:
            try:
                # 1. Ensure a Payment row exists and is captured
                pay_result = await session.execute(
                    select(Payment).where(Payment.agreement_id == agreement.id)
                )
                payment = pay_result.scalar_one_or_none()
                
                amount_paise = convert_decimal_to_paise(agreement.total_amount)
                
                if not payment:
                    payment = Payment(
                        agreement_id=agreement.id,
                        amount=agreement.total_amount,
                        amount_paise=amount_paise,
                        currency=agreement.currency,
                        status=PaymentStatus.CAPTURED.value,
                        razorpay_order_id=f"order_sim_{str(uuid.uuid4())[:12]}",
                        razorpay_payment_id=f"pay_sim_{str(uuid.uuid4())[:12]}",
                        captured_at=datetime.now(timezone.utc)
                    )
                    session.add(payment)
                else:
                    payment.status = PaymentStatus.CAPTURED.value
                    payment.razorpay_payment_id = f"pay_sim_{str(uuid.uuid4())[:12]}"
                    payment.captured_at = datetime.now(timezone.utc)
                    session.add(payment)
                
                # 2. Update Agreement Status
                agreement.status = AgreementStatus.PAYMENT_CAPTURED.value
                session.add(agreement)
                
                # 3. Commit inventory (skip if already committed or errors)
                try:
                    await commit_reservation(session, agreement.id)
                except Exception:
                    pass # Ignore if no reservation exists
                
                # 4. Record Audit Event
                await record_event(
                    session=session,
                    event_type=AuditEventType.PAYMENT_CAPTURED,
                    actor_type="SYSTEM",
                    agreement_id=agreement.id,
                    merchant_id=agreement.merchant_id,
                    metadata={"note": "Manually captured via admin script"}
                )
                
                # Flush per agreement
                await session.flush()
                count += 1
                
            except Exception as e:
                print(f"Failed to process agreement {agreement.id}: {e}")
                await session.rollback()
                continue
                
        # Final commit
        await session.commit()
        print(f"Successfully processed {count} agreements!")

if __name__ == "__main__":
    asyncio.run(process_all())
