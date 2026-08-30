import asyncio
from decimal import Decimal
from app.database.connection import AsyncSessionLocal
from sqlalchemy import select
from app.models.agreement import Agreement
from app.services.policy_service import list_policies
from app.policies.engine import PolicyEngine
from app.policies.models import PolicyEvaluationRequest, PolicyEvaluationContext
from app.policies.enums import ActionType

async def test():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Agreement).where(Agreement.status.in_(["approved", "payment_initiated", "pending_payment"]))
        )
        agreements = result.scalars().all()
        
        for agreement in agreements:
            policies = await list_policies(session, agreement.merchant_id)
            active = [p for p in policies if p.is_active]
            if not active:
                continue
            
            active_policy = active[0]
            policy_context = PolicyEvaluationContext(
                merchant_id=agreement.merchant_id,
                policy_id=active_policy.id,
                minimum_price=active_policy.minimum_price,
                maximum_discount_percent=active_policy.maximum_discount_percent,
                maximum_autonomous_transaction=active_policy.maximum_autonomous_transaction,
                human_approval_required=active_policy.human_approval_required
            )
            
            policy_request = PolicyEvaluationRequest(
                action=ActionType.CREATE_AGREEMENT,
                merchant_id=agreement.merchant_id,
                product_id=agreement.product_id,
                unit_price=agreement.unit_price,
                quantity=agreement.quantity,
                total_amount=agreement.total_amount,
                currency=agreement.currency,
                discount_percent=Decimal("0.0")
            )
            
            engine = PolicyEngine()
            policy_result = engine.evaluate(policy_request, policy_context)
            
            print(f"Agreement ID: {agreement.id} | Decision: {policy_result.decision}")
            if policy_result.blocking_reason:
                print(f"Blocking Reason: {policy_result.blocking_reason}")

if __name__ == "__main__":
    asyncio.run(test())
