from typing import List
from fastapi import APIRouter, Request
from app.networks import schemas
from app.networks.manager import NetworksManager

router = APIRouter(prefix="/networks", tags=["networks"])

# Initialize manager
networks_manager = NetworksManager()


@router.post("/", response_model=schemas.Network, status_code=201)
async def create_network(
    request: Request, network_data: schemas.NetworkCreate
) -> schemas.Network:
    """
    Create a new network
    """
    return await networks_manager.create_network(request.state.session, network_data)


@router.get("/", response_model=List[schemas.Network])
async def get_networks(request: Request) -> List[schemas.Network]:
    """
    Get list of networks
    """
    return await networks_manager.get_networks(request.state.session)


@router.get("/{network_id}", response_model=schemas.Network)
async def get_network(request: Request, network_id: int) -> schemas.Network:
    """
    Get network by ID
    """
    return await networks_manager.get_network_by_id(request.state.session, network_id)


@router.get("/slug/{slug}", response_model=schemas.Network)
async def get_network_by_slug(request: Request, slug: str) -> schemas.Network:
    """
    Get network by slug
    """
    return await networks_manager.get_network_by_slug(request.state.session, slug)


@router.get("/{network_id}/with-shops", response_model=schemas.NetworkWithShopPoints)
async def get_network_with_shops(
    request: Request, network_id: int
) -> schemas.NetworkWithShopPoints:
    """
    Get network with shop points
    """
    return await networks_manager.get_network_with_shop_points(
        request.state.session, network_id
    )


@router.get("/{network_id}/with-details", response_model=schemas.NetworkWithDetails)
async def get_network_with_details(
    request: Request, network_id: int
) -> schemas.NetworkWithDetails:
    """
    Get network with full details
    """
    return await networks_manager.get_network_with_details(
        request.state.session, network_id
    )


@router.put("/{network_id}", response_model=schemas.Network)
async def update_network(
    request: Request, network_id: int, network_data: schemas.NetworkUpdate
) -> schemas.Network:
    """
    Update network
    """
    return await networks_manager.update_network(
        request.state.session, network_id, network_data
    )


@router.delete("/{network_id}", status_code=204)
async def delete_network(request: Request, network_id: int) -> None:
    """
    Delete network
    """
    await networks_manager.delete_network(request.state.session, network_id)


@router.get("/summary/stats", response_model=schemas.NetworkSummary)
async def get_networks_summary(request: Request) -> schemas.NetworkSummary:
    """
    Get networks summary statistics
    """
    return await networks_manager.get_networks_summary(request.state.session)


@router.post("/by-ids", response_model=List[schemas.Network])
async def get_networks_by_ids(
    request: Request, network_ids: List[int]
) -> List[schemas.Network]:
    """
    Get networks by list of IDs
    """
    return await networks_manager.get_networks_by_ids(
        request.state.session, network_ids
    )
