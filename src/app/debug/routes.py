from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
from app.debug.init import DebugDataInitializer

router = APIRouter(prefix="/debug", tags=["debug"])

# Initialize data initializer
initializer = DebugDataInitializer()


@router.post("/init-test-data")
async def initialize_test_data(request: Request) -> Dict[str, Any]:
    """
    Initialize application with test data for all domains except inventory.
    This will create product categories, networks, shop points, and products.
    Each step is independent and can be run multiple times safely.
    """
    try:
        result = await initializer.initialize_all_data()
        return {
            "success": True,
            "message": "Test data initialization completed successfully",
            "steps_completed": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize test data: {str(e)}"
        )


@router.post("/init-categories")
async def initialize_categories(request: Request) -> Dict[str, Any]:
    """
    Initialize product categories only.
    """
    try:
        result = await initializer.get_or_create_categories()
        return {
            "success": True,
            "message": "Product categories initialized successfully",
            "categories_created": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize categories: {str(e)}"
        )


@router.post("/init-networks")
async def initialize_networks(request: Request) -> Dict[str, Any]:
    """
    Initialize networks only.
    """
    try:
        result = await initializer.get_or_create_networks()
        return {
            "success": True,
            "message": "Networks initialized successfully",
            "networks_created": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize networks: {str(e)}"
        )


@router.post("/init-shop-points")
async def initialize_shop_points(request: Request) -> Dict[str, Any]:
    """
    Initialize shop points only.
    """
    try:
        # First get networks
        networks = await initializer.get_or_create_networks()
        if not networks:
            return {
                "success": False,
                "message": "No networks found. Please initialize networks first.",
                "shop_points_created": []
            }
        
        result = await initializer.get_or_create_shop_points(networks)
        return {
            "success": True,
            "message": "Shop points initialized successfully",
            "shop_points_created": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize shop points: {str(e)}"
        )


@router.post("/init-products")
async def initialize_products(request: Request) -> Dict[str, Any]:
    """
    Initialize products only.
    """
    try:
        # First get networks and categories
        networks = await initializer.get_or_create_networks()
        categories = await initializer.get_or_create_categories()
        
        if not networks:
            return {
                "success": False,
                "message": "No networks found. Please initialize networks first.",
                "products_created": []
            }
        
        if not categories:
            return {
                "success": False,
                "message": "No categories found. Please initialize categories first.",
                "products_created": []
            }
        
        result = await initializer.get_or_create_products(networks, categories)
        return {
            "success": True,
            "message": "Products initialized successfully",
            "products_created": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize products: {str(e)}"
        )


@router.get("/status")
async def get_initialization_status(request: Request) -> Dict[str, Any]:
    """
    Get current status of initialized data.
    """
    try:
        # Get counts of existing data
        networks = await initializer.get_or_create_networks()
        categories = await initializer.get_or_create_categories()
        
        # For shop points and products, we need to make separate requests
        # since they depend on networks
        shop_points_count = 0
        products_count = 0
        
        if networks:
            shop_points = await initializer.get_or_create_shop_points(networks)
            shop_points_count = len(shop_points)
            
            if categories:
                products = await initializer.get_or_create_products(networks, categories)
                products_count = len(products)
        
        status = {
            "networks": len(networks),
            "categories": len(categories),
            "shop_points": shop_points_count,
            "products": products_count
        }
        
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )
