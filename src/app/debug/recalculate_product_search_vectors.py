"""Utilities for recalculating product full-text search vectors."""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.products.service import ProductsService


async def recalculate_product_search_vectors(
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    Recalculate product search vectors for all products.

    Returns:
        Dictionary with process statistics.
    """
    products_service = ProductsService()
    updated_count = await products_service.recalculate_all_products_search_vectors(
        session
    )
    await session.commit()

    return {
        "success": True,
        "message": f"Recalculated search vectors for {updated_count} products",
        "updated_count": updated_count,
    }
