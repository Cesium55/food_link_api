"""
API integration tests for product categories endpoints
"""
import pytest
from fastapi import status
from sqlalchemy import select

from app.product_categories.models import ProductCategory


CATEGORY_DATA = {
    "name": "Test Category",
    "slug": "test-category"
}

CATEGORY_DATA_WITH_PARENT = {
    "name": "Subcategory",
    "slug": "subcategory",
    "parent_category_id": 1
}

CATEGORY_UPDATE_DATA = {
    "name": "Updated Category Name",
    "slug": "updated-category-slug"
}


def get_response_data(response_data: dict) -> dict:
    """Helper function to extract data from wrapped response"""
    return response_data.get("data", response_data)


class TestCreateCategoryAPI:
    """Tests for /product-categories endpoint (POST)"""
    
    @pytest.mark.asyncio
    async def test_create_category_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful category creation"""
        response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["name"] == CATEGORY_DATA["name"]
        assert data["slug"] == CATEGORY_DATA["slug"]
        assert data["parent_category_id"] is None
        
        # Verify category was created in database
        result = await test_session.execute(
            select(ProductCategory).where(ProductCategory.slug == CATEGORY_DATA["slug"])
        )
        category = result.scalar_one_or_none()
        assert category is not None
        assert category.name == CATEGORY_DATA["name"]
    
    @pytest.mark.asyncio
    async def test_create_category_with_parent_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful category creation with parent"""
        # Create parent category first
        parent_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        parent_id = get_response_data(parent_response.json())["id"]
        
        # Create subcategory
        subcategory_data = CATEGORY_DATA_WITH_PARENT.copy()
        subcategory_data["parent_category_id"] = parent_id
        response = await client.post(
            "/product-categories",
            json=subcategory_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["name"] == subcategory_data["name"]
        assert data["parent_category_id"] == parent_id
    
    @pytest.mark.asyncio
    async def test_create_category_duplicate_slug(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test creating category with duplicate slug"""
        await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        
        # Try to create another category with same slug
        response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_create_category_invalid_data(self, client, mock_settings, mock_image_manager_init):
        """Test creating category with invalid data"""
        response = await client.post(
            "/product-categories",
            json={"name": ""}  # Empty name
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetCategoryAPI:
    """Tests for /product-categories/{category_id} endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_category_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category by ID"""
        create_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        category_id = get_response_data(create_response.json())["id"]
        
        response = await client.get(f"/product-categories/{category_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == category_id
        assert data["name"] == CATEGORY_DATA["name"]
    
    @pytest.mark.asyncio
    async def test_get_category_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test getting non-existent category"""
        response = await client.get("/product-categories/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_category_by_slug_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category by slug"""
        await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        
        response = await client.get(f"/product-categories/slug/{CATEGORY_DATA['slug']}")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["slug"] == CATEGORY_DATA["slug"]
    
    @pytest.mark.asyncio
    async def test_get_category_by_slug_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test getting category by non-existent slug"""
        response = await client.get("/product-categories/slug/nonexistent-slug")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetCategoriesListAPI:
    """Tests for /product-categories endpoint (GET - list)"""
    
    @pytest.mark.asyncio
    async def test_get_categories_list_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting list of categories"""
        # Create multiple categories
        for i in range(3):
            category_data = {
                "name": f"Category {i}",
                "slug": f"category-{i}"
            }
            await client.post(
                "/product-categories",
                json=category_data
            )
        
        response = await client.get("/product-categories")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) >= 3
    
    @pytest.mark.asyncio
    async def test_get_root_categories_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting root categories"""
        # Create root category
        await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        
        # Create subcategory
        parent_response = await client.post(
            "/product-categories",
            json={"name": "Parent", "slug": "parent"}
        )
        parent_id = get_response_data(parent_response.json())["id"]
        
        subcategory_data = CATEGORY_DATA_WITH_PARENT.copy()
        subcategory_data["parent_category_id"] = parent_id
        await client.post(
            "/product-categories",
            json=subcategory_data
        )
        
        response = await client.get("/product-categories/root")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        # Should have at least 2 root categories (CATEGORY_DATA and Parent)
        assert len(data) >= 2
        # All should have parent_category_id as None
        for category in data:
            assert category["parent_category_id"] is None


class TestGetCategoryWithRelationsAPI:
    """Tests for category endpoints with relations"""
    
    @pytest.mark.asyncio
    async def test_get_category_with_parent_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category with parent"""
        # Create parent category
        parent_response = await client.post(
            "/product-categories",
            json={"name": "Parent Category", "slug": "parent-category"}
        )
        parent_id = get_response_data(parent_response.json())["id"]
        
        # Create subcategory
        subcategory_data = CATEGORY_DATA_WITH_PARENT.copy()
        subcategory_data["parent_category_id"] = parent_id
        subcategory_response = await client.post(
            "/product-categories",
            json=subcategory_data
        )
        subcategory_id = get_response_data(subcategory_response.json())["id"]
        
        response = await client.get(f"/product-categories/{subcategory_id}/with-parent")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == subcategory_id
        assert data["parent_category"] is not None
        assert data["parent_category"]["id"] == parent_id
    
    @pytest.mark.asyncio
    async def test_get_category_with_parent_no_parent(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category with parent when parent is None"""
        create_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        category_id = get_response_data(create_response.json())["id"]
        
        response = await client.get(f"/product-categories/{category_id}/with-parent")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["parent_category"] is None
    
    @pytest.mark.asyncio
    async def test_get_category_with_subcategories_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category with subcategories"""
        # Create parent category
        parent_response = await client.post(
            "/product-categories",
            json={"name": "Parent Category", "slug": "parent-category"}
        )
        parent_id = get_response_data(parent_response.json())["id"]
        
        # Create subcategories
        for i in range(2):
            subcategory_data = {
                "name": f"Subcategory {i}",
                "slug": f"subcategory-{i}",
                "parent_category_id": parent_id
            }
            await client.post(
                "/product-categories",
                json=subcategory_data
            )
        
        response = await client.get(f"/product-categories/{parent_id}/with-subcategories")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data["subcategories"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_category_with_products_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category with products"""
        # Create category
        create_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        category_id = get_response_data(create_response.json())["id"]
        
        response = await client.get(f"/product-categories/{category_id}/with-products")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == category_id
        assert "products" in data
        assert isinstance(data["products"], list)
    
    @pytest.mark.asyncio
    async def test_get_category_with_details_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category with details"""
        # Create parent category
        parent_response = await client.post(
            "/product-categories",
            json={"name": "Parent Category", "slug": "parent-category"}
        )
        parent_id = get_response_data(parent_response.json())["id"]
        
        # Create subcategory
        subcategory_data = CATEGORY_DATA_WITH_PARENT.copy()
        subcategory_data["parent_category_id"] = parent_id
        subcategory_response = await client.post(
            "/product-categories",
            json=subcategory_data
        )
        subcategory_id = get_response_data(subcategory_response.json())["id"]
        
        response = await client.get(f"/product-categories/{subcategory_id}/with-details")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == subcategory_id
        assert "parent_category" in data
        assert "subcategories" in data
        assert "products" in data
    
    @pytest.mark.asyncio
    async def test_get_category_with_offers_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category with offers"""
        # Create category
        create_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        category_id = get_response_data(create_response.json())["id"]
        
        response = await client.get(f"/product-categories/{category_id}/with-offers")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == category_id
        assert "offers" in data
        assert isinstance(data["offers"], list)
    
    @pytest.mark.asyncio
    async def test_get_category_offers_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting category offers"""
        # Create category
        create_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        category_id = get_response_data(create_response.json())["id"]
        
        response = await client.get(f"/product-categories/{category_id}/offers")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert isinstance(data, list)


class TestUpdateCategoryAPI:
    """Tests for /product-categories/{category_id} endpoint (PUT)"""
    
    @pytest.mark.asyncio
    async def test_update_category_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful category update"""
        create_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        category_id = get_response_data(create_response.json())["id"]
        
        response = await client.put(
            f"/product-categories/{category_id}",
            json=CATEGORY_UPDATE_DATA
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["name"] == CATEGORY_UPDATE_DATA["name"]
        assert data["slug"] == CATEGORY_UPDATE_DATA["slug"]
    
    @pytest.mark.asyncio
    async def test_update_category_partial(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test partial category update"""
        create_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        category_id = get_response_data(create_response.json())["id"]
        
        response = await client.put(
            f"/product-categories/{category_id}",
            json={"name": "Only Name Updated"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["name"] == "Only Name Updated"
        # Slug should remain unchanged
        assert data["slug"] == CATEGORY_DATA["slug"]
    
    @pytest.mark.asyncio
    async def test_update_category_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test updating non-existent category"""
        response = await client.put(
            "/product-categories/99999",
            json=CATEGORY_UPDATE_DATA
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteCategoryAPI:
    """Tests for /product-categories/{category_id} endpoint (DELETE)"""
    
    @pytest.mark.asyncio
    async def test_delete_category_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful category deletion"""
        create_response = await client.post(
            "/product-categories",
            json=CATEGORY_DATA
        )
        category_id = get_response_data(create_response.json())["id"]
        
        response = await client.delete(f"/product-categories/{category_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify category was deleted
        result = await test_session.execute(
            select(ProductCategory).where(ProductCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        assert category is None
    
    @pytest.mark.asyncio
    async def test_delete_category_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test deleting non-existent category"""
        response = await client.delete("/product-categories/99999")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestGetCategoriesSummaryAPI:
    """Tests for /product-categories/summary/stats endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_categories_summary_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting categories summary statistics"""
        # Create some categories
        for i in range(3):
            category_data = {
                "name": f"Summary Category {i}",
                "slug": f"summary-category-{i}"
            }
            await client.post(
                "/product-categories",
                json=category_data
            )
        
        response = await client.get("/product-categories/summary/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "total_categories" in data
        assert "total_root_categories" in data
        assert "avg_products_per_category" in data
        assert data["total_categories"] >= 3


class TestGetCategoriesByIDsAPI:
    """Tests for /product-categories/by-ids endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_categories_by_ids_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting categories by list of IDs"""
        category_ids = []
        for i in range(3):
            category_data = {
                "name": f"ByID Category {i}",
                "slug": f"byid-category-{i}"
            }
            create_response = await client.post(
                "/product-categories",
                json=category_data
            )
            category_id = get_response_data(create_response.json())["id"]
            category_ids.append(category_id)
        
        response = await client.post(
            "/product-categories/by-ids",
            json=category_ids
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) == 3
        assert all(cat["id"] in category_ids for cat in data)
    
    @pytest.mark.asyncio
    async def test_get_categories_by_ids_empty_list(self, client, mock_settings, mock_image_manager_init):
        """Test getting categories by empty list"""
        response = await client.post(
            "/product-categories/by-ids",
            json=[]
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_get_categories_by_ids_nonexistent(self, client, mock_settings, mock_image_manager_init):
        """Test getting categories by non-existent IDs"""
        response = await client.post(
            "/product-categories/by-ids",
            json=[99999, 99998]
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) == 0
