"""
NEXORA — Buyer Agent Schemas

Contains strict definitions for inputs, outputs, and the runtime LangGraph state.
All financial values must use Decimal in deterministic code.
"""
import uuid
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal, TypedDict, cast

from pydantic import BaseModel, Field


class BuyerIntent(BaseModel):
    """
    The structured input provided to start a Buyer Agent run.
    """
    buyer_id: uuid.UUID
    merchant_id: uuid.UUID
    product_query: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    maximum_budget: Decimal = Field(..., max_digits=18, decimal_places=2)
    preferred_currency: str = Field("INR", pattern="^INR$")
    requirements: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)


class ActionType(str, Enum):
    """
    Controlled actions the LLM is permitted to take.
    """
    SEARCH_PRODUCTS = "SEARCH_PRODUCTS"
    SELECT_PRODUCT = "SELECT_PRODUCT"
    PROPOSE_AGREEMENT = "PROPOSE_AGREEMENT"
    STOP = "STOP"


class BuyerAgentAction(BaseModel):
    """
    The structured output expected from the LLM.
    """
    action: ActionType
    
    # Optional fields depending on the action
    search_query: str | None = None
    product_id: uuid.UUID | None = None
    
    # Proposal fields (raw strings from LLM to avoid JSON-float issues, will be deterministically parsed)
    proposed_unit_price: str | None = None
    proposed_discount_percent: str | None = None
    
    reason: str = Field(..., description="The reasoning behind selecting this action.")


# Helper to merge state dicts in LangGraph
def merge_list(a: list, b: list) -> list:
    return a + b


class BuyerAgentState(TypedDict):
    """
    The internal runtime state of the LangGraph orchestrator.
    This is NOT persistent business state.
    """
    run_id: str
    intent: BuyerIntent
    
    # Progression tracking
    step_count: int
    status: Literal["in_progress", "completed", "failed", "awaiting_human_approval"]
    error_reason: str | None
    
    # Tool output/discovery
    candidate_products: list[dict[str, Any]]
    
    # Negotiation context
    selected_product_id: uuid.UUID | None
    proposal_revisions: int  # Track how many times a proposal was rejected and revised
    
    # LLM Structured Action
    current_action: BuyerAgentAction | None
    
    # Deterministic calculation state
    deterministic_total: Decimal | None
    
    # Policy outcome
    policy_decision: Literal["ALLOW", "HUMAN_APPROVAL_REQUIRED", "DENY"] | None
    policy_reasons: list[str] | None
    
    # Final Result
    negotiation_id: uuid.UUID | None
    
    # Message history for LangChain
    messages: Annotated[list[Any], merge_list]
