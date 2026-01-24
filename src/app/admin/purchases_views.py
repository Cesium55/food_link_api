from sqladmin import ModelView

import app.purchases.models as purchases_models


class PurchaseAdmin(ModelView, model=purchases_models.Purchase):
    pass


class PurchaseOfferAdmin(ModelView, model=purchases_models.PurchaseOffer):
    pass


class PurchaseOfferResultAdmin(
    ModelView, model=purchases_models.PurchaseOfferResult
):
    pass
