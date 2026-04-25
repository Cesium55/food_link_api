"""API integration tests for payments domain."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from sqlalchemy import select

from app.auth.models import User
from app.payments.models import UserPayment
from app.purchases.models import Purchase


TEST_PASSWORD = "password123"


def get_response_data(response_data: dict):
    return response_data.get("data", response_data)


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


async def create_purchase_and_payment_in_db(
    test_session,
    *,
    user_id: int,
    purchase_status: str = "pending",
    payment_status: str = "pending",
    yookassa_payment_id: str = "yk_test_payment",
    amount: Decimal = Decimal("100.00"),
):
    purchase = Purchase(user_id=user_id, status=purchase_status, total_cost=amount)
    test_session.add(purchase)
    await test_session.flush()

    payment = UserPayment(
        purchase_id=purchase.id,
        yookassa_payment_id=yookassa_payment_id,
        status=payment_status,
        amount=amount,
        currency="RUB",
        description=f"Payment for purchase #{purchase.id}",
    )
    test_session.add(payment)
    await test_session.commit()
    await test_session.refresh(purchase)
    await test_session.refresh(payment)
    return purchase, payment


class TestGetPaymentsAPI:
    @pytest.mark.asyncio
    async def test_get_payment_by_purchase_success(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        email = "payment-by-purchase@example.com"
        token = await register_user_and_get_token(client, email)
        user = await get_user_by_email(test_session, email)
        purchase, payment = await create_purchase_and_payment_in_db(test_session, user_id=user.id)

        response = await client.get(
            f"/payments/purchase/{purchase.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == payment.id
        assert data["purchase_id"] == purchase.id

    @pytest.mark.asyncio
    async def test_get_payment_by_purchase_for_other_user_returns_403(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        await register_user_and_get_token(client, "payment-owner@example.com")
        other_token = await register_user_and_get_token(client, "payment-other@example.com")

        owner = await get_user_by_email(test_session, "payment-owner@example.com")
        purchase, _payment = await create_purchase_and_payment_in_db(test_session, user_id=owner.id)

        response = await client.get(
            f"/payments/purchase/{purchase.id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_payment_by_id_success(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        email = "payment-by-id@example.com"
        token = await register_user_and_get_token(client, email)
        user = await get_user_by_email(test_session, email)
        _purchase, payment = await create_purchase_and_payment_in_db(test_session, user_id=user.id)

        response = await client.get(
            f"/payments/{payment.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == payment.id

    @pytest.mark.asyncio
    async def test_get_payment_status_success_without_auth(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        email = "payment-status@example.com"
        await register_user_and_get_token(client, email)
        user = await get_user_by_email(test_session, email)
        purchase, payment = await create_purchase_and_payment_in_db(test_session, user_id=user.id)

        response = await client.get(f"/payments/{payment.id}/status")

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["payment_id"] == payment.id
        assert data["purchase_id"] == purchase.id
        assert data["status"] == "pending"


class TestPaymentActionsAPI:
    @pytest.mark.asyncio
    async def test_check_payment_status_updates_from_yookassa(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        email = "payment-check@example.com"
        token = await register_user_and_get_token(client, email)
        user = await get_user_by_email(test_session, email)
        _purchase, payment = await create_purchase_and_payment_in_db(
            test_session,
            user_id=user.id,
            payment_status="pending",
            yookassa_payment_id="yk_check_1",
        )

        with patch(
            "app.payments.routes.payments_manager._get_yookassa_payment",
            new=AsyncMock(return_value={"status": "waiting_for_capture"}),
        ):
            response = await client.post(
                f"/payments/{payment.id}/check",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == payment.id
        assert data["status"] == "waiting_for_capture"

    @pytest.mark.asyncio
    async def test_cancel_payment_success(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        email = "payment-cancel@example.com"
        token = await register_user_and_get_token(client, email)
        user = await get_user_by_email(test_session, email)
        _purchase, payment = await create_purchase_and_payment_in_db(
            test_session,
            user_id=user.id,
            payment_status="pending",
            yookassa_payment_id="yk_cancel_1",
        )

        with patch(
            "app.payments.routes.payments_manager._cancel_yookassa_payment",
            new=AsyncMock(
                return_value={
                    "status": "canceled",
                    "cancellation_details": {"reason": "manual"},
                }
            ),
        ):
            response = await client.post(
                f"/payments/{payment.id}/cancel",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["id"] == payment.id
        assert data["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_payment_of_other_user_returns_403(
        self,
        client,
        test_session,
        mock_settings,
        mock_image_manager_init,
    ):
        await register_user_and_get_token(client, "payment-cancel-owner@example.com")
        other_token = await register_user_and_get_token(client, "payment-cancel-other@example.com")

        owner = await get_user_by_email(test_session, "payment-cancel-owner@example.com")
        _purchase, payment = await create_purchase_and_payment_in_db(
            test_session,
            user_id=owner.id,
            payment_status="pending",
            yookassa_payment_id="yk_cancel_403",
        )

        with patch(
            "app.payments.routes.payments_manager._cancel_yookassa_payment",
            new=AsyncMock(return_value={"status": "canceled"}),
        ):
            response = await client.post(
                f"/payments/{payment.id}/cancel",
                headers={"Authorization": f"Bearer {other_token}"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
