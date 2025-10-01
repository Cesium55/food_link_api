from typing import List
from fastapi import APIRouter, Request, Query
from app.inventory import schemas
from app.inventory.manager import InventoryManager

router = APIRouter(prefix="/inventory", tags=["inventory"])

# Initialize manager
inventory_manager = InventoryManager()


@router.post("/", response_model=schemas.ProductEntry, status_code=201)
async def create_product_entry(entry_data: schemas.ProductEntryCreate) -> schemas.ProductEntry:
    """
    Create a new product entry
    """
    return await inventory_manager.create_product_entry(entry_data)


@router.get("/", response_model=List[schemas.ProductEntry])
async def get_product_entries(request: Request) -> List[schemas.ProductEntry]:
    """
    Get list of product entries
    """
    return await inventory_manager.get_product_entries(request.state.session)


@router.get("/{entry_id}", response_model=schemas.ProductEntry)
async def get_product_entry(entry_id: int) -> schemas.ProductEntry:
    """
    Get product entry by ID
    """
    return await inventory_manager.get_product_entry_by_id(entry_id)


@router.get("/product/{product_id}", response_model=List[schemas.ProductEntry])
async def get_product_entries_by_product(product_id: int) -> List[schemas.ProductEntry]:
    """
    Get product entries by product ID
    """
    return await inventory_manager.get_product_entries_by_product(product_id)


@router.get("/shop/{shop_id}", response_model=List[schemas.ProductEntry])
async def get_product_entries_by_shop(shop_id: int) -> List[schemas.ProductEntry]:
    """
    Get product entries by shop point ID
    """
    return await inventory_manager.get_product_entries_by_shop(shop_id)


@router.get("/{entry_id}/with-product", response_model=schemas.ProductEntryWithProduct)
async def get_product_entry_with_product(entry_id: int) -> schemas.ProductEntryWithProduct:
    """
    Get product entry with product information
    """
    return await inventory_manager.get_product_entry_with_product(entry_id)


@router.get("/{entry_id}/with-shop", response_model=schemas.ProductEntryWithShop)
async def get_product_entry_with_shop(entry_id: int) -> schemas.ProductEntryWithShop:
    """
    Get product entry with shop point information
    """
    return await inventory_manager.get_product_entry_with_shop(entry_id)


@router.get("/{entry_id}/with-details", response_model=schemas.ProductEntryWithDetails)
async def get_product_entry_with_details(entry_id: int) -> schemas.ProductEntryWithDetails:
    """
    Get product entry with full details
    """
    return await inventory_manager.get_product_entry_with_details(entry_id)


@router.put("/{entry_id}", response_model=schemas.ProductEntry)
async def update_product_entry(
    entry_id: int, 
    entry_data: schemas.ProductEntryUpdate
) -> schemas.ProductEntry:
    """
    Update product entry
    """
    return await inventory_manager.update_product_entry(entry_id, entry_data)


@router.delete("/{entry_id}", status_code=204)
async def delete_product_entry(entry_id: int) -> None:
    """
    Delete product entry
    """
    await inventory_manager.delete_product_entry(entry_id)


@router.get("/summary/stats", response_model=schemas.InventorySummary)
async def get_inventory_summary() -> schemas.InventorySummary:
    """
    Get inventory summary statistics
    """
    return await inventory_manager.get_inventory_summary()


@router.get("/summary/expiring", response_model=schemas.ExpiringProductsSummary)
async def get_expiring_products_summary(
    days_ahead: int = Query(7, ge=1, le=365, description="Number of days ahead to check for expiring products")
) -> schemas.ExpiringProductsSummary:
    """
    Get expiring products summary
    """
    return await inventory_manager.get_expiring_products_summary(days_ahead)


@router.post("/by-ids", response_model=List[schemas.ProductEntry])
async def get_product_entries_by_ids(entry_ids: List[int]) -> List[schemas.ProductEntry]:
    """
    Get product entries by list of IDs
    """
    return await inventory_manager.get_product_entries_by_ids(entry_ids)