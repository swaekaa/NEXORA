"""
NEXORA — Buyer Agent Tools

Contains bounded tools for the Buyer Agent.
All tools are thin adapters over existing deterministic service layer methods.
No raw SQL. No business logic. No financial decisions.

Architecture: LLM → Agent Tool → Service Layer → Database
"""
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_service import list_products, get_product
from app.services.negotiation_service import get_negotiation, get_negotiation_messages as _get_messages
from app.exceptions import ResourceNotFoundError


@tool
async def search_products(merchant_id: str, query: str, config: RunnableConfig) -> list[dict[str, Any]]:
    """
    Search for products in the merchant's catalog that match the query.
    Always use this tool to discover available products before making a selection.

    Args:
        merchant_id: The UUID of the merchant.
        query: The search term to match against product names and descriptions.
        config: Injected configuration containing 'session' (do not provide).
    """
    session: AsyncSession = config["configurable"]["session"]
    m_id = uuid.UUID(merchant_id)

    # Query database safely via service
    products = await list_products(session, m_id)

    query_words = [w.strip() for w in query.lower().replace('-', ' ').split() if w.strip()]
    results = []
    for p in products:
        name = p.name.lower()
        desc = (p.description or "").lower()

        # Match if no query, or if ANY word from the query is in the name or description
        if not query_words or any(w in name or w in desc for w in query_words):
            # Return bounded DTOs, omitting internal database details
            results.append({
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "price": str(p.price),
                "sku": p.sku,
                "inventory": p.inventory,
                "status": p.status
            })

    return results


@tool
async def get_negotiation_status(negotiation_id: str, config: RunnableConfig) -> dict[str, Any]:
    """
    Get the current state and round count of an active negotiation.
    Use this to understand where the negotiation stands before deciding your next action.

    Args:
        negotiation_id: The UUID of the negotiation.
        config: Injected configuration containing 'session' (do not provide).
    """
    session: AsyncSession = config["configurable"]["session"]
    neg_id = uuid.UUID(negotiation_id)
    negotiation = await get_negotiation(session, neg_id)
    if not negotiation:
        return {"error": f"Negotiation {negotiation_id} not found"}
    return {
        "negotiation_id": str(negotiation.id),
        "state": negotiation.state,
        "round_count": negotiation.round_count,
        "max_rounds": negotiation.max_rounds,
        "started_at": negotiation.started_at.isoformat(),
    }


@tool
async def get_negotiation_history(negotiation_id: str, config: RunnableConfig) -> list[dict[str, Any]]:
    """
    Get the full message history of a negotiation in chronological order.
    Use this to understand the trajectory of the negotiation and what offers have been made.

    Args:
        negotiation_id: The UUID of the negotiation.
        config: Injected configuration containing 'session' (do not provide).
    """
    session: AsyncSession = config["configurable"]["session"]
    neg_id = uuid.UUID(negotiation_id)
    messages = await _get_messages(session, neg_id)
    return [
        {
            "sequence": m.sequence_number,
            "sender": m.sender_type,
            "message_type": m.message_type,
            "content": m.content,
            "unit_price": m.payload.get("unit_price") if m.payload else None,
            "quantity": m.payload.get("quantity") if m.payload else None,
            "total_amount": m.payload.get("total_amount") if m.payload else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@tool
async def get_product_inventory(merchant_id: str, product_id: str, config: RunnableConfig) -> dict[str, Any]:
    """
    Check the current inventory level for a specific product.
    Use this to understand product availability before committing to a quantity.

    Args:
        merchant_id: The UUID of the merchant who owns the product.
        product_id: The UUID of the product.
        config: Injected configuration containing 'session' (do not provide).
    """
    session: AsyncSession = config["configurable"]["session"]
    m_id = uuid.UUID(merchant_id)
    p_id = uuid.UUID(product_id)
    try:
        product = await get_product(session, m_id, p_id)
        return {
            "product_id": str(product.id),
            "name": product.name,
            "inventory": product.inventory,
            "status": product.status,
            "base_price": str(product.price),
        }
    except ResourceNotFoundError:
        return {"error": f"Product {product_id} not found for merchant {merchant_id}"}


@tool
def evaluate_counteroffer(
    counteroffer_unit_price: str,
    quantity: int,
    maximum_budget: str,
) -> dict[str, Any]:
    """
    Deterministically evaluate whether a merchant's counteroffer fits within budget constraints.
    Use this to decide whether to ACCEPT_COUNTER, COUNTER_PROPOSAL, or STOP.

    Args:
        counteroffer_unit_price: The merchant's proposed unit price as a string (e.g. "12500.00").
        quantity: The quantity of units.
        maximum_budget: The buyer's maximum total budget as a string (e.g. "450000.00").

    Returns a dict with: total_amount, fits_budget, budget_remaining, recommendation.
    """
    try:
        unit_price = Decimal(counteroffer_unit_price).quantize(Decimal("0.01"))
        qty = Decimal(quantity)
        budget = Decimal(maximum_budget).quantize(Decimal("0.01"))
        total = (unit_price * qty).quantize(Decimal("0.01"))
        fits = total <= budget
        remaining = (budget - total).quantize(Decimal("0.01"))
        overage_percent = float(((total - budget) / budget * 100).quantize(Decimal("0.01"))) if total > budget else 0.0
        return {
            "total_amount": str(total),
            "fits_budget": fits,
            "budget_remaining": str(remaining) if fits else "0.00",
            "overage_percent": overage_percent,
            "recommendation": "ACCEPT_COUNTER" if fits else f"COUNTER_PROPOSAL or STOP (exceeds budget by {overage_percent:.1f}%)",
        }
    except (InvalidOperation, ValueError, TypeError) as e:
        return {"error": f"Invalid numeric input: {str(e)}"}
