from decimal import Decimal

from .enums import PolicyDecision, ActionType
from .models import (
    PolicyCheck,
    PolicyEvaluationContext,
    PolicyEvaluationRequest,
    PolicyResult,
)


class PolicyEngine:
    """
    Deterministic Policy Engine.
    
    This engine evaluates a proposed action (PolicyEvaluationRequest) against
    a set of constraints (PolicyEvaluationContext) and returns a PolicyResult.
    
    It is a pure system:
    - Zero external network calls.
    - Zero database queries.
    - Zero LLM calls.
    - Strict Decimal arithmetic for all financial rules.
    
    Precedence: DENY > HUMAN_APPROVAL_REQUIRED > ALLOW
    """

    def evaluate(
        self,
        request: PolicyEvaluationRequest,
        context: PolicyEvaluationContext,
    ) -> PolicyResult:
        
        # 1. Total Integrity Rule
        integrity_check = self._rule_total_integrity(request)
        
        # 2. Currency Rule
        currency_check = self._rule_currency(request)
        
        # 3. Minimum Price Rule
        min_price_check = self._rule_minimum_price(request, context)
        
        # 4. Maximum Discount Rule
        max_discount_check = self._rule_maximum_discount(request, context)
        
        # 5. Human Approval Override
        override_check = self._rule_human_approval_override(context)
        
        # 6. Autonomous Limit Rule
        limit_check = self._rule_autonomous_limit(request, context)
        
        checks = [
            integrity_check,
            currency_check,
            min_price_check,
            max_discount_check,
            override_check,
            limit_check,
        ]
        
        return self._compile_result(checks)

    def _rule_total_integrity(self, request: PolicyEvaluationRequest) -> PolicyCheck:
        """Total must equal exactly unit_price * quantity."""
        calculated = (request.unit_price * Decimal(request.quantity)).quantize(Decimal("0.01"))
        stored = request.total_amount.quantize(Decimal("0.01"))
        
        passed = (calculated == stored)
        return PolicyCheck(
            rule_name="AGREEMENT_TOTAL_INTEGRITY",
            passed=passed,
            expected=str(calculated),
            actual=str(stored),
            reason="" if passed else f"Total amount mismatch: calculated {calculated} (price {request.unit_price} x qty {request.quantity}), requested {stored}"
        )

    def _rule_currency(self, request: PolicyEvaluationRequest) -> PolicyCheck:
        """Currency must be INR for MVP."""
        passed = (request.currency == "INR")
        return PolicyCheck(
            rule_name="AGREEMENT_CURRENCY",
            passed=passed,
            expected="INR",
            actual=request.currency,
            reason="" if passed else f"Unsupported currency: {request.currency}"
        )

    def _rule_minimum_price(
        self, request: PolicyEvaluationRequest, context: PolicyEvaluationContext
    ) -> PolicyCheck:
        """Unit price cannot be below merchant floor."""
        passed = (request.unit_price >= context.minimum_price)
        return PolicyCheck(
            rule_name="MERCHANT_MIN_PRICE",
            passed=passed,
            expected=f">= {context.minimum_price}",
            actual=str(request.unit_price),
            reason="" if passed else f"Proposed price {request.unit_price} is below merchant minimum {context.minimum_price}"
        )

    def _rule_maximum_discount(
        self, request: PolicyEvaluationRequest, context: PolicyEvaluationContext
    ) -> PolicyCheck:
        """Discount cannot exceed merchant limit."""
        passed = (request.discount_percent <= context.maximum_discount_percent)
        return PolicyCheck(
            rule_name="MERCHANT_MAX_DISCOUNT",
            passed=passed,
            expected=f"<= {context.maximum_discount_percent}",
            actual=str(request.discount_percent),
            reason="" if passed else f"Proposed discount {request.discount_percent}% exceeds maximum {context.maximum_discount_percent}%"
        )

    def _rule_human_approval_override(self, context: PolicyEvaluationContext) -> PolicyCheck:
        """If human_approval_required is True, this check returns passed=False to trigger HUMAN_APPROVAL_REQUIRED."""
        passed = not context.human_approval_required
        return PolicyCheck(
            rule_name="MERCHANT_HUMAN_APPROVAL_OVERRIDE",
            passed=passed,
            expected="False",
            actual=str(context.human_approval_required),
            reason="" if passed else "Merchant policy requires all agreements to have manual human approval"
        )

    def _rule_autonomous_limit(
        self, request: PolicyEvaluationRequest, context: PolicyEvaluationContext
    ) -> PolicyCheck:
        """If total exceeds autonomous transaction limit, this check returns passed=False to trigger HUMAN_APPROVAL_REQUIRED."""
        passed = (request.total_amount <= context.maximum_autonomous_transaction)
        return PolicyCheck(
            rule_name="MERCHANT_AUTONOMOUS_LIMIT",
            passed=passed,
            expected=f"<= {context.maximum_autonomous_transaction}",
            actual=str(request.total_amount),
            reason="" if passed else f"Transaction total {request.total_amount} exceeds autonomous limit {context.maximum_autonomous_transaction}"
        )

    def _compile_result(self, checks: list[PolicyCheck]) -> PolicyResult:
        """
        Evaluate precedence: DENY > HUMAN_APPROVAL_REQUIRED > ALLOW
        
        Rules that trigger DENY:
        - AGREEMENT_TOTAL_INTEGRITY
        - AGREEMENT_CURRENCY
        - MERCHANT_MIN_PRICE
        - MERCHANT_MAX_DISCOUNT
        
        Rules that trigger HUMAN_APPROVAL_REQUIRED (if no DENY rules failed):
        - MERCHANT_HUMAN_APPROVAL_OVERRIDE
        - MERCHANT_AUTONOMOUS_LIMIT
        """
        deny_rules = {
            "AGREEMENT_TOTAL_INTEGRITY",
            "AGREEMENT_CURRENCY",
            "MERCHANT_MIN_PRICE",
            "MERCHANT_MAX_DISCOUNT",
        }
        
        failed_checks = [c for c in checks if not c.passed]
        
        # 1. Check for hard DENY violations
        deny_failures = [c for c in failed_checks if c.rule_name in deny_rules]
        if deny_failures:
            blocking = "; ".join(c.reason for c in deny_failures)
            return PolicyResult(
                decision=PolicyDecision.DENY,
                checks=checks,
                blocking_reason=blocking
            )
            
        # 2. Check for HUMAN_APPROVAL_REQUIRED conditions
        if failed_checks:
            blocking = "; ".join(c.reason for c in failed_checks)
            return PolicyResult(
                decision=PolicyDecision.HUMAN_APPROVAL_REQUIRED,
                checks=checks,
                blocking_reason=blocking
            )
            
        # 3. All checks passed
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            checks=checks
        )
