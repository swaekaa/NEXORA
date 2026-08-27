"""
NEXORA — Merchant Agent API Endpoints
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.connection import get_db
from app.agents.merchant.runner import run_merchant_agent


router = APIRouter(prefix="/merchants", tags=["Merchants Agent"])


class RunMerchantAgentResponse(BaseModel):
    run_id: str | None
    status: str
    error_reason: str | None
    step_count: int


@router.post("/{merchant_id}/agent/runs/{negotiation_id}", response_model=RunMerchantAgentResponse)
async def create_agent_run(
    merchant_id: uuid.UUID,
    negotiation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """
    Kicks off the Merchant Agent to evaluate a buyer's proposal.
    The agent will read the negotiation, evaluate the policy, and generate a response.
    """
    try:
        final_state = await run_merchant_agent(session, negotiation_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )
        
    return RunMerchantAgentResponse(
        run_id=final_state.get("run_id"),
        status=final_state.get("status", "failed"),
        error_reason=final_state.get("error_reason"),
        step_count=final_state.get("step_count", 0)
    )
