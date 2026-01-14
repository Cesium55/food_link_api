"""
API integration tests for shop points endpoints
"""
import pytest
from fastapi import status
from sqlalchemy import select
from unittest.mock import patch, AsyncMock, Mock

from app.auth.models import User
from app.sellers.models import Seller
from app.shop_points.models import ShopPoint


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

SHOP_POINT_UPDATE_DATA = {
    "latitude": 56.0,
    "longitude": 38.0,
    "city": "Обновленный город"
}

SHOP_POINT_BY_ADDRESS_DATA = {
    "raw_address": "Москва, Красная площадь, 1"
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


class TestCreateShopPointAPI:
    """Tests for /shop-points endpoint (POST)"""
    
    @pytest.mark.asyncio
    async def test_create_shop_point_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful shop point creation"""
        access_token = await create_seller_and_get_token(client)
        
        # Get seller ID from created seller
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
        data = get_response_data(response.json())
        assert data["seller_id"] == seller_id
        assert data["latitude"] == SHOP_POINT_DATA["latitude"]
        
        # Verify shop point was created in database
        result = await test_session.execute(
            select(ShopPoint).where(ShopPoint.seller_id == seller_id)
        )
        shop_point = result.scalar_one_or_none()
        assert shop_point is not None
    
    @pytest.mark.asyncio
    async def test_create_shop_point_wrong_seller(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test creating shop point for another seller (should fail)"""
        access_token1 = await create_seller_and_get_token(client, "seller1@example.com")
        
        # Create second seller
        access_token2 = await create_seller_and_get_token(client, "seller2@example.com")
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        seller2_id = get_response_data(response.json())["id"]
        
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller2_id
        
        # Try to create shop point for seller2 using seller1's token
        response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_create_shop_point_no_auth(self, client, mock_settings, mock_image_manager_init):
        """Test creating shop point without authentication"""
        response = await client.post(
            "/shop-points",
            json=SHOP_POINT_DATA
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_create_shop_point_invalid_data(self, client, mock_settings, mock_image_manager_init):
        """Test creating shop point with invalid data"""
        access_token = await create_seller_and_get_token(client)
        
        # Test with invalid latitude type (should be float, not string)
        invalid_data = SHOP_POINT_DATA.copy()
        invalid_data["latitude"] = "invalid"
        
        response = await client.post(
            "/shop-points",
            json=invalid_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetShopPointAPI:
    """Tests for /shop-points/{shop_point_id} endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_shop_point_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting shop point by ID"""
        access_token = await create_seller_and_get_token(client)
        
        # Get seller ID
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        # Create shop point
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        create_response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        shop_point_id = get_response_data(create_response.json())["id"]
        
        # Get shop point
        response = await client.get(f"/shop-points/{shop_point_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == shop_point_id
        assert data["seller_id"] == seller_id
    
    @pytest.mark.asyncio
    async def test_get_shop_point_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test getting non-existent shop point"""
        response = await client.get("/shop-points/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_shop_points_by_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting shop points by seller ID"""
        access_token = await create_seller_and_get_token(client)
        
        # Get seller ID
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        # Create shop points
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        for i in range(2):
            shop_point_data["latitude"] = 55.7558 + i * 0.01
            await client.post(
                "/shop-points",
                json=shop_point_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        # Get shop points by seller
        response = await client.get(f"/shop-points/seller/{seller_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) >= 2
    
    @pytest.mark.asyncio
    async def test_get_shop_point_with_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting shop point with seller information"""
        access_token = await create_seller_and_get_token(client)
        
        # Get seller ID
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        # Create shop point
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        create_response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        shop_point_id = get_response_data(create_response.json())["id"]
        
        # Get shop point with seller
        response = await client.get(f"/shop-points/{shop_point_id}/with-seller")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == shop_point_id
        assert "seller" in data
        assert data["seller"]["id"] == seller_id


class TestGetShopPointsListAPI:
    """Tests for /shop-points endpoint (GET - list)"""
    
    @pytest.mark.asyncio
    async def test_get_shop_points_list_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting paginated list of shop points"""
        # Create multiple sellers and shop points
        for i in range(2):
            email = f"shop{i}@example.com"
            access_token = await create_seller_and_get_token(client, email)
            
            response = await client.get(
                "/sellers/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            seller_id = get_response_data(response.json())["id"]
            
            shop_point_data = SHOP_POINT_DATA.copy()
            shop_point_data["seller_id"] = seller_id
            shop_point_data["city"] = f"City {i}"
            await client.post(
                "/shop-points",
                json=shop_point_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        response = await client.get("/shop-points?page=1&page_size=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pagination"]["total_items"] >= 2
        assert len(data["data"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_shop_points_list_pagination(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test pagination"""
        access_token = await create_seller_and_get_token(client)
        
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        # Create multiple shop points
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        for i in range(5):
            shop_point_data["latitude"] = 55.7558 + i * 0.01
            await client.post(
                "/shop-points",
                json=shop_point_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        response = await client.get("/shop-points?page=1&page_size=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 2
        assert data["pagination"]["page"] == 1
    
    @pytest.mark.asyncio
    async def test_get_shop_points_with_filters(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting shop points with filters"""
        access_token = await create_seller_and_get_token(client)
        
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        shop_point_data["region"] = "Москва"
        shop_point_data["city"] = "Москва"
        await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        response = await client.get("/shop-points?region=Москва&city=Москва")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) >= 1


class TestUpdateShopPointAPI:
    """Tests for /shop-points/{shop_point_id} endpoint (PUT)"""
    
    @pytest.mark.asyncio
    async def test_update_shop_point_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful shop point update"""
        access_token = await create_seller_and_get_token(client)
        
        # Get seller ID
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        # Create shop point
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        create_response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        shop_point_id = get_response_data(create_response.json())["id"]
        
        # Update shop point
        response = await client.put(
            f"/shop-points/{shop_point_id}",
            json=SHOP_POINT_UPDATE_DATA,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["city"] == SHOP_POINT_UPDATE_DATA["city"]
        assert data["latitude"] == SHOP_POINT_UPDATE_DATA["latitude"]
    
    @pytest.mark.asyncio
    async def test_update_shop_point_not_own(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test updating another seller's shop point (should fail)"""
        access_token1 = await create_seller_and_get_token(client, "user1@example.com")
        
        # Get seller1 ID and create shop point
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        seller1_id = get_response_data(response.json())["id"]
        
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller1_id
        create_response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        shop_point1_id = get_response_data(create_response.json())["id"]
        
        # Create second seller
        access_token2 = await create_seller_and_get_token(client, "user2@example.com")
        
        # Try to update shop point of seller1 using seller2's token
        response = await client.put(
            f"/shop-points/{shop_point1_id}",
            json=SHOP_POINT_UPDATE_DATA,
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_update_shop_point_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test updating non-existent shop point"""
        access_token = await create_seller_and_get_token(client)
        
        response = await client.put(
            "/shop-points/99999",
            json=SHOP_POINT_UPDATE_DATA,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteShopPointAPI:
    """Tests for /shop-points/{shop_point_id} endpoint (DELETE)"""
    
    @pytest.mark.asyncio
    async def test_delete_shop_point_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful shop point deletion"""
        access_token = await create_seller_and_get_token(client)
        
        # Get seller ID
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        # Create shop point
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        create_response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        shop_point_id = get_response_data(create_response.json())["id"]
        
        # Delete shop point
        response = await client.delete(
            f"/shop-points/{shop_point_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify shop point was deleted
        result = await test_session.execute(select(ShopPoint).where(ShopPoint.id == shop_point_id))
        shop_point = result.scalar_one_or_none()
        assert shop_point is None
    
    @pytest.mark.asyncio
    async def test_delete_shop_point_not_own(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test deleting another seller's shop point (should fail)"""
        access_token1 = await create_seller_and_get_token(client, "user1@example.com")
        
        # Get seller1 ID and create shop point
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        seller1_id = get_response_data(response.json())["id"]
        
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller1_id
        create_response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        shop_point1_id = get_response_data(create_response.json())["id"]
        
        # Create second seller
        access_token2 = await create_seller_and_get_token(client, "user2@example.com")
        
        # Try to delete shop point of seller1 using seller2's token
        response = await client.delete(
            f"/shop-points/{shop_point1_id}",
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetShopPointsSummaryAPI:
    """Tests for /shop-points/summary/stats endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_shop_points_summary_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting shop points summary statistics"""
        # Create some shop points
        for i in range(2):
            email = f"summary{i}@example.com"
            access_token = await create_seller_and_get_token(client, email)
            
            response = await client.get(
                "/sellers/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            seller_id = get_response_data(response.json())["id"]
            
            shop_point_data = SHOP_POINT_DATA.copy()
            shop_point_data["seller_id"] = seller_id
            await client.post(
                "/shop-points",
                json=shop_point_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        response = await client.get("/shop-points/summary/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "total_shop_points" in data
        assert "total_sellers" in data
        assert "avg_shop_points_per_seller" in data
        assert data["total_shop_points"] >= 2


class TestGetShopPointsByIDsAPI:
    """Tests for /shop-points/by-ids endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_shop_points_by_ids_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting shop points by list of IDs"""
        shop_point_ids = []
        access_token = await create_seller_and_get_token(client)
        
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        for i in range(3):
            shop_point_data["latitude"] = 55.7558 + i * 0.01
            create_response = await client.post(
                "/shop-points",
                json=shop_point_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            shop_point_id = get_response_data(create_response.json())["id"]
            shop_point_ids.append(shop_point_id)
        
        response = await client.post(
            "/shop-points/by-ids",
            json=shop_point_ids
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) == 3
        assert all(sp["id"] in shop_point_ids for sp in data)


class TestCreateShopPointByAddressAPI:
    """Tests for /shop-points/by-address endpoint"""
    
    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful shop point creation by address"""
        access_token = await create_seller_and_get_token(client)
        
        with patch('app.shop_points.manager.create_geocoder') as mock_create_geocoder:
            mock_geocoder = AsyncMock()
            mock_geocode_result = Mock()
            mock_geocode_result.latitude = 55.7558
            mock_geocode_result.longitude = 37.6173
            mock_geocode_result.address_raw = "Москва, Красная площадь, 1"
            mock_geocode_result.formatted_address = "Россия, Москва, Красная площадь, 1"
            mock_geocode_result.region = "Москва"
            mock_geocode_result.city = "Москва"
            mock_geocode_result.street = "Красная площадь"
            mock_geocode_result.house = "1"
            mock_geocode_result.geo_id = "geo_id_123"
            
            mock_geocoder.geocode_address = AsyncMock(return_value=mock_geocode_result)
            mock_geocoder.close = AsyncMock()
            mock_create_geocoder.return_value = mock_geocoder
            
            response = await client.post(
                "/shop-points/by-address",
                json=SHOP_POINT_BY_ADDRESS_DATA,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = get_response_data(response.json())
            assert data["city"] == "Москва"
            assert data["latitude"] == 55.7558
    
    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_not_seller(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test creating shop point by address when user is not seller"""
        # Create user without seller account
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        response = await client.post(
            "/shop-points/by-address",
            json=SHOP_POINT_BY_ADDRESS_DATA,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_no_auth(self, client, mock_settings, mock_image_manager_init):
        """Test creating shop point by address without authentication"""
        response = await client.post(
            "/shop-points/by-address",
            json=SHOP_POINT_BY_ADDRESS_DATA
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestShopPointImageAPI:
    """Tests for shop point image upload and deletion"""
    
    @pytest.mark.asyncio
    async def test_upload_shop_point_image_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful shop point image upload"""
        access_token = await create_seller_and_get_token(client)
        
        # Get seller ID
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(response.json())["id"]
        
        # Create shop point
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller_id
        create_response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        shop_point_id = get_response_data(create_response.json())["id"]
        
        with patch('app.shop_points.manager.ImageManager.upload_image', new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = "test/path/image.jpg"
            
            response = await client.post(
                f"/shop-points/{shop_point_id}/images",
                files={"file": ("test.jpg", b"fake image data", "image/jpeg")},
                data={"order": 0},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = get_response_data(response.json())
            assert "path" in data
    
    @pytest.mark.asyncio
    async def test_upload_shop_point_image_not_own(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test uploading image for another seller's shop point (should fail)"""
        access_token1 = await create_seller_and_get_token(client, "user1@example.com")
        
        # Get seller1 ID and create shop point
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        seller1_id = get_response_data(response.json())["id"]
        
        shop_point_data = SHOP_POINT_DATA.copy()
        shop_point_data["seller_id"] = seller1_id
        create_response = await client.post(
            "/shop-points",
            json=shop_point_data,
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        shop_point1_id = get_response_data(create_response.json())["id"]
        
        # Create second seller
        access_token2 = await create_seller_and_get_token(client, "user2@example.com")
        
        # Try to upload image for seller1's shop point using seller2's token
        response = await client.post(
            f"/shop-points/{shop_point1_id}/images",
            files={"file": ("test.jpg", b"fake image data", "image/jpeg")},
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
