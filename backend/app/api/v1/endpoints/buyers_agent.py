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
from app.services.orchestrator import run_negotiation_loop
from fastapi import BackgroundTasks


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
    background_tasks: BackgroundTasks,
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
        
    if final_state.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM_MODEL_UNAVAILABLE or execution error: {final_state.get('error_reason', 'Unknown error')}"
        )
        
    negotiation_id = final_state.get("negotiation_id")
    if negotiation_id and final_state.get("status") != "failed":
        # Launch the orchestration loop to automatically continue the negotiation
        background_tasks.add_task(run_negotiation_loop, negotiation_id, intent)
        
    return RunAgentResponse(
        run_id=final_state["run_id"],
        status=final_state["status"],
        error_reason=final_state["error_reason"],
        negotiation_id=negotiation_id,
        step_count=final_state["step_count"]
    )
