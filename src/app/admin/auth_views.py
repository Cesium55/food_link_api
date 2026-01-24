from fastapi import Request
from sqladmin import ModelView, action
from sqlalchemy import update

import app.auth.models as auth_models

from app.admin.common import action_auto_returner


class UserAdmin(ModelView, model=auth_models.User):
    @action(
        name="phone_verify",
        label="Отметить верефицированным по телефону",
        confirmation_message="Вы уверены?",
    )
    @action_auto_returner
    async def phone_verify(self, request: Request):
        ids = request.query_params.get("pks")
        if not ids:
            return
        ids = list(map(int, ids.split(",")))
        stmt = (
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(phone_verified=True)
        )
        session = self.session_maker()
        await session.execute(stmt)
        await session.commit()

    @action(
        name="phone_deverify",
        label="Отметить не верефицированным по телефону",
        confirmation_message="Вы уверены?",
    )
    @action_auto_returner
    async def phone_deverify(self, request: Request):
        ids = request.query_params.get("pks")
        if not ids:
            return
        ids = list(map(int, ids.split(",")))
        stmt = (
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(phone_verified=False)
        )
        session = self.session_maker()
        await session.execute(stmt)
        await session.commit()

    column_list = ["id", "email", "is_seller", "phone_verified"]
    column_details_exclude_list = ["password_hash", "firebase_token"]

    def email_formatter(obj, p):
        if not obj.email:
            return obj.email
        e_splitted = obj.email.split("@")
        if len(e_splitted[0]) < 3:
            return obj.email
        return (
            e_splitted[0][:2]
            + "*" * (len(e_splitted[0]) - 2)
            + "@"
            + e_splitted[1]
        )

    column_formatters = {
        "email": email_formatter,
    }


class RefreshTokenAdmin(ModelView, model=auth_models.RefreshToken):
    pass
