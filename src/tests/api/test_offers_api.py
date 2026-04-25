"""API integration tests for offers domain."""

from decimal import Decimal

import pytest
from fastapi import status
from sqlalchemy import select

from app.auth.models import User
from app.offers.models import Offer
from app.sellers.models import Seller


TEST_PASSWORD = "password123"

SELLER_DATA_IP = {
    "full_name": "Иванов Иван Иванович",
    "short_name": "Иванов ИП",
    "description": "Тестовый продавец",
    "inn": "123456789012",
    "is_IP": True,
    "ogrn": "123456789012345",
}

PRODUCT_DATA = {
    "name": "Offer Product",
    "description": "Product description",
    "article": "ART-OFFER-001",
    "code": "CODE-OFFER-001",
    "category_ids": [],
    "attributes": [],
}

SHOP_POINT_DATA = {
    "latitude": 55.7558,
    "longitude": 37.6173,
    "address_raw": "Москва, Красная площадь, 1",
    "address_formated": "Россия, Москва, Красная площадь, 1",
    "region": "Москва",
    "city": "Москва",
    "street": "Красная площадь",
    "house": "1",
    "geo_id": "geo_id_123",
}

OFFER_CREATE_DATA = {
    "pricing_strategy_id": None,
    "expires_date": None,
    "original_cost": None,
    "current_cost": "80.00",
    "count": 10,
}

OFFER_UPDATE_DATA = {
    "current_cost": "75.00",
    "count": 15,
}


def get_response_data(response_data: dict):
    return response_data.get("data", response_data)


async def register_user_and_get_token(client, email: str) -> str:
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK
    return get_response_data(response.json())["access_token"]


async def create_seller_in_db(test_session, email: str, **overrides) -> Seller:
    user_result = await test_session.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    assert user is not None, f"User with email {email} not found"

    user.is_seller = True

    payload = {
        "email": email,
        "phone": None,
        "full_name": SELLER_DATA_IP["full_name"],
        "short_name": SELLER_DATA_IP["short_name"],
        "description": SELLER_DATA_IP["description"],
        "inn": SELLER_DATA_IP["inn"],
        "is_IP": SELLER_DATA_IP["is_IP"],
        "ogrn": SELLER_DATA_IP["ogrn"],
        "master_id": user.id,
        "status": 0,
        "verification_level": 0,
        "registration_doc_url": "",
        "balance": 0,
    }
    payload.update(overrides)

    seller = Seller(**payload)
    test_session.add(seller)
    await test_session.commit()
    await test_session.refresh(seller)
    return seller


async def create_product_via_api(client, token: str) -> dict:
    response = await client.post(
        "/products",
        json=PRODUCT_DATA,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())


async def create_shop_point_via_api(client, token: str, seller_id: int) -> dict:
    response = await client.post(
        "/shop-points",
        json={**SHOP_POINT_DATA, "seller_id": seller_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())


async def create_offer_via_api(client, token: str, product_id: int, shop_id: int, **overrides) -> dict:
    payload = {
        **OFFER_CREATE_DATA,
        "product_id": product_id,
        "shop_id": shop_id,
        **overrides,
    }
    response = await client.post(
        "/offers",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())


class TestCreateOfferAPI:
    @pytest.mark.asyncio
    async def test_create_offer_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "offer-create@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        product = await create_product_via_api(client, token)
        shop = await create_shop_point_via_api(client, token, seller.id)

        response = await client.post(
            "/offers",
            json={**OFFER_CREATE_DATA, "product_id": product["id"], "shop_id": shop["id"]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["product_id"] == product["id"]
        assert data["shop_id"] == shop["id"]
        assert Decimal(str(data["current_cost"])) == Decimal("80.00")
        assert data["count"] == 10

        result = await test_session.execute(select(Offer).where(Offer.id == data["id"]))
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_create_offer_without_auth_returns_401(self, client, mock_settings, mock_image_manager_init):
        response = await client.post(
            "/offers",
            json={**OFFER_CREATE_DATA, "product_id": 1, "shop_id": 1},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_offer_wrong_owner_returns_403(self, client, test_session, mock_settings, mock_image_manager_init):
        owner_email = "offer-owner@example.com"
        owner_token = await register_user_and_get_token(client, owner_email)
        owner_seller = await create_seller_in_db(test_session, owner_email)
        owner_product = await create_product_via_api(client, owner_token)
        owner_shop = await create_shop_point_via_api(client, owner_token, owner_seller.id)

        other_email = "offer-other@example.com"
        other_token = await register_user_and_get_token(client, other_email)
        await create_seller_in_db(test_session, other_email)

        response = await client.post(
            "/offers",
            json={
                **OFFER_CREATE_DATA,
                "product_id": owner_product["id"],
                "shop_id": owner_shop["id"],
            },
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetOffersAPI:
    @pytest.mark.asyncio
    async def test_get_offer_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "offer-get@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        product = await create_product_via_api(client, token)
        shop = await create_shop_point_via_api(client, token, seller.id)
        offer = await create_offer_via_api(client, token, product["id"], shop["id"])

        response = await client.get(f"/offers/{offer['id']}")

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == offer["id"]
        assert data["product_id"] == product["id"]

    @pytest.mark.asyncio
    async def test_get_offer_not_found_returns_404(self, client, mock_settings, mock_image_manager_init):
        response = await client.get("/offers/999999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_offer_with_product_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "offer-with-product@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        product = await create_product_via_api(client, token)
        shop = await create_shop_point_via_api(client, token, seller.id)
        offer = await create_offer_via_api(client, token, product["id"], shop["id"])

        response = await client.get(f"/offers/{offer['id']}/with-product")

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "product" in data
        assert data["product"]["id"] == product["id"]

    @pytest.mark.asyncio
    async def test_get_offers_list_and_filters(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "offer-list@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        product = await create_product_via_api(client, token)
        shop = await create_shop_point_via_api(client, token, seller.id)
        await create_offer_via_api(client, token, product["id"], shop["id"])

        response = await client.get(f"/offers?page=1&page_size=10&product_id={product['id']}")
        assert response.status_code == status.HTTP_200_OK

        body = response.json()
        assert "data" in body and "pagination" in body
        assert body["pagination"]["page"] == 1
        assert len(body["data"]) >= 1
        assert all(item["product_id"] == product["id"] for item in body["data"])

    @pytest.mark.asyncio
    async def test_get_offers_with_products_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "offer-with-products@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        product = await create_product_via_api(client, token)
        shop = await create_shop_point_via_api(client, token, seller.id)
        await create_offer_via_api(client, token, product["id"], shop["id"])

        response = await client.get("/offers/with-products")
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "product" in data[0]


class TestUpdateDeleteOfferAPI:
    @pytest.mark.asyncio
    async def test_update_offer_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "offer-update@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        product = await create_product_via_api(client, token)
        shop = await create_shop_point_via_api(client, token, seller.id)
        offer = await create_offer_via_api(client, token, product["id"], shop["id"])

        response = await client.put(
            f"/offers/{offer['id']}",
            json=OFFER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert Decimal(str(data["current_cost"])) == Decimal("75.00")
        assert data["count"] == 15

    @pytest.mark.asyncio
    async def test_update_offer_wrong_owner_returns_403(self, client, test_session, mock_settings, mock_image_manager_init):
        owner_email = "offer-update-owner@example.com"
        owner_token = await register_user_and_get_token(client, owner_email)
        owner_seller = await create_seller_in_db(test_session, owner_email)
        owner_product = await create_product_via_api(client, owner_token)
        owner_shop = await create_shop_point_via_api(client, owner_token, owner_seller.id)
        offer = await create_offer_via_api(client, owner_token, owner_product["id"], owner_shop["id"])

        other_email = "offer-update-other@example.com"
        other_token = await register_user_and_get_token(client, other_email)
        await create_seller_in_db(test_session, other_email)

        response = await client.put(
            f"/offers/{offer['id']}",
            json=OFFER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_offer_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "offer-delete@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        product = await create_product_via_api(client, token)
        shop = await create_shop_point_via_api(client, token, seller.id)
        offer = await create_offer_via_api(client, token, product["id"], shop["id"])

        response = await client.delete(
            f"/offers/{offer['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        result = await test_session.execute(select(Offer).where(Offer.id == offer["id"]))
        assert result.scalar_one_or_none() is None


class TestPricingStrategiesAPI:
    @pytest.mark.asyncio
    async def test_get_pricing_strategies_success(self, client, mock_settings, mock_image_manager_init):
        response = await client.get("/offers/pricing-strategies")
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_pricing_strategy_not_found_returns_404(self, client, mock_settings, mock_image_manager_init):
        response = await client.get("/offers/pricing-strategies/999999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
