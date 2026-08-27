"""
NEXORA — Buyer Agent API Endpoints
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.connection import get_db
from app.agents.buyer.schemas import BuyerIntent, BuyerAgentState
from app.agents.buyer.runner import run_buyer_agent


router = APIRouter(prefix="/buyers", tags=["Buyers Agent"])


class RunAgentResponse(BaseModel):
    run_id: str
    status: str
    error_reason: str | None
    negotiation_id: uuid.UUID | None
    step_count: int


@router.post("/{buyer_id}/agent/runs", response_model=RunAgentResponse)
async def create_agent_run(
    buyer_id: uuid.UUID,
    intent: BuyerIntent,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """
    Kicks off the Buyer Agent to autonomously search for products,
    evaluate them, and negotiate an agreement.
    """
    if intent.buyer_id != buyer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="buyer_id in path must match buyer_id in intent body"
        )
        
    try:
        final_state = await run_buyer_agent(session, intent)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )
        
    return RunAgentResponse(
        run_id=final_state["run_id"],
        status=final_state["status"],
        error_reason=final_state["error_reason"],
        negotiation_id=final_state.get("negotiation_id"),
        step_count=final_state["step_count"]
    )
