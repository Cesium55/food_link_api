import pytest
from unittest.mock import AsyncMock, Mock
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException, status

from app.product_categories.manager import ProductCategoriesManager
from app.product_categories.service import ProductCategoriesService
from app.product_categories.models import ProductCategory
from app.product_categories import schemas
from app.products.models import Product
from app.products.service import ProductsService
from app.offers.service import OffersService


# Constants
TEST_CATEGORY_ID = 1
TEST_PARENT_CATEGORY_ID = 2
TEST_CATEGORY_NAME = "Test Category"
TEST_CATEGORY_SLUG = "test-category"
TEST_PARENT_CATEGORY_NAME = "Parent Category"
TEST_PARENT_CATEGORY_SLUG = "parent-category"


@pytest.fixture
def mock_session():
    """Create a mock async session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_category():
    """Create a mock category"""
    category = Mock(spec=ProductCategory)
    category.id = TEST_CATEGORY_ID
    category.name = TEST_CATEGORY_NAME
    category.slug = TEST_CATEGORY_SLUG
    category.parent_category_id = None
    category.parent_category = None
    category.subcategories = []
    category.products = []
    return category


@pytest.fixture
def mock_parent_category():
    """Create a mock parent category"""
    parent_category = Mock(spec=ProductCategory)
    parent_category.id = TEST_PARENT_CATEGORY_ID
    parent_category.name = TEST_PARENT_CATEGORY_NAME
    parent_category.slug = TEST_PARENT_CATEGORY_SLUG
    parent_category.parent_category_id = None
    parent_category.parent_category = None
    parent_category.subcategories = []
    parent_category.products = []
    return parent_category


@pytest.fixture
def mock_category_with_parent(mock_category, mock_parent_category):
    """Create a mock category with parent"""
    mock_category.parent_category_id = TEST_PARENT_CATEGORY_ID
    mock_category.parent_category = mock_parent_category
    return mock_category


@pytest.fixture
def product_categories_service():
    """Create ProductCategoriesService instance"""
    return ProductCategoriesService()


@pytest.fixture
def product_categories_manager():
    """Create ProductCategoriesManager instance"""
    return ProductCategoriesManager()


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


def create_category_create_schema(parent_id: Optional[int] = None) -> schemas.ProductCategoryCreate:
    """Create ProductCategoryCreate schema"""
    return schemas.ProductCategoryCreate(
        name=TEST_CATEGORY_NAME,
        slug=TEST_CATEGORY_SLUG,
        parent_category_id=parent_id
    )


def create_category_update_schema() -> schemas.ProductCategoryUpdate:
    """Create ProductCategoryUpdate schema"""
    return schemas.ProductCategoryUpdate(
        name="Updated Category Name",
        slug="updated-category-slug"
    )


class TestProductCategoriesService:
    """Tests for ProductCategoriesService class"""

    @pytest.mark.asyncio
    async def test_create_category(self, product_categories_service, mock_session, mock_category):
        """Test creating category"""
        category_create = create_category_create_schema()
        mock_session.execute.return_value = create_mock_execute_result(mock_category)
        
        category = await product_categories_service.create_category(mock_session, category_create)
        
        assert category is not None
        assert category.id == TEST_CATEGORY_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_category_with_parent(self, product_categories_service, mock_session, mock_category):
        """Test creating category with parent"""
        category_create = create_category_create_schema(parent_id=TEST_PARENT_CATEGORY_ID)
        mock_category.parent_category_id = TEST_PARENT_CATEGORY_ID
        mock_session.execute.return_value = create_mock_execute_result(mock_category)
        
        category = await product_categories_service.create_category(mock_session, category_create)
        
        assert category is not None
        assert category.parent_category_id == TEST_PARENT_CATEGORY_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_by_id_found(self, product_categories_service, mock_session, mock_category):
        """Test getting category by ID - category found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_category, "scalar_one_or_none")
        
        category = await product_categories_service.get_category_by_id(mock_session, TEST_CATEGORY_ID)
        
        assert category is not None
        assert category.id == TEST_CATEGORY_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_by_id_not_found(self, product_categories_service, mock_session):
        """Test getting category by ID - category not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        category = await product_categories_service.get_category_by_id(mock_session, 999)
        
        assert category is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_by_slug_found(self, product_categories_service, mock_session, mock_category):
        """Test getting category by slug - category found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_category, "scalar_one_or_none")
        
        category = await product_categories_service.get_category_by_slug(mock_session, TEST_CATEGORY_SLUG)
        
        assert category is not None
        assert category.slug == TEST_CATEGORY_SLUG
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_by_slug_not_found(self, product_categories_service, mock_session):
        """Test getting category by slug - category not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        category = await product_categories_service.get_category_by_slug(mock_session, "nonexistent-slug")
        
        assert category is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_categories(self, product_categories_service, mock_session, mock_category):
        """Test getting list of categories"""
        categories_list = [mock_category]
        mock_session.execute.return_value = create_mock_scalars_result(categories_list)
        
        categories = await product_categories_service.get_categories(mock_session)
        
        assert len(categories) == 1
        assert categories[0].id == TEST_CATEGORY_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_categories_empty(self, product_categories_service, mock_session):
        """Test getting empty list of categories"""
        mock_session.execute.return_value = create_mock_scalars_result([])
        
        categories = await product_categories_service.get_categories(mock_session)
        
        assert len(categories) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_root_categories(self, product_categories_service, mock_session, mock_category):
        """Test getting root categories"""
        categories_list = [mock_category]
        mock_session.execute.return_value = create_mock_scalars_result(categories_list)
        
        categories = await product_categories_service.get_root_categories(mock_session)
        
        assert len(categories) == 1
        assert categories[0].parent_category_id is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_with_parent(self, product_categories_service, mock_session, mock_category_with_parent):
        """Test getting category with parent"""
        mock_session.execute.return_value = create_mock_execute_result(mock_category_with_parent, "scalar_one_or_none")
        
        category = await product_categories_service.get_category_with_parent(mock_session, TEST_CATEGORY_ID)
        
        assert category is not None
        assert category.parent_category is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_with_subcategories(self, product_categories_service, mock_session, mock_category):
        """Test getting category with subcategories"""
        subcategory = Mock(spec=ProductCategory)
        subcategory.id = 3
        subcategory.name = "Subcategory"
        subcategory.slug = "subcategory"
        mock_category.subcategories = [subcategory]
        mock_session.execute.return_value = create_mock_execute_result(mock_category, "scalar_one_or_none")
        
        category = await product_categories_service.get_category_with_subcategories(mock_session, TEST_CATEGORY_ID)
        
        assert category is not None
        assert len(category.subcategories) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_with_products(self, product_categories_service, mock_session, mock_category):
        """Test getting category with products"""
        mock_session.execute.return_value = create_mock_execute_result(mock_category, "scalar_one_or_none")
        
        category = await product_categories_service.get_category_with_products(mock_session, TEST_CATEGORY_ID)
        
        assert category is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_with_details(self, product_categories_service, mock_session, mock_category_with_parent):
        """Test getting category with details"""
        subcategory = Mock(spec=ProductCategory)
        subcategory.id = 3
        mock_category_with_parent.subcategories = [subcategory]
        mock_session.execute.return_value = create_mock_execute_result(mock_category_with_parent, "scalar_one_or_none")
        
        category = await product_categories_service.get_category_with_details(mock_session, TEST_CATEGORY_ID)
        
        assert category is not None
        assert category.parent_category is not None
        assert len(category.subcategories) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_category(self, product_categories_service, mock_session, mock_category):
        """Test updating category"""
        category_update = create_category_update_schema()
        updated_category = Mock(spec=ProductCategory)
        updated_category.id = TEST_CATEGORY_ID
        updated_category.name = "Updated Category Name"
        updated_category.slug = "updated-category-slug"
        updated_category.parent_category_id = None
        
        # First call for update, second call for getting updated category
        mock_session.execute.side_effect = [
            Mock(),  # Update execution
            create_mock_execute_result(updated_category, "scalar_one")
        ]
        
        result = await product_categories_service.update_category(
            mock_session, TEST_CATEGORY_ID, category_update
        )
        
        assert result is not None
        assert result.name == "Updated Category Name"
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_category(self, product_categories_service, mock_session):
        """Test deleting category"""
        mock_session.execute.return_value = Mock()
        
        await product_categories_service.delete_category(mock_session, TEST_CATEGORY_ID)
        
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_categories_summary(self, product_categories_service, mock_session):
        """Test getting categories summary"""
        mock_session.execute.side_effect = [
            create_mock_execute_result(10, "scalar"),  # Total categories
            create_mock_execute_result(5, "scalar"),   # Root categories
            create_mock_execute_result(50, "scalar")  # Total products
        ]
        
        summary = await product_categories_service.get_categories_summary(mock_session)
        
        assert summary.total_categories == 10
        assert summary.total_root_categories == 5
        assert summary.avg_products_per_category == 5.0
        assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_get_categories_summary_zero_categories(self, product_categories_service, mock_session):
        """Test getting categories summary with zero categories"""
        mock_session.execute.side_effect = [
            create_mock_execute_result(0, "scalar"),  # Total categories
            create_mock_execute_result(0, "scalar"), # Root categories
            create_mock_execute_result(0, "scalar")  # Total products
        ]
        
        summary = await product_categories_service.get_categories_summary(mock_session)
        
        assert summary.total_categories == 0
        assert summary.total_root_categories == 0
        assert summary.avg_products_per_category == 0.0

    @pytest.mark.asyncio
    async def test_get_categories_by_ids(self, product_categories_service, mock_session, mock_category):
        """Test getting categories by list of IDs"""
        categories_list = [mock_category]
        mock_session.execute.return_value = create_mock_scalars_result(categories_list)
        
        categories = await product_categories_service.get_categories_by_ids(mock_session, [TEST_CATEGORY_ID])
        
        assert len(categories) == 1
        assert categories[0].id == TEST_CATEGORY_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_categories_by_product(self, product_categories_service, mock_session, mock_category):
        """Test getting categories by product ID"""
        categories_list = [mock_category]
        mock_session.execute.return_value = create_mock_scalars_result(categories_list)
        
        categories = await product_categories_service.get_categories_by_product(mock_session, 1)
        
        assert len(categories) == 1
        assert categories[0].id == TEST_CATEGORY_ID
        mock_session.execute.assert_called_once()


class TestProductCategoriesManager:
    """Tests for ProductCategoriesManager class"""

    @pytest.mark.asyncio
    async def test_create_category_success(self, product_categories_manager, mock_session, mock_category):
        """Test successful category creation"""
        category_create = create_category_create_schema()
        product_categories_manager.service.create_category = AsyncMock(return_value=mock_category)
        product_categories_manager.service.get_category_by_id = AsyncMock(return_value=mock_category)
        
        result = await product_categories_manager.create_category(mock_session, category_create)
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategory)
        assert result.id == TEST_CATEGORY_ID
        product_categories_manager.service.create_category.assert_called_once()
        product_categories_manager.service.get_category_by_id.assert_called_once_with(mock_session, TEST_CATEGORY_ID)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_categories(self, product_categories_manager, mock_session, mock_category):
        """Test getting list of categories"""
        categories_list = [mock_category]
        product_categories_manager.service.get_categories = AsyncMock(return_value=categories_list)
        
        result = await product_categories_manager.get_categories(mock_session)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.ProductCategory)
        product_categories_manager.service.get_categories.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_category_by_id_success(self, product_categories_manager, mock_session, mock_category):
        """Test getting category by ID - success"""
        product_categories_manager.service.get_category_by_id = AsyncMock(return_value=mock_category)
        
        result = await product_categories_manager.get_category_by_id(mock_session, TEST_CATEGORY_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategory)
        assert result.id == TEST_CATEGORY_ID
        product_categories_manager.service.get_category_by_id.assert_called_once_with(mock_session, TEST_CATEGORY_ID)

    @pytest.mark.asyncio
    async def test_get_category_by_id_not_found(self, product_categories_manager, mock_session):
        """Test getting category by ID - not found"""
        product_categories_manager.service.get_category_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await product_categories_manager.get_category_by_id(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_category_by_slug_success(self, product_categories_manager, mock_session, mock_category):
        """Test getting category by slug - success"""
        product_categories_manager.service.get_category_by_slug = AsyncMock(return_value=mock_category)
        
        result = await product_categories_manager.get_category_by_slug(mock_session, TEST_CATEGORY_SLUG)
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategory)
        assert result.slug == TEST_CATEGORY_SLUG
        product_categories_manager.service.get_category_by_slug.assert_called_once_with(mock_session, TEST_CATEGORY_SLUG)

    @pytest.mark.asyncio
    async def test_get_category_by_slug_not_found(self, product_categories_manager, mock_session):
        """Test getting category by slug - not found"""
        product_categories_manager.service.get_category_by_slug = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await product_categories_manager.get_category_by_slug(mock_session, "nonexistent-slug")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_root_categories(self, product_categories_manager, mock_session, mock_category):
        """Test getting root categories"""
        categories_list = [mock_category]
        product_categories_manager.service.get_root_categories = AsyncMock(return_value=categories_list)
        
        result = await product_categories_manager.get_root_categories(mock_session)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.ProductCategory)
        product_categories_manager.service.get_root_categories.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_category_with_parent_success(self, product_categories_manager, mock_session, mock_category_with_parent):
        """Test getting category with parent - success"""
        product_categories_manager.service.get_category_with_parent = AsyncMock(return_value=mock_category_with_parent)
        
        result = await product_categories_manager.get_category_with_parent(mock_session, TEST_CATEGORY_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategoryWithParent)
        assert result.parent_category is not None
        product_categories_manager.service.get_category_with_parent.assert_called_once_with(mock_session, TEST_CATEGORY_ID)

    @pytest.mark.asyncio
    async def test_get_category_with_parent_not_found(self, product_categories_manager, mock_session):
        """Test getting category with parent - not found"""
        product_categories_manager.service.get_category_with_parent = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await product_categories_manager.get_category_with_parent(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_category_with_parent_no_parent(self, product_categories_manager, mock_session, mock_category):
        """Test getting category with parent when parent is None"""
        product_categories_manager.service.get_category_with_parent = AsyncMock(return_value=mock_category)
        
        result = await product_categories_manager.get_category_with_parent(mock_session, TEST_CATEGORY_ID)
        
        assert result is not None
        assert result.parent_category is None

    @pytest.mark.asyncio
    async def test_get_category_with_subcategories_success(self, product_categories_manager, mock_session, mock_category):
        """Test getting category with subcategories - success"""
        subcategory = Mock(spec=ProductCategory)
        subcategory.id = 3
        subcategory.name = "Subcategory"
        subcategory.slug = "subcategory"
        subcategory.parent_category_id = TEST_CATEGORY_ID
        subcategory.parent_category = None
        subcategory.subcategories = []
        subcategory.products = []
        mock_category.subcategories = [subcategory]
        product_categories_manager.service.get_category_with_subcategories = AsyncMock(return_value=mock_category)
        
        result = await product_categories_manager.get_category_with_subcategories(mock_session, TEST_CATEGORY_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategoryWithSubcategories)
        assert len(result.subcategories) == 1
        product_categories_manager.service.get_category_with_subcategories.assert_called_once_with(mock_session, TEST_CATEGORY_ID)

    @pytest.mark.asyncio
    async def test_get_category_with_subcategories_not_found(self, product_categories_manager, mock_session):
        """Test getting category with subcategories - not found"""
        product_categories_manager.service.get_category_with_subcategories = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await product_categories_manager.get_category_with_subcategories(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_category_with_products_success(self, product_categories_manager, mock_session, mock_category):
        """Test getting category with products - success"""
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        mock_product.seller_id = 1
        mock_product.name = "Test Product"
        mock_product.description = None
        mock_product.article = None
        mock_product.code = None
        mock_product.images = []
        mock_product.attributes = []
        mock_product.categories = []
        
        product_categories_manager.service.get_category_with_products = AsyncMock(return_value=mock_category)
        product_categories_manager.products_service = Mock(spec=ProductsService)
        product_categories_manager.products_service.get_products_by_category = AsyncMock(return_value=[mock_product])
        
        result = await product_categories_manager.get_category_with_products(mock_session, TEST_CATEGORY_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategoryWithProducts)
        assert len(result.products) == 1
        product_categories_manager.service.get_category_with_products.assert_called_once_with(mock_session, TEST_CATEGORY_ID)

    @pytest.mark.asyncio
    async def test_get_category_with_products_not_found(self, product_categories_manager, mock_session):
        """Test getting category with products - not found"""
        product_categories_manager.service.get_category_with_products = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await product_categories_manager.get_category_with_products(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_category_with_details_success(self, product_categories_manager, mock_session, mock_category_with_parent):
        """Test getting category with details - success"""
        subcategory = Mock(spec=ProductCategory)
        subcategory.id = 3
        subcategory.name = "Subcategory"
        subcategory.slug = "subcategory"
        subcategory.parent_category_id = TEST_CATEGORY_ID
        subcategory.parent_category = None
        subcategory.subcategories = []
        subcategory.products = []
        mock_category_with_parent.subcategories = [subcategory]
        
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        mock_product.seller_id = 1
        mock_product.name = "Test Product"
        mock_product.description = None
        mock_product.article = None
        mock_product.code = None
        mock_product.images = []
        mock_product.attributes = []
        mock_product.categories = []
        
        product_categories_manager.service.get_category_with_details = AsyncMock(return_value=mock_category_with_parent)
        product_categories_manager.products_service = Mock(spec=ProductsService)
        product_categories_manager.products_service.get_products_by_category = AsyncMock(return_value=[mock_product])
        
        result = await product_categories_manager.get_category_with_details(mock_session, TEST_CATEGORY_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategoryWithDetails)
        assert result.parent_category is not None
        assert len(result.subcategories) == 1
        assert len(result.products) == 1

    @pytest.mark.asyncio
    async def test_get_category_with_details_not_found(self, product_categories_manager, mock_session):
        """Test getting category with details - not found"""
        product_categories_manager.service.get_category_with_details = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await product_categories_manager.get_category_with_details(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_category_success(self, product_categories_manager, mock_session, mock_category):
        """Test updating category - success"""
        category_update = create_category_update_schema()
        updated_category = Mock(spec=ProductCategory)
        updated_category.id = TEST_CATEGORY_ID
        updated_category.name = "Updated Category Name"
        updated_category.slug = "updated-category-slug"
        updated_category.parent_category_id = None
        
        product_categories_manager.service.update_category = AsyncMock(return_value=updated_category)
        
        result = await product_categories_manager.update_category(
            mock_session, TEST_CATEGORY_ID, category_update
        )
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategory)
        assert result.name == "Updated Category Name"
        product_categories_manager.service.update_category.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_category_success(self, product_categories_manager, mock_session):
        """Test deleting category - success"""
        product_categories_manager.service.delete_category = AsyncMock()
        
        await product_categories_manager.delete_category(mock_session, TEST_CATEGORY_ID)
        
        product_categories_manager.service.delete_category.assert_called_once_with(mock_session, TEST_CATEGORY_ID)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_with_offers_success(self, product_categories_manager, mock_session, mock_category):
        """Test getting category with offers - success"""
        # Create mock product for offer
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        mock_product.seller_id = 1
        mock_product.name = "Test Product"
        mock_product.description = "Test description"
        mock_product.article = "ART001"
        mock_product.code = "CODE001"
        mock_product.images = []
        mock_product.attributes = []
        mock_product.categories = []
        
        # Create mock offer with all required fields
        mock_offer = Mock()
        mock_offer.id = 1
        mock_offer.product_id = 1
        mock_offer.shop_id = 1
        mock_offer.expires_date = datetime.now(timezone.utc)
        mock_offer.original_cost = Decimal("100.00")
        mock_offer.current_cost = Decimal("80.00")
        mock_offer.count = 10
        mock_offer.pricing_strategy_id = None
        mock_offer.reserved_count = 0
        mock_offer.product = mock_product
        
        product_categories_manager.service.get_category_by_id = AsyncMock(return_value=mock_category)
        product_categories_manager.offers_service = Mock(spec=OffersService)
        product_categories_manager.offers_service.get_offers_with_products = AsyncMock(return_value=[mock_offer])
        
        result = await product_categories_manager.get_category_with_offers(mock_session, TEST_CATEGORY_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductCategoryWithOffers)
        product_categories_manager.service.get_category_by_id.assert_called_once_with(mock_session, TEST_CATEGORY_ID)
        product_categories_manager.offers_service.get_offers_with_products.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_with_offers_not_found(self, product_categories_manager, mock_session):
        """Test getting category with offers - not found"""
        product_categories_manager.service.get_category_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await product_categories_manager.get_category_with_offers(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_category_offers_success(self, product_categories_manager, mock_session, mock_category):
        """Test getting category offers - success"""
        # Create mock product for offer
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        mock_product.seller_id = 1
        mock_product.name = "Test Product"
        mock_product.description = "Test description"
        mock_product.article = "ART001"
        mock_product.code = "CODE001"
        mock_product.images = []
        mock_product.attributes = []
        mock_product.categories = []
        
        # Create mock offer with all required fields
        mock_offer = Mock()
        mock_offer.id = 1
        mock_offer.product_id = 1
        mock_offer.shop_id = 1
        mock_offer.expires_date = datetime.now(timezone.utc)
        mock_offer.original_cost = Decimal("100.00")
        mock_offer.current_cost = Decimal("80.00")
        mock_offer.count = 10
        mock_offer.pricing_strategy_id = None
        mock_offer.reserved_count = 0
        mock_offer.product = mock_product
        
        product_categories_manager.service.get_category_by_id = AsyncMock(return_value=mock_category)
        product_categories_manager.offers_service = Mock(spec=OffersService)
        product_categories_manager.offers_service.get_offers_with_products = AsyncMock(return_value=[mock_offer])
        
        result = await product_categories_manager.get_category_offers(mock_session, TEST_CATEGORY_ID)
        
        assert len(result) == 1
        product_categories_manager.service.get_category_by_id.assert_called_once_with(mock_session, TEST_CATEGORY_ID)
        product_categories_manager.offers_service.get_offers_with_products.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_offers_not_found(self, product_categories_manager, mock_session):
        """Test getting category offers - not found"""
        product_categories_manager.service.get_category_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await product_categories_manager.get_category_offers(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_categories_summary(self, product_categories_manager, mock_session):
        """Test getting categories summary"""
        summary = schemas.ProductCategorySummary(
            total_categories=10,
            total_root_categories=5,
            avg_products_per_category=5.0
        )
        product_categories_manager.service.get_categories_summary = AsyncMock(return_value=summary)
        
        result = await product_categories_manager.get_categories_summary(mock_session)
        
        assert result.total_categories == 10
        assert result.total_root_categories == 5
        assert result.avg_products_per_category == 5.0
        product_categories_manager.service.get_categories_summary.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_categories_by_ids(self, product_categories_manager, mock_session, mock_category):
        """Test getting categories by list of IDs"""
        categories_list = [mock_category]
        product_categories_manager.service.get_categories_by_ids = AsyncMock(return_value=categories_list)
        
        result = await product_categories_manager.get_categories_by_ids(mock_session, [TEST_CATEGORY_ID])
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.ProductCategory)
        product_categories_manager.service.get_categories_by_ids.assert_called_once_with(mock_session, [TEST_CATEGORY_ID])
