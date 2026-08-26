from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services.payment_service import process_webhook_event, PaymentServiceError, DuplicateWebhookError
from app.payments.razorpay_client import get_razorpay_client, RazorpayClientProtocol


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db),
    razorpay_client: RazorpayClientProtocol = Depends(get_razorpay_client)
) -> Any:
    """
    Ingests and processes Razorpay webhooks.
    Must verify signature against raw body bytes BEFORE parsing JSON.
    """
    raw_body = await request.body()
    
    try:
        await process_webhook_event(
            session=db,
            raw_body=raw_body,
            signature=x_razorpay_signature,
            razorpay_client=razorpay_client
        )
        return {"status": "ok"}
    except DuplicateWebhookError:
        # We successfully skipped a duplicate event. Razorpay expects a 200 OK.
        return {"status": "ok", "message": "duplicate ignored"}
    except PaymentServiceError as e:
        # Invalid signature, missing event type, etc.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # DB failure or processing failure - raise 500 so Razorpay retries
        raise HTTPException(status_code=500, detail="Internal server error")
