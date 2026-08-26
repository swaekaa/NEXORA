from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.connection import get_db
from app.services.inventory_service import (
    release_expired_reservations,
    fulfill_reservation,
    InventoryServiceError,
    ReservationStateError
)

router = APIRouter()

@router.post("/release-expired", status_code=status.HTTP_200_OK)
async def release_expired_inventory_reservations(
    session: AsyncSession = Depends(get_db)
):
    """
    Internal/maintenance endpoint to release expired inventory reservations.
    Returns the number of reservations released.
    """
    try:
        count = await release_expired_reservations(session)
        # Note: the get_db dependency automatically commits on success,
        # but release_expired_reservations handles multiple reservations.
        # It's safer to commit here to ensure all are released together.
        await session.commit()
        return {"released_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agreements/{agreement_id}/fulfill", status_code=status.HTTP_200_OK)
async def fulfill_agreement_inventory(
    agreement_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
):
    """
    Marks a COMMITTED reservation as FULFILLED.
    """
    try:
        await fulfill_reservation(session, agreement_id)
        await session.commit()
        return {"status": "success", "message": "Reservation fulfilled"}
    except ReservationStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InventoryServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
