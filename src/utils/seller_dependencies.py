from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from utils.auth_dependencies import CurrentUserData, get_current_user_data


class CurrentSellerData(BaseModel):
    id: int


async def get_current_seller(
    request: Request,
    current_user: CurrentUserData = Depends(get_current_user_data)
) -> CurrentSellerData:
    """
    Get current seller based on authenticated user.
    Raises 403 if user is not a seller.
    Raises 404 if seller account not found.
    """
    if current_user.seller_id is not None:
        return CurrentSellerData(id=current_user.seller_id)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only sellers can access this endpoint"
    )


async def verify_seller_owns_resource(
    resource_seller_id: int,
    current_seller: CurrentSellerData
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
