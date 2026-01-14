import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException, status

from app.offers.manager import OffersManager
from app.offers.service import OffersService
from app.offers.models import Offer, PricingStrategy, PricingStrategyStep
from app.offers import schemas
from app.products.models import Product
from app.shop_points.models import ShopPoint
from app.sellers.models import Seller


# Constants
TEST_OFFER_ID = 1
TEST_PRODUCT_ID = 1
TEST_SHOP_ID = 1
TEST_SELLER_ID = 1
TEST_PRICING_STRATEGY_ID = 1
TEST_ORIGINAL_COST = Decimal("100.00")
TEST_CURRENT_COST = Decimal("80.00")
TEST_COUNT = 10
TEST_RESERVED_COUNT = 2


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
    seller.master_id = 1
    return seller


@pytest.fixture
def mock_product():
    """Create a mock product"""
    product = Mock(spec=Product)
    product.id = TEST_PRODUCT_ID
    product.name = "Test Product"
    product.description = "Test description"
    product.article = "ART-001"
    product.code = "CODE-001"
    product.seller_id = TEST_SELLER_ID
    product.images = []
    product.attributes = []
    product.categories = []
    # Add category_ids property for schema validation
    product.category_ids = []
    return product


@pytest.fixture
def mock_shop_point():
    """Create a mock shop point"""
    shop_point = Mock(spec=ShopPoint)
    shop_point.id = TEST_SHOP_ID
    shop_point.seller_id = TEST_SELLER_ID
    shop_point.latitude = 55.7558
    shop_point.longitude = 37.6173
    return shop_point


@pytest.fixture
def mock_offer():
    """Create a mock offer"""
    offer = Mock(spec=Offer)
    offer.id = TEST_OFFER_ID
    offer.product_id = TEST_PRODUCT_ID
    offer.shop_id = TEST_SHOP_ID
    offer.pricing_strategy_id = None
    offer.expires_date = None
    offer.original_cost = TEST_ORIGINAL_COST
    offer.current_cost = TEST_CURRENT_COST
    offer.count = TEST_COUNT
    offer.reserved_count = TEST_RESERVED_COUNT
    return offer


@pytest.fixture
def mock_pricing_strategy():
    """Create a mock pricing strategy"""
    strategy = Mock(spec=PricingStrategy)
    strategy.id = TEST_PRICING_STRATEGY_ID
    strategy.name = "Test Strategy"
    strategy.steps = []
    return strategy


@pytest.fixture
def mock_pricing_strategy_step():
    """Create a mock pricing strategy step"""
    step = Mock(spec=PricingStrategyStep)
    step.id = 1
    step.strategy_id = TEST_PRICING_STRATEGY_ID
    step.time_remaining_seconds = 3600
    step.discount_percent = Decimal("10.00")
    return step


@pytest.fixture
def offers_service():
    """Create OffersService instance"""
    return OffersService()


@pytest.fixture
def offers_manager():
    """Create OffersManager instance"""
    return OffersManager()


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


def create_mock_scalar_result(return_value):
    """Create a mock result for session.execute with scalar()"""
    mock_result = Mock()
    mock_result.scalar.return_value = return_value
    return mock_result


def create_offer_create_schema(
    with_pricing_strategy: bool = False,
    expires_date: Optional[datetime] = None
) -> schemas.OfferCreate:
    """Create OfferCreate schema"""
    if expires_date is None:
        expires_date = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=24)
    
    if with_pricing_strategy:
        return schemas.OfferCreate(
            product_id=TEST_PRODUCT_ID,
            shop_id=TEST_SHOP_ID,
            pricing_strategy_id=TEST_PRICING_STRATEGY_ID,
            expires_date=expires_date,
            original_cost=TEST_ORIGINAL_COST,
            current_cost=None,
            count=TEST_COUNT
        )
    else:
        return schemas.OfferCreate(
            product_id=TEST_PRODUCT_ID,
            shop_id=TEST_SHOP_ID,
            pricing_strategy_id=None,
            expires_date=None,
            original_cost=None,
            current_cost=TEST_CURRENT_COST,
            count=TEST_COUNT
        )


def create_offer_update_schema() -> schemas.OfferUpdate:
    """Create OfferUpdate schema"""
    return schemas.OfferUpdate(
        current_cost=Decimal("75.00"),
        count=15
    )


class TestOffersService:
    """Tests for OffersService class"""

    @pytest.mark.asyncio
    async def test_create_offer(self, offers_service, mock_session, mock_offer):
        """Test creating offer"""
        offer_create = create_offer_create_schema()
        mock_session.execute.return_value = create_mock_execute_result(mock_offer)
        
        offer = await offers_service.create_offer(mock_session, offer_create)
        
        assert offer is not None
        assert offer.id == TEST_OFFER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_offer_with_pricing_strategy(self, offers_service, mock_session, mock_offer):
        """Test creating offer with pricing strategy"""
        expires_date = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=24)
        offer_create = create_offer_create_schema(with_pricing_strategy=True, expires_date=expires_date)
        # Set pricing_strategy_id on mock offer
        mock_offer.pricing_strategy_id = TEST_PRICING_STRATEGY_ID
        mock_session.execute.return_value = create_mock_execute_result(mock_offer)
        
        offer = await offers_service.create_offer(mock_session, offer_create)
        
        assert offer is not None
        assert offer.pricing_strategy_id == TEST_PRICING_STRATEGY_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offer_by_id_found(self, offers_service, mock_session, mock_offer):
        """Test getting offer by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_offer, "scalar_one_or_none")
        
        offer = await offers_service.get_offer_by_id(mock_session, TEST_OFFER_ID)
        
        assert offer is not None
        assert offer.id == TEST_OFFER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offer_by_id_not_found(self, offers_service, mock_session):
        """Test getting offer by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        offer = await offers_service.get_offer_by_id(mock_session, 999)
        
        assert offer is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offer_by_product_and_shop_found(self, offers_service, mock_session, mock_offer):
        """Test getting offer by product_id and shop_id - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_offer, "scalar_one_or_none")
        
        offer = await offers_service.get_offer_by_product_and_shop(
            mock_session, TEST_PRODUCT_ID, TEST_SHOP_ID
        )
        
        assert offer is not None
        assert offer.product_id == TEST_PRODUCT_ID
        assert offer.shop_id == TEST_SHOP_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offer_by_product_and_shop_not_found(self, offers_service, mock_session):
        """Test getting offer by product_id and shop_id - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        offer = await offers_service.get_offer_by_product_and_shop(
            mock_session, TEST_PRODUCT_ID, TEST_SHOP_ID
        )
        
        assert offer is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offer_with_product(self, offers_service, mock_session, mock_offer, mock_product):
        """Test getting offer with product information"""
        mock_offer.product = mock_product
        mock_session.execute.return_value = create_mock_execute_result(mock_offer, "scalar_one_or_none")
        
        offer = await offers_service.get_offer_with_product(mock_session, TEST_OFFER_ID)
        
        assert offer is not None
        assert offer.id == TEST_OFFER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offers(self, offers_service, mock_session, mock_offer):
        """Test getting list of offers"""
        offers_list = [mock_offer]
        mock_session.execute.return_value = create_mock_scalars_result(offers_list)
        
        offers = await offers_service.get_offers(mock_session)
        
        assert len(offers) == 1
        assert offers[0].id == TEST_OFFER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offers_empty(self, offers_service, mock_session):
        """Test getting empty list of offers"""
        mock_session.execute.return_value = create_mock_scalars_result([])
        
        offers = await offers_service.get_offers(mock_session)
        
        assert len(offers) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offers_paginated(self, offers_service, mock_session, mock_offer):
        """Test getting paginated offers"""
        offers_list = [mock_offer]
        mock_session.execute.side_effect = [
            create_mock_scalar_result(1),  # Count query
            create_mock_scalars_result(offers_list)  # Offers query
        ]
        
        offers, total_count = await offers_service.get_offers_paginated(
            mock_session, page=1, page_size=10
        )
        
        assert len(offers) == 1
        assert total_count == 1
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_offers_paginated_with_filters(self, offers_service, mock_session, mock_offer):
        """Test getting paginated offers with filters"""
        offers_list = [mock_offer]
        mock_session.execute.side_effect = [
            create_mock_scalar_result(1),  # Count query
            create_mock_scalars_result(offers_list)  # Offers query
        ]
        
        offers, total_count = await offers_service.get_offers_paginated(
            mock_session, page=1, page_size=10,
            product_id=TEST_PRODUCT_ID,
            min_current_cost=Decimal("50.00")
        )
        
        assert len(offers) == 1
        assert total_count == 1

    @pytest.mark.asyncio
    async def test_get_offers_with_products(self, offers_service, mock_session, mock_offer, mock_product):
        """Test getting offers with products"""
        mock_offer.product = mock_product
        offers_list = [mock_offer]
        mock_session.execute.return_value = create_mock_scalars_result(offers_list)
        
        offers = await offers_service.get_offers_with_products(mock_session)
        
        assert len(offers) == 1
        assert offers[0].id == TEST_OFFER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_offer(self, offers_service, mock_session, mock_offer):
        """Test updating offer"""
        offer_update = create_offer_update_schema()
        mock_session.execute.return_value = create_mock_execute_result(mock_offer)
        
        updated_offer = await offers_service.update_offer(
            mock_session, TEST_OFFER_ID, offer_update
        )
        
        assert updated_offer is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_offer(self, offers_service, mock_session):
        """Test deleting offer"""
        mock_session.execute.return_value = Mock()
        
        await offers_service.delete_offer(mock_session, TEST_OFFER_ID)
        
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offers_by_ids(self, offers_service, mock_session, mock_offer):
        """Test getting offers by IDs"""
        offers_list = [mock_offer]
        mock_session.execute.return_value = create_mock_scalars_result(offers_list)
        
        offers = await offers_service.get_offers_by_ids(mock_session, [TEST_OFFER_ID])
        
        assert len(offers) == 1
        assert offers[0].id == TEST_OFFER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offers_by_ids_empty(self, offers_service, mock_session):
        """Test getting offers by empty IDs list"""
        offers = await offers_service.get_offers_by_ids(mock_session, [])
        
        assert len(offers) == 0
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_offer_reserved_count(self, offers_service, mock_session, mock_offer):
        """Test updating offer reserved count"""
        mock_session.execute.return_value = create_mock_execute_result(mock_offer)
        
        updated_offer = await offers_service.update_offer_reserved_count(
            mock_session, TEST_OFFER_ID, 5
        )
        
        assert updated_offer is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_offer_count(self, offers_service, mock_session, mock_offer):
        """Test updating offer count"""
        mock_session.execute.return_value = create_mock_execute_result(mock_offer)
        
        updated_offer = await offers_service.update_offer_count(
            mock_session, TEST_OFFER_ID, 10
        )
        
        assert updated_offer is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_strategies(self, offers_service, mock_session, mock_pricing_strategy):
        """Test getting pricing strategies"""
        strategies_list = [mock_pricing_strategy]
        mock_session.execute.return_value = create_mock_scalars_result(strategies_list)
        
        strategies = await offers_service.get_pricing_strategies(mock_session)
        
        assert len(strategies) == 1
        assert strategies[0].id == TEST_PRICING_STRATEGY_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_strategy_by_id_found(self, offers_service, mock_session, mock_pricing_strategy):
        """Test getting pricing strategy by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_pricing_strategy, "scalar_one_or_none")
        
        strategy = await offers_service.get_pricing_strategy_by_id(mock_session, TEST_PRICING_STRATEGY_ID)
        
        assert strategy is not None
        assert strategy.id == TEST_PRICING_STRATEGY_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricing_strategy_by_id_not_found(self, offers_service, mock_session):
        """Test getting pricing strategy by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        strategy = await offers_service.get_pricing_strategy_by_id(mock_session, 999)
        
        assert strategy is None
        mock_session.execute.assert_called_once()


class TestOffersManager:
    """Tests for OffersManager class"""

    @pytest.mark.asyncio
    async def test_create_offer_success(
        self, offers_manager, mock_session, mock_seller, mock_product, mock_shop_point, mock_offer
    ):
        """Test successful offer creation"""
        offer_create = create_offer_create_schema()
        offers_manager.products_service.get_product_by_id = AsyncMock(return_value=mock_product)
        offers_manager.shop_points_service.get_shop_point_by_id = AsyncMock(return_value=mock_shop_point)
        offers_manager.service.create_offer = AsyncMock(return_value=mock_offer)
        
        with patch('app.offers.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await offers_manager.create_offer(
                mock_session, offer_create, mock_seller
            )
            
            assert result is not None
            assert isinstance(result, schemas.Offer)
            assert mock_verify.call_count == 2  # Verify product and shop point ownership
            offers_manager.service.create_offer.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_offer_product_not_found(self, offers_manager, mock_session, mock_seller):
        """Test offer creation when product not found"""
        offer_create = create_offer_create_schema()
        offers_manager.products_service.get_product_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await offers_manager.create_offer(mock_session, offer_create, mock_seller)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Product" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_offer_shop_point_not_found(
        self, offers_manager, mock_session, mock_seller, mock_product
    ):
        """Test offer creation when shop point not found"""
        offer_create = create_offer_create_schema()
        offers_manager.products_service.get_product_by_id = AsyncMock(return_value=mock_product)
        offers_manager.shop_points_service.get_shop_point_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await offers_manager.create_offer(mock_session, offer_create, mock_seller)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Shop point" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_offers(self, offers_manager, mock_session, mock_offer):
        """Test getting list of offers"""
        offers_list = [mock_offer]
        offers_manager.service.get_offers = AsyncMock(return_value=offers_list)
        
        result = await offers_manager.get_offers(mock_session)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.Offer)
        offers_manager.service.get_offers.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_offers_paginated(self, offers_manager, mock_session, mock_offer):
        """Test getting paginated offers"""
        offers_list = [mock_offer]
        offers_manager.service.get_offers_paginated = AsyncMock(return_value=(offers_list, 1))
        
        result = await offers_manager.get_offers_paginated(mock_session, page=1, page_size=10)
        
        assert result.pagination.total_items == 1
        assert len(result.items) == 1
        assert isinstance(result.items[0], schemas.Offer)
        offers_manager.service.get_offers_paginated.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offers_with_products(self, offers_manager, mock_session, mock_offer, mock_product):
        """Test getting offers with products"""
        mock_offer.product = mock_product
        offers_list = [mock_offer]
        offers_manager.service.get_offers_with_products = AsyncMock(return_value=offers_list)
        
        result = await offers_manager.get_offers_with_products(mock_session)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.OfferWithProduct)
        offers_manager.service.get_offers_with_products.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_offer_by_id_success(self, offers_manager, mock_session, mock_offer):
        """Test getting offer by ID - success"""
        offers_manager.service.get_offer_by_id = AsyncMock(return_value=mock_offer)
        
        result = await offers_manager.get_offer_by_id(mock_session, TEST_OFFER_ID)
        
        assert result is not None
        assert isinstance(result, schemas.Offer)
        offers_manager.service.get_offer_by_id.assert_called_once_with(mock_session, TEST_OFFER_ID)

    @pytest.mark.asyncio
    async def test_get_offer_by_id_not_found(self, offers_manager, mock_session):
        """Test getting offer by ID - not found"""
        offers_manager.service.get_offer_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await offers_manager.get_offer_by_id(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_offer_with_product_success(
        self, offers_manager, mock_session, mock_offer, mock_product
    ):
        """Test getting offer with product - success"""
        mock_offer.product = mock_product
        offers_manager.service.get_offer_with_product = AsyncMock(return_value=mock_offer)
        
        result = await offers_manager.get_offer_with_product(mock_session, TEST_OFFER_ID)
        
        assert result is not None
        assert isinstance(result, schemas.OfferWithProduct)
        assert result.product is not None

    @pytest.mark.asyncio
    async def test_get_offer_with_product_not_found(self, offers_manager, mock_session):
        """Test getting offer with product - not found"""
        offers_manager.service.get_offer_with_product = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await offers_manager.get_offer_with_product(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_offer_success(
        self, offers_manager, mock_session, mock_offer, mock_product, mock_seller
    ):
        """Test successful offer update"""
        offer_update = create_offer_update_schema()
        offers_manager.service.get_offer_by_id = AsyncMock(return_value=mock_offer)
        offers_manager.products_service.get_product_by_id = AsyncMock(return_value=mock_product)
        offers_manager.service.update_offer = AsyncMock(return_value=mock_offer)
        
        with patch('app.offers.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await offers_manager.update_offer(
                mock_session, TEST_OFFER_ID, offer_update, mock_seller
            )
            
            assert result is not None
            assert isinstance(result, schemas.Offer)
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            offers_manager.service.update_offer.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_offer_not_found(self, offers_manager, mock_session, mock_seller):
        """Test offer update when offer not found"""
        offer_update = create_offer_update_schema()
        offers_manager.service.get_offer_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await offers_manager.update_offer(
                mock_session, 999, offer_update, mock_seller
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_offer_success(
        self, offers_manager, mock_session, mock_offer, mock_product, mock_seller
    ):
        """Test successful offer deletion"""
        offers_manager.service.get_offer_by_id = AsyncMock(return_value=mock_offer)
        offers_manager.products_service.get_product_by_id = AsyncMock(return_value=mock_product)
        offers_manager.service.delete_offer = AsyncMock()
        
        with patch('app.offers.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            await offers_manager.delete_offer(mock_session, TEST_OFFER_ID, mock_seller)
            
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            offers_manager.service.delete_offer.assert_called_once_with(mock_session, TEST_OFFER_ID)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_offer_not_found(self, offers_manager, mock_session, mock_seller):
        """Test offer deletion when offer not found"""
        offers_manager.service.get_offer_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await offers_manager.delete_offer(mock_session, 999, mock_seller)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_pricing_strategies(self, offers_manager, mock_session, mock_pricing_strategy):
        """Test getting pricing strategies"""
        strategies_list = [mock_pricing_strategy]
        offers_manager.service.get_pricing_strategies = AsyncMock(return_value=strategies_list)
        
        result = await offers_manager.get_pricing_strategies(mock_session)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.PricingStrategy)
        offers_manager.service.get_pricing_strategies.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_pricing_strategy_by_id_success(
        self, offers_manager, mock_session, mock_pricing_strategy
    ):
        """Test getting pricing strategy by ID - success"""
        offers_manager.service.get_pricing_strategy_by_id = AsyncMock(return_value=mock_pricing_strategy)
        
        result = await offers_manager.get_pricing_strategy_by_id(mock_session, TEST_PRICING_STRATEGY_ID)
        
        assert result is not None
        assert isinstance(result, schemas.PricingStrategy)
        offers_manager.service.get_pricing_strategy_by_id.assert_called_once_with(
            mock_session, TEST_PRICING_STRATEGY_ID
        )

    @pytest.mark.asyncio
    async def test_get_pricing_strategy_by_id_not_found(self, offers_manager, mock_session):
        """Test getting pricing strategy by ID - not found"""
        offers_manager.service.get_pricing_strategy_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await offers_manager.get_pricing_strategy_by_id(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    def test_calculate_dynamic_price_no_strategy(self, offers_manager, mock_offer):
        """Test calculating dynamic price when no strategy"""
        mock_offer.pricing_strategy_id = None
        mock_offer.current_cost = TEST_CURRENT_COST
        
        price = offers_manager.calculate_dynamic_price(mock_offer)
        
        assert price == TEST_CURRENT_COST

    @pytest.mark.asyncio
    def test_calculate_dynamic_price_with_strategy(self, offers_manager, mock_offer, mock_pricing_strategy, mock_pricing_strategy_step):
        """Test calculating dynamic price with strategy"""
        expires_date = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=2)
        mock_offer.pricing_strategy_id = TEST_PRICING_STRATEGY_ID
        mock_offer.expires_date = expires_date
        mock_offer.original_cost = TEST_ORIGINAL_COST
        mock_offer.current_cost = None
        mock_offer.pricing_strategy = mock_pricing_strategy
        mock_pricing_strategy.steps = [mock_pricing_strategy_step]
        
        price = offers_manager.calculate_dynamic_price(mock_offer)
        
        assert price is not None
        assert price < TEST_ORIGINAL_COST  # Should have discount applied

    @pytest.mark.asyncio
    def test_calculate_dynamic_price_expired(self, offers_manager, mock_offer, mock_pricing_strategy):
        """Test calculating dynamic price when offer is expired"""
        expires_date = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=1)
        mock_offer.pricing_strategy_id = TEST_PRICING_STRATEGY_ID
        mock_offer.expires_date = expires_date
        mock_offer.original_cost = TEST_ORIGINAL_COST
        
        price = offers_manager.calculate_dynamic_price(mock_offer)
        
        assert price is None  # Expired offers return None
