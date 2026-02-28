"""
Unit tests for purchases domain
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException, status

from app.purchases.manager import PurchasesManager
from app.purchases.service import PurchasesService
from app.purchases.models import Purchase, PurchaseOffer, PurchaseOfferResult, PurchaseStatus
from app.purchases import schemas
from app.offers.models import Offer
from app.products.models import Product
from app.shop_points.models import ShopPoint
from app.sellers.models import Seller
from app.payments.models import PaymentStatus


# Constants
TEST_USER_ID = 1
TEST_PURCHASE_ID = 1
TEST_OFFER_ID = 1
TEST_OFFER_ID_2 = 2
TEST_PRODUCT_ID = 1
TEST_SHOP_ID = 1
TEST_SELLER_ID = 1
TEST_PAYMENT_ID = 1
TEST_TOTAL_COST = Decimal("100.00")
TEST_COST_PER_ITEM = Decimal("50.00")
TEST_QUANTITY = 2


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
    user = Mock()
    user.id = TEST_USER_ID
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_product():
    """Create a mock product"""
    product = Mock(spec=Product)
    product.id = TEST_PRODUCT_ID
    product.name = "Test Product"
    product.description = "Test description"
    return product


@pytest.fixture
def mock_offer(mock_product):
    """Create a mock offer"""
    offer = Mock(spec=Offer)
    offer.id = TEST_OFFER_ID
    offer.product_id = TEST_PRODUCT_ID
    offer.shop_id = TEST_SHOP_ID
    offer.pricing_strategy_id = None
    offer.expires_date = None
    offer.original_cost = None
    offer.current_cost = TEST_COST_PER_ITEM
    offer.count = 10
    offer.reserved_count = 0
    offer.product = mock_product
    return offer


@pytest.fixture
def mock_offer_2(mock_product):
    """Create a second mock offer"""
    offer = Mock(spec=Offer)
    offer.id = TEST_OFFER_ID_2
    offer.product_id = TEST_PRODUCT_ID
    offer.shop_id = TEST_SHOP_ID
    offer.pricing_strategy_id = None
    offer.expires_date = None
    offer.original_cost = None
    offer.current_cost = TEST_COST_PER_ITEM
    offer.count = 5
    offer.reserved_count = 0
    offer.product = mock_product
    return offer


@pytest.fixture
def mock_purchase():
    """Create a mock purchase"""
    purchase = Mock(spec=Purchase)
    purchase.id = TEST_PURCHASE_ID
    purchase.user_id = TEST_USER_ID
    purchase.status = PurchaseStatus.PENDING.value
    purchase.total_cost = TEST_TOTAL_COST
    purchase.created_at = datetime.now(timezone.utc)
    purchase.updated_at = datetime.now(timezone.utc)
    return purchase


@pytest.fixture
def mock_purchase_offer():
    """Create a mock purchase offer"""
    # Create a simple object that works with model_validate
    class MockPurchaseOffer:
        def __init__(self):
            self.purchase_id = TEST_PURCHASE_ID
            self.offer_id = TEST_OFFER_ID
            self.quantity = TEST_QUANTITY
            self.cost_at_purchase = TEST_COST_PER_ITEM
            self.fulfillment_status = None
            self.fulfilled_quantity = None
            self.fulfilled_by_seller_id = None
            self.unfulfilled_reason = None
    
    return MockPurchaseOffer()


@pytest.fixture
def mock_purchase_offer_result():
    """Create a mock purchase offer result"""
    result = Mock(spec=PurchaseOfferResult)
    result.id = 1
    result.purchase_id = TEST_PURCHASE_ID
    result.offer_id = TEST_OFFER_ID
    result.status = schemas.OfferProcessingStatus.SUCCESS.value
    result.requested_quantity = TEST_QUANTITY
    result.processed_quantity = TEST_QUANTITY
    result.available_quantity = None
    result.message = f"Successfully processed {TEST_QUANTITY} items for offer {TEST_OFFER_ID}"
    return result


@pytest.fixture
def mock_payment():
    """Create a mock payment"""
    payment = Mock()
    payment.id = TEST_PAYMENT_ID
    payment.purchase_id = TEST_PURCHASE_ID
    payment.status = PaymentStatus.SUCCEEDED.value
    return payment


@pytest.fixture
def purchases_service():
    """Create PurchasesService instance"""
    return PurchasesService()


@pytest.fixture
def purchases_manager():
    """Create PurchasesManager instance"""
    return PurchasesManager()


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


def create_purchase_create_schema(offer_ids: List[int] = None, quantities: List[int] = None) -> schemas.PurchaseCreate:
    """Create PurchaseCreate schema"""
    if offer_ids is None:
        offer_ids = [TEST_OFFER_ID]
    if quantities is None:
        quantities = [TEST_QUANTITY]
    
    offers = [
        schemas.PurchaseOfferCreate(offer_id=offer_id, quantity=quantity)
        for offer_id, quantity in zip(offer_ids, quantities)
    ]
    return schemas.PurchaseCreate(offers=offers)


def create_purchase_update_schema(status: Optional[str] = None) -> schemas.PurchaseUpdate:
    """Create PurchaseUpdate schema"""
    return schemas.PurchaseUpdate(status=status)


class TestPurchasesService:
    """Tests for PurchasesService class"""

    @pytest.mark.asyncio
    async def test_create_purchase(self, purchases_service, mock_session, mock_purchase):
        """Test creating purchase"""
        mock_session.execute.return_value = create_mock_execute_result(mock_purchase)
        
        purchase = await purchases_service.create_purchase(
            mock_session, TEST_USER_ID, TEST_TOTAL_COST
        )
        
        assert purchase is not None
        assert purchase.id == TEST_PURCHASE_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_purchase_without_total_cost(self, purchases_service, mock_session, mock_purchase):
        """Test creating purchase without total cost"""
        mock_session.execute.return_value = create_mock_execute_result(mock_purchase)
        
        purchase = await purchases_service.create_purchase(mock_session, TEST_USER_ID)
        
        assert purchase is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_purchase_offers(self, purchases_service, mock_session, mock_purchase_offer):
        """Test creating purchase offers"""
        offers_data = [
            {
                "offer_id": TEST_OFFER_ID,
                "quantity": TEST_QUANTITY,
                "cost_at_purchase": TEST_COST_PER_ITEM
            }
        ]
        mock_session.execute.return_value = create_mock_scalars_result([mock_purchase_offer])
        
        purchase_offers = await purchases_service.create_purchase_offers(
            mock_session, TEST_PURCHASE_ID, offers_data
        )
        
        assert len(purchase_offers) == 1
        assert purchase_offers[0].offer_id == TEST_OFFER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_purchase_offers_empty_list(self, purchases_service, mock_session):
        """Test creating purchase offers with empty list"""
        purchase_offers = await purchases_service.create_purchase_offers(
            mock_session, TEST_PURCHASE_ID, []
        )
        
        assert len(purchase_offers) == 0
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_purchase_by_id_found(self, purchases_service, mock_session, mock_purchase):
        """Test getting purchase by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_purchase, "scalar_one_or_none")
        
        purchase = await purchases_service.get_purchase_by_id(mock_session, TEST_PURCHASE_ID)
        
        assert purchase is not None
        assert purchase.id == TEST_PURCHASE_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_purchase_by_id_not_found(self, purchases_service, mock_session):
        """Test getting purchase by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        purchase = await purchases_service.get_purchase_by_id(mock_session, 999)
        
        assert purchase is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_purchase_by_id_for_update(self, purchases_service, mock_session, mock_purchase):
        """Test getting purchase by ID with FOR UPDATE lock"""
        mock_session.execute.return_value = create_mock_execute_result(mock_purchase, "scalar_one_or_none")
        
        purchase = await purchases_service.get_purchase_by_id_for_update(mock_session, TEST_PURCHASE_ID)
        
        assert purchase is not None
        assert purchase.id == TEST_PURCHASE_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_purchase_offers_by_purchase_id(self, purchases_service, mock_session, mock_purchase_offer):
        """Test getting purchase offers by purchase ID"""
        mock_session.execute.return_value = create_mock_scalars_result([mock_purchase_offer])
        
        purchase_offers = await purchases_service.get_purchase_offers_by_purchase_id(
            mock_session, TEST_PURCHASE_ID
        )
        
        assert len(purchase_offers) == 1
        assert purchase_offers[0].purchase_id == TEST_PURCHASE_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_purchases_by_user(self, purchases_service, mock_session, mock_purchase):
        """Test getting purchases by user ID"""
        mock_session.execute.return_value = create_mock_scalars_result([mock_purchase])
        
        purchases = await purchases_service.get_purchases_by_user(mock_session, TEST_USER_ID)
        
        assert len(purchases) == 1
        assert purchases[0].user_id == TEST_USER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_purchases_by_user_empty(self, purchases_service, mock_session):
        """Test getting purchases by user ID - empty list"""
        mock_session.execute.return_value = create_mock_scalars_result([])
        
        purchases = await purchases_service.get_purchases_by_user(mock_session, TEST_USER_ID)
        
        assert len(purchases) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_purchases_paginated(self, purchases_service, mock_session, mock_purchase):
        """Test getting paginated purchases"""
        mock_count_result = create_mock_scalar_result(1)
        mock_purchases_result = create_mock_scalars_result([mock_purchase])
        
        def execute_side_effect(*args, **kwargs):
            # First call is count query, second is data query
            if mock_session.execute.call_count == 1:
                return mock_count_result
            return mock_purchases_result
        
        mock_session.execute.side_effect = execute_side_effect
        
        purchases, total_count = await purchases_service.get_purchases_paginated(
            mock_session, page=1, page_size=10
        )
        
        assert len(purchases) == 1
        assert total_count == 1
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_purchases_paginated_with_filters(
        self, purchases_service, mock_session, mock_purchase
    ):
        """Test getting paginated purchases with filters"""
        mock_count_result = create_mock_scalar_result(1)
        mock_purchases_result = create_mock_scalars_result([mock_purchase])
        
        def execute_side_effect(*args, **kwargs):
            if mock_session.execute.call_count == 1:
                return mock_count_result
            return mock_purchases_result
        
        mock_session.execute.side_effect = execute_side_effect
        
        min_created_at = datetime.now(timezone.utc) - timedelta(days=1)
        max_created_at = datetime.now(timezone.utc)
        
        purchases, total_count = await purchases_service.get_purchases_paginated(
            mock_session,
            page=1,
            page_size=10,
            status=PurchaseStatus.PENDING.value,
            user_id=TEST_USER_ID,
            min_created_at=min_created_at,
            max_created_at=max_created_at
        )
        
        assert len(purchases) == 1
        assert total_count == 1

    @pytest.mark.asyncio
    async def test_get_seller_purchases_paginated(
        self, purchases_service, mock_session, mock_purchase, mock_purchase_offer, mock_offer
    ):
        """Test getting paginated purchases for seller."""
        mock_purchase_offer.offer = mock_offer

        mock_count_result = create_mock_scalar_result(1)
        mock_purchase_ids_result = Mock()
        mock_purchase_ids_result.all.return_value = [(TEST_PURCHASE_ID,)]
        mock_purchases_result = create_mock_scalars_result([mock_purchase])
        mock_purchase_offers_result = create_mock_scalars_result([mock_purchase_offer])

        mock_session.execute.side_effect = [
            mock_count_result,
            mock_purchase_ids_result,
            mock_purchases_result,
            mock_purchase_offers_result,
        ]

        purchases, total_count, purchase_offers_map = await purchases_service.get_seller_purchases_paginated(
            session=mock_session,
            seller_id=TEST_SELLER_ID,
            page=1,
            page_size=10,
            status=PurchaseStatus.PENDING.value,
            fulfillment_status="unprocessed",
        )

        assert total_count == 1
        assert len(purchases) == 1
        assert purchases[0].id == TEST_PURCHASE_ID
        assert TEST_PURCHASE_ID in purchase_offers_map
        assert len(purchase_offers_map[TEST_PURCHASE_ID]) == 1

    @pytest.mark.asyncio
    async def test_get_seller_purchases_paginated_empty_page(
        self, purchases_service, mock_session
    ):
        """Test getting paginated purchases for seller with no records on page."""
        mock_count_result = create_mock_scalar_result(0)
        mock_purchase_ids_result = Mock()
        mock_purchase_ids_result.all.return_value = []

        mock_session.execute.side_effect = [
            mock_count_result,
            mock_purchase_ids_result,
        ]

        purchases, total_count, purchase_offers_map = await purchases_service.get_seller_purchases_paginated(
            session=mock_session,
            seller_id=TEST_SELLER_ID,
            page=1,
            page_size=10,
        )

        assert total_count == 0
        assert purchases == []
        assert purchase_offers_map == {}

    @pytest.mark.asyncio
    async def test_get_pending_purchase_by_user_found(
        self, purchases_service, mock_session, mock_purchase
    ):
        """Test getting pending purchase by user - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_purchase, "scalar_one_or_none")
        
        purchase = await purchases_service.get_pending_purchase_by_user(mock_session, TEST_USER_ID)
        
        assert purchase is not None
        assert purchase.status == PurchaseStatus.PENDING.value
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_purchase_by_user_not_found(self, purchases_service, mock_session):
        """Test getting pending purchase by user - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        purchase = await purchases_service.get_pending_purchase_by_user(mock_session, TEST_USER_ID)
        
        assert purchase is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_purchase_by_user_for_update(
        self, purchases_service, mock_session, mock_purchase
    ):
        """Test getting pending purchase by user with FOR UPDATE lock"""
        mock_session.execute.return_value = create_mock_execute_result(mock_purchase, "scalar_one_or_none")
        
        purchase = await purchases_service.get_pending_purchase_by_user(
            mock_session, TEST_USER_ID, for_update=True
        )
        
        assert purchase is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_purchase_status(self, purchases_service, mock_session, mock_purchase):
        """Test updating purchase status"""
        updated_purchase = Mock(spec=Purchase)
        updated_purchase.id = TEST_PURCHASE_ID
        updated_purchase.status = PurchaseStatus.CONFIRMED.value
        
        mock_session.execute.return_value = create_mock_execute_result(updated_purchase)
        
        result = await purchases_service.update_purchase_status(
            mock_session, TEST_PURCHASE_ID, PurchaseStatus.CONFIRMED.value
        )
        
        assert result.status == PurchaseStatus.CONFIRMED.value
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_purchase(self, purchases_service, mock_session):
        """Test deleting purchase"""
        mock_session.execute.return_value = None
        
        await purchases_service.delete_purchase(mock_session, TEST_PURCHASE_ID)
        
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_purchase_offer_results(
        self, purchases_service, mock_session, mock_purchase_offer_result
    ):
        """Test creating purchase offer results"""
        results_data = [
            {
                "offer_id": TEST_OFFER_ID,
                "status": schemas.OfferProcessingStatus.SUCCESS.value,
                "requested_quantity": TEST_QUANTITY,
                "processed_quantity": TEST_QUANTITY,
                "message": "Success"
            }
        ]
        mock_session.execute.return_value = create_mock_scalars_result([mock_purchase_offer_result])
        
        results = await purchases_service.create_purchase_offer_results(
            mock_session, TEST_PURCHASE_ID, results_data
        )
        
        assert len(results) == 1
        assert results[0].offer_id == TEST_OFFER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_purchase_offer_results_by_purchase_id(
        self, purchases_service, mock_session, mock_purchase_offer_result
    ):
        """Test getting purchase offer results by purchase ID"""
        mock_session.execute.return_value = create_mock_scalars_result([mock_purchase_offer_result])
        
        results = await purchases_service.get_purchase_offer_results_by_purchase_id(
            mock_session, TEST_PURCHASE_ID
        )
        
        assert len(results) == 1
        assert results[0].purchase_id == TEST_PURCHASE_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_purchase_offer_fulfillment(
        self, purchases_service, mock_session, mock_purchase_offer
    ):
        """Test updating purchase offer fulfillment"""
        updated_po = Mock(spec=PurchaseOffer)
        updated_po.purchase_id = TEST_PURCHASE_ID
        updated_po.offer_id = TEST_OFFER_ID
        updated_po.fulfillment_status = "fulfilled"
        updated_po.fulfilled_quantity = TEST_QUANTITY
        
        mock_session.execute.return_value = create_mock_execute_result(updated_po)
        
        result = await purchases_service.update_purchase_offer_fulfillment(
            mock_session,
            TEST_PURCHASE_ID,
            TEST_OFFER_ID,
            "fulfilled",
            TEST_QUANTITY,
            TEST_SELLER_ID
        )
        
        assert result.fulfillment_status == "fulfilled"
        assert result.fulfilled_quantity == TEST_QUANTITY
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_all_offers_fulfilled_true(
        self, purchases_service, mock_session, mock_purchase_offer
    ):
        """Test checking if all offers are fulfilled - true"""
        mock_purchase_offer.fulfillment_status = "fulfilled"
        mock_purchase_offer.fulfilled_quantity = TEST_QUANTITY  # fulfilled_quantity == quantity
        mock_session.execute.side_effect = [
            create_mock_scalars_result([mock_purchase_offer])  # All offers
        ]
        
        result = await purchases_service.check_all_offers_fulfilled(mock_session, TEST_PURCHASE_ID)
        
        assert result is True
        assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_check_all_offers_fulfilled_false(
        self, purchases_service, mock_session, mock_purchase_offer
    ):
        """Test checking if all offers are fulfilled - false"""
        mock_purchase_offer.fulfillment_status = None
        mock_purchase_offer.fulfilled_quantity = None
        mock_session.execute.side_effect = [
            create_mock_scalars_result([mock_purchase_offer])  # All offers
        ]
        
        result = await purchases_service.check_all_offers_fulfilled(mock_session, TEST_PURCHASE_ID)
        
        assert result is False
        assert mock_session.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_check_all_offers_fulfilled_partial_quantity(
        self, purchases_service, mock_session, mock_purchase_offer
    ):
        """Test checking if all offers are fulfilled - false when fulfilled_quantity < quantity"""
        mock_purchase_offer.fulfillment_status = "fulfilled"
        mock_purchase_offer.fulfilled_quantity = TEST_QUANTITY - 1  # Less than requested
        mock_session.execute.side_effect = [
            create_mock_scalars_result([mock_purchase_offer])  # All offers
        ]
        
        result = await purchases_service.check_all_offers_fulfilled(mock_session, TEST_PURCHASE_ID)
        
        assert result is False
        assert mock_session.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_check_all_offers_fulfilled_not_fulfilled_status(
        self, purchases_service, mock_session, mock_purchase_offer
    ):
        """Test checking if all offers are fulfilled - false when status is 'not_fulfilled'"""
        mock_purchase_offer.fulfillment_status = "not_fulfilled"
        mock_purchase_offer.fulfilled_quantity = TEST_QUANTITY
        mock_session.execute.side_effect = [
            create_mock_scalars_result([mock_purchase_offer])  # All offers
        ]
        
        result = await purchases_service.check_all_offers_fulfilled(mock_session, TEST_PURCHASE_ID)
        
        assert result is False
        assert mock_session.execute.call_count == 1


class TestPurchasesManager:
    """Tests for PurchasesManager class"""

    @pytest.mark.asyncio
    async def test_get_purchase_by_id_success(
        self, purchases_manager, mock_session, mock_purchase, mock_purchase_offer, mock_offer, mock_purchase_offer_result
    ):
        """Test getting purchase by ID - success"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.get_purchase_offers_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer]
        )
        purchases_manager.offers_service.get_offers_by_ids = AsyncMock(return_value=[mock_offer])
        purchases_manager.service.get_purchase_offer_results_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer_result]
        )
        
        result = await purchases_manager.get_purchase_by_id(mock_session, TEST_PURCHASE_ID)
        
        assert result is not None
        assert isinstance(result, schemas.PurchaseWithOffers)
        assert result.id == TEST_PURCHASE_ID
        purchases_manager.service.get_purchase_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_purchase_by_id_not_found(self, purchases_manager, mock_session):
        """Test getting purchase by ID - not found"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.get_purchase_by_id(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_pending_purchase_by_user_success(
        self, purchases_manager, mock_session, mock_purchase, mock_purchase_offer, mock_offer, mock_purchase_offer_result
    ):
        """Test getting pending purchase by user - success"""
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.get_purchase_offers_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer]
        )
        purchases_manager.offers_service.get_offers_by_ids = AsyncMock(return_value=[mock_offer])
        purchases_manager.service.get_purchase_offer_results_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer_result]
        )
        
        result = await purchases_manager.get_pending_purchase_by_user(mock_session, TEST_USER_ID)
        
        assert result is not None
        assert isinstance(result, schemas.PurchaseWithOffers)
        assert result.status == PurchaseStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_get_pending_purchase_by_user_not_found(self, purchases_manager, mock_session):
        """Test getting pending purchase by user - not found"""
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.get_pending_purchase_by_user(mock_session, TEST_USER_ID)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_purchases_by_user(
        self, purchases_manager, mock_session, mock_purchase
    ):
        """Test getting purchases by user"""
        purchases_manager.service.get_purchases_by_user = AsyncMock(return_value=[mock_purchase])
        
        result = await purchases_manager.get_purchases_by_user(mock_session, TEST_USER_ID)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.Purchase)
        assert result[0].user_id == TEST_USER_ID

    @pytest.mark.asyncio
    async def test_get_purchases_paginated(
        self, purchases_manager, mock_session, mock_purchase
    ):
        """Test getting paginated purchases"""
        purchases_manager.service.get_purchases_paginated = AsyncMock(
            return_value=([mock_purchase], 1)
        )
        
        result = await purchases_manager.get_purchases_paginated(
            mock_session, page=1, page_size=10
        )
        
        assert result.pagination.total_items == 1
        assert len(result.items) == 1
        assert isinstance(result.items[0], schemas.Purchase)

    @pytest.mark.asyncio
    async def test_get_seller_purchases_paginated(
        self, purchases_manager, mock_session, mock_purchase, mock_purchase_offer, mock_offer
    ):
        """Test getting seller purchases with purchase items."""
        mock_purchase_offer.offer = mock_offer
        purchases_manager.service.get_seller_purchases_paginated = AsyncMock(
            return_value=([mock_purchase], 1, {TEST_PURCHASE_ID: [mock_purchase_offer]})
        )

        result = await purchases_manager.get_seller_purchases_paginated(
            session=mock_session,
            seller_id=TEST_SELLER_ID,
            page=1,
            page_size=10,
            purchase_status=PurchaseStatus.PENDING.value,
        )

        assert result.pagination.total_items == 1
        assert len(result.items) == 1
        assert isinstance(result.items[0], schemas.PurchaseWithOffers)
        assert result.items[0].id == TEST_PURCHASE_ID
        assert len(result.items[0].purchase_offers) == 1

    @pytest.mark.asyncio
    async def test_update_purchase_status_success(
        self, purchases_manager, mock_session, mock_purchase
    ):
        """Test updating purchase status - success"""
        updated_purchase = Mock(spec=Purchase)
        updated_purchase.id = TEST_PURCHASE_ID
        updated_purchase.status = PurchaseStatus.CONFIRMED.value
        updated_purchase.user_id = TEST_USER_ID
        updated_purchase.total_cost = TEST_TOTAL_COST
        updated_purchase.created_at = datetime.now(timezone.utc)
        updated_purchase.updated_at = datetime.now(timezone.utc)
        
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.update_purchase_status = AsyncMock(return_value=updated_purchase)
        
        status_data = create_purchase_update_schema(PurchaseStatus.CONFIRMED.value)
        result = await purchases_manager.update_purchase_status(
            mock_session, TEST_PURCHASE_ID, status_data
        )
        
        assert result.status == PurchaseStatus.CONFIRMED.value
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_purchase_status_not_found(self, purchases_manager, mock_session):
        """Test updating purchase status - purchase not found"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=None)
        
        status_data = create_purchase_update_schema(PurchaseStatus.CONFIRMED.value)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.update_purchase_status(
                mock_session, 999, status_data
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_purchase_status_invalid_status(
        self, purchases_manager, mock_session, mock_purchase
    ):
        """Test updating purchase status - invalid status"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        
        status_data = create_purchase_update_schema("invalid_status")
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.update_purchase_status(
                mock_session, TEST_PURCHASE_ID, status_data
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_update_purchase_status_cancelled_releases_reservations(
        self, purchases_manager, mock_session, mock_purchase, mock_purchase_offer
    ):
        """Test updating purchase status to cancelled releases reservations"""
        updated_purchase = Mock(spec=Purchase)
        updated_purchase.id = TEST_PURCHASE_ID
        updated_purchase.status = PurchaseStatus.CANCELLED.value
        updated_purchase.user_id = TEST_USER_ID
        updated_purchase.total_cost = TEST_TOTAL_COST
        updated_purchase.created_at = datetime.now(timezone.utc)
        updated_purchase.updated_at = datetime.now(timezone.utc)
        
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.get_purchase_offers_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer]
        )
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(return_value=[])
        purchases_manager.offers_service.update_offer_reserved_count = AsyncMock()
        purchases_manager.service.update_purchase_status = AsyncMock(return_value=updated_purchase)
        
        status_data = create_purchase_update_schema(PurchaseStatus.CANCELLED.value)
        result = await purchases_manager.update_purchase_status(
            mock_session, TEST_PURCHASE_ID, status_data
        )
        
        assert result.status == PurchaseStatus.CANCELLED.value
        purchases_manager.offers_service.update_offer_reserved_count.assert_called()

    @pytest.mark.asyncio
    async def test_delete_purchase_success(
        self, purchases_manager, mock_session, mock_purchase
    ):
        """Test deleting purchase - success"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.get_purchase_offers_by_purchase_id = AsyncMock(return_value=[])
        purchases_manager.service.delete_purchase = AsyncMock()
        
        await purchases_manager.delete_purchase(mock_session, TEST_PURCHASE_ID)
        
        purchases_manager.service.delete_purchase.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_purchase_not_found(self, purchases_manager, mock_session):
        """Test deleting purchase - not found"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.delete_purchase(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_purchase_releases_reservations(
        self, purchases_manager, mock_session, mock_purchase, mock_purchase_offer
    ):
        """Test deleting purchase releases reservations if pending"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.get_purchase_offers_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer]
        )
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(return_value=[])
        purchases_manager.offers_service.update_offer_reserved_count = AsyncMock()
        purchases_manager.service.delete_purchase = AsyncMock()
        
        await purchases_manager.delete_purchase(mock_session, TEST_PURCHASE_ID)
        
        purchases_manager.offers_service.update_offer_reserved_count.assert_called()
        purchases_manager.service.delete_purchase.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_order_token_success(
        self, purchases_manager, mock_session, mock_purchase, mock_payment
    ):
        """Test generating order token - success"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        purchases_manager.jwt_utils.create_order_token = Mock(return_value="test_token")
        
        result = await purchases_manager.generate_order_token(
            mock_session, TEST_PURCHASE_ID, TEST_USER_ID
        )
        
        assert result.token == "test_token"
        assert result.order_id == TEST_PURCHASE_ID
        purchases_manager.jwt_utils.create_order_token.assert_called_once_with(TEST_PURCHASE_ID)

    @pytest.mark.asyncio
    async def test_generate_order_token_purchase_not_found(self, purchases_manager, mock_session):
        """Test generating order token - purchase not found"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.generate_order_token(
                mock_session, 999, TEST_USER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_order_token_wrong_user(
        self, purchases_manager, mock_session, mock_purchase
    ):
        """Test generating order token - wrong user"""
        mock_purchase.user_id = 999
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.generate_order_token(
                mock_session, TEST_PURCHASE_ID, TEST_USER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_generate_order_token_no_payment(
        self, purchases_manager, mock_session, mock_purchase
    ):
        """Test generating order token - no payment"""
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=None
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.generate_order_token(
                mock_session, TEST_PURCHASE_ID, TEST_USER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_generate_order_token_not_paid(
        self, purchases_manager, mock_session, mock_purchase, mock_payment
    ):
        """Test generating order token - payment not succeeded"""
        mock_payment.status = PaymentStatus.PENDING.value
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.generate_order_token(
                mock_session, TEST_PURCHASE_ID, TEST_USER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_verify_purchase_token_success(
        self, purchases_manager, mock_session, mock_purchase, mock_payment, mock_purchase_offer, mock_offer
    ):
        """Test verifying purchase token - success"""
        payload = {"order_id": TEST_PURCHASE_ID}
        purchases_manager.jwt_utils.verify_order_token = Mock(return_value=payload)
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        purchases_manager.service.get_purchase_offers_by_seller_and_purchase = AsyncMock(
            return_value=[mock_purchase_offer]
        )
        mock_purchase_offer.offer = mock_offer
        # mock_offer already has product from fixture
        
        result = await purchases_manager.verify_purchase_token(
            mock_session, "test_token", TEST_SELLER_ID
        )
        
        assert result.purchase_id == TEST_PURCHASE_ID
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_verify_purchase_token_invalid_token(self, purchases_manager, mock_session):
        """Test verifying purchase token - invalid token"""
        purchases_manager.jwt_utils.verify_order_token = Mock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.verify_purchase_token(
                mock_session, "invalid_token", TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_verify_purchase_token_no_order_id(
        self, purchases_manager, mock_session
    ):
        """Test verifying purchase token - no order_id in payload"""
        payload = {"some_other_key": "value"}  # Payload exists but no order_id
        purchases_manager.jwt_utils.verify_order_token = Mock(return_value=payload)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.verify_purchase_token(
                mock_session, "test_token", TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_verify_purchase_token_purchase_not_found(
        self, purchases_manager, mock_session
    ):
        """Test verifying purchase token - purchase not found"""
        payload = {"order_id": 999}
        purchases_manager.jwt_utils.verify_order_token = Mock(return_value=payload)
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.verify_purchase_token(
                mock_session, "test_token", TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_verify_purchase_token_not_paid(
        self, purchases_manager, mock_session, mock_purchase, mock_payment
    ):
        """Test verifying purchase token - payment not succeeded"""
        payload = {"order_id": TEST_PURCHASE_ID}
        mock_payment.status = PaymentStatus.PENDING.value
        purchases_manager.jwt_utils.verify_order_token = Mock(return_value=payload)
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.verify_purchase_token(
                mock_session, "test_token", TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_purchase_success(
        self, purchases_manager, mock_session, mock_offer, mock_purchase, mock_purchase_offer, mock_purchase_offer_result
    ):
        """Test creating purchase - success"""
        purchase_data = create_purchase_create_schema()
        
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(
            return_value=[mock_offer]
        )
        purchases_manager.offers_manager.calculate_dynamic_price = Mock(return_value=TEST_COST_PER_ITEM)
        purchases_manager.offers_service.update_offer_reserved_count = AsyncMock()
        purchases_manager.service.create_purchase = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.create_purchase_offers = AsyncMock(return_value=[mock_purchase_offer])
        purchases_manager.service.create_purchase_offer_results = AsyncMock(return_value=[mock_purchase_offer_result])
        purchases_manager.payments_manager.create_payment_for_purchase = AsyncMock()
        purchases_manager.offers_service.get_offers_by_ids = AsyncMock(return_value=[mock_offer])
        purchases_manager.service.get_purchase_offer_results_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer_result]
        )
        
        with patch('app.purchases.manager.check_purchase_expiration') as mock_celery_task:
            result = await purchases_manager.create_purchase(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
            
            assert result is not None
            assert isinstance(result, schemas.PurchaseWithOffers)
            assert result.id == TEST_PURCHASE_ID
            purchases_manager.service.create_purchase.assert_called_once()
            purchases_manager.offers_service.update_offer_reserved_count.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_purchase_empty_offers(self, purchases_manager, mock_session):
        """Test creating purchase - empty offers list"""
        # Create purchase data with empty offers list bypassing Pydantic validation
        purchase_data = schemas.PurchaseCreate.model_construct(offers=[])
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.create_purchase(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "at least one offer" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_purchase_existing_pending(
        self, purchases_manager, mock_session, mock_purchase
    ):
        """Test creating purchase - user already has pending purchase"""
        purchase_data = create_purchase_create_schema()
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=mock_purchase)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.create_purchase(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
        
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "pending purchase" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_purchase_offer_not_found(
        self, purchases_manager, mock_session, mock_offer
    ):
        """Test creating purchase - offer not found"""
        purchase_data = create_purchase_create_schema()
        
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(return_value=[])
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.create_purchase(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_purchase_offer_expired(
        self, purchases_manager, mock_session, mock_offer
    ):
        """Test creating purchase - offer expired"""
        purchase_data = create_purchase_create_schema()
        mock_offer.expires_date = datetime.now(timezone.utc) - timedelta(hours=1)
        
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(
            return_value=[mock_offer]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.create_purchase(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_purchase_insufficient_quantity(
        self, purchases_manager, mock_session, mock_offer
    ):
        """Test creating purchase - insufficient quantity"""
        purchase_data = create_purchase_create_schema(quantities=[100])  # Request more than available
        
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(
            return_value=[mock_offer]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.create_purchase(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "insufficient" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_purchase_cannot_calculate_price(
        self, purchases_manager, mock_session, mock_offer
    ):
        """Test creating purchase - cannot calculate price"""
        purchase_data = create_purchase_create_schema()
        
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(
            return_value=[mock_offer]
        )
        purchases_manager.offers_manager.calculate_dynamic_price = Mock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.create_purchase(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "calculate price" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_success(
        self, purchases_manager, mock_session, mock_offer, mock_purchase, mock_purchase_offer, mock_purchase_offer_result
    ):
        """Test creating purchase with partial success - success"""
        purchase_data = create_purchase_create_schema()
        
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(
            return_value=[mock_offer]
        )
        purchases_manager.offers_manager.calculate_dynamic_price = Mock(return_value=TEST_COST_PER_ITEM)
        purchases_manager.offers_service.update_offer_reserved_count = AsyncMock()
        purchases_manager.service.create_purchase = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.create_purchase_offers = AsyncMock(return_value=[mock_purchase_offer])
        purchases_manager.service.create_purchase_offer_results = AsyncMock(return_value=[mock_purchase_offer_result])
        purchases_manager.payments_manager.create_payment_for_purchase = AsyncMock()
        purchases_manager.offers_service.get_offers_by_ids = AsyncMock(return_value=[mock_offer])
        purchases_manager.service.get_purchase_offer_results_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer_result]
        )
        
        with patch('app.purchases.manager.check_purchase_expiration') as mock_celery_task:
            result = await purchases_manager.create_purchase_with_partial_success(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
            
            assert result is not None
            assert isinstance(result, schemas.PurchaseCreateResponse)
            assert result.purchase.id == TEST_PURCHASE_ID
            assert result.total_processed == 1
            assert result.total_failed == 0

    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_no_offers_processed(
        self, purchases_manager, mock_session, mock_offer
    ):
        """Test creating purchase with partial success - no offers processed"""
        purchase_data = create_purchase_create_schema()
        mock_offer.count = 0
        mock_offer.reserved_count = 0
        
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(
            return_value=[mock_offer]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.create_purchase_with_partial_success(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "no offers could be processed" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_partial_quantity(
        self, purchases_manager, mock_session, mock_offer, mock_purchase, mock_purchase_offer, mock_purchase_offer_result
    ):
        """Test creating purchase with partial success - partial quantity available"""
        purchase_data = create_purchase_create_schema(quantities=[10])  # Request 10, but only 5 available
        mock_offer.count = 5
        mock_offer.reserved_count = 0
        
        purchases_manager.service.get_pending_purchase_by_user = AsyncMock(return_value=None)
        purchases_manager.offers_service.get_offers_by_ids_for_update = AsyncMock(
            return_value=[mock_offer]
        )
        purchases_manager.offers_manager.calculate_dynamic_price = Mock(return_value=TEST_COST_PER_ITEM)
        purchases_manager.offers_service.update_offer_reserved_count = AsyncMock()
        purchases_manager.service.create_purchase = AsyncMock(return_value=mock_purchase)
        purchases_manager.service.create_purchase_offers = AsyncMock(return_value=[mock_purchase_offer])
        purchases_manager.service.create_purchase_offer_results = AsyncMock(return_value=[mock_purchase_offer_result])
        purchases_manager.payments_manager.create_payment_for_purchase = AsyncMock()
        purchases_manager.offers_service.get_offers_by_ids = AsyncMock(return_value=[mock_offer])
        purchases_manager.service.get_purchase_offer_results_by_purchase_id = AsyncMock(
            return_value=[mock_purchase_offer_result]
        )
        
        with patch('app.purchases.manager.check_purchase_expiration') as mock_celery_task:
            result = await purchases_manager.create_purchase_with_partial_success(
                mock_session, TEST_USER_ID, purchase_data, "http://test.com"
            )
            
            assert result is not None
            assert result.total_processed == 1
            # Should process 5 items (available) instead of 10 (requested)

    @pytest.mark.asyncio
    async def test_fulfill_order_items_success(
        self, purchases_manager, mock_session, mock_purchase, mock_payment, mock_purchase_offer, mock_offer
    ):
        """Test fulfilling order items - success"""
        fulfillment_data = schemas.OrderFulfillmentRequest(
            items=[
                schemas.PurchaseOfferFulfillmentStatus(
                    purchase_offer_id=TEST_OFFER_ID,
                    offer_id=TEST_OFFER_ID,
                    status="fulfilled",
                    fulfilled_quantity=TEST_QUANTITY
                )
            ]
        )
        
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        
        # Mock shop points query
        mock_shop_point_result = Mock()
        mock_shop_point_result.all.return_value = [(TEST_SHOP_ID,)]
        mock_session.execute.return_value = mock_shop_point_result
        
        # Mock offers query
        mock_offer_result = Mock()
        mock_offer_result.all.return_value = [(TEST_OFFER_ID,)]
        mock_session.execute.side_effect = [mock_shop_point_result, mock_offer_result]
        
        # Mock purchase offer query
        mock_po_result = Mock()
        mock_po_result.scalar_one_or_none.return_value = mock_purchase_offer
        mock_session.execute.side_effect = [
            mock_shop_point_result,
            mock_offer_result,
            mock_po_result
        ]
        
        updated_po = Mock(spec=PurchaseOffer)
        updated_po.purchase_id = TEST_PURCHASE_ID
        updated_po.offer_id = TEST_OFFER_ID
        updated_po.fulfillment_status = "fulfilled"
        updated_po.fulfilled_quantity = TEST_QUANTITY
        
        purchases_manager.service.update_purchase_offer_fulfillment = AsyncMock(return_value=updated_po)
        purchases_manager.service.check_all_offers_fulfilled = AsyncMock(return_value=True)
        purchases_manager.service.update_purchase_status = AsyncMock()
        
        result = await purchases_manager.fulfill_order_items(
            mock_session, TEST_PURCHASE_ID, fulfillment_data, TEST_SELLER_ID
        )
        
        assert result is not None
        assert isinstance(result, schemas.OrderFulfillmentResponse)
        assert len(result.fulfilled_items) == 1

    @pytest.mark.asyncio
    async def test_fulfill_order_items_purchase_not_found(self, purchases_manager, mock_session):
        """Test fulfilling order items - purchase not found"""
        fulfillment_data = schemas.OrderFulfillmentRequest(
            items=[
                schemas.PurchaseOfferFulfillmentStatus(
                    purchase_offer_id=TEST_OFFER_ID,
                    offer_id=TEST_OFFER_ID,
                    status="fulfilled",
                    fulfilled_quantity=TEST_QUANTITY
                )
            ]
        )
        
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.fulfill_order_items(
                mock_session, 999, fulfillment_data, TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_fulfill_order_items_not_paid(
        self, purchases_manager, mock_session, mock_purchase, mock_payment
    ):
        """Test fulfilling order items - purchase not paid"""
        fulfillment_data = schemas.OrderFulfillmentRequest(
            items=[
                schemas.PurchaseOfferFulfillmentStatus(
                    purchase_offer_id=TEST_OFFER_ID,
                    offer_id=TEST_OFFER_ID,
                    status="fulfilled",
                    fulfilled_quantity=TEST_QUANTITY
                )
            ]
        )
        
        mock_payment.status = PaymentStatus.PENDING.value
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.fulfill_order_items(
                mock_session, TEST_PURCHASE_ID, fulfillment_data, TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "not paid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_fulfill_order_items_offer_not_found(
        self, purchases_manager, mock_session, mock_purchase, mock_payment
    ):
        """Test fulfilling order items - purchase offer not found"""
        fulfillment_data = schemas.OrderFulfillmentRequest(
            items=[
                schemas.PurchaseOfferFulfillmentStatus(
                    purchase_offer_id=999,
                    offer_id=999,
                    status="fulfilled",
                    fulfilled_quantity=TEST_QUANTITY
                )
            ]
        )
        
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        
        # Mock shop points query
        mock_shop_point_result = Mock()
        mock_shop_point_result.all.return_value = [(TEST_SHOP_ID,)]
        
        # Mock offers query
        mock_offer_result = Mock()
        mock_offer_result.all.return_value = [(TEST_OFFER_ID,)]
        
        # Mock purchase offer query - not found
        mock_po_result = Mock()
        mock_po_result.scalar_one_or_none.return_value = None
        
        mock_session.execute.side_effect = [
            mock_shop_point_result,
            mock_offer_result,
            mock_po_result
        ]
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.fulfill_order_items(
                mock_session, TEST_PURCHASE_ID, fulfillment_data, TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_fulfill_order_items_wrong_seller(
        self, purchases_manager, mock_session, mock_purchase, mock_payment
    ):
        """Test fulfilling order items - offer doesn't belong to seller"""
        fulfillment_data = schemas.OrderFulfillmentRequest(
            items=[
                schemas.PurchaseOfferFulfillmentStatus(
                    purchase_offer_id=TEST_OFFER_ID,
                    offer_id=TEST_OFFER_ID,
                    status="fulfilled",
                    fulfilled_quantity=TEST_QUANTITY
                )
            ]
        )
        
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        
        # Mock shop points query
        mock_shop_point_result = Mock()
        mock_shop_point_result.all.return_value = [(TEST_SHOP_ID,)]
        
        # Mock offers query - return different offer ID
        mock_offer_result = Mock()
        mock_offer_result.all.return_value = [(999,)]  # Different offer ID
        
        # Mock purchase offer query
        mock_po_result = Mock()
        mock_po = Mock(spec=PurchaseOffer)
        mock_po.purchase_id = TEST_PURCHASE_ID
        mock_po.offer_id = TEST_OFFER_ID
        mock_po.quantity = TEST_QUANTITY
        mock_po_result.scalar_one_or_none.return_value = mock_po
        
        mock_session.execute.side_effect = [
            mock_shop_point_result,
            mock_offer_result,
            mock_po_result
        ]
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.fulfill_order_items(
                mock_session, TEST_PURCHASE_ID, fulfillment_data, TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_fulfill_order_items_exceeds_quantity(
        self, purchases_manager, mock_session, mock_purchase, mock_payment, mock_purchase_offer
    ):
        """Test fulfilling order items - fulfilled quantity exceeds requested"""
        fulfillment_data = schemas.OrderFulfillmentRequest(
            items=[
                schemas.PurchaseOfferFulfillmentStatus(
                    purchase_offer_id=TEST_OFFER_ID,
                    offer_id=TEST_OFFER_ID,
                    status="fulfilled",
                    fulfilled_quantity=100  # More than requested
                )
            ]
        )
        
        purchases_manager.service.get_purchase_by_id = AsyncMock(return_value=mock_purchase)
        purchases_manager.payments_manager.service.get_payment_by_purchase_id = AsyncMock(
            return_value=mock_payment
        )
        
        # Mock shop points query
        mock_shop_point_result = Mock()
        mock_shop_point_result.all.return_value = [(TEST_SHOP_ID,)]
        
        # Mock offers query
        mock_offer_result = Mock()
        mock_offer_result.all.return_value = [(TEST_OFFER_ID,)]
        
        # Mock purchase offer query
        mock_po_result = Mock()
        mock_po_result.scalar_one_or_none.return_value = mock_purchase_offer
        
        mock_session.execute.side_effect = [
            mock_shop_point_result,
            mock_offer_result,
            mock_po_result
        ]
        
        with pytest.raises(HTTPException) as exc_info:
            await purchases_manager.fulfill_order_items(
                mock_session, TEST_PURCHASE_ID, fulfillment_data, TEST_SELLER_ID
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds" in exc_info.value.detail.lower()
