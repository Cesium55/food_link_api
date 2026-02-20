from typing import List

from fastapi import Request
from sqladmin import ModelView, action
from sqlalchemy import select, update

from app.admin.common import action_auto_returner, action_with_ids, logger
from app.auth.service import AuthService
from app.sellers import schemas as seller_schemas
from app.sellers.service import SellersService
from app.support.service import SupportService

import app.sellers.models as sellers_models


class SellerAdmin(ModelView, model=sellers_models.Seller):
    column_list = ["id", "full_name", ]


class SellerImageAdmin(ModelView, model=sellers_models.SellerImage):
    pass


class SellerRegistrationRequestAdmin(ModelView, model=sellers_models.SellerRegistrationRequest):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sellers_service = SellersService()
        self.auth_service = AuthService()
        self.support_service = SupportService()

    column_list = [
        "id",
        "user_id",
        "full_name",
        "short_name",
        "inn",
        "is_IP",
        "ogrn",
        "status",
        "terms_accepted",
        "created_at",
        "updated_at",
    ]

    @staticmethod
    def _has_required_fields(
        req: sellers_models.SellerRegistrationRequest,
    ) -> bool:
        return all(
            [
                req.full_name is not None and req.full_name.strip() != "",
                req.short_name is not None and req.short_name.strip() != "",
                req.inn is not None and req.inn.strip() != "",
                req.is_IP is not None,
                req.ogrn is not None and req.ogrn.strip() != "",
                req.terms_accepted,
            ]
        )

    @action(
        name="approve_requests",
        label="Одобрить заявки",
        confirmation_message="Подтвердить одобрение выбранных заявок?",
    )
    @action_auto_returner
    @action_with_ids
    async def approve_requests(self, request: Request, ids: List[int]):
        if not ids:
            return

        async with self.session_maker() as session:
            for req_id in ids:
                result = await session.execute(
                    select(sellers_models.SellerRegistrationRequest).where(
                        sellers_models.SellerRegistrationRequest.id == req_id
                    )
                )
                registration_request = result.scalar_one_or_none()
                if registration_request is None:
                    logger.warning("Registration request not found", extra={"request_id": req_id})
                    continue

                if registration_request.status == seller_schemas.SellerRegistrationRequestStatus.APPROVED.value:
                    continue

                if not self._has_required_fields(registration_request):
                    logger.warning(
                        "Registration request is incomplete; skipping approval",
                        extra={"request_id": req_id, "user_id": registration_request.user_id},
                    )
                    continue

                existing_seller = await self.sellers_service.get_seller_by_master_id(
                    session, registration_request.user_id
                )
                if existing_seller is not None:
                    await session.execute(
                        update(sellers_models.SellerRegistrationRequest)
                        .where(sellers_models.SellerRegistrationRequest.id == req_id)
                        .values(
                            status=seller_schemas.SellerRegistrationRequestStatus.APPROVED.value
                        )
                    )
                    continue

                user = await self.auth_service.get_user(
                    session, registration_request.user_id
                )
                if user is None or not user.email:
                    logger.warning(
                        "Cannot approve request: user/email missing",
                        extra={"request_id": req_id, "user_id": registration_request.user_id},
                    )
                    continue

                seller_create_data = seller_schemas.SellerCreate(
                    full_name=registration_request.full_name,
                    short_name=registration_request.short_name,
                    description=registration_request.description,
                    inn=registration_request.inn,
                    is_IP=registration_request.is_IP,
                    ogrn=registration_request.ogrn,
                )

                await self.sellers_service.create_seller(
                    session=session,
                    schema=seller_create_data,
                    user_id=registration_request.user_id,
                    email=user.email,
                )
                await self.auth_service.update_user_is_seller(
                    session, registration_request.user_id, True
                )
                await session.execute(
                    update(sellers_models.SellerRegistrationRequest)
                    .where(sellers_models.SellerRegistrationRequest.id == req_id)
                    .values(
                        status=seller_schemas.SellerRegistrationRequestStatus.APPROVED.value
                    )
                )

                await self.support_service.create_master_chat_message(
                    session=session,
                    user_id=registration_request.user_id,
                    sender_type="system",
                    message_text="Ваша заявка на регистрацию продавца была одобрена.",
                )

            await session.commit()
