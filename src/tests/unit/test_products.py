import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Optional, List
from fastapi import HTTPException, status

from app.products.manager import ProductsManager
from app.products.service import ProductsService
from app.products.models import Product, ProductImage, ProductAttribute
from app.products import schemas
from app.sellers.models import Seller
from app.sellers.service import SellersService
from app.product_categories.models import ProductCategory
from app.product_categories.service import ProductCategoriesService
from app.auth.models import User


# Constants
TEST_PRODUCT_ID = 1
TEST_SELLER_ID = 1
TEST_USER_ID = 1
TEST_CATEGORY_ID = 1
TEST_PRODUCT_NAME = "Test Product"
TEST_PRODUCT_DESCRIPTION = "Test product description"
TEST_PRODUCT_ARTICLE = "ART-001"
TEST_PRODUCT_CODE = "CODE-001"


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
    user.email = "user@example.com"
    user.phone = "79991234567"
    user.is_seller = True
    return user


@pytest.fixture
def mock_seller():
    """Create a mock seller"""
    seller = Mock(spec=Seller)
    seller.id = TEST_SELLER_ID
    seller.email = "seller@example.com"
    seller.phone = "79991234567"
    seller.full_name = "Test Seller Full Name"
    seller.short_name = "Test Seller"
    seller.description = "Test description"
    seller.inn = "123456789012"
    seller.is_IP = True
    seller.ogrn = "123456789012345"
    seller.master_id = TEST_USER_ID
    seller.status = 0
    seller.verification_level = 0
    seller.registration_doc_url = ""
    seller.balance = 0.0
    seller.images = []
    return seller


@pytest.fixture
def mock_category():
    """Create a mock category"""
    category = Mock(spec=ProductCategory)
    category.id = TEST_CATEGORY_ID
    category.name = "Test Category"
    category.slug = "test-category"
    category.parent_category_id = None
    return category


@pytest.fixture
def mock_product():
    """Create a mock product"""
    product = Mock(spec=Product)
    product.id = TEST_PRODUCT_ID
    product.name = TEST_PRODUCT_NAME
    product.description = TEST_PRODUCT_DESCRIPTION
    product.article = TEST_PRODUCT_ARTICLE
    product.code = TEST_PRODUCT_CODE
    product.seller_id = TEST_SELLER_ID
    product.images = []
    product.attributes = []
    product.categories = []
    return product


@pytest.fixture
def mock_product_image():
    """Create a mock product image"""
    image = Mock(spec=ProductImage)
    image.id = 1
    image.product_id = TEST_PRODUCT_ID
    image.path = "s3://bucket/products/1/image.jpg"
    image.order = 0
    return image


@pytest.fixture
def mock_product_attribute():
    """Create a mock product attribute"""
    attribute = Mock(spec=ProductAttribute)
    attribute.id = 1
    attribute.product_id = TEST_PRODUCT_ID
    attribute.slug = "weight"
    attribute.name = "Вес"
    attribute.value = "500 г"
    return attribute


@pytest.fixture
def products_service():
    """Create ProductsService instance"""
    return ProductsService()


@pytest.fixture
def products_manager():
    """Create ProductsManager instance"""
    return ProductsManager()


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


def create_product_create_schema(
    category_ids: Optional[List[int]] = None,
    attributes: Optional[List[schemas.ProductAttributeCreateInline]] = None
) -> schemas.ProductCreate:
    """Create ProductCreate schema"""
    return schemas.ProductCreate(
        name=TEST_PRODUCT_NAME,
        description=TEST_PRODUCT_DESCRIPTION,
        article=TEST_PRODUCT_ARTICLE,
        code=TEST_PRODUCT_CODE,
        category_ids=category_ids or [],
        attributes=attributes or []
    )


def create_product_update_schema() -> schemas.ProductUpdate:
    """Create ProductUpdate schema"""
    return schemas.ProductUpdate(
        name="Updated Product Name",
        description="Updated description"
    )


def create_product_attribute_create_schema() -> schemas.ProductAttributeCreate:
    """Create ProductAttributeCreate schema"""
    return schemas.ProductAttributeCreate(
        product_id=TEST_PRODUCT_ID,
        slug="weight",
        name="Вес",
        value="500 г"
    )


def create_product_attribute_create_inline() -> schemas.ProductAttributeCreateInline:
    """Create ProductAttributeCreateInline schema"""
    return schemas.ProductAttributeCreateInline(
        slug="weight",
        name="Вес",
        value="500 г"
    )


class TestProductsService:
    """Tests for ProductsService class"""

    @pytest.mark.asyncio
    async def test_create_product(self, products_service, mock_session, mock_product):
        """Test creating product"""
        product_create = create_product_create_schema()
        mock_session.execute.return_value = create_mock_execute_result(mock_product)
        
        product = await products_service.create_product(
            mock_session, product_create, TEST_SELLER_ID
        )
        
        assert product is not None
        assert product.id == TEST_PRODUCT_ID
        assert mock_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_create_product_with_categories(self, products_service, mock_session, mock_product):
        """Test creating product with categories"""
        product_create = create_product_create_schema(category_ids=[TEST_CATEGORY_ID])
        mock_session.execute.side_effect = [
            create_mock_execute_result(mock_product),
            Mock()  # Category insertion
        ]
        
        product = await products_service.create_product(
            mock_session, product_create, TEST_SELLER_ID
        )
        
        assert product is not None
        assert mock_session.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_create_product_with_attributes(self, products_service, mock_session, mock_product):
        """Test creating product with attributes"""
        attributes = [create_product_attribute_create_inline()]
        product_create = create_product_create_schema(attributes=attributes)
        mock_session.execute.side_effect = [
            create_mock_execute_result(mock_product),
            Mock()  # Attribute insertion
        ]
        
        product = await products_service.create_product(
            mock_session, product_create, TEST_SELLER_ID
        )
        
        assert product is not None
        assert mock_session.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_get_product_by_id_found(self, products_service, mock_session, mock_product):
        """Test getting product by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_product, "scalar_one_or_none")
        
        product = await products_service.get_product_by_id(mock_session, TEST_PRODUCT_ID)
        
        assert product is not None
        assert product.id == TEST_PRODUCT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_by_id_not_found(self, products_service, mock_session):
        """Test getting product by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        product = await products_service.get_product_by_id(mock_session, 999)
        
        assert product is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_products(self, products_service, mock_session, mock_product):
        """Test getting list of products"""
        products_list = [mock_product]
        mock_session.execute.return_value = create_mock_scalars_result(products_list)
        
        products = await products_service.get_products(mock_session)
        
        assert len(products) == 1
        assert products[0].id == TEST_PRODUCT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_products_empty(self, products_service, mock_session):
        """Test getting empty list of products"""
        mock_session.execute.return_value = create_mock_scalars_result([])
        
        products = await products_service.get_products(mock_session)
        
        assert len(products) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_products_paginated(self, products_service, mock_session, mock_product):
        """Test getting paginated products"""
        products_list = [mock_product]
        mock_session.execute.side_effect = [
            create_mock_scalar_result(1),  # Count query
            create_mock_scalars_result(products_list)  # Products query
        ]
        
        products, total_count = await products_service.get_products_paginated(
            mock_session, page=1, page_size=10
        )
        
        assert len(products) == 1
        assert total_count == 1
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_products_paginated_with_filters(self, products_service, mock_session, mock_product):
        """Test getting paginated products with filters"""
        products_list = [mock_product]
        mock_session.execute.side_effect = [
            create_mock_scalar_result(1),  # Count query
            create_mock_scalars_result(products_list)  # Products query
        ]
        
        products, total_count = await products_service.get_products_paginated(
            mock_session, page=1, page_size=10, article=TEST_PRODUCT_ARTICLE, seller_id=TEST_SELLER_ID
        )
        
        assert len(products) == 1
        assert total_count == 1

    @pytest.mark.asyncio
    async def test_get_products_paginated_with_category_filter(self, products_service, mock_session, mock_product):
        """Test getting paginated products with category filter"""
        products_list = [mock_product]
        mock_session.execute.side_effect = [
            create_mock_scalar_result(1),  # Count query
            create_mock_scalars_result(products_list)  # Products query
        ]
        
        products, total_count = await products_service.get_products_paginated(
            mock_session, page=1, page_size=10, category_ids=[TEST_CATEGORY_ID]
        )
        
        assert len(products) == 1
        assert total_count == 1

    @pytest.mark.asyncio
    async def test_get_products_by_seller(self, products_service, mock_session, mock_product):
        """Test getting products by seller ID"""
        products_list = [mock_product]
        mock_session.execute.return_value = create_mock_scalars_result(products_list)
        
        products = await products_service.get_products_by_seller(mock_session, TEST_SELLER_ID)
        
        assert len(products) == 1
        assert products[0].seller_id == TEST_SELLER_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_products_by_category(self, products_service, mock_session, mock_product):
        """Test getting products by category ID"""
        products_list = [mock_product]
        mock_session.execute.return_value = create_mock_scalars_result(products_list)
        
        products = await products_service.get_products_by_category(mock_session, TEST_CATEGORY_ID)
        
        assert len(products) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product(self, products_service, mock_session, mock_product):
        """Test updating product"""
        product_update = create_product_update_schema()
        mock_session.execute.side_effect = [
            create_mock_execute_result(mock_product),  # Update
            create_mock_execute_result(mock_product)  # Get updated product
        ]
        
        updated_product = await products_service.update_product(
            mock_session, TEST_PRODUCT_ID, product_update
        )
        
        assert updated_product is not None
        assert mock_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_update_product_with_categories(self, products_service, mock_session, mock_product, mock_category):
        """Test updating product with categories"""
        product_update = schemas.ProductUpdate(category_ids=[TEST_CATEGORY_ID])
        # Set up product with categories for final load
        mock_product_with_categories = Mock(spec=Product)
        mock_product_with_categories.id = TEST_PRODUCT_ID
        mock_product_with_categories.name = TEST_PRODUCT_NAME
        mock_product_with_categories.description = TEST_PRODUCT_DESCRIPTION
        mock_product_with_categories.article = TEST_PRODUCT_ARTICLE
        mock_product_with_categories.code = TEST_PRODUCT_CODE
        mock_product_with_categories.seller_id = TEST_SELLER_ID
        mock_product_with_categories.images = []
        mock_product_with_categories.attributes = []
        mock_product_with_categories.categories = [mock_category]  # Product now has category
        
        # Sequence of execute calls:
        # 1. Get product (no update_data, so just select)
        # 2. Delete categories
        # 3. Insert categories (_add_categories_to_product)
        # 4. Get updated product with relations
        mock_session.execute.side_effect = [
            create_mock_execute_result(mock_product),  # Get product (no update_data, so just select)
            Mock(),  # Delete categories
            Mock(),  # Insert categories (_add_categories_to_product)
            create_mock_execute_result(mock_product_with_categories)  # Get updated product with relations
        ]
        
        updated_product = await products_service.update_product(
            mock_session, TEST_PRODUCT_ID, product_update
        )
        
        assert updated_product is not None
        assert len(updated_product.categories) == 1
        assert updated_product.categories[0].id == TEST_CATEGORY_ID
        assert mock_session.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_delete_product(self, products_service, mock_session):
        """Test deleting product"""
        mock_session.execute.return_value = Mock()
        
        await products_service.delete_product(mock_session, TEST_PRODUCT_ID)
        
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_products_summary(self, products_service, mock_session):
        """Test getting products summary"""
        mock_session.execute.side_effect = [
            create_mock_scalar_result(10),  # Total products
            create_mock_scalar_result(5)  # Total sellers
        ]
        
        summary = await products_service.get_products_summary(mock_session)
        
        assert summary.total_products == 10
        assert summary.total_sellers == 5
        assert summary.avg_products_per_seller == 2.0
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_products_summary_zero_sellers(self, products_service, mock_session):
        """Test getting products summary with zero sellers"""
        mock_session.execute.side_effect = [
            create_mock_scalar_result(0),  # Total products
            create_mock_scalar_result(0)  # Total sellers
        ]
        
        summary = await products_service.get_products_summary(mock_session)
        
        assert summary.total_products == 0
        assert summary.total_sellers == 0
        assert summary.avg_products_per_seller == 0.0

    @pytest.mark.asyncio
    async def test_get_products_by_ids(self, products_service, mock_session, mock_product):
        """Test getting products by IDs"""
        products_list = [mock_product]
        mock_session.execute.return_value = create_mock_scalars_result(products_list)
        
        products = await products_service.get_products_by_ids(mock_session, [TEST_PRODUCT_ID])
        
        assert len(products) == 1
        assert products[0].id == TEST_PRODUCT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_attribute(self, products_service, mock_session, mock_product_attribute):
        """Test creating product attribute"""
        attribute_create = create_product_attribute_create_schema()
        mock_session.execute.return_value = create_mock_execute_result(mock_product_attribute)
        
        attribute = await products_service.create_product_attribute(mock_session, attribute_create)
        
        assert attribute is not None
        assert attribute.id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_attribute_by_id_found(self, products_service, mock_session, mock_product_attribute):
        """Test getting product attribute by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_product_attribute, "scalar_one_or_none")
        
        attribute = await products_service.get_product_attribute_by_id(mock_session, 1)
        
        assert attribute is not None
        assert attribute.id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_attribute_by_id_not_found(self, products_service, mock_session):
        """Test getting product attribute by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        attribute = await products_service.get_product_attribute_by_id(mock_session, 999)
        
        assert attribute is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_attributes_by_product(self, products_service, mock_session, mock_product_attribute):
        """Test getting product attributes by product ID"""
        attributes_list = [mock_product_attribute]
        mock_session.execute.return_value = create_mock_scalars_result(attributes_list)
        
        attributes = await products_service.get_product_attributes_by_product(mock_session, TEST_PRODUCT_ID)
        
        assert len(attributes) == 1
        assert attributes[0].product_id == TEST_PRODUCT_ID
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_attribute_by_product_and_slug_found(
        self, products_service, mock_session, mock_product_attribute
    ):
        """Test getting product attribute by product ID and slug - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_product_attribute, "scalar_one_or_none")
        
        attribute = await products_service.get_product_attribute_by_product_and_slug(
            mock_session, TEST_PRODUCT_ID, "weight"
        )
        
        assert attribute is not None
        assert attribute.slug == "weight"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_attribute_by_product_and_slug_not_found(
        self, products_service, mock_session
    ):
        """Test getting product attribute by product ID and slug - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        attribute = await products_service.get_product_attribute_by_product_and_slug(
            mock_session, TEST_PRODUCT_ID, "nonexistent"
        )
        
        assert attribute is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product_attribute(self, products_service, mock_session, mock_product_attribute):
        """Test updating product attribute"""
        attribute_update = schemas.ProductAttributeUpdate(name="Обновленный вес", value="1000 г")
        mock_session.execute.side_effect = [
            Mock(),  # Update
            create_mock_execute_result(mock_product_attribute)  # Get updated attribute
        ]
        
        updated_attribute = await products_service.update_product_attribute(
            mock_session, 1, attribute_update
        )
        
        assert updated_attribute is not None
        assert mock_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_delete_product_attribute(self, products_service, mock_session):
        """Test deleting product attribute"""
        mock_session.execute.return_value = Mock()
        
        await products_service.delete_product_attribute(mock_session, 1)
        
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_image(self, products_service, mock_session, mock_product_image):
        """Test creating product image"""
        mock_session.execute.return_value = create_mock_execute_result(mock_product_image)
        
        image = await products_service.create_product_image(
            mock_session, TEST_PRODUCT_ID, "s3://bucket/products/1/image.jpg", 0
        )
        
        assert image is not None
        assert image.id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_image_by_id_found(self, products_service, mock_session, mock_product_image):
        """Test getting product image by ID - found"""
        mock_session.execute.return_value = create_mock_execute_result(mock_product_image, "scalar_one_or_none")
        
        image = await products_service.get_product_image_by_id(mock_session, 1)
        
        assert image is not None
        assert image.id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_image_by_id_not_found(self, products_service, mock_session):
        """Test getting product image by ID - not found"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        image = await products_service.get_product_image_by_id(mock_session, 999)
        
        assert image is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_product_image(self, products_service, mock_session):
        """Test deleting product image"""
        mock_session.execute.return_value = Mock()
        
        await products_service.delete_product_image(mock_session, 1)
        
        mock_session.execute.assert_called_once()


class TestProductsManager:
    """Tests for ProductsManager class"""

    @pytest.mark.asyncio
    async def test_create_product_success(self, products_manager, mock_session, mock_user, mock_seller, mock_product):
        """Test successful product creation"""
        product_create = create_product_create_schema()
        products_manager.sellers_service.get_seller_by_master_id = AsyncMock(return_value=mock_seller)
        products_manager.service.create_product = AsyncMock(return_value=mock_product)
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        
        result = await products_manager.create_product(mock_session, product_create, mock_user)
        
        assert result is not None
        assert result.id == TEST_PRODUCT_ID
        products_manager.sellers_service.get_seller_by_master_id.assert_called_once_with(mock_session, TEST_USER_ID)
        products_manager.service.create_product.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_user_not_seller(self, products_manager, mock_session, mock_user):
        """Test product creation when user is not a seller"""
        mock_user.is_seller = False
        product_create = create_product_create_schema()
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.create_product(mock_session, product_create, mock_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Only sellers" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_product_seller_not_found(self, products_manager, mock_session, mock_user):
        """Test product creation when seller account not found"""
        mock_user.is_seller = True
        product_create = create_product_create_schema()
        products_manager.sellers_service.get_seller_by_master_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.create_product(mock_session, product_create, mock_user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Seller account not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_products(self, products_manager, mock_session, mock_product):
        """Test getting list of products"""
        products_list = [mock_product]
        products_manager.service.get_products = AsyncMock(return_value=products_list)
        
        result = await products_manager.get_products(mock_session)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.Product)
        products_manager.service.get_products.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_products_paginated(self, products_manager, mock_session, mock_product):
        """Test getting paginated products"""
        products_list = [mock_product]
        products_manager.service.get_products_paginated = AsyncMock(return_value=(products_list, 1))
        
        result = await products_manager.get_products_paginated(mock_session, page=1, page_size=10)
        
        assert result.pagination.total_items == 1
        assert len(result.items) == 1
        assert isinstance(result.items[0], schemas.Product)
        products_manager.service.get_products_paginated.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_by_id_success(self, products_manager, mock_session, mock_product):
        """Test getting product by ID - success"""
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        
        result = await products_manager.get_product_by_id(mock_session, TEST_PRODUCT_ID)
        
        assert result is not None
        assert isinstance(result, schemas.Product)
        products_manager.service.get_product_by_id.assert_called_once_with(mock_session, TEST_PRODUCT_ID)

    @pytest.mark.asyncio
    async def test_get_product_by_id_not_found(self, products_manager, mock_session):
        """Test getting product by ID - not found"""
        products_manager.service.get_product_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.get_product_by_id(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_products_by_seller(self, products_manager, mock_session, mock_product):
        """Test getting products by seller ID"""
        products_list = [mock_product]
        products_manager.service.get_products_by_seller = AsyncMock(return_value=products_list)
        
        result = await products_manager.get_products_by_seller(mock_session, TEST_SELLER_ID)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.Product)
        products_manager.service.get_products_by_seller.assert_called_once_with(mock_session, TEST_SELLER_ID)

    @pytest.mark.asyncio
    async def test_get_product_with_seller_success(
        self, products_manager, mock_session, mock_product, mock_seller
    ):
        """Test getting product with seller - success"""
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        products_manager.sellers_service.get_seller_by_id = AsyncMock(return_value=mock_seller)
        
        result = await products_manager.get_product_with_seller(mock_session, TEST_PRODUCT_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductWithSeller)
        assert result.seller is not None

    @pytest.mark.asyncio
    async def test_get_product_with_seller_product_not_found(self, products_manager, mock_session):
        """Test getting product with seller - product not found"""
        products_manager.service.get_product_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.get_product_with_seller(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_product_with_seller_seller_not_found(
        self, products_manager, mock_session, mock_product
    ):
        """Test getting product with seller - seller not found"""
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        products_manager.sellers_service.get_seller_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.get_product_with_seller(mock_session, TEST_PRODUCT_ID)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_product_with_categories_success(
        self, products_manager, mock_session, mock_product, mock_category
    ):
        """Test getting product with categories - success"""
        mock_product.categories = [mock_category]
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        
        result = await products_manager.get_product_with_categories(mock_session, TEST_PRODUCT_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductWithCategories)
        assert len(result.categories) == 1

    @pytest.mark.asyncio
    async def test_get_product_with_details_success(
        self, products_manager, mock_session, mock_product, mock_seller, mock_category
    ):
        """Test getting product with details - success"""
        mock_product.categories = [mock_category]
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        products_manager.sellers_service.get_seller_by_id = AsyncMock(return_value=mock_seller)
        
        result = await products_manager.get_product_with_details(mock_session, TEST_PRODUCT_ID)
        
        assert result is not None
        assert isinstance(result, schemas.ProductWithDetails)
        assert result.seller is not None
        assert len(result.categories) == 1

    @pytest.mark.asyncio
    async def test_update_product_success(
        self, products_manager, mock_session, mock_product, mock_seller
    ):
        """Test successful product update"""
        product_update = create_product_update_schema()
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        products_manager.service.update_product = AsyncMock(return_value=mock_product)
        
        with patch('app.products.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await products_manager.update_product(
                mock_session, TEST_PRODUCT_ID, product_update, mock_seller
            )
            
            assert result is not None
            assert isinstance(result, schemas.Product)
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            products_manager.service.update_product.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product_not_found(self, products_manager, mock_session, mock_seller):
        """Test product update when product not found"""
        product_update = create_product_update_schema()
        products_manager.service.get_product_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.update_product(
                mock_session, 999, product_update, mock_seller
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_product_wrong_owner(self, products_manager, mock_session, mock_product, mock_seller):
        """Test product update when seller doesn't own the product"""
        product_update = create_product_update_schema()
        mock_product.seller_id = 999  # Different seller
        mock_seller.id = TEST_SELLER_ID
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        
        with patch('app.products.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource"
            )
            with pytest.raises(HTTPException) as exc_info:
                await products_manager.update_product(
                    mock_session, TEST_PRODUCT_ID, product_update, mock_seller
                )
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_product_success(
        self, products_manager, mock_session, mock_product, mock_seller
    ):
        """Test successful product deletion"""
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        products_manager.service.delete_product = AsyncMock()
        
        with patch('app.products.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            await products_manager.delete_product(mock_session, TEST_PRODUCT_ID, mock_seller)
            
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            products_manager.service.delete_product.assert_called_once_with(mock_session, TEST_PRODUCT_ID)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_product_not_found(self, products_manager, mock_session, mock_seller):
        """Test product deletion when product not found"""
        products_manager.service.get_product_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.delete_product(mock_session, 999, mock_seller)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_products_summary(self, products_manager, mock_session):
        """Test getting products summary"""
        summary_data = schemas.ProductSummary(
            total_products=10,
            total_sellers=5,
            avg_products_per_seller=2.0
        )
        products_manager.service.get_products_summary = AsyncMock(return_value=summary_data)
        
        result = await products_manager.get_products_summary(mock_session)
        
        assert result.total_products == 10
        assert result.total_sellers == 5
        assert result.avg_products_per_seller == 2.0

    @pytest.mark.asyncio
    async def test_get_products_by_ids(self, products_manager, mock_session, mock_product):
        """Test getting products by IDs"""
        products_list = [mock_product]
        products_manager.service.get_products_by_ids = AsyncMock(return_value=products_list)
        
        result = await products_manager.get_products_by_ids(mock_session, [TEST_PRODUCT_ID])
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.Product)
        products_manager.service.get_products_by_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_attribute_success(
        self, products_manager, mock_session, mock_product, mock_seller, mock_product_attribute
    ):
        """Test successful product attribute creation"""
        attribute_create = create_product_attribute_create_schema()
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        products_manager.service.create_product_attribute = AsyncMock(return_value=mock_product_attribute)
        
        with patch('app.products.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await products_manager.create_product_attribute(
                mock_session, attribute_create, mock_seller
            )
            
            assert result is not None
            assert isinstance(result, schemas.ProductAttribute)
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            products_manager.service.create_product_attribute.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_attribute_product_not_found(
        self, products_manager, mock_session, mock_seller
    ):
        """Test product attribute creation when product not found"""
        attribute_create = create_product_attribute_create_schema()
        products_manager.service.get_product_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.create_product_attribute(
                mock_session, attribute_create, mock_seller
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_product_attribute_by_id_success(
        self, products_manager, mock_session, mock_product_attribute
    ):
        """Test getting product attribute by ID - success"""
        products_manager.service.get_product_attribute_by_id = AsyncMock(return_value=mock_product_attribute)
        
        result = await products_manager.get_product_attribute_by_id(mock_session, 1)
        
        assert result is not None
        assert isinstance(result, schemas.ProductAttribute)
        products_manager.service.get_product_attribute_by_id.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_product_attribute_by_id_not_found(self, products_manager, mock_session):
        """Test getting product attribute by ID - not found"""
        products_manager.service.get_product_attribute_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.get_product_attribute_by_id(mock_session, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_product_attributes_by_product(
        self, products_manager, mock_session, mock_product_attribute
    ):
        """Test getting product attributes by product ID"""
        attributes_list = [mock_product_attribute]
        products_manager.service.get_product_attributes_by_product = AsyncMock(return_value=attributes_list)
        
        result = await products_manager.get_product_attributes_by_product(mock_session, TEST_PRODUCT_ID)
        
        assert len(result) == 1
        assert isinstance(result[0], schemas.ProductAttribute)
        products_manager.service.get_product_attributes_by_product.assert_called_once_with(
            mock_session, TEST_PRODUCT_ID
        )

    @pytest.mark.asyncio
    async def test_get_product_attribute_by_product_and_slug_success(
        self, products_manager, mock_session, mock_product_attribute
    ):
        """Test getting product attribute by product ID and slug - success"""
        products_manager.service.get_product_attribute_by_product_and_slug = AsyncMock(
            return_value=mock_product_attribute
        )
        
        result = await products_manager.get_product_attribute_by_product_and_slug(
            mock_session, TEST_PRODUCT_ID, "weight"
        )
        
        assert result is not None
        assert isinstance(result, schemas.ProductAttribute)
        products_manager.service.get_product_attribute_by_product_and_slug.assert_called_once_with(
            mock_session, TEST_PRODUCT_ID, "weight"
        )

    @pytest.mark.asyncio
    async def test_get_product_attribute_by_product_and_slug_not_found(
        self, products_manager, mock_session
    ):
        """Test getting product attribute by product ID and slug - not found"""
        products_manager.service.get_product_attribute_by_product_and_slug = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.get_product_attribute_by_product_and_slug(
                mock_session, TEST_PRODUCT_ID, "nonexistent"
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_product_attribute_success(
        self, products_manager, mock_session, mock_product, mock_seller, mock_product_attribute
    ):
        """Test successful product attribute update"""
        attribute_update = schemas.ProductAttributeUpdate(name="Updated Name", value="Updated Value")
        products_manager.service.get_product_attribute_by_id = AsyncMock(return_value=mock_product_attribute)
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        products_manager.service.update_product_attribute = AsyncMock(return_value=mock_product_attribute)
        
        with patch('app.products.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            result = await products_manager.update_product_attribute(
                mock_session, 1, attribute_update, mock_seller
            )
            
            assert result is not None
            assert isinstance(result, schemas.ProductAttribute)
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            products_manager.service.update_product_attribute.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product_attribute_not_found(self, products_manager, mock_session, mock_seller):
        """Test product attribute update when attribute not found"""
        attribute_update = schemas.ProductAttributeUpdate(name="Updated Name")
        products_manager.service.get_product_attribute_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.update_product_attribute(
                mock_session, 999, attribute_update, mock_seller
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_product_attribute_success(
        self, products_manager, mock_session, mock_product, mock_seller, mock_product_attribute
    ):
        """Test successful product attribute deletion"""
        products_manager.service.get_product_attribute_by_id = AsyncMock(return_value=mock_product_attribute)
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        products_manager.service.delete_product_attribute = AsyncMock()
        
        with patch('app.products.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            await products_manager.delete_product_attribute(mock_session, 1, mock_seller)
            
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            products_manager.service.delete_product_attribute.assert_called_once_with(mock_session, 1)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_product_attribute_not_found(self, products_manager, mock_session, mock_seller):
        """Test product attribute deletion when attribute not found"""
        products_manager.service.get_product_attribute_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await products_manager.delete_product_attribute(mock_session, 999, mock_seller)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    @patch('app.products.manager.ImageManager')
    async def test_upload_product_image_success(
        self, mock_image_manager_class, products_manager, mock_session, mock_product, mock_seller
    ):
        """Test successful product image upload"""
        mock_image_manager = Mock()
        mock_image_manager.upload_and_create_image_record = AsyncMock(
            return_value=schemas.ProductImage(id=1, path="s3://bucket/products/1/image.jpg", order=0)
        )
        mock_image_manager_class.return_value = mock_image_manager
        products_manager.image_manager = mock_image_manager
        
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        
        with patch('app.products.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            mock_file = Mock()
            result = await products_manager.upload_product_image(
                mock_session, TEST_PRODUCT_ID, mock_file, 0, mock_seller
            )
            
            assert result is not None
            assert isinstance(result, schemas.ProductImage)
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)

    @pytest.mark.asyncio
    @patch('app.products.manager.ImageManager')
    async def test_delete_product_image_success(
        self, mock_image_manager_class, products_manager, mock_session, mock_product, mock_seller, mock_product_image
    ):
        """Test successful product image deletion"""
        mock_image_manager = Mock()
        mock_image_manager.delete_image_record = AsyncMock()
        mock_image_manager_class.return_value = mock_image_manager
        products_manager.image_manager = mock_image_manager
        
        products_manager.service.get_product_image_by_id = AsyncMock(return_value=mock_product_image)
        products_manager.service.get_product_by_id = AsyncMock(return_value=mock_product)
        
        with patch('app.products.manager.verify_seller_owns_resource', new_callable=AsyncMock) as mock_verify:
            await products_manager.delete_product_image(mock_session, 1, mock_seller)
            
            mock_verify.assert_called_once_with(TEST_SELLER_ID, mock_seller)
            mock_image_manager.delete_image_record.assert_called_once()
