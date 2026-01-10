"""
API integration tests for sellers endpoints
"""
import pytest
from fastapi import status
from sqlalchemy import select
from unittest.mock import patch, AsyncMock

from app.auth.models import User
from app.sellers.models import Seller


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

SELLER_DATA_UR = {
    "full_name": "ООО Тестовая Компания",
    "short_name": "ТестКомпания",
    "description": "Тестовый продавец",
    "inn": "1234567890",
    "is_IP": False,
    "ogrn": "1234567890123"
}

SELLER_UPDATE_DATA = {
    "short_name": "Обновленное название",
    "description": "Обновленное описание",
    "status": 1,
    "verification_level": 2
}


def get_response_data(response_data: dict) -> dict:
    return response_data.get("data", response_data)


class TestCreateSellerAPI:
    """Tests for /sellers endpoint (POST)"""
    
    @pytest.mark.asyncio
    async def test_create_seller_ip_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful seller creation (IP)"""
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        response = await client.post(
            "/sellers",
            json=SELLER_DATA_IP,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["full_name"] == SELLER_DATA_IP["full_name"]
        assert data["is_IP"] is True
        
        result = await test_session.execute(select(User).where(User.email == TEST_EMAIL))
        user = result.scalar_one_or_none()
        assert user.is_seller is True
    
    @pytest.mark.asyncio
    async def test_create_seller_ur_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful seller creation (UR)"""
        response = await client.post(
            "/auth/register",
            json={"email": "company@example.com", "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        response = await client.post(
            "/sellers",
            json=SELLER_DATA_UR,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["is_IP"] is False
    
    @pytest.mark.asyncio
    async def test_create_seller_already_exists(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test creating seller when user already has one"""
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        await client.post(
            "/sellers",
            json=SELLER_DATA_IP,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        response = await client.post(
            "/sellers",
            json=SELLER_DATA_UR,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_create_seller_no_auth(self, client, mock_settings, mock_image_manager_init):
        """Test creating seller without authentication"""
        response = await client.post(
            "/sellers",
            json=SELLER_DATA_IP
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetSellerAPI:
    """Tests for /sellers/{seller_id} and /sellers/me"""
    
    @pytest.mark.asyncio
    async def test_get_seller_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting seller by ID"""
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        create_response = await client.post(
            "/sellers",
            json=SELLER_DATA_IP,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(create_response.json())["id"]
        
        response = await client.get(f"/sellers/{seller_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == seller_id
        assert data["short_name"] == SELLER_DATA_IP["short_name"]
    
    @pytest.mark.asyncio
    async def test_get_seller_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test getting non-existent seller"""
        response = await client.get("/sellers/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_my_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting current user's seller"""
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        await client.post(
            "/sellers",
            json=SELLER_DATA_IP,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["full_name"] == SELLER_DATA_IP["full_name"]
    
    @pytest.mark.asyncio
    async def test_get_my_seller_no_seller_account(self, client, mock_settings, mock_image_manager_init):
        """Test getting my seller when user has no seller account"""
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        response = await client.get(
            "/sellers/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetSellersListAPI:
    """Tests for /sellers endpoint (GET - list)"""
    
    @pytest.mark.asyncio
    async def test_get_sellers_list_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting paginated list of sellers"""
        for i in range(3):
            email = f"test{i}@example.com"
            response = await client.post(
                "/auth/register",
                json={"email": email, "password": TEST_PASSWORD}
            )
            data = get_response_data(response.json())
            access_token = data["access_token"]
            
            seller_data = SELLER_DATA_IP.copy()
            seller_data["short_name"] = f"Seller {i}"
            seller_data["inn"] = f"12345678901{i}"
            
            await client.post(
                "/sellers",
                json=seller_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        response = await client.get("/sellers?page=1&page_size=10")
        
        assert response.status_code == status.HTTP_200_OK
        # data = get_response_data(response.json())
        data = response.json()
        assert data["pagination"]["total_items"] >= 3
        assert len(data["data"]) >= 3
    
    @pytest.mark.asyncio
    async def test_get_sellers_list_pagination(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test pagination"""
        for i in range(5):
            email = f"page{i}@example.com"
            response = await client.post(
                "/auth/register",
                json={"email": email, "password": TEST_PASSWORD}
            )
            data = get_response_data(response.json())
            access_token = data["access_token"]
            
            seller_data = SELLER_DATA_IP.copy()
            seller_data["short_name"] = f"Page {i}"
            seller_data["inn"] = f"12345678904{i}"
            
            await client.post(
                "/sellers",
                json=seller_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        response = await client.get("/sellers?page=1&page_size=2")
        assert response.status_code == status.HTTP_200_OK
        # data = get_response_data(response.json())
        data = response.json()
        assert len(data["data"]) == 2
        assert data["pagination"]["page"] == 1


class TestUpdateSellerAPI:
    """Tests for /sellers/{seller_id} endpoint (PUT)"""
    
    @pytest.mark.asyncio
    async def test_update_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful seller update"""
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        create_response = await client.post(
            "/sellers",
            json=SELLER_DATA_IP,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(create_response.json())["id"]
        
        response = await client.put(
            f"/sellers/{seller_id}",
            json=SELLER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["short_name"] == SELLER_UPDATE_DATA["short_name"]
    
    @pytest.mark.asyncio
    async def test_update_seller_not_own(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test updating another user's seller (should fail)"""
        response = await client.post(
            "/auth/register",
            json={"email": "user1@example.com", "password": TEST_PASSWORD}
        )
        data1 = get_response_data(response.json())
        access_token1 = data1["access_token"]
        
        create_response = await client.post(
            "/sellers",
            json=SELLER_DATA_IP,
            headers={"Authorization": f"Bearer {access_token1}"}
        )
        seller1_id = get_response_data(create_response.json())["id"]
        
        response = await client.post(
            "/auth/register",
            json={"email": "user2@example.com", "password": TEST_PASSWORD}
        )
        data2 = get_response_data(response.json())
        access_token2 = data2["access_token"]
        
        response = await client.put(
            f"/sellers/{seller1_id}",
            json=SELLER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {access_token2}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteSellerAPI:
    """Tests for /sellers/{seller_id} endpoint (DELETE)"""
    
    @pytest.mark.asyncio
    async def test_delete_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful seller deletion"""
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        create_response = await client.post(
            "/sellers",
            json=SELLER_DATA_IP,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(create_response.json())["id"]
        
        response = await client.delete(
            f"/sellers/{seller_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        result = await test_session.execute(select(Seller).where(Seller.id == seller_id))
        seller = result.scalar_one_or_none()
        assert seller is None


class TestGetSellersSummaryAPI:
    """Tests for /sellers/summary/stats endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_sellers_summary_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting sellers summary statistics"""
        for i in range(2):
            email = f"summary{i}@example.com"
            response = await client.post(
                "/auth/register",
                json={"email": email, "password": TEST_PASSWORD}
            )
            data = get_response_data(response.json())
            access_token = data["access_token"]
            
            seller_data = SELLER_DATA_IP.copy()
            seller_data["short_name"] = f"Summary {i}"
            seller_data["inn"] = f"12345678905{i}"
            
            await client.post(
                "/sellers",
                json=seller_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        response = await client.get("/sellers/summary/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "total_sellers" in data
        assert data["total_sellers"] >= 2


class TestGetSellersByIDsAPI:
    """Tests for /sellers/by-ids endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_sellers_by_ids_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting sellers by list of IDs"""
        seller_ids = []
        for i in range(3):
            email = f"byid{i}@example.com"
            response = await client.post(
                "/auth/register",
                json={"email": email, "password": TEST_PASSWORD}
            )
            data = get_response_data(response.json())
            access_token = data["access_token"]
            
            seller_data = SELLER_DATA_IP.copy()
            seller_data["short_name"] = f"ByID {i}"
            seller_data["inn"] = f"12345678906{i}"
            
            create_response = await client.post(
                "/sellers",
                json=seller_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            seller_id = get_response_data(create_response.json())["id"]
            seller_ids.append(seller_id)
        
        response = await client.post(
            "/sellers/by-ids",
            json=seller_ids
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) == 3


class TestSellerImageAPI:
    """Tests for seller image upload and deletion"""
    
    @pytest.mark.asyncio
    async def test_upload_seller_image_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful seller image upload"""
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = get_response_data(response.json())
        access_token = data["access_token"]
        
        create_response = await client.post(
            "/sellers",
            json=SELLER_DATA_IP,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        seller_id = get_response_data(create_response.json())["id"]
        
        with patch('app.sellers.manager.ImageManager.upload_image', new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = "test/path/image.jpg"
            
            response = await client.post(
                f"/sellers/{seller_id}/images",
                files={"file": ("test.jpg", b"fake image data", "image/jpeg")},
                data={"order": 0},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = get_response_data(response.json())
            assert "path" in data
