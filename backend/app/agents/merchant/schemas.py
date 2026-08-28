"""
NEXORA — Merchant Agent Schemas
"""
import uuid
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field


class MerchantIntent(BaseModel):
    """
    The structured input provided to start a Merchant Agent run.
    Contains the buyer's proposal and the merchant's policy constraints.
    """
    negotiation_id: uuid.UUID
    buyer_id: uuid.UUID
    merchant_id: uuid.UUID
    product_id: uuid.UUID
    
    # The buyer's latest proposal
    buyer_proposed_quantity: int
    buyer_proposed_unit_price: Decimal
    buyer_proposed_discount_percent: Decimal
    
    # The merchant's constraints (loaded by service, not hallucinated)
    policy_id: uuid.UUID
    policy_minimum_price: Decimal
    policy_maximum_discount_percent: Decimal
    policy_maximum_autonomous_transaction: Decimal
    policy_requires_human_approval: bool
    
    currency: str = "INR"
    
    # Negotiation history
    round_count: int
    max_rounds: int
    
    product_description: str
    buyer_message: str | None


class MerchantActionType(str, Enum):
    """
    Controlled actions the Merchant LLM is permitted to take.
    """
    ACCEPT_PROPOSAL = "ACCEPT_PROPOSAL"
    REJECT_PROPOSAL = "REJECT_PROPOSAL"
    COUNTER_PROPOSAL = "COUNTER_PROPOSAL"
    REQUEST_HUMAN_APPROVAL = "REQUEST_HUMAN_APPROVAL"


class MerchantAgentAction(BaseModel):
    """
    The structured output expected from the Merchant LLM.
    """
    action: MerchantActionType
    
    # Fields required for COUNTER_PROPOSAL (strings to prevent JSON float precision loss)
    proposed_unit_price: str | None = None
    proposed_discount_percent: str | None = None
    proposed_quantity: int | None = None
    
    reason: str = Field(..., description="The reasoning behind selecting this action.")


def merge_list(a: list, b: list) -> list:
    return a + b


class MerchantAgentState(TypedDict):
    """
    The internal runtime state of the LangGraph orchestrator.
    """
    run_id: str
    intent: MerchantIntent
    
    # Progression tracking
    step_count: int
    status: Literal["in_progress", "completed", "failed", "awaiting_human_approval"]
    error_reason: str | None
    
    proposal_revisions: int  # Track how many times a counter-offer was rejected by PolicyEngine
    
    # LLM Structured Action
    current_action: MerchantAgentAction | None
    
    # Deterministic calculation state (if countering)
    deterministic_total: Decimal | None
    
    # Policy outcome (when verifying the action)
    policy_decision: Literal["ALLOW", "HUMAN_APPROVAL_REQUIRED", "DENY"] | None
    policy_reasons: list[str] | None
    
    # Message history for LangChain
    messages: Annotated[list[Any], merge_list]
