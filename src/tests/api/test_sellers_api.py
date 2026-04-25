"""API integration tests for sellers domain (without POST /sellers endpoint)."""

import pytest
from fastapi import status
from sqlalchemy import select

from app.auth.models import User
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

SELLER_UPDATE_DATA = {
    "short_name": "Обновленное название",
    "description": "Обновленное описание",
    "status": 1,
    "verification_level": 2,
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


class TestGetSellerAPI:
    @pytest.mark.asyncio
    async def test_get_seller_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "seller-get@example.com"
        await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        response = await client.get(f"/sellers/{seller.id}")

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == seller.id
        assert data["short_name"] == SELLER_DATA_IP["short_name"]

    @pytest.mark.asyncio
    async def test_get_seller_not_found_returns_404(self, client, mock_settings, mock_image_manager_init):
        response = await client.get("/sellers/999999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_my_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "seller-me@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)

        response = await client.get("/sellers/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["full_name"] == SELLER_DATA_IP["full_name"]

    @pytest.mark.asyncio
    async def test_get_my_seller_without_seller_returns_404(self, client, mock_settings, mock_image_manager_init):
        token = await register_user_and_get_token(client, "no-seller@example.com")

        response = await client.get("/sellers/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSellersListAPI:
    @pytest.mark.asyncio
    async def test_get_sellers_list_with_pagination(self, client, test_session, mock_settings, mock_image_manager_init):
        for idx in range(3):
            email = f"seller-list-{idx}@example.com"
            await register_user_and_get_token(client, email)
            await create_seller_in_db(
                test_session,
                email,
                short_name=f"Seller {idx}",
                inn=f"1234567890{idx:02d}",
            )

        response = await client.get("/sellers?page=1&page_size=2")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "pagination" in body
        assert body["pagination"]["page"] == 1
        assert body["pagination"]["page_size"] == 2
        assert len(body["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_sellers_by_ids_success(self, client, test_session, mock_settings, mock_image_manager_init):
        seller_ids = []
        for idx in range(2):
            email = f"seller-ids-{idx}@example.com"
            await register_user_and_get_token(client, email)
            seller = await create_seller_in_db(
                test_session,
                email,
                short_name=f"By IDs {idx}",
                inn=f"2234567890{idx:02d}",
            )
            seller_ids.append(seller.id)

        response = await client.post("/sellers/by-ids", json=seller_ids)

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert len(data) == 2
        assert {item["id"] for item in data} == set(seller_ids)


class TestSellersSummaryAPI:
    @pytest.mark.asyncio
    async def test_sellers_summary_success(self, client, test_session, mock_settings, mock_image_manager_init):
        for idx in range(2):
            email = f"seller-summary-{idx}@example.com"
            await register_user_and_get_token(client, email)
            await create_seller_in_db(
                test_session,
                email,
                short_name=f"Summary {idx}",
                inn=f"3234567890{idx:02d}",
            )

        response = await client.get("/sellers/summary/stats")
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert data["total_sellers"] >= 2
        assert "total_products" in data
        assert "avg_products_per_seller" in data


class TestUpdateDeleteSellerAPI:
    @pytest.mark.asyncio
    async def test_update_own_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "seller-update-own@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        response = await client.put(
            f"/sellers/{seller.id}",
            json=SELLER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["short_name"] == SELLER_UPDATE_DATA["short_name"]
        assert data["status"] == SELLER_UPDATE_DATA["status"]

    @pytest.mark.asyncio
    async def test_update_other_seller_returns_403(self, client, test_session, mock_settings, mock_image_manager_init):
        owner_email = "seller-owner@example.com"
        owner_token = await register_user_and_get_token(client, owner_email)
        owner_seller = await create_seller_in_db(test_session, owner_email)

        other_email = "seller-other@example.com"
        other_token = await register_user_and_get_token(client, other_email)
        await create_seller_in_db(test_session, other_email)

        response = await client.put(
            f"/sellers/{owner_seller.id}",
            json=SELLER_UPDATE_DATA,
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert owner_token
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_own_seller_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "seller-delete@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        response = await client.delete(
            f"/sellers/{seller.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        result = await test_session.execute(select(Seller).where(Seller.id == seller.id))
        assert result.scalar_one_or_none() is None


class TestSellerRegistrationRequestAPI:
    @pytest.mark.asyncio
    async def test_registration_request_crud_flow(self, client, mock_settings, mock_image_manager_init):
        token = await register_user_and_get_token(client, "seller-request@example.com")

        create_response = await client.post(
            "/sellers/registration-request",
            json={"description": "draft", "terms_accepted": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        created = get_response_data(create_response.json())
        assert created["status"] == "pending"
        request_id = created["id"]

        get_response = await client.get(
            "/sellers/registration-request",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == status.HTTP_200_OK
        fetched = get_response_data(get_response.json())
        assert fetched["id"] == request_id

        update_response = await client.put(
            "/sellers/registration-request",
            json={"description": "updated draft", "terms_accepted": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == status.HTTP_200_OK
        updated = get_response_data(update_response.json())
        assert updated["description"] == "updated draft"

        delete_response = await client.delete(
            "/sellers/registration-request",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        get_after_delete = await client.get(
            "/sellers/registration-request",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_after_delete.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_registration_request_duplicate_returns_400(self, client, mock_settings, mock_image_manager_init):
        token = await register_user_and_get_token(client, "seller-request-dup@example.com")

        first = await client.post(
            "/sellers/registration-request",
            json={"description": "first"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first.status_code == status.HTTP_201_CREATED

        second = await client.post(
            "/sellers/registration-request",
            json={"description": "second"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == status.HTTP_400_BAD_REQUEST
