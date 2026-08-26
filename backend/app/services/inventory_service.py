"""
NEXORA — Inventory Service

Deterministic service for managing inventory reservations.
Enforces that inventory is decremented safely via atomic PostgreSQL UPDATEs.
Agents have NO direct access to these operations.
"""

import uuid
from datetime import timedelta

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.product import Product, ProductStatus
from app.models.agreement import Agreement, AgreementStatus
from app.models.inventory_reservation import InventoryReservation, ReservationStatus
from app.database.base import utcnow
from app.config import settings
from app.services.audit_service import record_event, AuditEventType
from app.models.approval_request import ApprovalStatus


class InventoryServiceError(Exception):
    """Base exception for inventory service operations."""
    pass


class InsufficientInventoryError(InventoryServiceError):
    """Raised when there is not enough stock to fulfill the reservation."""
    pass


class ReservationStateError(InventoryServiceError):
    """Raised when an invalid state transition is attempted on a reservation."""
    pass


async def reserve_inventory(session: AsyncSession, agreement_id: uuid.UUID) -> InventoryReservation:
    """
    Atomically deduct inventory and create a reservation for the agreement.
    Idempotent: if a RESERVED reservation already exists, returns it.
    """
    # 1. Check if reservation already exists
    result = await session.execute(
        select(InventoryReservation).where(InventoryReservation.agreement_id == agreement_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        if existing.status == ReservationStatus.RESERVED.value:
            return existing
        raise ReservationStateError(f"Reservation already exists in state: {existing.status}")

    # 2. Fetch Agreement
    result = await session.execute(select(Agreement).where(Agreement.id == agreement_id))
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise InventoryServiceError("Agreement not found")
        
    # We only reserve inventory if the agreement is validated or approved (ready for payment)
    if agreement.status not in (AgreementStatus.VALIDATED.value, AgreementStatus.APPROVED.value):
        raise ReservationStateError(f"Agreement must be VALIDATED or APPROVED to reserve inventory, got {agreement.status}")

    qty = agreement.quantity
    product_id = agreement.product_id

    # 3. Verify Product Status
    result = await session.execute(select(Product.status).where(Product.id == product_id))
    product_status = result.scalar_one_or_none()
    
    if not product_status:
        raise InventoryServiceError("Product not found")
        
    if product_status != ProductStatus.ACTIVE:
        raise InventoryServiceError(f"Cannot reserve inventory for product in state: {product_status}")

    # 4. ATOMIC Inventory Deduction
    # This completely bypasses race conditions by using row-level locking natively in Postgres.
    stmt = (
        update(Product)
        .where(
            Product.id == product_id,
            Product.inventory >= qty
        )
        .values(inventory=Product.inventory - qty)
    )
    
    update_result = await session.execute(stmt)
    
    if update_result.rowcount == 0:
        raise InsufficientInventoryError(f"Insufficient inventory for product {product_id}")

    # 5. Create Reservation Record
    expires_at = utcnow() + timedelta(minutes=settings.INVENTORY_RESERVATION_TTL_MINUTES)
    
    reservation = InventoryReservation(
        agreement_id=agreement_id,
        product_id=product_id,
        quantity=qty,
        status=ReservationStatus.RESERVED.value,
        expires_at=expires_at
    )
    
    session.add(reservation)
    
    await record_event(
        session=session,
        event_type=AuditEventType.INVENTORY_RESERVED,
        actor_type="SYSTEM",
        agreement_id=agreement_id,
        merchant_id=agreement.merchant_id,
        metadata={"product_id": str(product_id), "quantity": qty}
    )
    
    # We do not commit here! The caller is responsible for committing the transaction
    # to ensure atomicity with payment intent creation.
    return reservation


async def commit_reservation(session: AsyncSession, agreement_id: uuid.UUID) -> None:
    """
    Transition a reservation from RESERVED -> COMMITTED.
    Called when a payment is successfully captured.
    """
    result = await session.execute(
        select(InventoryReservation).where(InventoryReservation.agreement_id == agreement_id)
    )
    reservation = result.scalar_one_or_none()
    
    if not reservation:
        return
        
    if reservation.status == ReservationStatus.COMMITTED.value:
        return  # Idempotent
        
    if reservation.status != ReservationStatus.RESERVED.value:
        raise ReservationStateError(f"Cannot commit reservation in state: {reservation.status}")
        
    reservation.status = ReservationStatus.COMMITTED.value
    reservation.expires_at = None
    session.add(reservation)
    
    # We need the merchant_id for the audit event.
    result_agr = await session.execute(select(Agreement.merchant_id).where(Agreement.id == agreement_id))
    merchant_id = result_agr.scalar_one_or_none()
    
    if merchant_id:
        await record_event(
            session=session,
            event_type=AuditEventType.INVENTORY_COMMITTED,
            actor_type="SYSTEM",
            agreement_id=agreement_id,
            merchant_id=merchant_id,
            metadata={"product_id": str(reservation.product_id), "quantity": reservation.quantity}
        )


async def release_reservation(session: AsyncSession, agreement_id: uuid.UUID, is_expiration: bool = False) -> None:
    """
    Transition a reservation from RESERVED -> RELEASED (or EXPIRED).
    Restores the inventory quantity to the product.
    Called when payment fails, razorpay creation fails, or TTL expires.
    """
    result = await session.execute(
        select(InventoryReservation).where(InventoryReservation.agreement_id == agreement_id)
    )
    reservation = result.scalar_one_or_none()
    
    if not reservation:
        return
        
    if reservation.status in (ReservationStatus.RELEASED.value, ReservationStatus.EXPIRED.value):
        return  # Idempotent
        
    if reservation.status != ReservationStatus.RESERVED.value:
        raise ReservationStateError(f"Cannot release reservation in state: {reservation.status}")
        
    # 1. Restore inventory
    stmt = (
        update(Product)
        .where(Product.id == reservation.product_id)
        .values(inventory=Product.inventory + reservation.quantity)
    )
    await session.execute(stmt)
    
    # 2. Update reservation status
    reservation.status = ReservationStatus.EXPIRED.value if is_expiration else ReservationStatus.RELEASED.value
    reservation.expires_at = None
    session.add(reservation)
    
    # We need the merchant_id for the audit event.
    result_agr = await session.execute(select(Agreement.merchant_id).where(Agreement.id == agreement_id))
    merchant_id = result_agr.scalar_one_or_none()
    
    if merchant_id:
        await record_event(
            session=session,
            event_type=AuditEventType.INVENTORY_EXPIRED if is_expiration else AuditEventType.INVENTORY_RELEASED,
            actor_type="SYSTEM",
            agreement_id=agreement_id,
            merchant_id=merchant_id,
            metadata={"product_id": str(reservation.product_id), "quantity": reservation.quantity}
        )


async def fulfill_reservation(session: AsyncSession, agreement_id: uuid.UUID) -> None:
    """
    Transition a reservation from COMMITTED -> FULFILLED.
    """
    result = await session.execute(
        select(InventoryReservation).where(InventoryReservation.agreement_id == agreement_id)
    )
    reservation = result.scalar_one_or_none()
    
    if not reservation:
        raise InventoryServiceError("Reservation not found")
        
    if reservation.status == ReservationStatus.FULFILLED.value:
        return  # Idempotent
        
    if reservation.status != ReservationStatus.COMMITTED.value:
        raise ReservationStateError(f"Cannot fulfill reservation in state: {reservation.status}")
        
    reservation.status = ReservationStatus.FULFILLED.value
    session.add(reservation)
    
    result_agr = await session.execute(select(Agreement.merchant_id).where(Agreement.id == agreement_id))
    merchant_id = result_agr.scalar_one_or_none()
    
    if merchant_id:
        await record_event(
            session=session,
            event_type=AuditEventType.FULFILLMENT_COMPLETED,
            actor_type="SYSTEM",
            agreement_id=agreement_id,
            merchant_id=merchant_id,
            metadata={"product_id": str(reservation.product_id), "quantity": reservation.quantity}
        )


async def release_expired_reservations(session: AsyncSession) -> int:
    """
    Maintenance operation to find all RESERVED reservations past their TTL
    and release them back to inventory.
    Returns the number of reservations released.
    """
    now = utcnow()
    
    # Select FOR UPDATE to prevent race conditions with payment webhook
    # during expiration processing
    result = await session.execute(
        select(InventoryReservation)
        .where(
            InventoryReservation.status == ReservationStatus.RESERVED.value,
            InventoryReservation.expires_at <= now
        )
        .with_for_update()
    )
    
    reservations = result.scalars().all()
    count = 0
    
    for res in reservations:
        # Restore inventory
        stmt = (
            update(Product)
            .where(Product.id == res.product_id)
            .values(inventory=Product.inventory + res.quantity)
        )
        await session.execute(stmt)
        
        # Mark expired
        res.status = ReservationStatus.EXPIRED.value
        res.expires_at = None
        session.add(res)
        count += 1
        
    return count
