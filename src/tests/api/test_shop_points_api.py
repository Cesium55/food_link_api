"""API integration tests for shop points domain."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from sqlalchemy import select

from app.auth.models import User
from app.sellers.models import Seller
from app.shop_points.models import ShopPoint


TEST_PASSWORD = "password123"

SELLER_DATA_IP = {
    "full_name": "Иванов Иван Иванович",
    "short_name": "Иванов ИП",
    "description": "Тестовый продавец",
    "inn": "123456789012",
    "is_IP": True,
    "ogrn": "123456789012345",
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

SHOP_POINT_UPDATE_DATA = {
    "latitude": 56.0,
    "longitude": 38.0,
    "city": "Обновленный город",
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


async def create_shop_point_via_api(client, token: str, seller_id: int, **overrides) -> dict:
    payload = {**SHOP_POINT_DATA, "seller_id": seller_id, **overrides}
    response = await client.post(
        "/shop-points",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())


class TestCreateShopPointAPI:
    @pytest.mark.asyncio
    async def test_create_shop_point_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "shop-create@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        response = await client.post(
            "/shop-points",
            json={**SHOP_POINT_DATA, "seller_id": seller.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["seller_id"] == seller.id
        assert data["latitude"] == SHOP_POINT_DATA["latitude"]

        result = await test_session.execute(select(ShopPoint).where(ShopPoint.id == data["id"]))
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_create_shop_point_wrong_seller_returns_403(self, client, test_session, mock_settings, mock_image_manager_init):
        owner_email = "shop-owner@example.com"
        owner_token = await register_user_and_get_token(client, owner_email)
        await create_seller_in_db(test_session, owner_email)

        other_email = "shop-other@example.com"
        await register_user_and_get_token(client, other_email)
        other_seller = await create_seller_in_db(test_session, other_email)

        response = await client.post(
            "/shop-points",
            json={**SHOP_POINT_DATA, "seller_id": other_seller.id},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_shop_point_without_auth_returns_401(self, client, mock_settings, mock_image_manager_init):
        response = await client.post("/shop-points", json={**SHOP_POINT_DATA, "seller_id": 1})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_shop_point_invalid_payload_returns_422(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "shop-invalid@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        response = await client.post(
            "/shop-points",
            json={"seller_id": seller.id, "latitude": "bad"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestGetShopPointAPI:
    @pytest.mark.asyncio
    async def test_get_shop_point_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "shop-get@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        created = await create_shop_point_via_api(client, token, seller.id)

        response = await client.get(f"/shop-points/{created['id']}")

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == created["id"]
        assert data["seller_id"] == seller.id

    @pytest.mark.asyncio
    async def test_get_shop_point_not_found_returns_404(self, client, mock_settings, mock_image_manager_init):
        response = await client.get("/shop-points/999999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_shop_points_by_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "shop-by-seller@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        await create_shop_point_via_api(client, token, seller.id, latitude=55.1)
        await create_shop_point_via_api(client, token, seller.id, latitude=55.2)

        response = await client.get(f"/shop-points/seller/{seller.id}")
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert len(data) == 2
        assert all(item["seller_id"] == seller.id for item in data)


class TestShopPointsListAPI:
    @pytest.mark.asyncio
    async def test_get_shop_points_list_with_pagination_and_filters(self, client, test_session, mock_settings, mock_image_manager_init):
        first_email = "shop-list-1@example.com"
        first_token = await register_user_and_get_token(client, first_email)
        first_seller = await create_seller_in_db(test_session, first_email)
        await create_shop_point_via_api(client, first_token, first_seller.id, city="Москва", region="Москва")

        second_email = "shop-list-2@example.com"
        second_token = await register_user_and_get_token(client, second_email)
        second_seller = await create_seller_in_db(test_session, second_email)
        await create_shop_point_via_api(client, second_token, second_seller.id, city="Казань", region="Татарстан")

        response = await client.get("/shop-points?page=1&page_size=1&region=Москва&city=Москва")
        assert response.status_code == status.HTTP_200_OK

        body = response.json()
        assert body["pagination"]["page"] == 1
        assert body["pagination"]["page_size"] == 1
        assert body["pagination"]["total_items"] >= 1
        assert len(body["data"]) == 1
        assert body["data"][0]["city"] == "Москва"


class TestUpdateDeleteShopPointAPI:
    @pytest.mark.asyncio
    async def test_update_shop_point_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "shop-update@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        created = await create_shop_point_via_api(client, token, seller.id)

        response = await client.put(
            f"/shop-points/{created['id']}",
            json=SHOP_POINT_UPDATE_DATA,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["city"] == SHOP_POINT_UPDATE_DATA["city"]
        assert data["latitude"] == SHOP_POINT_UPDATE_DATA["latitude"]

    @pytest.mark.asyncio
    async def test_update_other_seller_shop_point_returns_403(self, client, test_session, mock_settings, mock_image_manager_init):
        owner_email = "shop-update-owner@example.com"
        owner_token = await register_user_and_get_token(client, owner_email)
        owner_seller = await create_seller_in_db(test_session, owner_email)
        created = await create_shop_point_via_api(client, owner_token, owner_seller.id)

        other_email = "shop-update-other@example.com"
        other_token = await register_user_and_get_token(client, other_email)
        await create_seller_in_db(test_session, other_email)

        response = await client.put(
            f"/shop-points/{created['id']}",
            json=SHOP_POINT_UPDATE_DATA,
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_shop_point_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "shop-delete@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)
        created = await create_shop_point_via_api(client, token, seller.id)

        response = await client.delete(
            f"/shop-points/{created['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        result = await test_session.execute(select(ShopPoint).where(ShopPoint.id == created["id"]))
        assert result.scalar_one_or_none() is None


class TestShopPointsAuxAPI:
    @pytest.mark.asyncio
    async def test_get_shop_points_summary_success(self, client, test_session, mock_settings, mock_image_manager_init):
        for idx in range(2):
            email = f"shop-summary-{idx}@example.com"
            token = await register_user_and_get_token(client, email)
            seller = await create_seller_in_db(test_session, email)
            await create_shop_point_via_api(client, token, seller.id, latitude=55.0 + idx)

        response = await client.get("/shop-points/summary/stats")
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert data["total_shop_points"] >= 2
        assert data["total_sellers"] >= 2

    @pytest.mark.asyncio
    async def test_get_shop_points_by_ids_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "shop-by-ids@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        first = await create_shop_point_via_api(client, token, seller.id, latitude=55.11)
        second = await create_shop_point_via_api(client, token, seller.id, latitude=55.22)

        response = await client.post("/shop-points/by-ids", json=[first["id"], second["id"]])

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) == 2
        assert {item["id"] for item in data} == {first["id"], second["id"]}

    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "shop-by-address@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)

        geocode_result = SimpleNamespace(
            latitude=55.7558,
            longitude=37.6173,
            address_raw="Москва, Красная площадь, 1",
            formatted_address="Россия, Москва, Красная площадь, 1",
            region="Москва",
            city="Москва",
            street="Красная площадь",
            house="1",
            geo_id="geo_id_123",
        )
        geocoder = AsyncMock()
        geocoder.geocode_address = AsyncMock(return_value=geocode_result)
        geocoder.close = AsyncMock()

        with patch("app.shop_points.manager.create_geocoder", return_value=geocoder):
            response = await client.post(
                "/shop-points/by-address",
                json={"raw_address": "Москва, Красная площадь, 1"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["city"] == "Москва"
        assert data["latitude"] == 55.7558

    @pytest.mark.asyncio
    async def test_create_shop_point_by_address_not_seller_returns_403(self, client, mock_settings, mock_image_manager_init):
        token = await register_user_and_get_token(client, "shop-by-address-no-seller@example.com")

        response = await client.post(
            "/shop-points/by-address",
            json={"raw_address": "Москва, Красная площадь, 1"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
