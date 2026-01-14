"""
API integration tests for offers endpoints
"""
import pytest
from fastapi import status
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.auth.models import User
from app.sellers.models import Seller
from app.products.models import Product
from app.shop_points.models import ShopPoint
from app.offers.models import Offer


TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"

SELLER_DATA_IP = {
    "full_name": "Иванов Иван Иванович",
    "short_name": "Иванов ИП",
    "description": "Тестовый продавец",
    "inn": "123456789012",
    "is_IP": True,
    "ogrn": "123456789012345"
}

PRODUCT_DATA = {
    "name": "Test Product",
    "description": "Test product description",
    "article": "ART-001",
    "code": "CODE-001",
    "category_ids": [],
    "attributes": []
}

SHOP_POINT_DATA = {
    "seller_id": 1,
    "latitude": 55.7558,
    "longitude": 37.6173,
    "address_raw": "Москва, Красная площадь, 1",
    "address_formated": "Россия, Москва, Красная площадь, 1",
    "region": "Москва",
    "city": "Москва",
    "street": "Красная площадь",
    "house": "1",
    "geo_id": "geo_id_123"
}

OFFER_DATA_FIXED_PRICE = {
    "product_id": 1,
    "shop_id": 1,
    "pricing_strategy_id": None,
    "expires_date": None,
    "original_cost": None,
    "current_cost": "80.00",
    "count": 10
}

OFFER_DATA_DYNAMIC_PRICING = {
    "product_id": 1,
    "shop_id": 1,
    "pricing_strategy_id": None,  # Will be set in test
    "expires_date": None,  # Will be set in test
    "original_cost": "100.00",
    "current_cost": None,
    "count": 10
}

OFFER_UPDATE_DATA = {
    "current_cost": "75.00",
    "count": 15
}


def get_response_data(response_data: dict) -> dict:
    """Helper function to extract data from wrapped response"""
    return response_data.get("data", response_data)


async def create_seller_and_get_token(client, email: str = TEST_EMAIL) -> str:
    """Helper function to create seller and get access token"""
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": TEST_PASSWORD}
    )
    data = get_response_data(response.json())
    access_token = data["access_token"]
    
    await client.post(
        "/sellers",
        json=SELLER_DATA_IP,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    return access_token


async def create_product(client, access_token: str) -> dict:
    """Helper function to create product and return its data"""
    response = await client.post(
        "/products",
        json=PRODUCT_DATA,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())


async def create_shop_point(client, access_token: str) -> dict:
    """Helper function to create shop point and return its data"""
    # Get seller ID
    response = await client.get(
        "/sellers/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    seller_id = get_response_data(response.json())["id"]
    
    shop_point_data = SHOP_POINT_DATA.copy()
    shop_point_data["seller_id"] = seller_id
    
    response = await client.post(
        "/shop-points",
        json=shop_point_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())


async def create_offer(client, access_token: str, offer_data: dict = None) -> dict:
    """Helper function to create offer and return its data"""
    if offer_data is None:
        offer_data = OFFER_DATA_FIXED_PRICE.copy()
    
    response = await client.post(
        "/offers",
        json=offer_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())


class TestCreateOfferAPI:
    """Tests for /offers endpoint (POST)"""
    
    @pytest.mark.asyncio
    async def test_create_offer_fixed_price_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful offer creation with fixed price"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        
        offer_data = OFFER_DATA_FIXED_PRICE.copy()
        offer_data["product_id"] = product["id"]
        offer_data["shop_id"] = shop_point["id"]
        
        response = await client.post(
            "/offers",
            json=offer_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["product_id"] == product["id"]
        assert data["shop_id"] == shop_point["id"]
        # Convert string to Decimal for comparison
        assert Decimal(str(data["current_cost"])) == Decimal(offer_data["current_cost"])
        assert data["count"] == offer_data["count"]
        
        # Verify offer was created in database
        result = await test_session.execute(
            select(Offer).where(Offer.id == data["id"])
        )
        offer = result.scalar_one_or_none()
        assert offer is not None
        assert offer.product_id == product["id"]
    
    @pytest.mark.asyncio
    async def test_create_offer_no_auth(self, client, mock_settings, mock_image_manager_init):
        """Test creating offer without authentication"""
        response = await client.post(
            "/offers",
            json=OFFER_DATA_FIXED_PRICE
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_create_offer_product_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test creating offer when product not found"""
        access_token = await create_seller_and_get_token(client)
        
        offer_data = OFFER_DATA_FIXED_PRICE.copy()
        offer_data["product_id"] = 99999
        
        response = await client.post(
            "/offers",
            json=offer_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_create_offer_shop_point_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test creating offer when shop point not found"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        
        offer_data = OFFER_DATA_FIXED_PRICE.copy()
        offer_data["product_id"] = product["id"]
        offer_data["shop_id"] = 99999
        
        response = await client.post(
            "/offers",
            json=offer_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_create_offer_wrong_owner(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test creating offer for product/shop point owned by another seller"""
        access_token1 = await create_seller_and_get_token(client)
        product1 = await create_product(client, access_token1)
        shop_point1 = await create_shop_point(client, access_token1)
        
        access_token2 = await create_seller_and_get_token(client, "seller2@example.com")
        
        offer_data = OFFER_DATA_FIXED_PRICE.copy()
        offer_data["product_id"] = product1["id"]
        offer_data["shop_id"] = shop_point1["id"]
        
        response = await client.post(
            "/offers",
            json=offer_data,
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_create_offer_invalid_data(self, client, mock_settings, mock_image_manager_init):
        """Test creating offer with invalid data"""
        access_token = await create_seller_and_get_token(client)
        
        # Missing required fields
        response = await client.post(
            "/offers",
            json={"product_id": 1},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetOfferAPI:
    """Tests for /offers/{offer_id} endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_offer_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting offer by ID"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        offer = await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        offer_id = offer["id"]
        
        response = await client.get(f"/offers/{offer_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == offer_id
        assert data["product_id"] == product["id"]
    
    @pytest.mark.asyncio
    async def test_get_offer_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test getting non-existent offer"""
        response = await client.get("/offers/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_offer_with_product(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting offer with product information"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        offer = await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        offer_id = offer["id"]
        
        response = await client.get(f"/offers/{offer_id}/with-product")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "product" in data
        assert data["product"]["id"] == product["id"]


class TestGetOffersListAPI:
    """Tests for /offers endpoint (GET)"""
    
    @pytest.mark.asyncio
    async def test_get_offers_list_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting list of offers"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        
        response = await client.get("/offers")
        
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        # Middleware wraps paginated responses: {"data": items, "pagination": {...}}
        assert "data" in response_json
        assert "pagination" in response_json
        assert isinstance(response_json["data"], list)
        assert len(response_json["data"]) >= 1
    
    @pytest.mark.asyncio
    async def test_get_offers_paginated(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting paginated offers"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        
        response = await client.get("/offers?page=1&page_size=10")
        
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        assert "data" in response_json
        assert "pagination" in response_json
        assert response_json["pagination"]["page"] == 1
        assert response_json["pagination"]["page_size"] == 10
    
    @pytest.mark.asyncio
    async def test_get_offers_filter_by_product_id(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test filtering offers by product ID"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        
        response = await client.get(f"/offers?product_id={product['id']}")
        
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        assert "data" in response_json
        assert isinstance(response_json["data"], list)
        assert len(response_json["data"]) >= 1
        assert all(item["product_id"] == product["id"] for item in response_json["data"])
    
    @pytest.mark.asyncio
    async def test_get_offers_filter_by_seller_id(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test filtering offers by seller ID"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        
        # Get seller ID
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        response = await client.get(f"/offers?seller_id={seller_id}")
        
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        assert "data" in response_json
        assert isinstance(response_json["data"], list)
        assert len(response_json["data"]) >= 1
    
    @pytest.mark.asyncio
    async def test_get_offers_filter_by_cost_range(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test filtering offers by cost range"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        
        response = await client.get("/offers?min_current_cost=50.00&max_current_cost=100.00")
        
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        assert "data" in response_json
        assert isinstance(response_json["data"], list)
    
    @pytest.mark.asyncio
    async def test_get_offers_with_products(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting offers with products"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        
        response = await client.get("/offers/with-products")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "product" in data[0]


class TestUpdateOfferAPI:
    """Tests for /offers/{offer_id} endpoint (PUT)"""
    
    @pytest.mark.asyncio
    async def test_update_offer_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful offer update"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        offer = await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        offer_id = offer["id"]
        
        response = await client.put(
            f"/offers/{offer_id}",
            json=OFFER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        # Convert string to Decimal for comparison
        assert Decimal(str(data["current_cost"])) == Decimal(OFFER_UPDATE_DATA["current_cost"])
        assert data["count"] == OFFER_UPDATE_DATA["count"]
        
        # Verify offer was updated in database
        result = await test_session.execute(
            select(Offer).where(Offer.id == offer_id)
        )
        updated_offer = result.scalar_one_or_none()
        assert updated_offer.count == OFFER_UPDATE_DATA["count"]
    
    @pytest.mark.asyncio
    async def test_update_offer_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test updating non-existent offer"""
        access_token = await create_seller_and_get_token(client)
        
        response = await client.put(
            "/offers/99999",
            json=OFFER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_update_offer_no_auth(self, client, mock_settings, mock_image_manager_init):
        """Test updating offer without authentication"""
        response = await client.put(
            "/offers/1",
            json=OFFER_UPDATE_DATA
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_update_offer_wrong_owner(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test updating offer owned by another seller"""
        access_token1 = await create_seller_and_get_token(client)
        product1 = await create_product(client, access_token1)
        shop_point1 = await create_shop_point(client, access_token1)
        offer = await create_offer(client, access_token1, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product1["id"],
            "shop_id": shop_point1["id"]
        })
        offer_id = offer["id"]
        
        access_token2 = await create_seller_and_get_token(client, "seller2@example.com")
        
        response = await client.put(
            f"/offers/{offer_id}",
            json=OFFER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteOfferAPI:
    """Tests for /offers/{offer_id} endpoint (DELETE)"""
    
    @pytest.mark.asyncio
    async def test_delete_offer_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful offer deletion"""
        access_token = await create_seller_and_get_token(client)
        product = await create_product(client, access_token)
        shop_point = await create_shop_point(client, access_token)
        offer = await create_offer(client, access_token, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product["id"],
            "shop_id": shop_point["id"]
        })
        offer_id = offer["id"]
        
        response = await client.delete(
            f"/offers/{offer_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify offer was deleted from database
        result = await test_session.execute(
            select(Offer).where(Offer.id == offer_id)
        )
        deleted_offer = result.scalar_one_or_none()
        assert deleted_offer is None
    
    @pytest.mark.asyncio
    async def test_delete_offer_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test deleting non-existent offer"""
        access_token = await create_seller_and_get_token(client)
        
        response = await client.delete(
            "/offers/99999",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_offer_no_auth(self, client, mock_settings, mock_image_manager_init):
        """Test deleting offer without authentication"""
        response = await client.delete("/offers/1")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_delete_offer_wrong_owner(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test deleting offer owned by another seller"""
        access_token1 = await create_seller_and_get_token(client)
        product1 = await create_product(client, access_token1)
        shop_point1 = await create_shop_point(client, access_token1)
        offer = await create_offer(client, access_token1, {
            **OFFER_DATA_FIXED_PRICE,
            "product_id": product1["id"],
            "shop_id": shop_point1["id"]
        })
        offer_id = offer["id"]
        
        access_token2 = await create_seller_and_get_token(client, "seller2@example.com")
        
        response = await client.delete(
            f"/offers/{offer_id}",
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPricingStrategiesAPI:
    """Tests for pricing strategies endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_pricing_strategies(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting pricing strategies list"""
        response = await client.get("/offers/pricing-strategies")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_pricing_strategy_by_id_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test getting non-existent pricing strategy"""
        response = await client.get("/offers/pricing-strategies/99999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
