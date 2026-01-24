from sqladmin import ModelView

import app.offers.models as offers_models


class OfferAdmin(ModelView, model=offers_models.Offer):
    pass


class PricingStrategyAdmin(ModelView, model=offers_models.PricingStrategy):
    pass


class PricingStrategyStepAdmin(ModelView, model=offers_models.PricingStrategyStep):
    pass
