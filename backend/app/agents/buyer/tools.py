"""
NEXORA — Buyer Agent Tools

Contains bounded tools for the Buyer Agent.
The only allowed LLM tool is discovering products. 
Negotiation creation and policy checks are deterministic processes outside the LLM's control.
"""
import uuid
from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.product_service import list_products

from langchain_core.runnables import RunnableConfig

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
    
    query = query.lower()
    results = []
    for p in products:
        name = p.name.lower()
        desc = (p.description or "").lower()
        
        if query in name or query in desc or not query:
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
