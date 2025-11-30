from typing import List
from fastapi import APIRouter, Request, Depends, UploadFile, File, Query
from app.products import schemas
from app.products.manager import ProductsManager
from utils.auth_dependencies import get_current_user
from app.auth.models import User

router = APIRouter(prefix="/products", tags=["products"])

# Initialize manager
products_manager = ProductsManager()


@router.post("", response_model=schemas.Product, status_code=201)
async def create_product(
    request: Request, 
    product_data: schemas.ProductCreate,
    current_user: User = Depends(get_current_user)
) -> schemas.Product:
    """
    Create a new product (with optional categories and attributes).
    Seller ID is automatically determined from the authenticated user.
    """
    return await products_manager.create_product(request.state.session, product_data, current_user)


@router.get("", response_model=List[schemas.Product])
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


@router.post("/attributes", response_model=schemas.ProductAttribute, status_code=201)
async def create_product_attribute(
    request: Request, attribute_data: schemas.ProductAttributeCreate
) -> schemas.ProductAttribute:
    """
    Create a new product attribute
    """
    return await products_manager.create_product_attribute(request.state.session, attribute_data)


@router.get("/attributes/{attribute_id}", response_model=schemas.ProductAttribute)
async def get_product_attribute(
    request: Request, attribute_id: int
) -> schemas.ProductAttribute:
    """
    Get product attribute by ID
    """
    return await products_manager.get_product_attribute_by_id(request.state.session, attribute_id)


@router.get("/{product_id}/attributes", response_model=List[schemas.ProductAttribute])
async def get_product_attributes(
    request: Request, product_id: int
) -> List[schemas.ProductAttribute]:
    """
    Get all attributes for a product
    """
    return await products_manager.get_product_attributes_by_product(request.state.session, product_id)


@router.get("/{product_id}/attributes/{slug}", response_model=schemas.ProductAttribute)
async def get_product_attribute_by_slug(
    request: Request, product_id: int, slug: str
) -> schemas.ProductAttribute:
    """
    Get product attribute by product ID and slug
    """
    return await products_manager.get_product_attribute_by_product_and_slug(request.state.session, product_id, slug)


@router.put("/attributes/{attribute_id}", response_model=schemas.ProductAttribute)
async def update_product_attribute(
    request: Request,
    attribute_id: int,
    attribute_data: schemas.ProductAttributeUpdate
) -> schemas.ProductAttribute:
    """
    Update product attribute
    """
    return await products_manager.update_product_attribute(request.state.session, attribute_id, attribute_data)


@router.delete("/attributes/{attribute_id}", status_code=204)
async def delete_product_attribute(request: Request, attribute_id: int) -> None:
    """
    Delete product attribute
    """
    await products_manager.delete_product_attribute(request.state.session, attribute_id)


@router.post("/{product_id}/images", response_model=schemas.ProductImage, status_code=201)
async def upload_product_image(
    request: Request,
    product_id: int,
    file: UploadFile = File(...),
    order: int = Query(default=0, ge=0)
) -> schemas.ProductImage:
    """
    Upload an image for a product
    """
    return await products_manager.upload_product_image(
        request.state.session, product_id, file, order
    )


@router.post("/{product_id}/images/batch", response_model=List[schemas.ProductImage], status_code=201)
async def upload_product_images(
    request: Request,
    product_id: int,
    files: List[UploadFile] = File(...),
    start_order: int = Query(default=0, ge=0)
) -> List[schemas.ProductImage]:
    """
    Upload multiple images for a product
    """
    return await products_manager.upload_product_images(
        request.state.session, product_id, files, start_order
    )


@router.delete("/images/{image_id}", status_code=204)
async def delete_product_image(request: Request, image_id: int) -> None:
    """
    Delete a product image
    """
    await products_manager.delete_product_image(request.state.session, image_id)