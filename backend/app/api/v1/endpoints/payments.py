from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.connection import get_db
from app.services.payment_service import initiate_payment, PaymentServiceError
from app.payments.razorpay_client import get_razorpay_client, RazorpayClientProtocol


router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentInitiateRequest(BaseModel):
    agreement_id: uuid.UUID


class PaymentInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    amount_paise: int
    currency: str
    status: str


@router.post("/initiate", response_model=PaymentInitiateResponse)
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
            "razorpay_order_id": payment.razorpay_order_id,
            "amount_paise": payment.amount_paise,
            "currency": payment.currency,
            "status": payment.status
        }
    except PaymentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Avoid leaking unhandled error messages, log instead
        raise HTTPException(status_code=500, detail="Internal server error during payment initiation")
