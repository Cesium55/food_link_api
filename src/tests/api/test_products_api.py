"""API integration tests for products domain."""

import pytest
from fastapi import status
from sqlalchemy import select

from app.auth.models import User
from app.products.models import Product
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
    "name": "Test Product",
    "description": "Test product description",
    "article": "ART-001",
    "code": "CODE-001",
    "category_ids": [],
    "attributes": [],
}

PRODUCT_UPDATE_DATA = {
    "name": "Updated Product Name",
    "description": "Updated description",
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


async def create_category(client, name: str, slug: str) -> int:
    response = await client.post("/product-categories", json={"name": name, "slug": slug})
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())["id"]


async def create_product_via_api(client, token: str, payload: dict | None = None) -> dict:
    response = await client.post(
        "/products",
        json=payload or PRODUCT_DATA,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return get_response_data(response.json())


class TestCreateProductAPI:
    @pytest.mark.asyncio
    async def test_create_product_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-create@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        response = await client.post(
            "/products",
            json=PRODUCT_DATA,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = get_response_data(response.json())
        assert data["name"] == PRODUCT_DATA["name"]
        assert data["seller_id"] == seller.id

        result = await test_session.execute(select(Product).where(Product.id == data["id"]))
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_create_product_with_category_and_attributes(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-create-rich@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)

        category_id = await create_category(client, "Test Category", "test-category")

        payload = {
            "name": "Rich Product",
            "description": "Product with categories and attributes",
            "article": "ART-RICH",
            "code": "CODE-RICH",
            "category_ids": [category_id],
            "attributes": [
                {"slug": "weight", "name": "Вес", "value": "500 г"},
                {"slug": "brand", "name": "Бренд", "value": "Test"},
            ],
        }

        created = await create_product_via_api(client, token, payload)
        assert category_id in created["category_ids"]
        assert len(created["attributes"]) == 2

    @pytest.mark.asyncio
    async def test_create_product_without_auth_returns_401(self, client, mock_settings, mock_image_manager_init):
        response = await client.post("/products", json=PRODUCT_DATA)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_product_not_seller_returns_403(self, client, mock_settings, mock_image_manager_init):
        token = await register_user_and_get_token(client, "product-not-seller@example.com")

        response = await client.post(
            "/products",
            json=PRODUCT_DATA,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetProductsAPI:
    @pytest.mark.asyncio
    async def test_get_product_by_id_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-get@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)
        created = await create_product_via_api(client, token)

        response = await client.get(f"/products/{created['id']}")
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert data["id"] == created["id"]
        assert data["name"] == PRODUCT_DATA["name"]

    @pytest.mark.asyncio
    async def test_get_product_not_found_returns_404(self, client, mock_settings, mock_image_manager_init):
        response = await client.get("/products/999999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_products_list_and_filters(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-list@example.com"
        token = await register_user_and_get_token(client, email)
        seller = await create_seller_in_db(test_session, email)

        category_id = await create_category(client, "Filter Category", "filter-category")

        await create_product_via_api(
            client,
            token,
            {
                "name": "First Product",
                "description": "Desc 1",
                "article": "A-1",
                "code": "C-1",
                "category_ids": [category_id],
                "attributes": [],
            },
        )
        await create_product_via_api(
            client,
            token,
            {
                "name": "Second Product",
                "description": "Desc 2",
                "article": "A-2",
                "code": "C-2",
                "category_ids": [],
                "attributes": [],
            },
        )

        response = await client.get(f"/products?page=1&page_size=10&seller_id={seller.id}")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "data" in body and "pagination" in body
        assert body["pagination"]["page"] == 1
        assert len(body["data"]) >= 2

        filtered = await client.get(f"/products?category_ids={category_id}")
        assert filtered.status_code == status.HTTP_200_OK
        filtered_body = filtered.json()
        assert len(filtered_body["data"]) >= 1

    @pytest.mark.asyncio
    async def test_get_products_by_ids_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-by-ids@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)

        p1 = await create_product_via_api(client, token, {**PRODUCT_DATA, "name": "ByIds-1", "article": "IDS-1"})
        p2 = await create_product_via_api(client, token, {**PRODUCT_DATA, "name": "ByIds-2", "article": "IDS-2"})

        response = await client.post("/products/by-ids", json=[p1["id"], p2["id"]])
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert len(data) == 2
        assert {item["id"] for item in data} == {p1["id"], p2["id"]}


class TestUpdateDeleteProductAPI:
    @pytest.mark.asyncio
    async def test_update_product_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-update@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)
        created = await create_product_via_api(client, token)

        response = await client.put(
            f"/products/{created['id']}",
            json=PRODUCT_UPDATE_DATA,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert data["name"] == PRODUCT_UPDATE_DATA["name"]

    @pytest.mark.asyncio
    async def test_update_product_wrong_owner_returns_403(self, client, test_session, mock_settings, mock_image_manager_init):
        owner_email = "product-owner@example.com"
        owner_token = await register_user_and_get_token(client, owner_email)
        await create_seller_in_db(test_session, owner_email)
        created = await create_product_via_api(client, owner_token)

        other_email = "product-other@example.com"
        other_token = await register_user_and_get_token(client, other_email)
        await create_seller_in_db(test_session, other_email)

        response = await client.put(
            f"/products/{created['id']}",
            json=PRODUCT_UPDATE_DATA,
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_product_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-delete@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)
        created = await create_product_via_api(client, token)

        response = await client.delete(
            f"/products/{created['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        result = await test_session.execute(select(Product).where(Product.id == created["id"]))
        assert result.scalar_one_or_none() is None


class TestProductsSummaryAPI:
    @pytest.mark.asyncio
    async def test_products_summary_success(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-summary@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)

        await create_product_via_api(client, token, {**PRODUCT_DATA, "name": "Summary-1", "article": "S-1"})
        await create_product_via_api(client, token, {**PRODUCT_DATA, "name": "Summary-2", "article": "S-2"})

        response = await client.get("/products/summary/stats")
        assert response.status_code == status.HTTP_200_OK

        data = get_response_data(response.json())
        assert data["total_products"] >= 2
        assert data["total_sellers"] >= 1


class TestProductAttributesAPI:
    @pytest.mark.asyncio
    async def test_product_attribute_crud_flow(self, client, test_session, mock_settings, mock_image_manager_init):
        email = "product-attr@example.com"
        token = await register_user_and_get_token(client, email)
        await create_seller_in_db(test_session, email)
        product = await create_product_via_api(client, token)

        create_attr_response = await client.post(
            "/products/attributes",
            json={
                "product_id": product["id"],
                "slug": "color",
                "name": "Цвет",
                "value": "Красный",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_attr_response.status_code == status.HTTP_201_CREATED
        created_attr = get_response_data(create_attr_response.json())

        get_attr_response = await client.get(f"/products/attributes/{created_attr['id']}")
        assert get_attr_response.status_code == status.HTTP_200_OK

        get_by_slug_response = await client.get(f"/products/{product['id']}/attributes/color")
        assert get_by_slug_response.status_code == status.HTTP_200_OK

        update_attr_response = await client.put(
            f"/products/attributes/{created_attr['id']}",
            json={"name": "Обновленный цвет", "value": "Синий"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_attr_response.status_code == status.HTTP_200_OK
        updated_attr = get_response_data(update_attr_response.json())
        assert updated_attr["value"] == "Синий"

        delete_attr_response = await client.delete(
            f"/products/attributes/{created_attr['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_attr_response.status_code == status.HTTP_204_NO_CONTENT
