from sqladmin import ModelView

import app.shop_points.models as shop_points_models


class ShopPointAdmin(ModelView, model=shop_points_models.ShopPoint):
    pass


class ShopPointImageAdmin(ModelView, model=shop_points_models.ShopPointImage):
    pass
