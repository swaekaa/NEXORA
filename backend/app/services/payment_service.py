"""
NEXORA — Payment Service

Orchestrates local Payment creation, Razorpay order integration, and Webhook processing.
"""
import uuid
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.agreement import Agreement, AgreementStatus
from app.models.payment import Payment, PaymentStatus
from app.models.payment_webhook_event import PaymentWebhookEvent
from app.payments.utils import convert_decimal_to_paise
from app.payments.razorpay_client import RazorpayClientProtocol


class PaymentServiceError(ValueError):
    pass


class DuplicateWebhookError(Exception):
    pass


async def get_payment(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()


async def get_payment_by_agreement(session: AsyncSession, agreement_id: uuid.UUID) -> Payment | None:
    result = await session.execute(
        select(Payment).where(Payment.agreement_id == agreement_id)
    )
    return result.scalar_one_or_none()


async def initiate_payment(
    session: AsyncSession,
    agreement_id: uuid.UUID,
    razorpay_client: RazorpayClientProtocol
) -> Payment:
    """
    Initiates payment for a VALIDATED or APPROVED agreement.
    Creates a local CREATED intent, then fetches/creates a Razorpay order.
    """
    # 1. Fetch and validate Agreement
    result = await session.execute(
        select(Agreement).where(Agreement.id == agreement_id)
    )
    agreement = result.scalar_one_or_none()
    
    if not agreement:
        raise PaymentServiceError("Agreement not found")
        
    if agreement.status not in (AgreementStatus.VALIDATED.value, AgreementStatus.APPROVED.value):
        raise PaymentServiceError(f"Agreement is not ready for payment. Status: {agreement.status}")
        
    if agreement.currency != "INR":
        raise PaymentServiceError("Only INR currency is supported for Razorpay payments")
        
    # 2. Convert to paise
    amount_paise = convert_decimal_to_paise(agreement.total_amount)
    
    # 3. Check for existing payment
    existing_payment = await get_payment_by_agreement(session, agreement_id)
    
    if existing_payment:
        if existing_payment.status != PaymentStatus.CREATED.value:
            raise PaymentServiceError(f"Payment already in progress. Status: {existing_payment.status}")
        return existing_payment
            
    # Recovery Scenario: Razorpay order was created, but DB update failed (e.g. crash).
    # We search Razorpay by receipt.
    receipt_id = f"agr_{str(agreement_id)[:35]}"
    orders = razorpay_client.fetch_orders_by_receipt(receipt_id)
    
    if orders:
        order_id = orders[0]["id"]
    else:
        notes = {
            "agreement_id": str(agreement_id),
            "merchant_id": str(agreement.merchant_id),
            "buyer_id": str(agreement.buyer_id)
        }
        order = razorpay_client.create_order(
            amount_paise=amount_paise,
            currency=agreement.currency,
            receipt=receipt_id,
            notes=notes
        )
        order_id = order["id"]

    # Insert into DB
    payment = Payment(
        agreement_id=agreement_id,
        amount=agreement.total_amount,
        amount_paise=amount_paise,
        currency=agreement.currency,
        status=PaymentStatus.CREATED.value,
        razorpay_order_id=order_id
    )
    session.add(payment)
    
    agreement.status = AgreementStatus.PAYMENT_INITIATED.value
    session.add(agreement)
    
    try:
        await session.commit()
        await session.refresh(payment)
    except IntegrityError:
        await session.rollback()
        raise PaymentServiceError("A payment is already being initiated for this agreement")
    
    return payment


async def process_webhook_event(
    session: AsyncSession,
    raw_body: bytes,
    signature: str,
    razorpay_client: RazorpayClientProtocol
) -> None:
    """
    Processes incoming Razorpay webhooks atomically.
    """
    # 1. Cryptographic validation (fails fast)
    if not razorpay_client.verify_webhook_signature(raw_body, signature):
        raise PaymentServiceError("Invalid webhook signature")
        
    # 2. Parse payload
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise PaymentServiceError("Invalid JSON payload")
        
    event_type = payload.get("event")
    
    # Extract Razorpay event id from header or body
    # Standard Razorpay sends event id in body (e.g. "contains": ["payment"], "event": "payment.captured")
    # For idempotency we use the Razorpay webhook payload's 'id' field, not the payment id
    event_id = payload.get("id")
    if not event_id:
        # Fallback to payment id if testing
        if "payment" in payload.get("payload", {}):
            event_id = payload["payload"]["payment"]["entity"]["id"]
        else:
            raise PaymentServiceError("Cannot find event_id for webhook deduplication")
            
    if not event_type:
        raise PaymentServiceError("Missing event type in webhook")
        
    import hashlib
    payload_hash = hashlib.sha256(raw_body).hexdigest()

    # 3. Idempotent Insert using ORM try-except
    webhook_event = PaymentWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        status="RECEIVED"
    )
    
    session.add(webhook_event)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        # Duplicate webhook, return safely
        raise DuplicateWebhookError(f"Webhook {event_id} already processed")
        
    # We now have the lock on this event within the current transaction
    webhook_event.status = "PROCESSING"
    
    # 4. Handle specific business logic
    if event_type == "payment.captured":
        await _handle_payment_captured(session, payload)
    elif event_type == "payment.failed":
        await _handle_payment_failed(session, payload)
    # Ignore other events
        
    webhook_event.status = "PROCESSED"
    from app.database.base import utcnow
    webhook_event.processed_at = utcnow()
    
    # 5. Commit all changes (Webhook status, Payment status, Agreement status) atomically
    await session.commit()


async def _handle_payment_captured(session: AsyncSession, payload: dict) -> None:
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = entity.get("order_id")
    payment_id = entity.get("id")
    
    if not order_id:
        return
        
    result = await session.execute(
        select(Payment).where(Payment.razorpay_order_id == order_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        # Unknown order, ignore safely
        return
        
    payment.status = PaymentStatus.CAPTURED.value
    payment.razorpay_payment_id = payment_id
    
    result = await session.execute(
        select(Agreement).where(Agreement.id == payment.agreement_id)
    )
    agreement = result.scalar_one_or_none()
    
    if agreement:
        agreement.status = AgreementStatus.PAYMENT_CAPTURED.value
        session.add(agreement)
        
    session.add(payment)


async def _handle_payment_failed(session: AsyncSession, payload: dict) -> None:
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = entity.get("order_id")
    
    if not order_id:
        return
        
    result = await session.execute(
        select(Payment).where(Payment.razorpay_order_id == order_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        return
        
    payment.status = PaymentStatus.FAILED.value
    
    result = await session.execute(
        select(Agreement).where(Agreement.id == payment.agreement_id)
    )
    agreement = result.scalar_one_or_none()
    
    if agreement:
        agreement.status = AgreementStatus.PAYMENT_FAILED.value
        session.add(agreement)
        
    session.add(payment)
