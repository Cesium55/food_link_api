# """
# API integration tests for purchases endpoints
# """
# import pytest
# from fastapi import status
# from sqlalchemy import select
# from unittest.mock import patch, AsyncMock, Mock
# from datetime import datetime, timezone, timedelta
# from decimal import Decimal
# from pathlib import Path
# import uuid

# from app.auth.models import User
# from app.sellers.models import Seller
# from app.products.models import Product
# from app.product_categories.models import ProductCategory
# from app.shop_points.models import ShopPoint
# from app.offers.models import Offer
# from app.purchases.models import Purchase, PurchaseStatus, PurchaseOffer
# from app.payments.models import UserPayment, PaymentStatus


# # Simple test logger function
# # Write to /home/mak/food_link/api/logs/ (outside src folder)
# TEST_LOG_FILE = Path(__file__).parent.parent.parent.parent / "logs" / "test_purchases_detailed.log"

# def log_test(message: str):
#     """Simple synchronous logger for tests"""
#     timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
#     log_message = f"{timestamp} | {message}\n"
    
#     # Create log directory if it doesn't exist
#     TEST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
#     # Write to file
#     with open(TEST_LOG_FILE, 'a', encoding='utf-8') as f:
#         f.write(log_message)
    
#     # Also output to console (using builtin print, not recursive call)
#     import builtins
#     builtins.print(f"[LOG] {message}")


# TEST_EMAIL = "test@example.com"
# TEST_PASSWORD = "password123"
# TEST_SELLER_EMAIL = "seller@example.com"
# TEST_BUYER_EMAIL = "buyer@example.com"  # Not used anymore, using unique_email() instead


# def unique_email(prefix: str = "user") -> str:
#     """Generate unique email for each test"""
#     return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"

# SELLER_DATA_IP = {
#     "full_name": "Иванов Иван Иванович",
#     "short_name": "Иванов ИП",
#     "description": "Тестовый продавец",
#     "inn": "123456789012",
#     "is_IP": True,
#     "ogrn": "123456789012345"
# }

# SHOP_POINT_DATA = {
#     "name": "Test Shop Point",
#     "address": "Test Address",
#     "latitude": 55.7558,
#     "longitude": 37.6173,
# }

# PRODUCT_DATA = {
#     "name": "Test Product",
#     "description": "Test product description",
#     "article": "ART-001",
#     "code": "CODE-001",
#     "category_ids": [],
#     "attributes": []
# }

# OFFER_DATA = {
#     "product_id": 1,
#     "shop_id": 1,
#     "count": 10,
#     "current_cost": 100.00,
# }


# def get_response_data(response_data: dict) -> dict:
#     """Helper function to extract data from wrapped response"""
#     return response_data.get("data", response_data)


# async def create_user_and_get_token(client, email: str = None) -> str:
#     """Helper function to create user and get access token"""
#     if email is None:
#         email = unique_email("user")
#     log_test(f"\n[HELPER] Creating user with email: {email}")
#     response = await client.post(
#         "/auth/register",
#         json={"email": email, "password": TEST_PASSWORD}
#     )
#     log_test(f"[HELPER] User registration response status: {response.status_code}")
#     data = get_response_data(response.json())
#     log_test(f"[HELPER] User created successfully")
#     return data["access_token"]


# async def create_seller_and_get_token(client, email: str = None) -> tuple[str, int]:
#     """Helper function to create seller and get access token and seller ID"""
#     if email is None:
#         email = unique_email("seller")
#     log_test(f"Creating seller with email: {email}")
#     access_token = await create_user_and_get_token(client, email)
    
#     response = await client.post(
#         "/sellers",
#         json=SELLER_DATA_IP,
#         headers={"Authorization": f"Bearer {access_token}"}
#     )
#     log_test(f"Seller creation response status: {response.status_code}")
#     data = get_response_data(response.json())
#     seller_id = data["id"]
#     log_test(f"Seller created with ID: {seller_id}")
    
#     return access_token, seller_id


# async def create_shop_point(client, access_token: str, seller_id: int) -> dict:
#     """Helper function to create shop point and return its data"""
#     log_test(f"Creating shop point for seller: {seller_id}")
#     shop_data = SHOP_POINT_DATA.copy()
#     shop_data["seller_id"] = seller_id
    
#     response = await client.post(
#         "/shop-points",
#         json=shop_data,
#         headers={"Authorization": f"Bearer {access_token}"}
#     )
#     log_test(f"Shop point creation response status: {response.status_code}")
#     assert response.status_code == status.HTTP_201_CREATED
#     data = get_response_data(response.json())
#     log_test(f"Shop point created with ID: {data['id']}")
#     return data


# async def create_product(client, access_token: str) -> dict:
#     """Helper function to create product and return its data"""
#     log_test("Creating product")
#     response = await client.post(
#         "/products",
#         json=PRODUCT_DATA,
#         headers={"Authorization": f"Bearer {access_token}"}
#     )
#     log_test(f"Product creation response status: {response.status_code}")
#     assert response.status_code == status.HTTP_201_CREATED
#     data = get_response_data(response.json())
#     log_test(f"Product created with ID: {data['id']}")
#     return data


# async def create_offer(client, access_token: str, product_id: int, shop_id: int, count: int = 10) -> dict:
#     """Helper function to create offer and return its data"""
#     log_test(f"Creating offer for product {product_id}, shop {shop_id}, count {count}")
#     offer_data = OFFER_DATA.copy()
#     offer_data["product_id"] = product_id
#     offer_data["shop_id"] = shop_id
#     offer_data["count"] = count
    
#     response = await client.post(
#         "/offers",
#         json=offer_data,
#         headers={"Authorization": f"Bearer {access_token}"}
#     )
#     log_test(f"Offer creation response status: {response.status_code}")
#     assert response.status_code == status.HTTP_201_CREATED
#     data = get_response_data(response.json())
#     log_test(f"Offer created with ID: {data['id']}")
#     return data


# async def create_purchase(client, access_token: str, offer_ids: list[int], quantities: list[int] = None) -> dict:
#     """Helper function to create purchase and return its data"""
#     if quantities is None:
#         quantities = [1] * len(offer_ids)
    
#     log_test(f"Creating purchase with offers: {offer_ids}, quantities: {quantities}")
#     purchase_data = {
#         "offers": [
#             {"offer_id": offer_id, "quantity": quantity}
#             for offer_id, quantity in zip(offer_ids, quantities)
#         ]
#     }
    
#     response = await client.post(
#         "/purchases",
#         json=purchase_data,
#         headers={"Authorization": f"Bearer {access_token}"}
#     )
#     log_test(f"Purchase creation response status: {response.status_code}")
#     assert response.status_code == status.HTTP_201_CREATED
#     data = get_response_data(response.json())
#     log_test(f"Purchase created with ID: {data['id']}")
#     return data


# class TestCreatePurchaseAPI:
#     """Tests for /purchases endpoint (POST)"""
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test successful purchase creation"""
#         log_test("=" * 80)
#         log_test("TEST: test_create_purchase_success - STARTED")
#         log_test("=" * 80)
        
#         # Create seller with product and offer
#         log_test("Step 1: Creating seller")
#         seller_token, seller_id = await create_seller_and_get_token(client)
        
#         log_test("Step 2: Creating shop point")
#         shop = await create_shop_point(client, seller_token, seller_id)
        
#         log_test("Step 3: Creating product")
#         product = await create_product(client, seller_token)
        
#         log_test("Step 4: Creating offer")
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer
#         log_test("Step 5: Creating buyer")
#         buyer_token = await create_user_and_get_token(client, None)
        
#         # Create purchase with mocked Celery task
#         log_test("Step 6: Mocking Celery task")
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
            
#             purchase_data = {
#                 "offers": [
#                     {"offer_id": offer["id"], "quantity": 2}
#                 ]
#             }
            
#             log_test(f"Step 7: Creating purchase with data: {purchase_data}")
#             response = await client.post(
#                 "/purchases",
#                 json=purchase_data,
#                 headers={"Authorization": f"Bearer {buyer_token}"}
#             )
#             log_test(f"Purchase creation response status: {response.status_code}")
        
#         log_test("Step 8: Validating response")
#         assert response.status_code == status.HTTP_201_CREATED
#         data = get_response_data(response.json())
#         assert "user_id" in data
#         assert data["status"] == PurchaseStatus.PENDING.value
#         assert "total_cost" in data
#         assert len(data["purchase_offers"]) == 1
#         assert data["purchase_offers"][0]["offer_id"] == offer["id"]
#         assert data["purchase_offers"][0]["quantity"] == 2
        
#         # Verify purchase was created in database
#         log_test("Step 9: Verifying purchase in database")
#         result = await test_session.execute(
#             select(Purchase).where(Purchase.id == data["id"])
#         )
#         purchase = result.scalar_one_or_none()
#         assert purchase is not None
#         assert purchase.user_id == data["user_id"]
        
#         log_test("TEST: test_create_purchase_success - PASSED")
#         log_test("=" * 80)
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_with_multiple_offers(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test creating purchase with multiple offers"""
#         log_test("TEST: test_create_purchase_with_multiple_offers - STARTED")
#         # Create seller with products and offers
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product1 = await create_product(client, seller_token)
#         product2 = await create_product(client, seller_token)
#         offer1 = await create_offer(client, seller_token, product1["id"], shop["id"])
#         offer2 = await create_offer(client, seller_token, product2["id"], shop["id"])
        
#         # Create buyer
#         log_test("Step: Creating buyer")
#         buyer_token = await create_user_and_get_token(client, None)
        
#         # Create purchase
#         log_test("Step: Mocking Celery task")
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
            
#             purchase_data = {
#                 "offers": [
#                     {"offer_id": offer1["id"], "quantity": 1},
#                     {"offer_id": offer2["id"], "quantity": 3}
#                 ]
#             }
            
#             log_test(f"Step: Creating purchase with 2 offers: {purchase_data}")
#             response = await client.post(
#                 "/purchases",
#                 json=purchase_data,
#                 headers={"Authorization": f"Bearer {buyer_token}"}
#             )
#             log_test(f"Step: Purchase response status: {response.status_code}")
        
#         log_test("Step: Validating response")
#         assert response.status_code == status.HTTP_201_CREATED
#         data = get_response_data(response.json())
#         assert len(data["purchase_offers"]) == 2
#         log_test("TEST: test_create_purchase_with_multiple_offers - PASSED")
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_no_auth(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test creating purchase without authentication"""
#         log_test("TEST: test_create_purchase_no_auth - STARTED")
#         purchase_data = {
#             "offers": [
#                 {"offer_id": 1, "quantity": 1}
#             ]
#         }
        
#         response = await client.post(
#             "/purchases",
#             json=purchase_data
#         )
        
#         assert response.status_code == status.HTTP_403_FORBIDDEN
#         log_test("TEST: test_create_purchase_no_auth - PASSED")
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_empty_offers(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test creating purchase with empty offers list"""
#         buyer_token = await create_user_and_get_token(client, None)
        
#         purchase_data = {
#             "offers": []
#         }
        
#         response = await client.post(
#             "/purchases",
#             json=purchase_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_offer_not_found(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test creating purchase with non-existent offer"""
#         buyer_token = await create_user_and_get_token(client, None)
        
#         purchase_data = {
#             "offers": [
#                 {"offer_id": 99999, "quantity": 1}
#             ]
#         }
        
#         response = await client.post(
#             "/purchases",
#             json=purchase_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_404_NOT_FOUND
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_insufficient_quantity(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test creating purchase with insufficient quantity"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"], count=5)
        
#         # Create buyer
#         buyer_token = await create_user_and_get_token(client, None)
        
#         # Try to purchase more than available
#         purchase_data = {
#             "offers": [
#                 {"offer_id": offer["id"], "quantity": 10}
#             ]
#         }
        
#         response = await client.post(
#             "/purchases",
#             json=purchase_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert "insufficient" in response.json()["detail"].lower()
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_already_has_pending(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test creating purchase when user already has a pending purchase"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer
#         buyer_token = await create_user_and_get_token(client, None)
        
#         # Create first purchase
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Try to create second purchase
#         purchase_data = {
#             "offers": [
#                 {"offer_id": offer["id"], "quantity": 1}
#             ]
#         }
        
#         response = await client.post(
#             "/purchases",
#             json=purchase_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_409_CONFLICT
#         assert "pending purchase" in response.json()["detail"].lower()


# class TestCreatePurchaseWithPartialSuccessAPI:
#     """Tests for /purchases/with-partial-success endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_with_partial_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test creating purchase with partial success"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"], count=5)
        
#         # Create buyer
#         buyer_token = await create_user_and_get_token(client, None)
        
#         # Create purchase requesting more than available
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
            
#             purchase_data = {
#                 "offers": [
#                     {"offer_id": offer["id"], "quantity": 10}  # Request more than available
#                 ]
#             }
            
#             response = await client.post(
#                 "/purchases/with-partial-success",
#                 json=purchase_data,
#                 headers={"Authorization": f"Bearer {buyer_token}"}
#             )
        
#         assert response.status_code == status.HTTP_201_CREATED
#         data = get_response_data(response.json())
#         assert data["user_id"] is not None
#         assert data["status"] == PurchaseStatus.PENDING.value
#         # Should process only available quantity (5)
#         assert data["purchase_offers"][0]["quantity"] == 5
    
#     @pytest.mark.asyncio
#     async def test_create_purchase_with_partial_success_all_unavailable(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test creating purchase with partial success when all offers are unavailable"""
#         # Create seller with product and offer with 0 count
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"], count=0)
        
#         # Create buyer
#         buyer_token = await create_user_and_get_token(client, None)
        
#         # Try to create purchase
#         purchase_data = {
#             "offers": [
#                 {"offer_id": offer["id"], "quantity": 1}
#             ]
#         }
        
#         response = await client.post(
#             "/purchases/with-partial-success",
#             json=purchase_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert "no offers could be processed" in response.json()["detail"].lower()


# class TestGetPurchasesAPI:
#     """Tests for GET /purchases endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_get_my_purchases_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test getting user's purchases"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Get purchases
#         response = await client.get(
#             "/purchases",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         response_json = response.json()
#         assert "data" in response_json
#         assert "pagination" in response_json
#         assert len(response_json["data"]) >= 1
    
#     @pytest.mark.asyncio
#     async def test_get_my_purchases_pagination(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test getting purchases with pagination"""
#         buyer_token = await create_user_and_get_token(client, None)
        
#         response = await client.get(
#             "/purchases?page=1&page_size=10",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         response_json = response.json()
#         assert response_json["pagination"]["page"] == 1
#         assert response_json["pagination"]["page_size"] == 10
    
#     @pytest.mark.asyncio
#     async def test_get_my_purchases_filter_by_status(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test filtering purchases by status"""
#         buyer_token = await create_user_and_get_token(client, None)
        
#         response = await client.get(
#             f"/purchases?status={PurchaseStatus.PENDING.value}",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         response_json = response.json()
#         assert "data" in response_json
#         # All returned purchases should have pending status
#         for purchase in response_json["data"]:
#             assert purchase["status"] == PurchaseStatus.PENDING.value
    
#     @pytest.mark.asyncio
#     async def test_get_my_purchases_no_auth(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test getting purchases without authentication"""
#         response = await client.get("/purchases")
#         assert response.status_code == status.HTTP_403_FORBIDDEN


# class TestGetPurchaseByIdAPI:
#     """Tests for GET /purchases/{purchase_id} endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_get_purchase_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test getting purchase by ID"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Get purchase by ID
#         response = await client.get(
#             f"/purchases/{purchase['id']}",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         data = get_response_data(response.json())
#         assert data["id"] == purchase["id"]
#         assert "purchase_offers" in data
    
#     @pytest.mark.asyncio
#     async def test_get_purchase_by_id_not_found(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test getting non-existent purchase"""
#         buyer_token = await create_user_and_get_token(client, None)
        
#         response = await client.get(
#             "/purchases/99999",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_404_NOT_FOUND
    
#     @pytest.mark.asyncio
#     async def test_get_purchase_by_id_wrong_user(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test getting purchase that belongs to another user"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer 1 and purchase
#         buyer1_token = await create_user_and_get_token(client, "buyer1@example.com")
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer1_token, [offer["id"]])
        
#         # Create buyer 2
#         buyer2_token = await create_user_and_get_token(client, "buyer2@example.com")
        
#         # Try to get buyer1's purchase with buyer2's token
#         response = await client.get(
#             f"/purchases/{purchase['id']}",
#             headers={"Authorization": f"Bearer {buyer2_token}"}
#         )
        
#         assert response.status_code == status.HTTP_403_FORBIDDEN


# class TestGetCurrentPendingPurchaseAPI:
#     """Tests for GET /purchases/current-pending endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_get_current_pending_purchase_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test getting current pending purchase"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Get current pending purchase
#         response = await client.get(
#             "/purchases/current-pending",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         data = get_response_data(response.json())
#         assert data["id"] == purchase["id"]
#         assert data["status"] == PurchaseStatus.PENDING.value
    
#     @pytest.mark.asyncio
#     async def test_get_current_pending_purchase_not_found(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test getting current pending purchase when none exists"""
#         buyer_token = await create_user_and_get_token(client, None)
        
#         response = await client.get(
#             "/purchases/current-pending",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_404_NOT_FOUND


# class TestUpdatePurchaseStatusAPI:
#     """Tests for PATCH /purchases/{purchase_id} endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_update_purchase_status_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test successful purchase status update"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Update purchase status
#         update_data = {
#             "status": PurchaseStatus.CANCELLED.value
#         }
        
#         response = await client.patch(
#             f"/purchases/{purchase['id']}",
#             json=update_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         data = get_response_data(response.json())
#         assert data["status"] == PurchaseStatus.CANCELLED.value
    
#     @pytest.mark.asyncio
#     async def test_update_purchase_status_not_found(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test updating non-existent purchase"""
#         buyer_token = await create_user_and_get_token(client, None)
        
#         update_data = {
#             "status": PurchaseStatus.CANCELLED.value
#         }
        
#         response = await client.patch(
#             "/purchases/99999",
#             json=update_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_404_NOT_FOUND
    
#     @pytest.mark.asyncio
#     async def test_update_purchase_status_wrong_user(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test updating purchase that belongs to another user"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer 1 and purchase
#         buyer1_token = await create_user_and_get_token(client, "buyer1@example.com")
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer1_token, [offer["id"]])
        
#         # Create buyer 2
#         buyer2_token = await create_user_and_get_token(client, "buyer2@example.com")
        
#         # Try to update buyer1's purchase with buyer2's token
#         update_data = {
#             "status": PurchaseStatus.CANCELLED.value
#         }
        
#         response = await client.patch(
#             f"/purchases/{purchase['id']}",
#             json=update_data,
#             headers={"Authorization": f"Bearer {buyer2_token}"}
#         )
        
#         assert response.status_code == status.HTTP_403_FORBIDDEN
    
#     @pytest.mark.asyncio
#     async def test_update_purchase_status_invalid_status(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test updating purchase with invalid status"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Try to update with invalid status
#         update_data = {
#             "status": "invalid_status"
#         }
        
#         response = await client.patch(
#             f"/purchases/{purchase['id']}",
#             json=update_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_400_BAD_REQUEST


# class TestDeletePurchaseAPI:
#     """Tests for DELETE /purchases/{purchase_id} endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_delete_purchase_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test successful purchase deletion"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         purchase_id = purchase["id"]
        
#         # Delete purchase
#         response = await client.delete(
#             f"/purchases/{purchase_id}",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_204_NO_CONTENT
        
#         # Verify purchase was deleted
#         result = await test_session.execute(
#             select(Purchase).where(Purchase.id == purchase_id)
#         )
#         deleted_purchase = result.scalar_one_or_none()
#         assert deleted_purchase is None
    
#     @pytest.mark.asyncio
#     async def test_delete_purchase_not_found(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test deleting non-existent purchase"""
#         buyer_token = await create_user_and_get_token(client, None)
        
#         response = await client.delete(
#             "/purchases/99999",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_404_NOT_FOUND
    
#     @pytest.mark.asyncio
#     async def test_delete_purchase_wrong_user(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test deleting purchase that belongs to another user"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer 1 and purchase
#         buyer1_token = await create_user_and_get_token(client, "buyer1@example.com")
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer1_token, [offer["id"]])
        
#         # Create buyer 2
#         buyer2_token = await create_user_and_get_token(client, "buyer2@example.com")
        
#         # Try to delete buyer1's purchase with buyer2's token
#         response = await client.delete(
#             f"/purchases/{purchase['id']}",
#             headers={"Authorization": f"Bearer {buyer2_token}"}
#         )
        
#         assert response.status_code == status.HTTP_403_FORBIDDEN


# class TestGenerateOrderTokenAPI:
#     """Tests for POST /purchases/{purchase_id}/token endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_generate_order_token_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test successful order token generation"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Set payment status to succeeded
#         result = await test_session.execute(
#             select(UserPayment).where(UserPayment.purchase_id == purchase["id"])
#         )
#         payment = result.scalar_one()
#         payment.status = PaymentStatus.SUCCEEDED.value
#         await test_session.commit()
        
#         # Generate token
#         response = await client.post(
#             f"/purchases/{purchase['id']}/token",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         data = get_response_data(response.json())
#         assert "token" in data
#         assert data["order_id"] == purchase["id"]
    
#     @pytest.mark.asyncio
#     async def test_generate_order_token_not_paid(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test generating token for unpaid order"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Generate token (payment is still pending)
#         response = await client.post(
#             f"/purchases/{purchase['id']}/token",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert "paid" in response.json()["detail"].lower()
    
#     @pytest.mark.asyncio
#     async def test_generate_order_token_wrong_user(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test generating token for another user's order"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer 1 and purchase
#         buyer1_token = await create_user_and_get_token(client, "buyer1@example.com")
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer1_token, [offer["id"]])
        
#         # Create buyer 2
#         buyer2_token = await create_user_and_get_token(client, "buyer2@example.com")
        
#         # Try to generate token with buyer2's token
#         response = await client.post(
#             f"/purchases/{purchase['id']}/token",
#             headers={"Authorization": f"Bearer {buyer2_token}"}
#         )
        
#         assert response.status_code == status.HTTP_403_FORBIDDEN


# class TestVerifyPurchaseTokenAPI:
#     """Tests for POST /purchases/verify-token endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_verify_purchase_token_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test successful purchase token verification"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Set payment status to succeeded
#         result = await test_session.execute(
#             select(UserPayment).where(UserPayment.purchase_id == purchase["id"])
#         )
#         payment = result.scalar_one()
#         payment.status = PaymentStatus.SUCCEEDED.value
#         await test_session.commit()
        
#         # Generate token
#         token_response = await client.post(
#             f"/purchases/{purchase['id']}/token",
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
#         token_data = get_response_data(token_response.json())
#         token = token_data["token"]
        
#         # Verify token as seller
#         verify_data = {
#             "token": token
#         }
        
#         response = await client.post(
#             "/purchases/verify-token",
#             json=verify_data,
#             headers={"Authorization": f"Bearer {seller_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         data = get_response_data(response.json())
#         assert data["purchase_id"] == purchase["id"]
#         assert "items" in data
    
#     @pytest.mark.asyncio
#     async def test_verify_purchase_token_not_seller(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test verifying token when user is not a seller"""
#         # Create buyer (not seller)
#         buyer_token = await create_user_and_get_token(client, None)
        
#         verify_data = {
#             "token": "fake_token"
#         }
        
#         response = await client.post(
#             "/purchases/verify-token",
#             json=verify_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_403_FORBIDDEN
#         assert "not a seller" in response.json()["detail"].lower()
    
#     @pytest.mark.asyncio
#     async def test_verify_purchase_token_invalid_token(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test verifying invalid token"""
#         # Create seller
#         seller_token, _, _ = await create_seller_and_get_token(client)
        
#         verify_data = {
#             "token": "invalid_token"
#         }
        
#         response = await client.post(
#             "/purchases/verify-token",
#             json=verify_data,
#             headers={"Authorization": f"Bearer {seller_token}"}
#         )
        
#         assert response.status_code == status.HTTP_401_UNAUTHORIZED


# class TestFulfillOrderItemsAPI:
#     """Tests for POST /purchases/{purchase_id}/fulfill endpoint"""
    
#     @pytest.mark.asyncio
#     async def test_fulfill_order_items_success(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test successful order fulfillment"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]], [2])
        
#         # Set payment status to succeeded
#         result = await test_session.execute(
#             select(UserPayment).where(UserPayment.purchase_id == purchase["id"])
#         )
#         payment = result.scalar_one()
#         payment.status = PaymentStatus.SUCCEEDED.value
#         await test_session.commit()
        
#         # Fulfill order
#         fulfillment_data = {
#             "items": [
#                 {
#                     "purchase_offer_id": offer["id"],
#                     "offer_id": offer["id"],
#                     "status": "fulfilled",
#                     "fulfilled_quantity": 2
#                 }
#             ]
#         }
        
#         response = await client.post(
#             f"/purchases/{purchase['id']}/fulfill",
#             json=fulfillment_data,
#             headers={"Authorization": f"Bearer {seller_token}"}
#         )
        
#         assert response.status_code == status.HTTP_200_OK
#         data = get_response_data(response.json())
#         assert "fulfilled_items" in data
#         assert len(data["fulfilled_items"]) == 1
#         assert data["fulfilled_items"][0]["status"] == "fulfilled"
    
#     @pytest.mark.asyncio
#     async def test_fulfill_order_items_not_seller(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test fulfilling order when user is not a seller"""
#         # Create buyer (not seller)
#         buyer_token = await create_user_and_get_token(client, None)
        
#         fulfillment_data = {
#             "items": [
#                 {
#                     "purchase_offer_id": 1,
#                     "offer_id": 1,
#                     "status": "fulfilled",
#                     "fulfilled_quantity": 1
#                 }
#             ]
#         }
        
#         response = await client.post(
#             "/purchases/1/fulfill",
#             json=fulfillment_data,
#             headers={"Authorization": f"Bearer {buyer_token}"}
#         )
        
#         assert response.status_code == status.HTTP_403_FORBIDDEN
#         assert "not a seller" in response.json()["detail"].lower()
    
#     @pytest.mark.asyncio
#     async def test_fulfill_order_items_not_paid(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test fulfilling unpaid order"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Try to fulfill (payment is still pending)
#         fulfillment_data = {
#             "items": [
#                 {
#                     "purchase_offer_id": offer["id"],
#                     "offer_id": offer["id"],
#                     "status": "fulfilled",
#                     "fulfilled_quantity": 1
#                 }
#             ]
#         }
        
#         response = await client.post(
#             f"/purchases/{purchase['id']}/fulfill",
#             json=fulfillment_data,
#             headers={"Authorization": f"Bearer {seller_token}"}
#         )
        
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert "not paid" in response.json()["detail"].lower()
    
#     @pytest.mark.asyncio
#     async def test_fulfill_order_items_wrong_seller(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test fulfilling order with wrong seller"""
#         # Create seller 1 with product and offer
#         seller1_token, seller1_id = await create_seller_and_get_token(client, "seller1@example.com")
#         shop1 = await create_shop_point(client, seller1_token, seller1_id)
#         product = await create_product(client, seller1_token)
#         offer = await create_offer(client, seller1_token, product["id"], shop1["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]])
        
#         # Set payment status to succeeded
#         result = await test_session.execute(
#             select(UserPayment).where(UserPayment.purchase_id == purchase["id"])
#         )
#         payment = result.scalar_one()
#         payment.status = PaymentStatus.SUCCEEDED.value
#         await test_session.commit()
        
#         # Create seller 2
#         seller2_token, _ = await create_seller_and_get_token(client, "seller2@example.com")
        
#         # Try to fulfill with seller2
#         fulfillment_data = {
#             "items": [
#                 {
#                     "purchase_offer_id": offer["id"],
#                     "offer_id": offer["id"],
#                     "status": "fulfilled",
#                     "fulfilled_quantity": 1
#                 }
#             ]
#         }
        
#         response = await client.post(
#             f"/purchases/{purchase['id']}/fulfill",
#             json=fulfillment_data,
#             headers={"Authorization": f"Bearer {seller2_token}"}
#         )
        
#         assert response.status_code == status.HTTP_403_FORBIDDEN
#         assert "does not belong" in response.json()["detail"].lower()
    
#     @pytest.mark.asyncio
#     async def test_fulfill_order_items_exceeds_quantity(self, client, test_session, mock_settings, mock_image_manager_init):
#         """Test fulfilling with quantity exceeding requested"""
#         # Create seller with product and offer
#         seller_token, seller_id = await create_seller_and_get_token(client)
#         shop = await create_shop_point(client, seller_token, seller_id)
#         product = await create_product(client, seller_token)
#         offer = await create_offer(client, seller_token, product["id"], shop["id"])
        
#         # Create buyer and purchase
#         buyer_token = await create_user_and_get_token(client, None)
        
#         with patch('app.purchases.manager.check_purchase_expiration') as mock_celery:
#             mock_celery.apply_async = Mock()
#             purchase = await create_purchase(client, buyer_token, [offer["id"]], [2])
        
#         # Set payment status to succeeded
#         result = await test_session.execute(
#             select(UserPayment).where(UserPayment.purchase_id == purchase["id"])
#         )
#         payment = result.scalar_one()
#         payment.status = PaymentStatus.SUCCEEDED.value
#         await test_session.commit()
        
#         # Try to fulfill with more quantity than requested
#         fulfillment_data = {
#             "items": [
#                 {
#                     "purchase_offer_id": offer["id"],
#                     "offer_id": offer["id"],
#                     "status": "fulfilled",
#                     "fulfilled_quantity": 10  # More than requested (2)
#                 }
#             ]
#         }
        
#         response = await client.post(
#             f"/purchases/{purchase['id']}/fulfill",
#             json=fulfillment_data,
#             headers={"Authorization": f"Bearer {seller_token}"}
#         )
        
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert "exceeds" in response.json()["detail"].lower()
