"""API integration tests for purchases domain."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from sqlalchemy import select

from app.auth.models import User
from app.offers.models import Offer
from app.payments.models import UserPayment
from app.purchases.models import Purchase
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

PRODUCT_DATA = {
    "name": "Purchase Product",
    "description": "Product description",
    "article": "ART-PURCHASE-001",
    "code": "CODE-PURCHASE-001",
    "category_ids": [],
    "attributes": [],
}

OFFER_CREATE_DATA = {
    "pricing_strategy_id": None,
    "expires_date": None,
    "original_cost": None,
    "current_cost": "80.00",
    "count": 10,
}


def get_response_data(response_data: dict):
    return response_data.get("data", response_data)


@pytest.fixture
def mock_purchase_integrations():
    """Mock only external integrations used during purchase creation."""
    with (
        patch(
            "app.purchases.manager.PaymentsManager.create_payment_for_purchase",
            new_callable=AsyncMock,
        ) as mock_create_payment,
        patch(
            "app.purchases.manager.PurchasesManager._notify_sellers_about_reservation",
            new_callable=AsyncMock,
        ) as mock_notify,
        patch("app.purchases.manager.check_purchase_expiration") as mock_task,
    ):
        mock_task.apply_async = Mock()
        yield {
            "create_payment": mock_create_payment,
            "notify": mock_notify,
            "task": mock_task,
        }


async def register_user_and_get_token(client, email: str) -> str:
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK
    return get_response_data(response.json())["access_token"]


async def get_user_by_email(test_session, email: str) -> User:
    result = await test_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    assert user is not None, f"User with email {email} not found"
    return user


async def create_seller_in_db(test_session, email: str, **overrides) -> Seller:
    user = await get_user_by_email(test_session, email)
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


async def create_purchase_via_api(client, token: str, offer_id: int, quantity: int = 1):
    response = await client.post(
        "/purchases",
        json={"offers": [{"offer_id": offer_id, "quantity": quantity}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response


async def create_purchase_with_partial_success_via_api(client, token: str, offers: list[dict]):
    response = await client.post(
        "/purchases/with-partial-success",
        json={"offers": offers},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response


class TestCreatePurchaseAPI:
    @pytest.mark.asyncio
    async def test_create_purchase_success(
        self,
        client,
        test_session,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        seller_email = "purchase-seller@example.com"
        seller_token = await register_user_and_get_token(client, seller_email)
        seller = await create_seller_in_db(test_session, seller_email)

        product = await create_product_via_api(client, seller_token)
        shop = await create_shop_point_via_api(client, seller_token, seller.id)
        offer = await create_offer_via_api(client, seller_token, product["id"], shop["id"])

        buyer_token = await register_user_and_get_token(client, "purchase-buyer@example.com")

        response = await create_purchase_via_api(client, buyer_token, offer["id"], quantity=2)

        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["status"] == "pending"
        assert Decimal(str(data["total_cost"])) == Decimal("160.00")
        assert len(data["purchase_offers"]) == 1
        assert data["purchase_offers"][0]["offer_id"] == offer["id"]
        assert data["purchase_offers"][0]["quantity"] == 2

    @pytest.mark.asyncio
    async def test_create_purchase_without_auth_returns_401(
        self,
        client,
        mock_settings,
        mock_image_manager_init,
    ):
        response = await client.post(
            "/purchases",
            json={"offers": [{"offer_id": 1, "quantity": 1}]},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_purchase_with_existing_pending_returns_409(
        self,
        client,
        test_session,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        seller_email = "purchase-conflict-seller@example.com"
        seller_token = await register_user_and_get_token(client, seller_email)
        seller = await create_seller_in_db(test_session, seller_email)

        product = await create_product_via_api(client, seller_token)
        shop = await create_shop_point_via_api(client, seller_token, seller.id)
        offer = await create_offer_via_api(client, seller_token, product["id"], shop["id"])

        buyer_token = await register_user_and_get_token(client, "purchase-conflict-buyer@example.com")

        first_response = await create_purchase_via_api(client, buyer_token, offer["id"], quantity=1)
        second_response = await create_purchase_via_api(client, buyer_token, offer["id"], quantity=1)

        assert first_response.status_code == status.HTTP_201_CREATED
        assert second_response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_create_purchase_with_nonexistent_offer_returns_400(
        self,
        client,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        buyer_token = await register_user_and_get_token(client, "purchase-invalid-notfound@example.com")
        response = await create_purchase_via_api(client, buyer_token, offer_id=999999, quantity=1)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        detail = response.json().get("detail", "")
        assert "No offers could be processed" in detail

    @pytest.mark.asyncio
    async def test_create_purchase_with_expired_offer_returns_400(
        self,
        client,
        test_session,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        seller_email = "purchase-invalid-expired-seller@example.com"
        seller_token = await register_user_and_get_token(client, seller_email)
        seller = await create_seller_in_db(test_session, seller_email)

        product = await create_product_via_api(client, seller_token)
        shop = await create_shop_point_via_api(client, seller_token, seller.id)
        expired_offer = await create_offer_via_api(
            client,
            seller_token,
            product["id"],
            shop["id"],
            count=5,
        )
        offer_result = await test_session.execute(select(Offer).where(Offer.id == expired_offer["id"]))
        offer_model = offer_result.scalar_one()
        offer_model.expires_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
        await test_session.commit()

        buyer_token = await register_user_and_get_token(client, "purchase-invalid-expired-buyer@example.com")
        response = await create_purchase_via_api(client, buyer_token, offer_id=expired_offer["id"], quantity=1)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_purchase_with_insufficient_quantity_returns_partial_success(
        self,
        client,
        test_session,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        seller_email = "purchase-invalid-qty-seller@example.com"
        seller_token = await register_user_and_get_token(client, seller_email)
        seller = await create_seller_in_db(test_session, seller_email)

        product = await create_product_via_api(client, seller_token)
        shop = await create_shop_point_via_api(client, seller_token, seller.id)
        small_offer = await create_offer_via_api(
            client,
            seller_token,
            product["id"],
            shop["id"],
            count=1,
        )

        buyer_token = await register_user_and_get_token(client, "purchase-invalid-qty-buyer@example.com")
        response = await create_purchase_via_api(client, buyer_token, offer_id=small_offer["id"], quantity=3)
        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert Decimal(str(data["total_cost"])) == Decimal("80.00")
        assert data["purchase_offers"][0]["quantity"] == 1
        assert data["offer_results"][0]["status"] == "insufficient_quantity"
        assert data["offer_results"][0]["requested_quantity"] == 3
        assert data["offer_results"][0]["processed_quantity"] == 1

    @pytest.mark.asyncio
    async def test_create_purchase_with_invalid_payload_returns_422(
        self,
        client,
        mock_settings,
        mock_image_manager_init,
    ):
        buyer_token = await register_user_and_get_token(client, "purchase-invalid-payload@example.com")
        response = await client.post(
            "/purchases",
            json={"offers": [{"offer_id": 1, "quantity": 0}]},
            headers={"Authorization": f"Bearer {buyer_token}"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestCreatePurchaseWithPartialSuccessAPI:
    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_mixed_results(
        self,
        client,
        test_session,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        seller_email = "purchase-partial-seller@example.com"
        seller_token = await register_user_and_get_token(client, seller_email)
        seller = await create_seller_in_db(test_session, seller_email)

        product = await create_product_via_api(client, seller_token)
        shop = await create_shop_point_via_api(client, seller_token, seller.id)
        limited_offer = await create_offer_via_api(
            client,
            seller_token,
            product["id"],
            shop["id"],
            count=2,
        )

        buyer_token = await register_user_and_get_token(client, "purchase-partial-buyer@example.com")
        response = await create_purchase_with_partial_success_via_api(
            client,
            buyer_token,
            offers=[
                {"offer_id": limited_offer["id"], "quantity": 5},
                {"offer_id": 999999, "quantity": 1},
            ],
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())

        assert data["status"] == "pending"
        assert Decimal(str(data["total_cost"])) == Decimal("160.00")
        assert len(data["purchase_offers"]) == 1
        assert data["purchase_offers"][0]["offer_id"] == limited_offer["id"]
        assert data["purchase_offers"][0]["quantity"] == 2

        assert len(data["offer_results"]) == 2
        results_by_offer_id = {item["offer_id"]: item for item in data["offer_results"]}

        limited_result = results_by_offer_id[limited_offer["id"]]
        assert limited_result["status"] == "insufficient_quantity"
        assert limited_result["requested_quantity"] == 5
        assert limited_result["processed_quantity"] == 2
        assert limited_result["available_quantity"] == 2

        missing_result = results_by_offer_id[999999]
        assert missing_result["status"] == "not_found"
        assert missing_result["requested_quantity"] == 1
        assert missing_result["processed_quantity"] is None

    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_all_failed_returns_400(
        self,
        client,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        buyer_token = await register_user_and_get_token(client, "purchase-partial-failed@example.com")
        response = await create_purchase_with_partial_success_via_api(
            client,
            buyer_token,
            offers=[{"offer_id": 999999, "quantity": 2}],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_with_expired_offer_only_returns_400(
        self,
        client,
        test_session,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        seller_email = "purchase-partial-expired-seller@example.com"
        seller_token = await register_user_and_get_token(client, seller_email)
        seller = await create_seller_in_db(test_session, seller_email)

        product = await create_product_via_api(client, seller_token)
        shop = await create_shop_point_via_api(client, seller_token, seller.id)
        expired_offer = await create_offer_via_api(
            client,
            seller_token,
            product["id"],
            shop["id"],
            count=2,
        )
        offer_result = await test_session.execute(select(Offer).where(Offer.id == expired_offer["id"]))
        offer_model = offer_result.scalar_one()
        offer_model.expires_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
        await test_session.commit()

        buyer_token = await register_user_and_get_token(client, "purchase-partial-expired-buyer@example.com")
        response = await create_purchase_with_partial_success_via_api(
            client,
            buyer_token,
            offers=[{"offer_id": expired_offer["id"], "quantity": 1}],
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_with_zero_available_offer_returns_400(
        self,
        client,
        test_session,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        seller_email = "purchase-partial-zero-seller@example.com"
        seller_token = await register_user_and_get_token(client, seller_email)
        seller = await create_seller_in_db(test_session, seller_email)

        product = await create_product_via_api(client, seller_token)
        shop = await create_shop_point_via_api(client, seller_token, seller.id)
        zero_offer = await create_offer_via_api(
            client,
            seller_token,
            product["id"],
            shop["id"],
            count=1,
        )
        offer_result = await test_session.execute(select(Offer).where(Offer.id == zero_offer["id"]))
        offer_model = offer_result.scalar_one()
        offer_model.reserved_count = 1
        await test_session.commit()

        buyer_token = await register_user_and_get_token(client, "purchase-partial-zero-buyer@example.com")
        response = await create_purchase_with_partial_success_via_api(
            client,
            buyer_token,
            offers=[{"offer_id": zero_offer["id"], "quantity": 1}],
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_with_invalid_quantity_returns_422(
        self,
        client,
        mock_settings,
        mock_image_manager_init,
    ):
        buyer_token = await register_user_and_get_token(client, "purchase-partial-invalid-qty@example.com")
        response = await create_purchase_with_partial_success_via_api(
            client,
            buyer_token,
            offers=[{"offer_id": 1, "quantity": 0}],
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_purchase_with_partial_success_without_auth_returns_401(
        self,
        client,
        mock_settings,
        mock_image_manager_init,
    ):
        response = await client.post(
            "/purchases/with-partial-success",
            json={"offers": [{"offer_id": 1, "quantity": 1}]},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetUpdateDeletePurchaseAPI:
    @pytest.mark.asyncio
    async def test_get_my_purchases_returns_only_current_user(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        user_1_token = await register_user_and_get_token(client, "purchase-list-1@example.com")
        await register_user_and_get_token(client, "purchase-list-2@example.com")

        user_1 = await get_user_by_email(test_session, "purchase-list-1@example.com")
        user_2 = await get_user_by_email(test_session, "purchase-list-2@example.com")

        test_session.add_all(
            [
                Purchase(user_id=user_1.id, status="pending", total_cost=Decimal("100.00")),
                Purchase(user_id=user_2.id, status="pending", total_cost=Decimal("200.00")),
            ]
        )
        await test_session.commit()

        response = await client.get(
            "/purchases?page=1&page_size=20",
            headers={"Authorization": f"Bearer {user_1_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "data" in body and "pagination" in body
        assert len(body["data"]) == 1
        assert body["data"][0]["user_id"] == user_1.id

    @pytest.mark.asyncio
    async def test_get_purchase_of_another_user_returns_403(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        await register_user_and_get_token(client, "purchase-owner@example.com")
        other_token = await register_user_and_get_token(client, "purchase-other@example.com")

        owner = await get_user_by_email(test_session, "purchase-owner@example.com")
        purchase = Purchase(user_id=owner.id, status="pending", total_cost=Decimal("90.00"))
        test_session.add(purchase)
        await test_session.commit()
        await test_session.refresh(purchase)

        response = await client.get(
            f"/purchases/{purchase.id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_patch_purchase_cancelled_releases_reserved_count(
        self,
        client,
        test_session,
        mock_purchase_integrations,
        mock_settings,
        mock_image_manager_init,
    ):
        seller_email = "purchase-cancel-seller@example.com"
        seller_token = await register_user_and_get_token(client, seller_email)
        seller = await create_seller_in_db(test_session, seller_email)

        product = await create_product_via_api(client, seller_token)
        shop = await create_shop_point_via_api(client, seller_token, seller.id)
        offer = await create_offer_via_api(client, seller_token, product["id"], shop["id"])

        buyer_token = await register_user_and_get_token(client, "purchase-cancel-buyer@example.com")
        create_response = await create_purchase_via_api(client, buyer_token, offer["id"], quantity=3)
        assert create_response.status_code == status.HTTP_201_CREATED
        purchase_id = get_response_data(create_response.json())["id"]

        update_response = await client.patch(
            f"/purchases/{purchase_id}",
            json={"status": "cancelled"},
            headers={"Authorization": f"Bearer {buyer_token}"},
        )

        assert update_response.status_code == status.HTTP_200_OK
        updated = get_response_data(update_response.json())
        assert updated["status"] == "cancelled"

        result = await test_session.execute(select(Offer).where(Offer.id == offer["id"]))
        offer_row = result.scalar_one()
        assert offer_row.reserved_count == 0

    @pytest.mark.asyncio
    async def test_delete_purchase_returns_405(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        token = await register_user_and_get_token(client, "purchase-delete@example.com")
        user = await get_user_by_email(test_session, "purchase-delete@example.com")

        purchase = Purchase(user_id=user.id, status="pending", total_cost=Decimal("50.00"))
        test_session.add(purchase)
        await test_session.commit()
        await test_session.refresh(purchase)

        response = await client.delete(
            f"/purchases/{purchase.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestOrderTokenAPI:
    @pytest.mark.asyncio
    async def test_generate_order_token_for_unpaid_purchase_returns_400(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        token = await register_user_and_get_token(client, "purchase-token-unpaid@example.com")
        user = await get_user_by_email(test_session, "purchase-token-unpaid@example.com")

        purchase = Purchase(user_id=user.id, status="pending", total_cost=Decimal("70.00"))
        test_session.add(purchase)
        await test_session.commit()
        await test_session.refresh(purchase)

        response = await client.post(
            f"/purchases/{purchase.id}/token",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_generate_order_token_for_paid_purchase_success(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        token = await register_user_and_get_token(client, "purchase-token-paid@example.com")
        user = await get_user_by_email(test_session, "purchase-token-paid@example.com")

        purchase = Purchase(user_id=user.id, status="confirmed", total_cost=Decimal("120.00"))
        test_session.add(purchase)
        await test_session.flush()

        payment = UserPayment(
            purchase_id=purchase.id,
            yookassa_payment_id="yk_purchase_token_paid",
            status="succeeded",
            amount=Decimal("120.00"),
            currency="RUB",
            description="Payment for token test",
        )
        test_session.add(payment)
        await test_session.commit()
        await test_session.refresh(purchase)

        response = await client.post(
            f"/purchases/{purchase.id}/token",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["order_id"] == purchase.id
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 10
