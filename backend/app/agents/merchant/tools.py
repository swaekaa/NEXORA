"""
NEXORA — Merchant Agent Tools

Thin adapters over existing deterministic service layer for the Merchant Agent.
These tools are for information gathering — authorization remains with the Policy Engine.
"""
import uuid
from typing import Any

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.negotiation_service import get_negotiation_messages as _get_messages, get_negotiation
from app.services.product_service import get_product
from app.exceptions import ResourceNotFoundError


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
async def get_product_info(merchant_id: str, product_id: str, config: RunnableConfig) -> dict[str, Any]:
    """
    Get current product details and inventory for a product being negotiated.

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
            "description": product.description,
            "base_price": str(product.price),
            "inventory": product.inventory,
            "status": product.status,
            "sku": product.sku,
        }
    except ResourceNotFoundError:
        return {"error": f"Product {product_id} not found for merchant {merchant_id}"}

