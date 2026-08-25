"""
NEXORA — Buyer Agent Tools

Contains bounded tools for the Buyer Agent.
The only allowed LLM tool is discovering products. 
Negotiation creation and policy checks are deterministic processes outside the LLM's control.
"""
from typing import Any

from langchain_core.tools import tool


@tool
def search_products(query: str, products_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Search for products in the merchant's catalog that match the query.
    Always use this tool to discover available products before making a selection.
    
    Args:
        query: The search term to match against product names and descriptions.
        products_list: The list of products (injected at runtime, do not provide).
    """
    query = query.lower()
    results = []
    for p in products_list:
        name = p.get("name", "").lower()
        desc = p.get("description", "").lower()
        if query in name or query in desc:
            results.append(p)
            
    # If no results from text filter, return all (fallback so LLM sees the catalog)
    if not results:
        return products_list
        
    return results
