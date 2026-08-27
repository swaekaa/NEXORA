"""
NEXORA — Agreement Service

Deterministic boundary for creating Agreements from Negotiations.
LLMs are entirely excluded from this process.
"""
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agreement import Agreement, AgreementStatus
from app.models.negotiation import Negotiation, NegotiationState
from app.models.negotiation_message import NegotiationMessage, MessageType
from app.models.product import Product
from app.policies.engine import PolicyEngine
from app.policies.models import PolicyEvaluationRequest, PolicyEvaluationContext
from app.policies.enums import PolicyDecision, ActionType
from app.services.audit_service import record_event, AuditEventType


class InvalidAgreementTransitionError(ValueError):
    """Raised when an agreement state transition is invalid."""
    pass


async def get_agreement(session: AsyncSession, agreement_id: uuid.UUID) -> Agreement | None:
    result = await session.execute(
        select(Agreement).where(Agreement.id == agreement_id)
    )
    return result.scalar_one_or_none()


async def create_agreement_from_negotiation(
    session: AsyncSession,
    negotiation_id: uuid.UUID
) -> Agreement:
    """
    Deterministically creates an Agreement from an ACCEPTED negotiation.
    Recalculates totals securely.
    """
    # 1. Fetch negotiation
    result = await session.execute(
        select(Negotiation).where(Negotiation.id == negotiation_id)
    )
    negotiation = result.scalar_one_or_none()
    
    if not negotiation:
        raise ValueError(f"Negotiation {negotiation_id} not found")
        
    if negotiation.state != NegotiationState.ACCEPTED.value:
        raise ValueError(f"Negotiation must be in ACCEPTED state, got {negotiation.state}")
        
    # Check if agreement already exists for this negotiation
    existing_result = await session.execute(
        select(Agreement).where(Agreement.negotiation_id == negotiation_id)
    )
    if existing_result.scalar_one_or_none():
        raise ValueError(f"Agreement already exists for negotiation {negotiation_id}")
        
    # 2. Fetch the final PROPOSAL (the one that was accepted)
    msg_result = await session.execute(
        select(NegotiationMessage)
        .where(NegotiationMessage.negotiation_id == negotiation_id)
        .where(NegotiationMessage.message_type.in_([MessageType.OFFER.value, MessageType.COUNTER_OFFER.value]))
        .order_by(NegotiationMessage.sequence_number.desc())
        .limit(1)
    )
    final_message = msg_result.scalar_one_or_none()
    
    if not final_message or not final_message.payload:
        raise ValueError(f"No payload found in final negotiation message")
        
    payload = final_message.payload
    
    # 3. Fetch product for snapshotting
    prod_result = await session.execute(
        select(Product).where(Product.id == negotiation.product_id)
    )
    product = prod_result.scalar_one_or_none()
    
    if not product:
        raise ValueError(f"Product {negotiation.product_id} not found")
        
    # 4. Deterministic Total Calculation
    try:
        quantity = int(payload["quantity"])
        unit_price = Decimal(str(payload["unit_price"]))
        currency = payload.get("currency", "INR")
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"Invalid payload format: {str(e)}")
        
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if unit_price <= 0:
        raise ValueError("Unit price must be positive")
    if currency != "INR":
        raise ValueError(f"Unsupported currency: {currency}")
        
    total_amount = (unit_price * quantity).quantize(Decimal("0.01"))
    
    # Optional: Verify it matches payload total_amount if provided
    payload_total = payload.get("total_amount")
    if payload_total is not None:
        if Decimal(str(payload_total)).quantize(Decimal("0.01")) != total_amount:
            raise ValueError("Payload total does not match deterministic calculation")

    # 5. Create immutable Agreement
    agreement = Agreement(
        negotiation_id=negotiation_id,
        merchant_id=negotiation.merchant_id,
        buyer_id=negotiation.buyer_id,
        product_id=negotiation.product_id,
        product_name=product.name,
        quantity=quantity,
        unit_price=unit_price,
        total_amount=total_amount,
        currency=currency,
        payment_terms="upfront",  # Default for MVP
        delivery_days=5,          # Default for MVP
        warranty_months=12,       # Default for MVP
        status=AgreementStatus.PENDING_VALIDATION.value
    )
    
    session.add(agreement)
    
    await record_event(
        session=session,
        event_type=AuditEventType.AGREEMENT_CREATED,
        actor_type="SYSTEM",
        agreement_id=agreement.id,
        merchant_id=agreement.merchant_id,
        metadata={"total_amount": str(agreement.total_amount)}
    )
    
    await session.commit()
    await session.refresh(agreement)
    
    return agreement


async def validate_agreement(
    session: AsyncSession,
    agreement_id: uuid.UUID,
    policy_context: PolicyEvaluationContext
) -> Agreement:
    """
    Performs final policy validation before payment initiation.
    """
    agreement = await get_agreement(session, agreement_id)
    if not agreement:
        raise ValueError(f"Agreement {agreement_id} not found")
        
    if agreement.status != AgreementStatus.PENDING_VALIDATION.value:
        raise InvalidAgreementTransitionError(
            f"Cannot validate agreement in state {agreement.status}"
        )
        
    # Build policy request from IMMUTABLE agreement terms
    request = PolicyEvaluationRequest(
        action=ActionType.CREATE_AGREEMENT,
        merchant_id=agreement.merchant_id,
        product_id=agreement.product_id,
        unit_price=agreement.unit_price,
        quantity=agreement.quantity,
        total_amount=agreement.total_amount,
        currency=agreement.currency,
        discount_percent=Decimal("0.0") # Extracted if needed, default to 0 for MVP
    )
    
    engine = PolicyEngine()
    result = engine.evaluate(request, policy_context)
    
    agreement.policy_decision = result.decision.value
    agreement.policy_checks = [
        {"rule": c.rule_name, "passed": c.passed, "reason": c.reason}
        for c in result.failed_checks
    ] if result.failed_checks else []
    
    if result.decision == PolicyDecision.ALLOW:
        agreement.status = AgreementStatus.VALIDATED.value
    elif result.decision == PolicyDecision.HUMAN_APPROVAL_REQUIRED:
        agreement.status = AgreementStatus.PENDING_APPROVAL.value
        from app.services.approval_service import create_approval_request
        reason = "One or more policies require human approval."
        if result.failed_checks:
            reason = result.failed_checks[0].reason
        await create_approval_request(session, agreement, result.decision.value, reason)
    else:
        agreement.status = AgreementStatus.VALIDATION_FAILED.value
        agreement.blocking_reason = "Policy constraints violated after agreement."
        
    session.add(agreement)
    
    event_type = AuditEventType.AGREEMENT_VALIDATED if result.decision == PolicyDecision.ALLOW else AuditEventType.AGREEMENT_VALIDATION_FAILED
    if result.decision == PolicyDecision.HUMAN_APPROVAL_REQUIRED:
        event_type = AuditEventType.POLICY_CHECK
        
    await record_event(
        session=session,
        event_type=event_type,
        actor_type="SYSTEM",
        agreement_id=agreement.id,
        merchant_id=agreement.merchant_id,
        metadata={"policy_decision": result.decision.value}
    )
    
    await session.commit()
    await session.refresh(agreement)
    
    return agreement


async def manually_approve_agreement(
    session: AsyncSession,
    agreement_id: uuid.UUID
) -> Agreement:
    """
    Transitions an agreement from PENDING_APPROVAL to APPROVED (simulates human action).
    """
    agreement = await get_agreement(session, agreement_id)
    if not agreement:
        raise ValueError("Agreement not found")
        
    if agreement.status != AgreementStatus.PENDING_APPROVAL.value:
        raise InvalidAgreementTransitionError(f"Cannot approve from {agreement.status}")
        
    agreement.status = AgreementStatus.APPROVED.value
    session.add(agreement)
    await session.commit()
    await session.refresh(agreement)
    
    return agreement
