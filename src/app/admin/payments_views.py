from typing import List

from fastapi import Request
from sqladmin import ModelView, action
from app.payments.manager import PaymentsManager

import app.payments.models as payments_models

from app.admin.common import (
    action_auto_returner,
    action_with_ids,
    json_to_html,
    logger,
    yookassa_client,
)


class UserPaymentAdmin(ModelView, model=payments_models.UserPayment):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.payments_manager = PaymentsManager()

    column_list = [
        "id",
        "purchase_id",
        "purchase.user.id",
        "purchase",
        "yookassa_payment_id",
        "status",
        "yookassa_status",
        "yookassa_data_formatted",
    ]

    async def list(self, request: Request):
        pagination = await super().list(request)
        rows = pagination.rows
        if not rows:
            return pagination

        logger.info(f"UserPaymentAdmin.list: processing {len(rows)} payment(s)")
        for obj in rows:
            if not obj.yookassa_payment_id:
                obj._yookassa_status = ""
                continue
            yookassa_data = await yookassa_client.get_payment(
                obj.yookassa_payment_id
            )
            obj._yookassa_status = yookassa_data.get("status")
            obj._yookassa_data = yookassa_data

        return pagination

    column_formatters = {
        "yookassa_status": lambda o, p: getattr(o, "_yookassa_status", 0),
        "yookassa_data_formatted": lambda m, a: json_to_html(getattr(m, "_yookassa_data", {})),
    }


    @action(
        name="status_sync",
        label="Sync status with yookassa",
    )
    @action_auto_returner
    @action_with_ids
    async def status_sync(self, request: Request, ids: List[int]):
        async with self.session_maker() as session:
            results = await self.payments_manager.sync_batch_status(session, ids)
            
            # Log results
            logger.info(
                f"Status sync completed: "
                f"{len(results['success'])} success, "
                f"{len(results['failed'])} failed, "
                f"{len(results['skipped'])} skipped"
            )
            
            return results
