from sqladmin import ModelView, BaseView, expose
from sqladmin.filters import AllUniqueStringValuesFilter
import app.purchases.models as purchases_models
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from app.offers.models import Offer
from app.purchases.models import Purchase, PurchaseOffer, PurchaseOfferResult
from app.sellers.models import Seller
from app.products.models import Product
from logger import hard_log


class PurchaseAdmin(ModelView, model=purchases_models.Purchase):
    icon = "fa-solid fa-cart-shopping"

    column_list = ["id", "user_id", "status", "total_cost", "sellers"]
    column_filters = [AllUniqueStringValuesFilter("status")]

    async def list(self, request: Request):
        pagination = await super().list(request)
        rows = pagination.rows
        if not rows:
            return pagination
        

        async with self.session_maker() as session:
            for i in range(len(pagination.rows)):
                pagination.rows[i] = (
                    await session.execute(
                        select(Purchase)
                        .options(
                            selectinload(Purchase.purchase_offers)
                            .selectinload(PurchaseOffer.offer)
                            .selectinload(Offer.product)
                            .selectinload(Product.seller)
                        )
                        .filter(Purchase.id == pagination.rows[i].id)
                    )
                ).scalars().one()
                print(pagination.rows[i].purchase_offers[0].offer.product.seller.short_name)
                

        return pagination
    


    column_formatters = {"sellers": lambda o, p: {o.purchase_offers[i].offer.product.seller.short_name for i in range(len(o.purchase_offers))}}



class PurchaseOfferAdmin(ModelView, model=purchases_models.PurchaseOffer):
    pass


class PurchaseOfferResultAdmin(ModelView, model=purchases_models.PurchaseOfferResult):
    pass
