from typing import List
from fastapi import APIRouter, Request
from app.products import schemas
from app.products.manager import ProductsManager

router = APIRouter(prefix="/products", tags=["products"])

# Initialize manager
products_manager = ProductsManager()


@router.post("/", response_model=schemas.Product, status_code=201)
async def create_product(
    request: Request, product_data: schemas.ProductCreate
) -> schemas.Product:
    """
    Create a new product
    """
    return await products_manager.create_product(request.state.session, product_data)


@router.get("/", response_model=List[schemas.Product])
async def get_products(request: Request) -> List[schemas.Product]:
    """
    Get list of products
    """
    return await products_manager.get_products(request.state.session)


@router.get("/{product_id}", response_model=schemas.Product)
async def get_product(request: Request, product_id: int) -> schemas.Product:
    """
    Get product by ID
    """
    return await products_manager.get_product_by_id(request.state.session, product_id)


@router.get("/seller/{seller_id}", response_model=List[schemas.Product])
async def get_products_by_seller(request: Request, seller_id: int) -> List[schemas.Product]:
    """
    Get products by seller ID
    """
    return await products_manager.get_products_by_seller(request.state.session, seller_id)


@router.get("/{product_id}/with-seller", response_model=schemas.ProductWithSeller)
async def get_product_with_seller(request: Request, product_id: int) -> schemas.ProductWithSeller:
    """
    Get product with seller information
    """
    return await products_manager.get_product_with_seller(request.state.session, product_id)


@router.get("/{product_id}/with-categories", response_model=schemas.ProductWithCategories)
async def get_product_with_categories(request: Request, product_id: int) -> schemas.ProductWithCategories:
    """
    Get product with categories
    """
    return await products_manager.get_product_with_categories(request.state.session, product_id)


@router.get("/{product_id}/with-details", response_model=schemas.ProductWithDetails)
async def get_product_with_details(request: Request, product_id: int) -> schemas.ProductWithDetails:
    """
    Get product with full details
    """
    return await products_manager.get_product_with_details(request.state.session, product_id)


@router.put("/{product_id}", response_model=schemas.Product)
async def update_product(
    request: Request,
    product_id: int, 
    product_data: schemas.ProductUpdate
) -> schemas.Product:
    """
    Update product
    """
    return await products_manager.update_product(request.state.session, product_id, product_data)


@router.delete("/{product_id}", status_code=204)
async def delete_product(request: Request, product_id: int) -> None:
    """
    Delete product
    """
    await products_manager.delete_product(request.state.session, product_id)


@router.get("/summary/stats", response_model=schemas.ProductSummary)
async def get_products_summary(request: Request) -> schemas.ProductSummary:
    """
    Get products summary statistics
    """
    return await products_manager.get_products_summary(request.state.session)


@router.post("/by-ids", response_model=List[schemas.Product])
async def get_products_by_ids(
    request: Request, product_ids: List[int]
) -> List[schemas.Product]:
    """
    Get products by list of IDs
    """
    return await products_manager.get_products_by_ids(request.state.session, product_ids)