from fastapi import Depends, HTTPException, Request, status
from app.auth.models import User
from app.sellers.models import Seller
from app.sellers.service import SellersService
from utils.auth_dependencies import get_current_user


async def get_current_seller(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Seller:
    """
    Get current seller based on authenticated user.
    Raises 403 if user is not a seller.
    Raises 404 if seller account not found.
    """
    if not current_user.is_seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access this endpoint"
        )
    
    sellers_service = SellersService()
    seller = await sellers_service.get_seller_by_master_id(
        request.state.session, current_user.id
    )
    
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller account not found for current user"
        )
    
    return seller


async def verify_seller_owns_resource(
    resource_seller_id: int,
    current_seller: Seller
) -> None:
    """
    Verify that current seller owns the resource.
    Raises 403 if seller doesn't own the resource.
    """
    if current_seller.id != resource_seller_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
