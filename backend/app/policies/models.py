import uuid
from decimal import Decimal
from pydantic import BaseModel, Field

from .enums import ActionType, PolicyDecision

class PolicyEvaluationContext(BaseModel):
    """
    The financial constraints defined by the merchant.
    This is essentially a pure Pydantic representation of the SQLAlchemy Policy model.
    """
    merchant_id: uuid.UUID
    policy_id: uuid.UUID
    minimum_price: Decimal
    maximum_discount_percent: Decimal
    maximum_autonomous_transaction: Decimal
    human_approval_required: bool


class PolicyEvaluationRequest(BaseModel):
    """
    The proposed commercial action that the agent wants to perform.
    """
    action: ActionType
    merchant_id: uuid.UUID
    product_id: uuid.UUID
    unit_price: Decimal = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    total_amount: Decimal = Field(..., gt=0)
    currency: str = "INR"
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class PolicyCheck(BaseModel):
    """
    The structured result of evaluating a single deterministic rule.
    """
    rule_name: str
    passed: bool
    expected: str
    actual: str
    reason: str


class PolicyResult(BaseModel):
    """
    The final compilation of all evaluated rules.
    """
    decision: PolicyDecision
    checks: list[PolicyCheck]
    blocking_reason: str | None = None

    @property
    def failed_checks(self) -> list[PolicyCheck]:
        return [c for c in self.checks if not c.passed]

    @property
    def passed_checks(self) -> list[PolicyCheck]:
        return [c for c in self.checks if c.passed]
