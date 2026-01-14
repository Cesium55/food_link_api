import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Optional, List
from fastapi import HTTPException, status

from app.sellers.manager import SellersManager
from app.sellers.service import SellersService
from app.sellers.models import Seller, SellerImage
from app.sellers import schemas
from app.auth.models import User
from app.shop_points.models import ShopPoint
from app.shop_points.service import ShopPointsService
from app.products.models import Product
from app.products.service import ProductsService


# Constants
TEST_SELLER_ID = 1
TEST_USER_ID = 1
TEST_EMAIL = "seller@example.com"
TEST_PHONE = "79991234567"
TEST_FULL_NAME = "Test Seller Full Name"
TEST_SHORT_NAME = "Test Seller"
TEST_INN_IP = "123456789012"
TEST_INN_ORG = "1234567890"
TEST_OGRN_IP = "123456789012345"
TEST_OGRN_ORG = "1234567890123"


@pytest.fixture
def mock_session():
    """Create a mock async session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock user"""
    user = Mock(spec=User)
    user.id = TEST_USER_ID
    user.email = TEST_EMAIL
    user.phone = TEST_PHONE
    user.is_seller = False
    return user


@pytest.fixture
def mock_seller():
    """Create a mock seller"""
    seller = Mock(spec=Seller)
    seller.id = TEST_SELLER_ID
    seller.email = TEST_EMAIL
    seller.phone = TEST_PHONE
    seller.full_name = TEST_FULL_NAME
    seller.short_name = TEST_SHORT_NAME
    seller.description = "Test description"
    seller.inn = TEST_INN_IP
    seller.is_IP = True
    seller.ogrn = TEST_OGRN_IP
    seller.master_id = TEST_USER_ID
    seller.status = 0
    seller.verification_level = 0
    seller.registration_doc_url = ""
    seller.balance = 0.0
    seller.firebase_token = None
    seller.images = []
    return seller


@pytest.fixture
def mock_seller_image():
    """Create a mock seller image"""
    image = Mock(spec=SellerImage)
    image.id = 1
    image.seller_id = TEST_SELLER_ID
    image.path = "s3://bucket/sellers/1/image.jpg"
    image.order = 0
    return image


@pytest.fixture
def sellers_service():
    """Create SellersService instance"""
    return SellersService()


@pytest.fixture
def sellers_manager():
    """Create SellersManager instance"""
    return SellersManager()


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


def create_seller_create_schema(is_IP: bool = True) -> schemas.SellerCreate:
    """Create SellerCreate schema"""
    return schemas.SellerCreate(
        full_name=TEST_FULL_NAME,
        short_name=TEST_SHORT_NAME,
        description="Test description",
        inn=TEST_INN_IP if is_IP else TEST_INN_ORG,
        is_IP=is_IP,
        ogrn=TEST_OGRN_IP if is_IP else TEST_OGRN_ORG
    )


def create_seller_update_schema() -> schemas.SellerUpdate:
    """Create SellerUpdate schema"""
    return schemas.SellerUpdate(
        full_name="Updated Full Name",
        short_name="Updated Short Name"
    )


class TestSellersService:
    """Tests for SellersService class"""

    @pytest.mark.asyncio
    async def test_check_user_exists_by_email_true(self, sellers_service, mock_session, mock_user):
        """Test checking user exists by email - user exists"""
        mock_session.execute.return_value = create_mock_execute_result(mock_user, "scalar_one_or_none")
        
        result = await sellers_service.check_user_exists_by_email(mock_session, TEST_EMAIL)
        
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_user_exists_by_email_false(self, sellers_service, mock_session):
        """Test checking user exists by email - user doesn't exist"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        result = await sellers_service.check_user_exists_by_email(mock_session, "nonexistent@example.com")
        
        assert result is False
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_user_exists_by_phone_true(self, sellers_service, mock_session, mock_user):
        """Test checking user exists by phone - user exists"""
        mock_session.execute.return_value = create_mock_execute_result(mock_user, "scalar_one_or_none")
        
        result = await sellers_service.check_user_exists_by_phone(mock_session, TEST_PHONE)
        
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_user_exists_by_phone_false(self, sellers_service, mock_session):
        """Test checking user exists by phone - user doesn't exist"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        result = await sellers_service.check_user_exists_by_phone(mock_session, "79999999999")
        
        assert result is False
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_user_exists_by_phone_none(self, sellers_service, mock_session):
        """Test checking user exists by phone - phone is None"""
        result = await sellers_service.check_user_exists_by_phone(mock_session, None)
        
        assert result is False
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_seller(self, sellers_service, mock_session, mock_seller):
        """Test creating seller"""
        seller_create = create_seller_create_schema()
        # First call returns created seller, second call returns seller with images
        mock_session.execute.side_effect = [
            create_mock_execute_result(mock_seller),
            create_mock_execute_result(mock_seller, "scalar_one")
        ]
        
        seller = await sellers_service.create_seller(
            mock_session, seller_create, TEST_USER_ID, TEST_EMAIL
        )
        
        assert seller is not None
        assert seller.id == TEST_SELLER_ID
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_seller_by_id_found(self, sellers_service, mock_session, mock_seller):
        """Test getting seller by ID - seller found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_seller, "scalar_one_or_none")
        
        seller = await sellers_service.get_seller_by_id(mock_session, TEST_SELLER_ID)
        
        assert seller is not None
        assert seller.id == TEST_SELLER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_seller_by_id_not_found(self, sellers_service, mock_session):
        """Test getting seller by ID - seller not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        seller = await sellers_service.get_seller_by_id(mock_session, 999)
        
        assert seller is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_seller_by_master_id_found(self, sellers_service, mock_session, mock_seller):
        """Test getting seller by master_id - seller found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_seller, "scalar_one_or_none")
        
        seller = await sellers_service.get_seller_by_master_id(mock_session, TEST_USER_ID)
        
        assert seller is not None
        assert seller.master_id == TEST_USER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_seller_by_master_id_not_found(self, sellers_service, mock_session):
        """Test getting seller by master_id - seller not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        seller = await sellers_service.get_seller_by_master_id(mock_session, 999)
        
        assert seller is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sellers(self, sellers_service, mock_session, mock_seller):
        """Test getting list of sellers"""
        sellers_list = [mock_seller]
        mock_session.execute.return_value = create_mock_scalars_result(sellers_list)
        
        sellers = await sellers_service.get_sellers(mock_session)
        
        assert len(sellers) == 1
        assert sellers[0].id == TEST_SELLER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sellers_empty(self, sellers_service, mock_session):
        """Test getting empty list of sellers"""
        mock_session.execute.return_value = create_mock_scalars_result([])
        
        sellers = await sellers_service.get_sellers(mock_session)
        
        assert len(sellers) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sellers_paginated(self, sellers_service, mock_session, mock_seller):
        """Test getting paginated sellers"""
        sellers_list = [mock_seller]
        # First call for count, second for paginated results
        mock_session.execute.side_effect = [
            create_mock_execute_result(1, "scalar"),
            create_mock_scalars_result(sellers_list)
        ]
        
        sellers, total_count = await sellers_service.get_sellers_paginated(
            mock_session, page=1, page_size=10
        )
        
        assert len(sellers) == 1
        assert total_count == 1
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_sellers_paginated_with_filters(self, sellers_service, mock_session, mock_seller):
        """Test getting paginated sellers with status and verification_level filters"""
        sellers_list = [mock_seller]
        mock_session.execute.side_effect = [
            create_mock_execute_result(1, "scalar"),
            create_mock_scalars_result(sellers_list)
        ]
        
        sellers, total_count = await sellers_service.get_sellers_paginated(
            mock_session, page=1, page_size=10, status=0, verification_level=0
        )
        
        assert len(sellers) == 1
        assert total_count == 1
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_seller_with_shop_points(self, sellers_service, mock_session, mock_seller):
        """Test getting seller with shop points"""
        mock_session.execute.return_value = create_mock_execute_result(mock_seller, "scalar_one_or_none")
        
        seller = await sellers_service.get_seller_with_shop_points(mock_session, TEST_SELLER_ID)
        
        assert seller is not None
        assert seller.id == TEST_SELLER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_seller_with_details(self, sellers_service, mock_session, mock_seller):
        """Test getting seller with details"""
        mock_session.execute.return_value = create_mock_execute_result(mock_seller, "scalar_one_or_none")
        
        seller = await sellers_service.get_seller_with_details(mock_session, TEST_SELLER_ID)
        
        assert seller is not None
        assert seller.id == TEST_SELLER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_seller(self, sellers_service, mock_session, mock_seller):
        """Test updating seller"""
        seller_update = create_seller_update_schema()
        # First call for update, second for getting updated seller
        mock_session.execute.side_effect = [
            Mock(),  # Update execution
            create_mock_execute_result(mock_seller, "scalar_one")
        ]
        
        updated_seller = await sellers_service.update_seller(
            mock_session, TEST_SELLER_ID, seller_update
        )
        
        assert updated_seller is not None
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_seller(self, sellers_service, mock_session):
        """Test deleting seller"""
        mock_session.execute.return_value = Mock()
        
        await sellers_service.delete_seller(mock_session, TEST_SELLER_ID)
        
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sellers_summary(self, sellers_service, mock_session):
        """Test getting sellers summary"""
        mock_session.execute.side_effect = [
            create_mock_execute_result(10, "scalar"),  # Total sellers
            create_mock_execute_result(50, "scalar")   # Total products
        ]
        
        summary = await sellers_service.get_sellers_summary(mock_session)
        
        assert summary.total_sellers == 10
        assert summary.total_products == 50
        assert summary.avg_products_per_seller == 5.0
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_sellers_summary_zero_sellers(self, sellers_service, mock_session):
        """Test getting sellers summary with zero sellers"""
        mock_session.execute.side_effect = [
            create_mock_execute_result(0, "scalar"),  # Total sellers
            create_mock_execute_result(0, "scalar")   # Total products
        ]
        
        summary = await sellers_service.get_sellers_summary(mock_session)
        
        assert summary.total_sellers == 0
        assert summary.total_products == 0
        assert summary.avg_products_per_seller == 0.0

    @pytest.mark.asyncio
    async def test_get_sellers_by_ids(self, sellers_service, mock_session, mock_seller):
        """Test getting sellers by list of IDs"""
        sellers_list = [mock_seller]
        mock_session.execute.return_value = create_mock_scalars_result(sellers_list)
        
        sellers = await sellers_service.get_sellers_by_ids(mock_session, [TEST_SELLER_ID])
        
        assert len(sellers) == 1
        assert sellers[0].id == TEST_SELLER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_seller_image(self, sellers_service, mock_session, mock_seller_image):
        """Test creating seller image"""
        mock_session.execute.return_value = create_mock_execute_result(mock_seller_image)
        
        image = await sellers_service.create_seller_image(
            mock_session, TEST_SELLER_ID, "s3://bucket/path.jpg", order=0
        )
        
        assert image is not None
        assert image.id == mock_seller_image.id
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_seller_image_by_id_found(self, sellers_service, mock_session, mock_seller_image):
        """Test getting seller image by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_seller_image, "scalar_one_or_none")
        
        image = await sellers_service.get_seller_image_by_id(mock_session, 1)
        
        assert image is not None
        assert image.id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_seller_image_by_id_not_found(self, sellers_service, mock_session):
        """Test getting seller image by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        image = await sellers_service.get_seller_image_by_id(mock_session, 999)
        
        assert image is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_seller_image(self, sellers_service, mock_session):
        """Test deleting seller image"""
        mock_session.execute.return_value = Mock()
        
        await sellers_service.delete_seller_image(mock_session, 1)
        
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_seller_firebase_token(self, sellers_service, mock_session, mock_seller):
        """Test updating seller firebase token"""
        mock_session.execute.side_effect = [
            Mock(),  # Update execution
            create_mock_execute_result(mock_seller, "scalar_one")
        ]
        
        updated_seller = await sellers_service.update_seller_firebase_token(
            mock_session, TEST_SELLER_ID, "firebase_token_123"
        )
        
        assert updated_seller is not None
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_seller_firebase_token(self, sellers_service, mock_session):
        """Test getting seller firebase token"""
        mock_session.execute.return_value = create_mock_execute_result("firebase_token_123", "scalar_one_or_none")
        
        token = await sellers_service.get_seller_firebase_token(mock_session, TEST_SELLER_ID)
        
        assert token == "firebase_token_123"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_seller_firebase_token_none(self, sellers_service, mock_session):
        """Test getting seller firebase token when it's None"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        token = await sellers_service.get_seller_firebase_token(mock_session, TEST_SELLER_ID)
        
        assert token is None
        mock_session.execute.assert_called_once()


class TestSellersManager:
    """Tests for SellersManager class"""

    @pytest.mark.asyncio
    async def test_create_seller_success(self, sellers_manager, mock_session, mock_user, mock_seller):
        """Test successful seller creation"""
        seller_create = create_seller_create_schema()
        sellers_manager.service.get_seller_by_master_id = AsyncMock(return_value=None)
        sellers_manager.service.create_seller = AsyncMock(return_value=mock_seller)
        sellers_manager.auth_service.update_user_is_seller = AsyncMock(return_value=mock_user)
        
        result = await sellers_manager.create_seller(mock_session, seller_create, mock_user)
        
        assert result is not None
        assert result.id == TEST_SELLER_ID
        sellers_manager.service.get_seller_by_master_id.assert_called_once_with(mock_session, TEST_USER_ID)
        sellers_manager.service.create_seller.assert_called_once()
        sellers_manager.auth_service.update_user_is_seller.assert_called_once_with(mock_session, TEST_USER_ID, True)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_seller_already_exists(self, sellers_manager, mock_session, mock_user, mock_seller):
        """Test seller creation when seller already exists"""
        seller_create = create_seller_create_schema()
        sellers_manager.service.get_seller_by_master_id = AsyncMock(return_value=mock_seller)
        sellers_manager.service.create_seller = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await sellers_manager.create_seller(mock_session, seller_create, mock_user)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "уже есть аккаунт продавца" in exc_info.value.detail
        sellers_manager.service.create_seller.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_sellers(self, sellers_manager, mock_session, mock_seller):
        """Test getting list of sellers"""
        sellers_list = [mock_seller]
        sellers_manager.service.get_sellers = AsyncMock(return_value=sellers_list)
        
        result = await sellers_manager.get_sellers(mock_session)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.PublicSeller)
        sellers_manager.service.get_sellers.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_sellers_paginated(self, sellers_manager, mock_session, mock_seller):
        """Test getting paginated sellers"""
        sellers_list = [mock_seller]
        sellers_manager.service.get_sellers_paginated = AsyncMock(return_value=(sellers_list, 1))
        
        result = await sellers_manager.get_sellers_paginated(mock_session, page=1, page_size=10)
        
        assert result.pagination.total_items == 1
        assert len(result.items) == 1
        assert isinstance(result.items[0], schemas.PublicSeller)
        sellers_manager.service.get_sellers_paginated.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sellers_paginated_with_filters(self, sellers_manager, mock_session, mock_seller):
        """Test getting paginated sellers with filters"""
        sellers_list = [mock_seller]
        sellers_manager.service.get_sellers_paginated = AsyncMock(return_value=(sellers_list, 1))
        
        result = await sellers_manager.get_sellers_paginated(
            mock_session, page=1, page_size=10, status=0, verification_level=0
        )
        
        assert result.pagination.total_items == 1
        sellers_manager.service.get_sellers_paginated.assert_called_once_with(
            mock_session, 1, 10, 0, 0
        )

    @pytest.mark.asyncio
    async def test_get_seller_by_id_success(self, sellers_manager, mock_session, mock_seller):
        """Test getting seller by ID - success"""
        sellers_manager.service.get_seller_by_id = AsyncMock(return_value=mock_seller)
        
        result = await sellers_manager.get_seller_by_id(mock_session, TEST_SELLER_ID)
        
        assert result is not None
        assert isinstance(result, schemas.PublicSeller)
        sellers_manager.service.get_seller_by_id.assert_called_once_with(mock_session, TEST_SELLER_ID)

    @pytest.mark.asyncio
    async def test_get_seller_by_id_not_found(self, sellers_manager, mock_session):
        """Test getting seller by ID - not found"""
        sellers_manager.service.get_seller_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await sellers_manager.get_seller_by_id(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_seller_by_email_success(self, sellers_manager, mock_session, mock_user, mock_seller):
        """Test getting seller by email - success"""
        sellers_manager.auth_service.get_user_by_email = AsyncMock(return_value=mock_user)
        sellers_manager.service.get_seller_by_master_id = AsyncMock(return_value=mock_seller)
        
        result = await sellers_manager.get_seller_by_email(mock_session, TEST_EMAIL)
        
        assert result is not None
        assert isinstance(result, schemas.Seller)
        sellers_manager.auth_service.get_user_by_email.assert_called_once_with(mock_session, TEST_EMAIL)
        sellers_manager.service.get_seller_by_master_id.assert_called_once_with(mock_session, TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_get_seller_by_email_user_not_found(self, sellers_manager, mock_session):
        """Test getting seller by email - user not found"""
        sellers_manager.auth_service.get_user_by_email = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await sellers_manager.get_seller_by_email(mock_session, "nonexistent@example.com")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "user" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_seller_by_email_seller_not_found(self, sellers_manager, mock_session, mock_user):
        """Test getting seller by email - seller not found"""
        sellers_manager.auth_service.get_user_by_email = AsyncMock(return_value=mock_user)
        sellers_manager.service.get_seller_by_master_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await sellers_manager.get_seller_by_email(mock_session, TEST_EMAIL)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "seller" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_seller_with_shop_points_success(self, sellers_manager, mock_session, mock_seller):
        """Test getting seller with shop points - success"""
        mock_shop_point = Mock(spec=ShopPoint)
        mock_shop_point.id = 1
        mock_shop_point.seller_id = TEST_SELLER_ID
        mock_shop_point.latitude = None
        mock_shop_point.longitude = None
        mock_shop_point.address_raw = None
        mock_shop_point.address_formated = None
        mock_shop_point.region = None
        mock_shop_point.city = None
        mock_shop_point.street = None
        mock_shop_point.house = None
        mock_shop_point.geo_id = None
        mock_shop_point.images = []
        
        sellers_manager.service.get_seller_with_shop_points = AsyncMock(return_value=mock_seller)
        # Mock service method, not manager method
        sellers_manager.shop_points_service = Mock(spec=ShopPointsService)
        sellers_manager.shop_points_service.get_shop_points_by_seller = AsyncMock(return_value=[mock_shop_point])
        
        result = await sellers_manager.get_seller_with_shop_points(mock_session, TEST_SELLER_ID)
        
        assert result is not None
        assert isinstance(result, schemas.PublicSellerWithShopPoints)
        assert len(result.shop_points) == 1

    @pytest.mark.asyncio
    async def test_get_seller_with_shop_points_not_found(self, sellers_manager, mock_session):
        """Test getting seller with shop points - seller not found"""
        sellers_manager.service.get_seller_with_shop_points = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await sellers_manager.get_seller_with_shop_points(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_seller_with_details_success(self, sellers_manager, mock_session, mock_seller):
        """Test getting seller with details - success"""
        mock_shop_point = Mock(spec=ShopPoint)
        mock_shop_point.id = 1
        mock_shop_point.seller_id = TEST_SELLER_ID
        mock_shop_point.latitude = None
        mock_shop_point.longitude = None
        mock_shop_point.address_raw = None
        mock_shop_point.address_formated = None
        mock_shop_point.region = None
        mock_shop_point.city = None
        mock_shop_point.street = None
        mock_shop_point.house = None
        mock_shop_point.geo_id = None
        mock_shop_point.images = []
        
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        mock_product.seller_id = TEST_SELLER_ID
        mock_product.name = "Test Product"
        mock_product.description = None
        mock_product.article = None
        mock_product.code = None
        mock_product.images = []
        mock_product.attributes = []
        mock_product.categories = []
        
        sellers_manager.service.get_seller_with_details = AsyncMock(return_value=mock_seller)
        # Mock service methods, not manager methods
        sellers_manager.shop_points_service = Mock(spec=ShopPointsService)
        sellers_manager.shop_points_service.get_shop_points_by_seller = AsyncMock(return_value=[mock_shop_point])
        sellers_manager.products_service = Mock(spec=ProductsService)
        sellers_manager.products_service.get_products_by_seller = AsyncMock(return_value=[mock_product])
        
        result = await sellers_manager.get_seller_with_details(mock_session, TEST_SELLER_ID)
        
        assert result is not None
        assert isinstance(result, schemas.PublicSellerWithDetails)
        assert len(result.shop_points) == 1
        assert len(result.products) == 1

    @pytest.mark.asyncio
    async def test_get_seller_with_details_not_found(self, sellers_manager, mock_session):
        """Test getting seller with details - seller not found"""
        sellers_manager.service.get_seller_with_details = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await sellers_manager.get_seller_with_details(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_seller_success(self, sellers_manager, mock_session, mock_seller):
        """Test updating seller - success"""
        seller_update = create_seller_update_schema()
        updated_seller = Mock(spec=Seller)
        updated_seller.id = TEST_SELLER_ID
        updated_seller.email = TEST_EMAIL
        updated_seller.phone = TEST_PHONE
        updated_seller.full_name = "Updated Full Name"
        updated_seller.short_name = "Updated Short Name"
        updated_seller.description = "Updated description"
        updated_seller.inn = TEST_INN_IP
        updated_seller.is_IP = True
        updated_seller.ogrn = TEST_OGRN_IP
        updated_seller.master_id = TEST_USER_ID
        updated_seller.status = 0
        updated_seller.verification_level = 0
        updated_seller.registration_doc_url = ""
        updated_seller.balance = 0.0
        updated_seller.images = []
        
        sellers_manager.service.update_seller = AsyncMock(return_value=updated_seller)
        
        with patch('app.sellers.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await sellers_manager.update_seller(
                mock_session, TEST_SELLER_ID, seller_update, mock_seller
            )
            
            assert result is not None
            assert isinstance(result, schemas.Seller)
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            sellers_manager.service.update_seller.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_seller_success(self, sellers_manager, mock_session, mock_seller):
        """Test deleting seller - success"""
        sellers_manager.service.delete_seller = AsyncMock()
        
        with patch('app.sellers.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            await sellers_manager.delete_seller(mock_session, TEST_SELLER_ID, mock_seller)
            
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            sellers_manager.service.delete_seller.assert_called_once_with(mock_session, TEST_SELLER_ID)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sellers_summary(self, sellers_manager, mock_session):
        """Test getting sellers summary"""
        summary = schemas.SellerSummary(
            total_sellers=10,
            total_products=50,
            avg_products_per_seller=5.0
        )
        sellers_manager.service.get_sellers_summary = AsyncMock(return_value=summary)
        
        result = await sellers_manager.get_sellers_summary(mock_session)
        
        assert result.total_sellers == 10
        assert result.total_products == 50
        assert result.avg_products_per_seller == 5.0
        sellers_manager.service.get_sellers_summary.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_sellers_by_ids(self, sellers_manager, mock_session, mock_seller):
        """Test getting sellers by list of IDs"""
        sellers_list = [mock_seller]
        sellers_manager.service.get_sellers_by_ids = AsyncMock(return_value=sellers_list)
        
        result = await sellers_manager.get_sellers_by_ids(mock_session, [TEST_SELLER_ID])
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.PublicSeller)
        sellers_manager.service.get_sellers_by_ids.assert_called_once_with(mock_session, [TEST_SELLER_ID])

    @pytest.mark.asyncio
    async def test_update_seller_firebase_token(self, sellers_manager, mock_session, mock_seller):
        """Test updating seller firebase token"""
        updated_seller = Mock(spec=Seller)
        updated_seller.id = TEST_SELLER_ID
        updated_seller.email = TEST_EMAIL
        updated_seller.phone = TEST_PHONE
        updated_seller.full_name = TEST_FULL_NAME
        updated_seller.short_name = TEST_SHORT_NAME
        updated_seller.description = "Test description"
        updated_seller.inn = TEST_INN_IP
        updated_seller.is_IP = True
        updated_seller.ogrn = TEST_OGRN_IP
        updated_seller.master_id = TEST_USER_ID
        updated_seller.status = 0
        updated_seller.verification_level = 0
        updated_seller.registration_doc_url = ""
        updated_seller.balance = 0.0
        updated_seller.firebase_token = "firebase_token_123"
        updated_seller.images = []
        
        sellers_manager.service.update_seller_firebase_token = AsyncMock(return_value=updated_seller)
        
        result = await sellers_manager.update_seller_firebase_token(
            mock_session, TEST_SELLER_ID, "firebase_token_123"
        )
        
        assert result is not None
        assert isinstance(result, schemas.Seller)
        sellers_manager.service.update_seller_firebase_token.assert_called_once_with(
            mock_session, TEST_SELLER_ID, "firebase_token_123"
        )
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_seller_firebase_token(self, sellers_manager, mock_session):
        """Test getting seller firebase token"""
        sellers_manager.service.get_seller_firebase_token = AsyncMock(return_value="firebase_token_123")
        
        result = await sellers_manager.get_seller_firebase_token(mock_session, TEST_SELLER_ID)
        
        assert result == "firebase_token_123"
        sellers_manager.service.get_seller_firebase_token.assert_called_once_with(mock_session, TEST_SELLER_ID)

    @pytest.mark.asyncio
    async def test_send_notification_to_seller_success(self, sellers_manager, mock_session, mock_seller):
        """Test sending notification to seller - success"""
        mock_seller.firebase_token = "firebase_token_123"
        sellers_manager.service.get_seller_by_id = AsyncMock(return_value=mock_seller)
        sellers_manager.notification_manager.send_notification = AsyncMock()
        
        await sellers_manager.send_notification_to_seller(
            mock_session, TEST_SELLER_ID, "Title", "Body", {"key": "value"}
        )
        
        sellers_manager.service.get_seller_by_id.assert_called_once_with(mock_session, TEST_SELLER_ID)
        sellers_manager.notification_manager.send_notification.assert_called_once_with(
            token="firebase_token_123",
            title="Title",
            body="Body",
            data={"key": "value"}
        )

    @pytest.mark.asyncio
    async def test_send_notification_to_seller_no_token(self, sellers_manager, mock_session, mock_seller):
        """Test sending notification to seller - no firebase token"""
        mock_seller.firebase_token = None
        sellers_manager.service.get_seller_by_id = AsyncMock(return_value=mock_seller)
        sellers_manager.notification_manager.send_notification = AsyncMock()
        
        await sellers_manager.send_notification_to_seller(
            mock_session, TEST_SELLER_ID, "Title", "Body"
        )
        
        sellers_manager.notification_manager.send_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_notification_to_seller_not_found(self, sellers_manager, mock_session):
        """Test sending notification to seller - seller not found"""
        sellers_manager.service.get_seller_by_id = AsyncMock(return_value=None)
        sellers_manager.notification_manager.send_notification = AsyncMock()
        
        await sellers_manager.send_notification_to_seller(
            mock_session, 999, "Title", "Body"
        )
        
        sellers_manager.notification_manager.send_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_notification_to_seller_exception(self, sellers_manager, mock_session, mock_seller):
        """Test sending notification to seller - exception handling"""
        mock_seller.firebase_token = "firebase_token_123"
        sellers_manager.service.get_seller_by_id = AsyncMock(return_value=mock_seller)
        sellers_manager.notification_manager.send_notification = AsyncMock(side_effect=Exception("Network error"))
        
        # Should not raise exception
        await sellers_manager.send_notification_to_seller(
            mock_session, TEST_SELLER_ID, "Title", "Body"
        )
        
        sellers_manager.notification_manager.send_notification.assert_called_once()
