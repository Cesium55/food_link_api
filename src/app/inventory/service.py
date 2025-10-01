from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.inventory import schemas
from src.models import ProductEntry


class InventoryService:
    """Service for working with inventory"""

    async def create_product_entry(
        self, session: AsyncSession, schema: schemas.ProductEntryCreate
    ) -> ProductEntry:
        """Create a new product availability record"""
        raise NotImplementedError

    async def get_product_entry_by_id(
        self, session: AsyncSession, entry_id: int
    ) -> Optional[ProductEntry]:
        """Get product availability record by ID"""
        raise NotImplementedError

    async def get_product_entries(
        self, session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[ProductEntry]:
        """Get list of all availability records with pagination"""
        return []

    async def get_product_entries_by_product(
        self, session: AsyncSession, product_id: int
    ) -> List[ProductEntry]:
        """Get availability records by product ID"""
        return []

    async def get_product_entries_by_shop(
        self, session: AsyncSession, shop_id: int
    ) -> List[ProductEntry]:
        """Get availability records by shop point ID"""
        return []

    async def get_product_entry_with_product(
        self, session: AsyncSession, entry_id: int
    ) -> Optional[ProductEntry]:
        """Get record with product information"""
        raise NotImplementedError

    async def get_product_entry_with_shop(
        self, session: AsyncSession, entry_id: int
    ) -> Optional[ProductEntry]:
        """Get record with shop point information"""
        raise NotImplementedError

    async def get_product_entry_with_details(
        self, session: AsyncSession, entry_id: int
    ) -> Optional[ProductEntry]:
        """Get record with full information"""
        raise NotImplementedError

    async def update_product_entry(
        self, session: AsyncSession, entry_id: int, schema: schemas.ProductEntryUpdate
    ) -> ProductEntry:
        """Update product availability record"""
        raise NotImplementedError

    async def delete_product_entry(
        self, session: AsyncSession, entry_id: int
    ) -> None:
        """Delete product availability record"""
        raise NotImplementedError

    async def get_inventory_summary(
        self, session: AsyncSession
    ) -> schemas.InventorySummary:
        """Get inventory summary statistics"""
        return schemas.InventorySummary(
            total_entries=0,
            total_products=0,
            total_shop_points=0,
            total_value=0.0
        )

    async def get_expiring_products_summary(
        self, session: AsyncSession, days_ahead: int = 7
    ) -> schemas.ExpiringProductsSummary:
        """Get expiring products summary"""
        return schemas.ExpiringProductsSummary(
            expiring_soon=0,
            expired=0,
            total_entries=0
        )

    async def search_product_entries(
        self, session: AsyncSession, query: str, skip: int = 0, limit: int = 100
    ) -> List[ProductEntry]:
        """Search availability records"""
        return []

    async def get_product_entries_by_ids(
        self, session: AsyncSession, entry_ids: List[int]
    ) -> List[ProductEntry]:
        """Get availability records by list of IDs"""
        return []
