import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Optional, List
from fastapi import HTTPException, status

from app.shop_points.manager import ShopPointsManager
from app.shop_points.service import ShopPointsService
from app.shop_points.models import ShopPoint, ShopPointImage
from app.shop_points import schemas
from app.sellers.models import Seller
from app.sellers.service import SellersService
from app.maps.yandex_geocoder import GeocodeResult


# Constants
TEST_SHOP_POINT_ID = 1
TEST_SELLER_ID = 1
TEST_LATITUDE = 55.7558
TEST_LONGITUDE = 37.6173
TEST_ADDRESS_RAW = "Москва, Красная площадь, 1"
TEST_ADDRESS_FORMATTED = "Россия, Москва, Красная площадь, 1"
TEST_REGION = "Москва"
TEST_CITY = "Москва"
TEST_STREET = "Красная площадь"
TEST_HOUSE = "1"
TEST_GEO_ID = "geo_id_123"


@pytest.fixture
def mock_session():
    """Create a mock async session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_seller():
    """Create a mock seller"""
    seller = Mock(spec=Seller)
    seller.id = TEST_SELLER_ID
    seller.email = "seller@example.com"
    seller.phone = "79991234567"
    seller.full_name = "Test Seller"
    seller.short_name = "Test Seller"
    seller.description = "Test description"
    seller.inn = "123456789012"
    seller.is_IP = True
    seller.ogrn = "123456789012345"
    seller.master_id = 1
    seller.status = 0
    seller.verification_level = 0
    seller.registration_doc_url = ""
    seller.balance = 0.0
    seller.firebase_token = None
    seller.images = []
    return seller


@pytest.fixture
def mock_shop_point():
    """Create a mock shop point"""
    shop_point = Mock(spec=ShopPoint)
    shop_point.id = TEST_SHOP_POINT_ID
    shop_point.seller_id = TEST_SELLER_ID
    shop_point.latitude = TEST_LATITUDE
    shop_point.longitude = TEST_LONGITUDE
    shop_point.address_raw = TEST_ADDRESS_RAW
    shop_point.address_formated = TEST_ADDRESS_FORMATTED
    shop_point.region = TEST_REGION
    shop_point.city = TEST_CITY
    shop_point.street = TEST_STREET
    shop_point.house = TEST_HOUSE
    shop_point.geo_id = TEST_GEO_ID
    shop_point.images = []
    return shop_point


@pytest.fixture
def mock_shop_point_image():
    """Create a mock shop point image"""
    image = Mock(spec=ShopPointImage)
    image.id = 1
    image.shop_point_id = TEST_SHOP_POINT_ID
    image.path = "s3://bucket/shop-points/1/image.jpg"
    image.order = 0
    return image


@pytest.fixture
def shop_points_service():
    """Create ShopPointsService instance"""
    return ShopPointsService()


@pytest.fixture
def shop_points_manager():
    """Create ShopPointsManager instance"""
    return ShopPointsManager()


# Helper functions
def create_mock_execute_result(return_value, scalar_method="scalar_one"):
    """Create a mock result for session.execute"""
    mock_result = Mock()
    getattr(mock_result, scalar_method).return_value = return_value
    return mock_result


def create_mock_scalars_result(return_value_list: List):
    """Create a mock result for session.execute with scalars().all()"""
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.all.return_value = return_value_list
    mock_result.scalars.return_value = mock_scalars
    return mock_result


def create_shop_point_create_schema() -> schemas.ShopPointCreate:
    """Create ShopPointCreate schema"""
    return schemas.ShopPointCreate(
        seller_id=TEST_SELLER_ID,
        latitude=TEST_LATITUDE,
        longitude=TEST_LONGITUDE,
        address_raw=TEST_ADDRESS_RAW,
        address_formated=TEST_ADDRESS_FORMATTED,
        region=TEST_REGION,
        city=TEST_CITY,
        street=TEST_STREET,
        house=TEST_HOUSE,
        geo_id=TEST_GEO_ID
    )


def create_shop_point_update_schema() -> schemas.ShopPointUpdate:
    """Create ShopPointUpdate schema"""
    return schemas.ShopPointUpdate(
        latitude=56.0,
        longitude=38.0,
        city="Updated City"
    )


class TestShopPointsService:
    """Tests for ShopPointsService class"""

    @pytest.mark.asyncio
    async def test_create_shop_point(self, shop_points_service, mock_session, mock_shop_point):
        """Test creating shop point"""
        shop_point_create = create_shop_point_create_schema()
        mock_session.execute.return_value = create_mock_execute_result(mock_shop_point)
        
        shop_point = await shop_points_service.create_shop_point(mock_session, shop_point_create)
        
        assert shop_point is not None
        assert shop_point.id == TEST_SHOP_POINT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_point_by_id_found(self, shop_points_service, mock_session, mock_shop_point):
        """Test getting shop point by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_shop_point, "scalar_one_or_none")
        
        shop_point = await shop_points_service.get_shop_point_by_id(mock_session, TEST_SHOP_POINT_ID)
        
        assert shop_point is not None
        assert shop_point.id == TEST_SHOP_POINT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_point_by_id_not_found(self, shop_points_service, mock_session):
        """Test getting shop point by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        shop_point = await shop_points_service.get_shop_point_by_id(mock_session, 999)
        
        assert shop_point is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_points(self, shop_points_service, mock_session, mock_shop_point):
        """Test getting list of shop points"""
        shop_points_list = [mock_shop_point]
        mock_session.execute.return_value = create_mock_scalars_result(shop_points_list)
        
        shop_points = await shop_points_service.get_shop_points(mock_session)
        
        assert len(shop_points) == 1
        assert shop_points[0].id == TEST_SHOP_POINT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_points_empty(self, shop_points_service, mock_session):
        """Test getting empty list of shop points"""
        mock_session.execute.return_value = create_mock_scalars_result([])
        
        shop_points = await shop_points_service.get_shop_points(mock_session)
        
        assert len(shop_points) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_points_paginated(self, shop_points_service, mock_session, mock_shop_point):
        """Test getting paginated shop points"""
        shop_points_list = [mock_shop_point]
        # First call for count, second for paginated results
        mock_session.execute.side_effect = [
            create_mock_execute_result(1, "scalar"),
            create_mock_scalars_result(shop_points_list)
        ]
        
        shop_points, total_count = await shop_points_service.get_shop_points_paginated(
            mock_session, page=1, page_size=10
        )
        
        assert len(shop_points) == 1
        assert total_count == 1
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_shop_points_paginated_with_filters(self, shop_points_service, mock_session, mock_shop_point):
        """Test getting paginated shop points with filters"""
        shop_points_list = [mock_shop_point]
        mock_session.execute.side_effect = [
            create_mock_execute_result(1, "scalar"),
            create_mock_scalars_result(shop_points_list)
        ]
        
        shop_points, total_count = await shop_points_service.get_shop_points_paginated(
            mock_session, page=1, page_size=10,
            region=TEST_REGION, city=TEST_CITY, seller_id=TEST_SELLER_ID,
            min_latitude=55.0, max_latitude=56.0,
            min_longitude=37.0, max_longitude=38.0
        )
        
        assert len(shop_points) == 1
        assert total_count == 1
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_shop_points_by_seller(self, shop_points_service, mock_session, mock_shop_point):
        """Test getting shop points by seller ID"""
        shop_points_list = [mock_shop_point]
        mock_session.execute.return_value = create_mock_scalars_result(shop_points_list)
        
        shop_points = await shop_points_service.get_shop_points_by_seller(mock_session, TEST_SELLER_ID)
        
        assert len(shop_points) == 1
        assert shop_points[0].seller_id == TEST_SELLER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_point_with_seller(self, shop_points_service, mock_session, mock_shop_point):
        """Test getting shop point with seller"""
        mock_session.execute.return_value = create_mock_execute_result(mock_shop_point, "scalar_one_or_none")
        
        shop_point = await shop_points_service.get_shop_point_with_seller(mock_session, TEST_SHOP_POINT_ID)
        
        assert shop_point is not None
        assert shop_point.id == TEST_SHOP_POINT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_shop_point(self, shop_points_service, mock_session, mock_shop_point):
        """Test updating shop point"""
        shop_point_update = create_shop_point_update_schema()
        updated_shop_point = Mock(spec=ShopPoint)
        updated_shop_point.id = TEST_SHOP_POINT_ID
        updated_shop_point.seller_id = TEST_SELLER_ID
        updated_shop_point.latitude = 56.0
        updated_shop_point.longitude = 38.0
        updated_shop_point.address_raw = None
        updated_shop_point.address_formated = None
        updated_shop_point.region = None
        updated_shop_point.city = "Updated City"
        updated_shop_point.street = None
        updated_shop_point.house = None
        updated_shop_point.geo_id = None
        updated_shop_point.images = []
        
        # First call for update, second for getting updated shop point
        mock_session.execute.side_effect = [
            Mock(),  # Update execution
            create_mock_execute_result(updated_shop_point, "scalar_one")
        ]
        
        result = await shop_points_service.update_shop_point(
            mock_session, TEST_SHOP_POINT_ID, shop_point_update
        )
        
        assert result is not None
        assert result.city == "Updated City"
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_shop_point(self, shop_points_service, mock_session):
        """Test deleting shop point"""
        mock_session.execute.return_value = Mock()
        
        await shop_points_service.delete_shop_point(mock_session, TEST_SHOP_POINT_ID)
        
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_points_summary(self, shop_points_service, mock_session):
        """Test getting shop points summary"""
        mock_session.execute.side_effect = [
            create_mock_execute_result(10, "scalar"),  # Total shop points
            create_mock_execute_result(5, "scalar")   # Total sellers
        ]
        
        summary = await shop_points_service.get_shop_points_summary(mock_session)
        
        assert summary.total_shop_points == 10
        assert summary.total_sellers == 5
        assert summary.avg_shop_points_per_seller == 2.0
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_shop_points_summary_zero_sellers(self, shop_points_service, mock_session):
        """Test getting shop points summary with zero sellers"""
        mock_session.execute.side_effect = [
            create_mock_execute_result(0, "scalar"),  # Total shop points
            create_mock_execute_result(0, "scalar")   # Total sellers
        ]
        
        summary = await shop_points_service.get_shop_points_summary(mock_session)
        
        assert summary.total_shop_points == 0
        assert summary.total_sellers == 0
        assert summary.avg_shop_points_per_seller == 0.0

    @pytest.mark.asyncio
    async def test_get_shop_points_by_ids(self, shop_points_service, mock_session, mock_shop_point):
        """Test getting shop points by list of IDs"""
        shop_points_list = [mock_shop_point]
        mock_session.execute.return_value = create_mock_scalars_result(shop_points_list)
        
        shop_points = await shop_points_service.get_shop_points_by_ids(mock_session, [TEST_SHOP_POINT_ID])
        
        assert len(shop_points) == 1
        assert shop_points[0].id == TEST_SHOP_POINT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_shop_point_by_address(self, shop_points_service, mock_session, mock_shop_point):
        """Test creating shop point by address"""
        geocoded_data = {
            "latitude": TEST_LATITUDE,
            "longitude": TEST_LONGITUDE,
            "address_raw": TEST_ADDRESS_RAW,
            "formatted_address": TEST_ADDRESS_FORMATTED,
            "region": TEST_REGION,
            "city": TEST_CITY,
            "street": TEST_STREET,
            "house": TEST_HOUSE,
            "geo_id": TEST_GEO_ID
        }
        mock_session.execute.return_value = create_mock_execute_result(mock_shop_point)
        
        shop_point = await shop_points_service.create_shop_point_by_address(
            mock_session, TEST_SELLER_ID, geocoded_data
        )
        
        assert shop_point is not None
        assert shop_point.id == TEST_SHOP_POINT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_shop_point_image(self, shop_points_service, mock_session, mock_shop_point_image):
        """Test creating shop point image"""
        mock_session.execute.return_value = create_mock_execute_result(mock_shop_point_image)
        
        image = await shop_points_service.create_shop_point_image(
            mock_session, TEST_SHOP_POINT_ID, "s3://bucket/path.jpg", order=0
        )
        
        assert image is not None
        assert image.id == mock_shop_point_image.id
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_point_image_by_id_found(self, shop_points_service, mock_session, mock_shop_point_image):
        """Test getting shop point image by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_shop_point_image, "scalar_one_or_none")
        
        image = await shop_points_service.get_shop_point_image_by_id(mock_session, 1)
        
        assert image is not None
        assert image.id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_point_image_by_id_not_found(self, shop_points_service, mock_session):
        """Test getting shop point image by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        image = await shop_points_service.get_shop_point_image_by_id(mock_session, 999)
        
        assert image is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_shop_point_image(self, shop_points_service, mock_session):
        """Test deleting shop point image"""
        mock_session.execute.return_value = Mock()
        
        await shop_points_service.delete_shop_point_image(mock_session, 1)
        
        mock_session.execute.assert_called_once()


class TestShopPointsManager:
    """Tests for ShopPointsManager class"""

    @pytest.mark.asyncio
    async def test_create_shop_point_success(self, shop_points_manager, mock_session, mock_seller, mock_shop_point):
        """Test successful shop point creation"""
        shop_point_create = create_shop_point_create_schema()
        shop_points_manager.service.create_shop_point = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        
        result = await shop_points_manager.create_shop_point(mock_session, shop_point_create, mock_seller)
        
        assert result is not None
        assert isinstance(result, schemas.ShopPoint)
        assert result.id == TEST_SHOP_POINT_ID
        shop_points_manager.service.create_shop_point.assert_called_once()
        shop_points_manager.service.get_shop_point_by_id.assert_called_once_with(mock_session, TEST_SHOP_POINT_ID)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_shop_point_wrong_seller(self, shop_points_manager, mock_session, mock_seller):
        """Test creating shop point for another seller (should fail)"""
        shop_point_create = create_shop_point_create_schema()
        shop_point_create.seller_id = 999  # Different seller ID
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.create_shop_point(mock_session, shop_point_create, mock_seller)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "own seller account" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_shop_point_no_seller(self, shop_points_manager, mock_session, mock_shop_point):
        """Test creating shop point without seller (should succeed)"""
        shop_point_create = create_shop_point_create_schema()
        shop_points_manager.service.create_shop_point = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        
        result = await shop_points_manager.create_shop_point(mock_session, shop_point_create, None)
        
        assert result is not None
        shop_points_manager.service.create_shop_point.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_points(self, shop_points_manager, mock_session, mock_shop_point):
        """Test getting list of shop points"""
        shop_points_list = [mock_shop_point]
        shop_points_manager.service.get_shop_points = AsyncMock(return_value=shop_points_list)
        
        result = await shop_points_manager.get_shop_points(mock_session)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.ShopPoint)
        shop_points_manager.service.get_shop_points.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_shop_points_paginated(self, shop_points_manager, mock_session, mock_shop_point):
        """Test getting paginated shop points"""
        shop_points_list = [mock_shop_point]
        shop_points_manager.service.get_shop_points_paginated = AsyncMock(return_value=(shop_points_list, 1))
        
        result = await shop_points_manager.get_shop_points_paginated(mock_session, page=1, page_size=10)
        
        assert result.pagination.total_items == 1
        assert len(result.items) == 1
        assert isinstance(result.items[0], schemas.ShopPoint)
        shop_points_manager.service.get_shop_points_paginated.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_points_paginated_with_filters(self, shop_points_manager, mock_session, mock_shop_point):
        """Test getting paginated shop points with filters"""
        shop_points_list = [mock_shop_point]
        shop_points_manager.service.get_shop_points_paginated = AsyncMock(return_value=(shop_points_list, 1))
        
        result = await shop_points_manager.get_shop_points_paginated(
            mock_session, page=1, page_size=10,
            region=TEST_REGION, city=TEST_CITY
        )
        
        assert result.pagination.total_items == 1
        shop_points_manager.service.get_shop_points_paginated.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shop_point_by_id_success(self, shop_points_manager, mock_session, mock_shop_point):
        """Test getting shop point by ID - success"""
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        
        result = await shop_points_manager.get_shop_point_by_id(mock_session, TEST_SHOP_POINT_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ShopPoint)
        assert result.id == TEST_SHOP_POINT_ID
        shop_points_manager.service.get_shop_point_by_id.assert_called_once_with(mock_session, TEST_SHOP_POINT_ID)

    @pytest.mark.asyncio
    async def test_get_shop_point_by_id_not_found(self, shop_points_manager, mock_session):
        """Test getting shop point by ID - not found"""
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.get_shop_point_by_id(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_shop_points_by_seller(self, shop_points_manager, mock_session, mock_shop_point):
        """Test getting shop points by seller ID"""
        shop_points_list = [mock_shop_point]
        shop_points_manager.service.get_shop_points_by_seller = AsyncMock(return_value=shop_points_list)
        
        result = await shop_points_manager.get_shop_points_by_seller(mock_session, TEST_SELLER_ID)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.ShopPoint)
        shop_points_manager.service.get_shop_points_by_seller.assert_called_once_with(mock_session, TEST_SELLER_ID)

    @pytest.mark.asyncio
    async def test_get_shop_point_with_seller_success(self, shop_points_manager, mock_session, mock_shop_point, mock_seller):
        """Test getting shop point with seller - success"""
        shop_points_manager.service.get_shop_point_with_seller = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.sellers_service = Mock(spec=SellersService)
        shop_points_manager.sellers_service.get_seller_by_id = AsyncMock(return_value=mock_seller)
        
        result = await shop_points_manager.get_shop_point_with_seller(mock_session, TEST_SHOP_POINT_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ShopPointWithSeller)
        assert result.seller is not None
        shop_points_manager.service.get_shop_point_with_seller.assert_called_once_with(mock_session, TEST_SHOP_POINT_ID)
        shop_points_manager.sellers_service.get_seller_by_id.assert_called_once_with(mock_session, TEST_SELLER_ID)

    @pytest.mark.asyncio
    async def test_get_shop_point_with_seller_not_found(self, shop_points_manager, mock_session):
        """Test getting shop point with seller - shop point not found"""
        shop_points_manager.service.get_shop_point_with_seller = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.get_shop_point_with_seller(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_shop_point_with_seller_seller_not_found(self, shop_points_manager, mock_session, mock_shop_point):
        """Test getting shop point with seller - seller not found"""
        shop_points_manager.service.get_shop_point_with_seller = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.sellers_service = Mock(spec=SellersService)
        shop_points_manager.sellers_service.get_seller_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.get_shop_point_with_seller(mock_session, TEST_SHOP_POINT_ID)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "seller" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_update_shop_point_success(self, shop_points_manager, mock_session, mock_seller, mock_shop_point):
        """Test updating shop point - success"""
        shop_point_update = create_shop_point_update_schema()
        updated_shop_point = Mock(spec=ShopPoint)
        updated_shop_point.id = TEST_SHOP_POINT_ID
        updated_shop_point.seller_id = TEST_SELLER_ID
        updated_shop_point.latitude = 56.0
        updated_shop_point.longitude = 38.0
        updated_shop_point.address_raw = None
        updated_shop_point.address_formated = None
        updated_shop_point.region = None
        updated_shop_point.city = "Updated City"
        updated_shop_point.street = None
        updated_shop_point.house = None
        updated_shop_point.geo_id = None
        updated_shop_point.images = []
        
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.service.update_shop_point = AsyncMock(return_value=updated_shop_point)
        
        with patch('app.shop_points.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await shop_points_manager.update_shop_point(
                mock_session, TEST_SHOP_POINT_ID, shop_point_update, mock_seller
            )
            
            assert result is not None
            assert isinstance(result, schemas.ShopPoint)
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            shop_points_manager.service.update_shop_point.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_shop_point_not_found(self, shop_points_manager, mock_session, mock_seller):
        """Test updating shop point - not found"""
        shop_point_update = create_shop_point_update_schema()
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.update_shop_point(
                mock_session, 999, shop_point_update, mock_seller
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_shop_point_success(self, shop_points_manager, mock_session, mock_seller, mock_shop_point):
        """Test deleting shop point - success"""
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.service.delete_shop_point = AsyncMock()
        
        with patch('app.shop_points.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            await shop_points_manager.delete_shop_point(mock_session, TEST_SHOP_POINT_ID, mock_seller)
            
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            shop_points_manager.service.delete_shop_point.assert_called_once_with(mock_session, TEST_SHOP_POINT_ID)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_shop_point_not_found(self, shop_points_manager, mock_session, mock_seller):
        """Test deleting shop point - not found"""
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.delete_shop_point(mock_session, 999, mock_seller)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_shop_points_summary(self, shop_points_manager, mock_session):
        """Test getting shop points summary"""
        summary = schemas.ShopPointSummary(
            total_shop_points=10,
            total_sellers=5,
            avg_shop_points_per_seller=2.0
        )
        shop_points_manager.service.get_shop_points_summary = AsyncMock(return_value=summary)
        
        result = await shop_points_manager.get_shop_points_summary(mock_session)
        
        assert result.total_shop_points == 10
        assert result.total_sellers == 5
        assert result.avg_shop_points_per_seller == 2.0
        shop_points_manager.service.get_shop_points_summary.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_shop_points_by_ids(self, shop_points_manager, mock_session, mock_shop_point):
        """Test getting shop points by list of IDs"""
        shop_points_list = [mock_shop_point]
        shop_points_manager.service.get_shop_points_by_ids = AsyncMock(return_value=shop_points_list)
        
        result = await shop_points_manager.get_shop_points_by_ids(mock_session, [TEST_SHOP_POINT_ID])
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.ShopPoint)
        shop_points_manager.service.get_shop_points_by_ids.assert_called_once_with(mock_session, [TEST_SHOP_POINT_ID])

    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_success(self, shop_points_manager, mock_session, mock_seller, mock_shop_point):
        """Test creating shop point by address - success"""
        shop_point_create_by_address = schemas.ShopPointCreateByAddress(raw_address=TEST_ADDRESS_RAW)
        
        geocoder_result = Mock(spec=GeocodeResult)
        geocoder_result.latitude = TEST_LATITUDE
        geocoder_result.longitude = TEST_LONGITUDE
        geocoder_result.address_raw = TEST_ADDRESS_RAW
        geocoder_result.formatted_address = f"Россия, {TEST_ADDRESS_FORMATTED}"
        geocoder_result.region = TEST_REGION
        geocoder_result.city = TEST_CITY
        geocoder_result.street = TEST_STREET
        geocoder_result.house = TEST_HOUSE
        geocoder_result.geo_id = TEST_GEO_ID
        
        mock_geocoder = AsyncMock()
        mock_geocoder.geocode_address = AsyncMock(return_value=geocoder_result)
        mock_geocoder.close = AsyncMock()
        
        shop_points_manager.sellers_service.get_seller_by_master_id = AsyncMock(return_value=mock_seller)
        shop_points_manager.service.create_shop_point_by_address = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        
        with patch('app.shop_points.manager.create_geocoder', return_value=mock_geocoder):
            result = await shop_points_manager.create_shop_point_by_address(
                mock_session, 1, shop_point_create_by_address
            )
            
            assert result is not None
            assert isinstance(result, schemas.ShopPoint)
            shop_points_manager.sellers_service.get_seller_by_master_id.assert_called_once_with(mock_session, 1)
            mock_geocoder.geocode_address.assert_called_once_with(TEST_ADDRESS_RAW)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_not_seller(self, shop_points_manager, mock_session):
        """Test creating shop point by address - user is not seller"""
        shop_point_create_by_address = schemas.ShopPointCreateByAddress(raw_address=TEST_ADDRESS_RAW)
        shop_points_manager.sellers_service.get_seller_by_master_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.create_shop_point_by_address(
                mock_session, 1, shop_point_create_by_address
            )
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "not a seller" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_not_found(self, shop_points_manager, mock_session, mock_seller):
        """Test creating shop point by address - address not found"""
        shop_point_create_by_address = schemas.ShopPointCreateByAddress(raw_address="Nonexistent Address")
        
        mock_geocoder = AsyncMock()
        mock_geocoder.geocode_address = AsyncMock(return_value=None)
        mock_geocoder.close = AsyncMock()
        
        shop_points_manager.sellers_service.get_seller_by_master_id = AsyncMock(return_value=mock_seller)
        
        with patch('app.shop_points.manager.create_geocoder', return_value=mock_geocoder):
            with pytest.raises(HTTPException) as exc_info:
                await shop_points_manager.create_shop_point_by_address(
                    mock_session, 1, shop_point_create_by_address
                )
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_not_russia(self, shop_points_manager, mock_session, mock_seller):
        """Test creating shop point by address - address not in Russia"""
        shop_point_create_by_address = schemas.ShopPointCreateByAddress(raw_address="New York, USA")
        
        geocoder_result = Mock(spec=GeocodeResult)
        geocoder_result.formatted_address = "USA, New York"
        
        mock_geocoder = AsyncMock()
        mock_geocoder.geocode_address = AsyncMock(return_value=geocoder_result)
        mock_geocoder.close = AsyncMock()
        
        shop_points_manager.sellers_service.get_seller_by_master_id = AsyncMock(return_value=mock_seller)
        
        with patch('app.shop_points.manager.create_geocoder', return_value=mock_geocoder):
            with pytest.raises(HTTPException) as exc_info:
                await shop_points_manager.create_shop_point_by_address(
                    mock_session, 1, shop_point_create_by_address
                )
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "russia" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_upload_shop_point_image_success(self, shop_points_manager, mock_session, mock_seller, mock_shop_point):
        """Test uploading shop point image - success"""
        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.read = AsyncMock(return_value=b"fake image data")
        
        mock_image = Mock()
        mock_image.id = 1
        mock_image.path = "s3://bucket/shop-points/1/image.jpg"
        mock_image.order = 0
        
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.image_manager.upload_and_create_image_record = AsyncMock(return_value=mock_image)
        
        with patch('app.shop_points.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await shop_points_manager.upload_shop_point_image(
                mock_session, TEST_SHOP_POINT_ID, mock_file, order=0, current_seller=mock_seller
            )
            
            assert result is not None
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            shop_points_manager.image_manager.upload_and_create_image_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_shop_point_image_not_found(self, shop_points_manager, mock_session, mock_seller):
        """Test uploading shop point image - shop point not found"""
        mock_file = Mock()
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.upload_shop_point_image(
                mock_session, 999, mock_file, current_seller=mock_seller
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_upload_shop_point_images_success(self, shop_points_manager, mock_session, mock_seller, mock_shop_point):
        """Test uploading multiple shop point images - success"""
        mock_files = [Mock(), Mock()]
        for f in mock_files:
            f.filename = "test.jpg"
            f.read = AsyncMock(return_value=b"fake image data")
        
        mock_images = [Mock(), Mock()]
        for i, img in enumerate(mock_images):
            img.id = i + 1
            img.path = f"s3://bucket/shop-points/1/image{i}.jpg"
            img.order = i
        
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.image_manager.upload_multiple_and_create_image_records = AsyncMock(return_value=mock_images)
        
        with patch('app.shop_points.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await shop_points_manager.upload_shop_point_images(
                mock_session, TEST_SHOP_POINT_ID, mock_files, start_order=0, current_seller=mock_seller
            )
            
            assert len(result) == 2
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            shop_points_manager.image_manager.upload_multiple_and_create_image_records.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_shop_point_image_success(self, shop_points_manager, mock_session, mock_seller, mock_shop_point, mock_shop_point_image):
        """Test deleting shop point image - success"""
        mock_shop_point_image.shop_point_id = TEST_SHOP_POINT_ID
        shop_points_manager.service.get_shop_point_image_by_id = AsyncMock(return_value=mock_shop_point_image)
        shop_points_manager.service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        shop_points_manager.image_manager.delete_image_record = AsyncMock()
        
        with patch('app.shop_points.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            await shop_points_manager.delete_shop_point_image(
                mock_session, 1, current_seller=mock_seller
            )
            
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            shop_points_manager.image_manager.delete_image_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_shop_point_image_not_found(self, shop_points_manager, mock_session, mock_seller):
        """Test deleting shop point image - image not found"""
        shop_points_manager.service.get_shop_point_image_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await shop_points_manager.delete_shop_point_image(
                mock_session, 999, current_seller=mock_seller
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
