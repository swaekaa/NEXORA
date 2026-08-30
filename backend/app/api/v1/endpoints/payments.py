from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.connection import get_db
from app.services.payment_service import initiate_payment, verify_payment, get_payment_by_agreement, PaymentServiceError
from app.payments.razorpay_client import get_razorpay_client, RazorpayClientProtocol


router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentInitiateRequest(BaseModel):
    agreement_id: uuid.UUID


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentResponse(BaseModel):
    payment_id: uuid.UUID
    razorpay_payment_id: str | None
    razorpay_order_id: str
    amount_paise: int | None
    currency: str
    status: str
    paid_at: str | None


@router.post("/initiate", response_model=PaymentResponse)
async def initiate_payment_endpoint(
    request: PaymentInitiateRequest,
    db: AsyncSession = Depends(get_db),
    razorpay_client: RazorpayClientProtocol = Depends(get_razorpay_client)
) -> Any:
    """
    Initiates payment for an agreement.
    Client only provides the agreement_id. Amounts are computed safely on backend.
    """
    try:
        payment = await initiate_payment(
            session=db,
            agreement_id=request.agreement_id,
            razorpay_client=razorpay_client
        )
        return {
            "payment_id": payment.id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "razorpay_order_id": payment.razorpay_order_id,
            "amount_paise": payment.amount_paise,
            "currency": payment.currency,
            "status": payment.status,
            "paid_at": payment.captured_at.isoformat() if payment.captured_at else None
        }
    except PaymentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/verify", response_model=PaymentResponse)
async def verify_payment_endpoint(
    request: PaymentVerifyRequest,
    db: AsyncSession = Depends(get_db),
    razorpay_client: RazorpayClientProtocol = Depends(get_razorpay_client)
) -> Any:
    """
    Synchronously verify the payment signature received from frontend.
    This acts as the primary truth pathway.
    """
    try:
        payment = await verify_payment(
            session=db,
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature,
            razorpay_client=razorpay_client
        )
        return {
            "payment_id": payment.id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "razorpay_order_id": payment.razorpay_order_id,
            "amount_paise": payment.amount_paise,
            "currency": payment.currency,
            "status": payment.status,
            "paid_at": payment.captured_at.isoformat() if payment.captured_at else None
        }
    except PaymentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/agreement/{agreement_id}", response_model=PaymentResponse)
async def get_payment_for_agreement_endpoint(
    agreement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve payment information for an agreement.
    Used by the frontend Deal Report to display authoritative payment details.
    """
    try:
        payment = await get_payment_by_agreement(db, agreement_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found for this agreement")
            
        return {
            "payment_id": payment.id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "razorpay_order_id": payment.razorpay_order_id,
            "amount_paise": payment.amount_paise,
            "currency": payment.currency,
            "status": payment.status,
            "paid_at": payment.captured_at.isoformat() if payment.captured_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
