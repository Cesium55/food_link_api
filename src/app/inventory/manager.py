from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.inventory import schemas
from app.inventory.service import InventoryService
from src.utils.errors_handler import handle_alchemy_error


class InventoryManager:
    """Manager for inventory business logic and validation"""

    def __init__(self):
        self.service = InventoryService()

    @handle_alchemy_error
    async def create_product_entry(self, entry_data: schemas.ProductEntryCreate) -> schemas.ProductEntry:
        """Create a new product entry with validation"""
        raise NotImplementedError

    async def get_product_entries(self, session: AsyncSession) -> List[schemas.ProductEntry]:
        """Get list of product entries"""
        return []

    async def get_product_entry_by_id(self, entry_id: int) -> schemas.ProductEntry:
        """Get product entry by ID"""
        raise NotImplementedError

    async def get_product_entries_by_product(self, product_id: int) -> List[schemas.ProductEntry]:
        """Get product entries by product ID"""
        return []

    async def get_product_entries_by_shop(self, shop_id: int) -> List[schemas.ProductEntry]:
        """Get product entries by shop point ID"""
        return []

    async def get_product_entry_with_product(self, entry_id: int) -> schemas.ProductEntryWithProduct:
        """Get product entry with product information"""
        raise NotImplementedError

    async def get_product_entry_with_shop(self, entry_id: int) -> schemas.ProductEntryWithShop:
        """Get product entry with shop point information"""
        raise NotImplementedError

    async def get_product_entry_with_details(self, entry_id: int) -> schemas.ProductEntryWithDetails:
        """Get product entry with full details"""
        raise NotImplementedError

    @handle_alchemy_error
    async def update_product_entry(
        self, 
        entry_id: int, 
        entry_data: schemas.ProductEntryUpdate
    ) -> schemas.ProductEntry:
        """Update product entry with validation"""
        raise NotImplementedError

    @handle_alchemy_error
    async def delete_product_entry(self, entry_id: int) -> None:
        """Delete product entry"""
        raise NotImplementedError

    async def get_inventory_summary(self) -> schemas.InventorySummary:
        """Get inventory summary statistics"""
        return schemas.InventorySummary(
            total_entries=0,
            total_products=0,
            total_shop_points=0,
            total_value=0.0
        )

    async def get_expiring_products_summary(self, days_ahead: int = 7) -> schemas.ExpiringProductsSummary:
        """Get expiring products summary"""
        return schemas.ExpiringProductsSummary(
            expiring_soon=0,
            expired=0,
            total_entries=0
        )

    async def get_product_entries_by_ids(self, entry_ids: List[int]) -> List[schemas.ProductEntry]:
        """Get product entries by list of IDs"""
        return []
